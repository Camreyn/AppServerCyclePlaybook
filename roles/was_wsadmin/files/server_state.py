# -*- coding: utf-8 -*-
# =============================================================================
# server_state.py
# Query the runtime state of a WebSphere application server
#
# Usage:
#   wsadmin.sh -lang jython -f server_state.py --node Node01 --server AppSrv01
#
# Output:
#   Node01/AppSrv01=STARTED
#   STATE:STARTED
#
# Possible states: STARTED, RUNNING, STOPPED, NOT_FOUND, UNKNOWN
# =============================================================================
import sys


def _arg(name, default=None):
    """Get a named argument value from sys.argv."""
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


NODE = _arg("--node")
SERVER = _arg("--server")


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


def main():
    if not NODE or not SERVER:
        raise Exception("Usage: server_state.py --node Node01 --server AppSrv01")

    st = _state(NODE, SERVER)
    print("%s/%s=%s" % (NODE, SERVER, st))
    print("STATE:%s" % st)


try:
    main()
except:
    t, v = sys.exc_info()[:2]
    sys.stderr.write("ERROR: %s\n" % v)
    sys.exit(2)
