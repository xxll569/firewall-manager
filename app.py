"""
app.py — macOS 防火墙管理工具
Run: python app.py
Open: http://127.0.0.1:5001
"""

import os
from flask import Flask, render_template, request, jsonify
import firewall_core as fw

app = Flask(__name__)
app.secret_key = os.urandom(24)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    status = fw.check_pf_status()
    rules  = fw.get_rules()
    return render_template("index.html",
                           pf_enabled=status.get("enabled", False),
                           pf_status=status.get("status", "Unknown"),
                           rules=rules,
                           common_ports=fw.COMMON_PORTS)


# ---------------------------------------------------------------------------
# API — pf status
# ---------------------------------------------------------------------------

@app.route("/api/status")
def api_status():
    return jsonify(fw.check_pf_status())


@app.route("/api/enable", methods=["POST"])
def api_enable():
    return jsonify(fw.enable_pf())


@app.route("/api/disable", methods=["POST"])
def api_disable():
    return jsonify(fw.disable_pf())


# ---------------------------------------------------------------------------
# API — rules
# ---------------------------------------------------------------------------

@app.route("/api/rules")
def api_rules():
    rules  = fw.get_rules()
    status = fw.check_pf_status()
    raw    = fw.get_raw_info()
    return jsonify({
        "success":    True,
        "rules":      rules,
        "count":      len(rules),
        "pf_enabled": status.get("enabled", False),
        "pf_status":  status.get("status", "Unknown"),
        "pf_error":   status.get("error", ""),
        "raw":        raw,
    })


@app.route("/api/rules/add", methods=["POST"])
def api_add():
    d         = request.get_json() or {}
    port      = d.get("port")
    protocol  = d.get("protocol", "tcp")
    direction = d.get("direction", "in")
    source    = d.get("source", "any")

    if not port:
        return jsonify({"success": False, "message": "端口号不能为空"})
    try:
        port = int(port)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        return jsonify({"success": False, "message": "端口号无效（1–65535）"})

    return jsonify(fw.add_rule(port, protocol, direction, source))


@app.route("/api/rules/remove", methods=["POST"])
def api_remove():
    d        = request.get_json() or {}
    port     = d.get("port")
    protocol = d.get("protocol", "tcp")
    if not port:
        return jsonify({"success": False, "message": "端口号不能为空"})
    return jsonify(fw.remove_rule(int(port), protocol))


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("  macOS 防火墙管理工具")
    print("  http://127.0.0.1:5001")
    print("=" * 50)
    s = fw.check_pf_status()
    print(f"  pf 状态: {s.get('status', 'Unknown')}")
    print(f"  Anchor:  {fw.ANCHOR_FILE}")
    print("=" * 50)
    app.run(debug=True, host="127.0.0.1", port=5001)
