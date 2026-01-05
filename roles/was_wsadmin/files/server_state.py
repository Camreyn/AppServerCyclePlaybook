# -*- coding: utf-8 -*-
import sys

def _arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default

NODE   = _arg("--node")
SERVER = _arg("--server")

def _server_mbean(node, server):
    query = "type=Server,node=%s,process=%s,*" % (node, server)
    return AdminControl.completeObjectName(query)

def main():
    if not NODE or not SERVER:
        raise Exception("Usage: server_state.py --node Node01 --server AppSrv01")

    mbean = _server_mbean(NODE, SERVER)
    if not mbean:
        print("%s/%s=NOT_FOUND" % (NODE, SERVER))
        return

    try:
        st = AdminControl.getAttribute(mbean, "state")
    except:
        st = "UNKNOWN"

    print("%s/%s=%s" % (NODE, SERVER, st))

try:
    main()
except:
    t, v = sys.exc_info()[:2]
    sys.stderr.write("ERROR: %s\n" % v)
    sys.exit(2)