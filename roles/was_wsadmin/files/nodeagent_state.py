# -*- coding: utf-8 -*-
# =============================================================================
# nodeagent_state.py
# Query the runtime state/readiness of a WebSphere nodeagent
#
# Usage:
#   wsadmin.sh -lang jython -f nodeagent_state.py --node Node01
#
# Output:
#   Node01/nodeagent=STARTED
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


def _nodeagent_mbean(node):
    """Get the MBean ObjectName for the nodeagent process on a node."""
    query = "type=Server,node=%s,process=nodeagent,*" % node
    return AdminControl.completeObjectName(query)


def _state(node):
    """Get the current state of the nodeagent."""
    mbean = _nodeagent_mbean(node)
    if not mbean:
        return "NOT_FOUND"
    try:
        return AdminControl.getAttribute(mbean, "state")
    except:
        return "UNKNOWN"


def main():
    if not NODE:
        raise Exception("Usage: nodeagent_state.py --node Node01")

    st = _state(NODE)
    print("%s/nodeagent=%s" % (NODE, st))
    print("STATE:%s" % st)


try:
    main()
except:
    t, v = sys.exc_info()[:2]
    sys.stderr.write("ERROR: %s\n" % v)
    sys.exit(2)
