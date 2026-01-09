# -*- coding: utf-8 -*-
import sys

def _args_after(flag):
    if flag not in sys.argv:
        return []
    idx = sys.argv.index(flag)
    return sys.argv[idx + 1:]

def _escape_json_string(s):
    if s is None:
        s = ""
    try:
        s = str(s)
    except:
        s = ""

    s = s.replace("\\", "\\\\")
    s = s.replace("\"", "\\\"")
    s = s.replace("\r", "\\r")
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    return s

def _json_value(v):
    if v is None:
        return "null"

    # bool is subclass of int in Python 2; check first
    try:
        if isinstance(v, bool):
            if v:
                return "true"
            return "false"
    except:
        pass

    try:
        if isinstance(v, (int, long)):
            return str(v)
    except:
        pass

    try:
        if isinstance(v, float):
            return str(v)
    except:
        pass

    return "\"" + _escape_json_string(v) + "\""

def _json_obj(d):
    parts = []
    keys = list(d.keys())
    keys.sort()
    i = 0
    while i < len(keys):
        k = keys[i]
        v = d[k]
        parts.append("\"" + _escape_json_string(k) + "\":" + _json_value(v))
        i += 1
    return "{" + ",".join(parts) + "}"

def _json_array_of_objects(objs):
    parts = []
    i = 0
    while i < len(objs):
        parts.append(_json_obj(objs[i]))
        i += 1
    return "[" + ",".join(parts) + "]"

def main():
    nodes = _args_after("--nodes")
    if not nodes:
        raise Exception("Usage: discover_targets.py --nodes Node01 Node02 ...")

    results = []

    for node in nodes:
        node_id = AdminConfig.getid("/Node:%s/" % node)
        if not node_id:
            results.append({"node": node, "error": "NODE_NOT_FOUND"})
            continue

        servers = AdminConfig.list("Server", node_id)
        if not servers:
            continue

        for s in servers.splitlines():
            try:
                stype = AdminConfig.showAttribute(s, "serverType")
            except:
                stype = ""

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
