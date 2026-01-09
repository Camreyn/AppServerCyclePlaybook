# -*- coding: utf-8 -*-
import sys

def _args_after(flag):
    if flag not in sys.argv:
        return []
    idx = sys.argv.index(flag)
    return sys.argv[idx + 1 :]

def _escape_json_string(s):
    """
    Minimal JSON string escaper for wsadmin/Jython environments where json module
    may not exist. Produces valid JSON string content.
    """
    if s is None:
        s = ""
    # Ensure we're working with a plain string type
    try:
        s = str(s)
    except:
        s = ""

    # Escape backslash, quotes, and control characters
    s = s.replace("\\", "\\\\")
    s = s.replace("\"", "\\\"")
    s = s.replace("\r", "\\r")
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    return s

def _json_obj(d):
    """
    Convert a flat dict of string keys -> primitive values into a JSON object string.
    Values supported: None, bool, int/long, float, str.
    """
    parts = []
    # Stable ordering isn't required, but it helps with debugging.
    keys = list(d.keys())
    keys.sort()
    for k in keys:
        v = d[k]
        k_s = "\"" + _escape_json_string(k) + "\""

        if v is None:
            v_s = "null"
        elif isinstance(v, bool):
            v_s = "true" if v else "false"
        elif isinstance(v, (int, long)):
            v_s = str(v)
        elif isinstance(v, float):
            # Avoid scientific notation surprises; plain str is usually OK here.
            v_s = str(v)
        else:
            v_s = "\"" + _escape_json_string(v) + "\""

        parts.append(k_s + ":" + v_s)
    return "{" + ",".join(parts) + "}"

def _json_array_of_objects(objs):
    return "[" + ",".join([_json_obj(o) for o in objs]) + "]"

def main():
    nodes = _args_after("--nodes")
    if not nodes:
        raise Exception("Usage: discover_targets.py --nodes Node01 Node02 ...")

    results = []

    for node in nodes:
        node_id = AdminConfig.getid("/Node:%s/" % node)
        if not node_id:
            # Node not found - still report it so caller can decide
            results.append({
                "node": node,
                "error": "NODE_NOT_FOUND"
            })
            continue

        servers = AdminConfig.list("Server", node_id)
        if not servers:
            continue

        for s in servers.splitlines():
            try:
                stype = AdminConfig.showAttribute(s, "serverType")
            except:
                stype = ""

            # Only application servers. This excludes NODE_AGENT and DEPLOYMENT_MANAGER.
            if stype != "APPLICATION_SERVER":
                continue

            try:
                sname = AdminConfig.showAttribute(s, "name")
            except:
                sname = ""

            results.append({
                "node": node,
                "server": sname,
                "serverType": stype
            })

    # Emit JSON only (no dependency on json module)
    # Expected by Ansible: {"targets": [ ... ]}
    out = "{"
    out += "\"targets\":" + _json_array_of_objects(results)
    out += "}"

    sys.stdout.write(out)
    sys.stdout.flush()

try:
    main()
except:
    t, v = sys.exc_info()[:2]
    sys.stderr.write("ERROR: %s\n" % v)
    sys.exit(2)
