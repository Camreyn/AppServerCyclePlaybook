# -*- coding: utf-8 -*-
# =============================================================================
# discover_targets.py
# Discovers APPLICATION_SERVER instances for specified WebSphere nodes
#
# Usage:
#   wsadmin.sh -lang jython -f discover_targets.py --nodes Node01 Node02 ...
#
# Output:
#   JSON object on the last line of stdout:
#   {"targets":[{"node":"Node01","server":"AppSrv01","serverType":"APPLICATION_SERVER"}, ...]}
#
# Nodes not found are reported with:
#   {"node":"NodeX","error":"NODE_NOT_FOUND"}
#
# Nodes with no application servers are reported with:
#   {"node":"NodeX","warning":"NO_APPLICATION_SERVERS_FOUND"}
# =============================================================================
import sys


def _args_after(flag):
    """Return all arguments after the specified flag."""
    if flag not in sys.argv:
        return []
    idx = sys.argv.index(flag)
    return sys.argv[idx + 1:]


def _escape_json_string(s):
    """Escape a string for JSON output."""
    if s is None:
        s = ""
    try:
        s = str(s)
    except Exception:
        s = ""

    s = s.replace("\\", "\\\\")
    s = s.replace("\"", "\\\"")
    s = s.replace("\r", "\\r")
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    return s


def _json_value(v):
    """Convert a Python value to JSON representation."""
    if v is None:
        return "null"

    try:
        if isinstance(v, bool):
            if v:
                return "true"
            else:
                return "false"
    except Exception:
        pass

    try:
        if isinstance(v, (int, long)):
            return str(v)
    except Exception:
        pass

    try:
        if isinstance(v, float):
            return str(v)
    except Exception:
        pass

    return "\"" + _escape_json_string(v) + "\""


def _json_obj(d):
    """Convert a dictionary to a JSON object string."""
    parts = []
    keys = list(d.keys())
    keys.sort()
    i = 0
    while i < len(keys):
        k = keys[i]
        v = d[k]
        parts.append("\"" + _escape_json_string(k) + "\":" + _json_value(v))
        i = i + 1
    return "{" + ",".join(parts) + "}"


def _json_array_of_objects(objs):
    """Convert a list of dictionaries to a JSON array string."""
    parts = []
    i = 0
    while i < len(objs):
        parts.append(_json_obj(objs[i]))
        i = i + 1
    return "[" + ",".join(parts) + "]"


def _safe_show_attribute(config_id, attr_name, default_value):
    """Best-effort attribute lookup."""
    try:
        value = AdminConfig.showAttribute(config_id, attr_name)
        if value is None:
            return default_value
        return value
    except Exception:
        return default_value


def main():
    nodes = _args_after("--nodes")
    if not nodes:
        raise Exception("Usage: discover_targets.py --nodes Node01 Node02 ...")

    results = []

    for node in nodes:
        node_id = AdminConfig.getid("/Node:%s/" % node)
        if not node_id:
            results.append({
                "node": node,
                "error": "NODE_NOT_FOUND"
            })
            continue

        servers = AdminConfig.list("Server", node_id)
        if not servers:
            results.append({
                "node": node,
                "warning": "NO_APPLICATION_SERVERS_FOUND"
            })
            continue

        node_appserver_count = 0

        for server_cfg in servers.splitlines():
            stype = _safe_show_attribute(server_cfg, "serverType", "")
            if stype != "APPLICATION_SERVER":
                continue

            sname = _safe_show_attribute(server_cfg, "name", "")
            if not sname:
                continue

            results.append({
                "node": node,
                "server": sname,
                "serverType": stype
            })
            node_appserver_count = node_appserver_count + 1

        if node_appserver_count == 0:
            results.append({
                "node": node,
                "warning": "NO_APPLICATION_SERVERS_FOUND"
            })

    out = "{"
    out = out + "\"targets\":" + _json_array_of_objects(results)
    out = out + "}"

    sys.stdout.flush()
    sys.stdout.write("\n")
    sys.stdout.write(out)
    sys.stdout.write("\n")
    sys.stdout.flush()


try:
    main()
except Exception:
    t, v = sys.exc_info()[:2]
    sys.stderr.write("ERROR: %s\n" % v)
    sys.exit(2)
