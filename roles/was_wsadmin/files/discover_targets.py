# -*- coding: utf-8 -*-
import sys
import json

def _args_after(flag):
    if flag not in sys.argv:
        return []
    idx = sys.argv.index(flag)
    return sys.argv[idx+1:]

def _as_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]

def _name(attr_list, key):
    # AdminConfig.showAttribute returns strings, not always safe; we use showAttribute directly.
    try:
        return AdminConfig.showAttribute(attr_list, key)
    except:
        return ""

def main():
    nodes = _args_after("--nodes")
    if not nodes:
        raise Exception("Usage: discover_targets.py --nodes Node01 Node02 ...")

    results = []
    for node in nodes:
        node_id = AdminConfig.getid("/Node:%s/" % node)
        if not node_id:
            # node not found - still report it so caller can decide
            results.append({"node": node, "error": "NODE_NOT_FOUND"})
            continue

        servers = AdminConfig.list("Server", node_id)
        if not servers:
            continue

        for s in servers.splitlines():
            stype = AdminConfig.showAttribute(s, "serverType")
            # Only application servers. This excludes NODE_AGENT and DEPLOYMENT_MANAGER.
            if stype != "APPLICATION_SERVER":
                continue

            sname = AdminConfig.showAttribute(s, "name")
            # Some environments have "utility" appservers; caller can exclude by regex later if desired.
            results.append({
                "node": node,
                "server": sname,
                "serverType": stype
            })

    # Emit JSON only (easy for Ansible from_json)
    sys.stdout.write(json.dumps({"targets": results}))
    sys.stdout.flush()

try:
    main()
except:
    t, v = sys.exc_info()[:2]
    sys.stderr.write("ERROR: %s\n" % v)
    sys.exit(2)