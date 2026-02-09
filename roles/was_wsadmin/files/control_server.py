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
    "cannot be reached",
    "failed to stop",
)

def _log(msg):
    """Write a log message to stdout."""
    sys.stdout.write("LOG: %s\n" % msg)
    sys.stdout.flush()

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
    _log("Entering _wait_for, looking for states: %s" % str(desired_states))
    start = time.time()
    attempts = 0
    while True:
        attempts = attempts + 1
        _log("Attempt %d: checking state..." % attempts)
        try:
            st = _state(node, server)
            _log("Attempt %d: state = %s" % (attempts, st))
        except:
            st = "ERROR_CHECKING"
            _log("Attempt %d: exception checking state, using ERROR_CHECKING" % attempts)
        
        if st in desired_states:
            _log("Reached state %s after %d attempts" % (st, attempts))
            return st
        
        elapsed = time.time() - start
        _log("Attempt %d: elapsed = %d seconds" % (attempts, int(elapsed)))
        
        if elapsed > TIMEOUT:
            raise Exception(
                "Timed out after %d seconds waiting for %s/%s to reach %s (last=%s, attempts=%d)" %
                (int(elapsed), node, server, ",".join(desired_states), st, attempts)
            )
        
        _log("Attempt %d: sleeping %d seconds..." % (attempts, DELAY))
        time.sleep(DELAY)

def _is_already_down_exception(exc):
    """Check if an exception indicates the server is already stopped."""
    msg = ""
    if exc is not None:
        try:
            msg = str(exc)
        except:
            try:
                msg = repr(exc)
            except:
                msg = ""
    
    for s in _ALREADY_DOWN_SUBSTRINGS:
        if s in msg:
            return 1
    return 0

def _get_exception_message(exc):
    """Get a useful message from an exception, handling Jython quirks."""
    msg = ""
    
    # Try various ways to get the exception message
    try:
        msg = str(exc)
    except:
        pass
    
    if not msg or msg == "true" or msg == "false":
        try:
            msg = repr(exc)
        except:
            pass
    
    if not msg or msg == "true" or msg == "false":
        try:
            msg = exc.getMessage()
        except:
            pass
    
    if not msg or msg == "true" or msg == "false":
        try:
            if exc.args:
                msg = exc.args[0]
            else:
                msg = "unknown"
        except:
            pass
    
    if not msg:
        msg = "Exception occurred but no message available"
    
    return msg

def main():
    if not ACTION or not NODE or not SERVER:
        raise Exception(
            "Usage: control_server.py --action start|stop --node Node01 --server AppSrv01 "
            "[--timeout N --delay N]"
        )

    _log("Action=%s Node=%s Server=%s Timeout=%d Delay=%d" % (ACTION, NODE, SERVER, TIMEOUT, DELAY))

    before = _state(NODE, SERVER)
    _log("Current state: %s" % before)

    if ACTION == "stop":
        # Idempotent: if already stopped, do nothing
        if before == "STOPPED" or before == "NOT_FOUND":
            print("CHANGED:false")
            print("STATE:%s" % before)
            return

        _log("Attempting to stop server...")
        try:
            AdminControl.stopServer(SERVER, NODE)
            _log("stopServer command completed, waiting for state change...")
        except Exception, e:
            exc_msg = _get_exception_message(e)
            _log("stopServer raised exception: %s" % exc_msg)
            if _is_already_down_exception(e):
                print("CHANGED:false")
                print("STATE:%s" % before)
                return
            raise Exception("stopServer failed: %s" % exc_msg)

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

        _log("Attempting to start server...")
        try:
            AdminControl.startServer(SERVER, NODE)
            _log("startServer command completed, waiting for state change...")
        except Exception, e:
            exc_msg = _get_exception_message(e)
            raise Exception("startServer failed: %s" % exc_msg)

        after = _wait_for(NODE, SERVER, ("STARTED", "RUNNING"))
        print("CHANGED:true")
        print("STATE:%s->%s" % (before, after))
        return

    raise Exception("Unsupported action: %s" % ACTION)

try:
    main()
except:
    t, v = sys.exc_info()[:2]
    msg = _get_exception_message(v)
    sys.stderr.write("ERROR: %s\n" % msg)
    sys.stderr.write("EXCEPTION_TYPE: %s\n" % t)
    sys.exit(2)
