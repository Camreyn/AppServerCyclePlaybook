# -*- coding: utf-8 -*-
# =============================================================================
# control_server.py
# Start or stop a WebSphere application server with idempotent behavior
#
# Usage:
#   wsadmin.sh -lang jython -f control_server.py \
#     --action start|stop --node Node01 --server AppSrv01 \
#     [--timeout 600] [--delay 5]
#
# Output:
#   CHANGED:true|false
#   STATE:<before>-><after>  (or just STATE:<current> if no change)
#
# The script is idempotent:
#   - stop on already-stopped server: CHANGED:false
#   - start on already-running server: CHANGED:false
# =============================================================================
import sys
import time


def _arg(name, default=None):
    """Get a named argument value from sys.argv."""
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


ACTION = _arg("--action")
NODE = _arg("--node")
SERVER = _arg("--server")
TIMEOUT = int(_arg("--timeout", "600"))
DELAY = int(_arg("--delay", "5"))

# Substrings that indicate server is already down (for stop idempotency)
_ALREADY_DOWN_SUBSTRINGS = (
    "Unable to locate running server",
    "is not running",
    "not running",
)


def _server_mbean(node, server):
    """Get the MBean ObjectName for a server."""
    query = "type=Server,node=%s,process=%s,*" % (node, server)
    return AdminControl.completeObjectName(query)


def _state(node, server):
    """Get the current state of a server."""
    mbean = _server_mbean(node, server)
    if not mbean:
        return "NOT_FOUND"
    try:
        return AdminControl.getAttribute(mbean, "state")
    except:
        return "UNKNOWN"


def _wait_for(node, server, desired_states):
    """Wait for a server to reach one of the desired states."""
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
    """Check if an exception indicates the server is already stopped."""
    msg = ""
    if exc is not None:
        try:
            msg = str(exc)
        except:
            msg = ""
    else:
        msg = ""

    for s in _ALREADY_DOWN_SUBSTRINGS:
        if s in msg:
            return 1
    return 0


def main():
    if not ACTION or not NODE or not SERVER:
        raise Exception(
            "Usage: control_server.py --action start|stop --node Node01 --server AppSrv01 "
            "[--timeout N --delay N]"
        )

    before = _state(NODE, SERVER)

    if ACTION == "stop":
        # Idempotent: if already stopped, do nothing
        if before == "STOPPED" or before == "NOT_FOUND":
            print("CHANGED:false")
            print("STATE:%s" % before)
            return

        try:
            AdminControl.stopServer(SERVER, NODE)
        except Exception, e:
            if _is_already_down_exception(e):
                print("CHANGED:false")
                print("STATE:%s" % before)
                return
            raise

        after = _wait_for(NODE, SERVER, ("STOPPED", "NOT_FOUND"))
        print("CHANGED:true")
        print("STATE:%s->%s" % (before, after))
        return

    if ACTION == "start":
        # Idempotent: if already running, do nothing
        if before == "STARTED" or before == "RUNNING":
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
