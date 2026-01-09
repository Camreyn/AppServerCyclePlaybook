# -*- coding: utf-8 -*-
#
# control_server.py
#
# wsadmin / Jython-safe control script for starting/stopping application servers.
# Designed to be:
# - Portable across WAS / Portal / BAW tiers
# - Idempotent (stop on an already-down server is not an error)
# - Free of nonessential stdlib dependencies (keeps compatibility high)
#
import sys
import time

def _arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default

ACTION  = _arg("--action")
NODE    = _arg("--node")
SERVER  = _arg("--server")
TIMEOUT = int(_arg("--timeout", "600"))
DELAY   = int(_arg("--delay", "5"))

# Common wsadmin/Jython error messages that effectively mean "already stopped"
_ALREADY_DOWN_SUBSTRINGS = (
    "Unable to locate running server",
    "is not running",
    "not running",
)

def _server_mbean(node, server):
    # For application servers
    query = "type=Server,node=%s,process=%s,*" % (node, server)
    return AdminControl.completeObjectName(query)

def _state(node, server):
    """
    Returns one of: RUNNING/STARTED/STOPPED/NOT_FOUND/UNKNOWN.
    NOT_FOUND is common when a server process is not present / not registered as running.
    """
    mbean = _server_mbean(node, server)
    if not mbean:
        return "NOT_FOUND"
    try:
        return AdminControl.getAttribute(mbean, "state")
    except:
        return "UNKNOWN"

def _wait_for(node, server, desired_states):
    start = time.time()
    while True:
        st = _state(node, server)
        if st in desired_states:
            return st
        if (time.time() - start) > TIMEOUT:
            raise Exception(
                "Timed out waiting for %s/%s to reach %s (last=%s)" %
                (node, server, ",".join(desired_states), st)
            )
        time.sleep(DELAY)

def _is_already_down_exception(exc):
    msg = str(exc) if exc is not None else ""
    for s in _ALREADY_DOWN_SUBSTRINGS:
        if s in msg:
            return True
    return False

def main():
    if not ACTION or not NODE or not SERVER:
        raise Exception(
            "Usage: control_server.py --action start|stop --node Node01 --server AppSrv01 "
            "[--timeout N --delay N]"
        )

    before = _state(NODE, SERVER)

    if ACTION == "stop":
        # Idempotency: STOPPED or NOT_FOUND both mean “already down enough”.
        if before in ("STOPPED", "NOT_FOUND"):
            print("CHANGED:false")
            print("STATE:%s" % before)
            return

        try:
            AdminControl.stopServer(SERVER, NODE)
        except Exception as e:
            # If stop fails because it's already not running, treat as success (idempotent).
            if _is_already_down_exception(e):
                print("CHANGED:false")
                print("STATE:%s" % before)
                return
            raise

        # After stopping, state may become STOPPED or disappear (NOT_FOUND) depending on platform/config.
        after = _wait_for(NODE, SERVER, ("STOPPED", "NOT_FOUND"))
        print("CHANGED:true")
        print("STATE:%s->%s" % (before, after))
        return

    if ACTION == "start":
        # Idempotency: treat both RUNNING and STARTED as already up.
        if before in ("STARTED", "RUNNING"):
            print("CHANGED:false")
            print("STATE:%s" % before)
            return

        AdminControl.startServer(SERVER, NODE)
        after = _wait_for(NODE, SERVER, ("STARTED", "RUNNING"))
        print("CHANGED:true")
        print("STATE:%s->%s" % (before, after))
        return

    raise Exception("Unsupported action: %s" % ACTION)

try:
    main()
except:
    t, v = sys.exc_info()[:2]
    sys.stderr.write("ERROR: %s\n" % v)
    sys.exit(2)
