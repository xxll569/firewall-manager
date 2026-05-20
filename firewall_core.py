"""
firewall_core.py
macOS pf firewall management — standalone module.
Anchor: fw-manager  (/etc/pf.anchors/fw-manager)
"""

import os
import re
import subprocess
from typing import Dict, List

ANCHOR_NAME = "fw-manager"
ANCHOR_FILE = f"/etc/pf.anchors/{ANCHOR_NAME}"
PF_CONF     = "/etc/pf.conf"


# ---------------------------------------------------------------------------
# pf status
# ---------------------------------------------------------------------------

def check_pf_status() -> Dict:
    """Return pf enabled/disabled status and raw info string."""
    try:
        r = subprocess.run(["pfctl", "-s", "info"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            r = subprocess.run(["sudo", "-n", "pfctl", "-s", "info"],
                               capture_output=True, text=True, timeout=10)
        output = r.stdout + r.stderr
        enabled = "Status: Enabled" in output
        m = re.search(r"Status:\s*(\w+)", output)
        status = m.group(1) if m else ("Enabled" if enabled else "Unknown")
        return {"success": True, "enabled": enabled, "status": status,
                "info": r.stdout.strip() or r.stderr.strip()}
    except Exception as e:
        return {"success": False, "enabled": False, "status": "Unknown", "error": str(e)}


def enable_pf() -> Dict:
    try:
        r = subprocess.run(["sudo", "pfctl", "-e"],
                           capture_output=True, text=True, timeout=10)
        return {"success": r.returncode == 0,
                "message": "pf 防火墙已启用" if r.returncode == 0 else r.stderr.strip()}
    except Exception as e:
        return {"success": False, "message": str(e)}


def disable_pf() -> Dict:
    try:
        r = subprocess.run(["sudo", "pfctl", "-d"],
                           capture_output=True, text=True, timeout=10)
        return {"success": r.returncode == 0,
                "message": "pf 防火墙已禁用" if r.returncode == 0 else r.stderr.strip()}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_anchor() -> List[str]:
    if not os.path.exists(ANCHOR_FILE):
        return []
    with open(ANCHOR_FILE, "r") as fh:
        return fh.readlines()


def _write_anchor(lines: List[str]) -> Dict:
    content = "".join(lines)
    r = subprocess.run(["sudo", "tee", ANCHOR_FILE],
                       input=content, capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return {"success": False, "message": r.stderr.strip()}
    return {"success": True}


def _ensure_anchor_in_pf_conf() -> None:
    """Register anchor reference in /etc/pf.conf if not already there."""
    try:
        with open(PF_CONF, "r") as fh:
            content = fh.read()
        if ANCHOR_NAME not in content:
            ref = (f'\nanchor "{ANCHOR_NAME}"\n'
                   f'load anchor "{ANCHOR_NAME}" from "{ANCHOR_FILE}"\n')
            subprocess.run(["sudo", "tee", "-a", PF_CONF],
                           input=ref, capture_output=True, text=True, timeout=10)
    except Exception:
        pass


def _reload_pf() -> Dict:
    r = subprocess.run(["sudo", "pfctl", "-f", PF_CONF],
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return {"success": False, "message": r.stderr.strip()}
    return {"success": True}


# ---------------------------------------------------------------------------
# Rule CRUD
# ---------------------------------------------------------------------------

def add_rule(port: int, protocol: str = "tcp",
             direction: str = "in", source: str = "any") -> Dict:
    """Open port: add a pass rule to the anchor."""
    rule_body = f"pass {direction} proto {protocol} from {source} to any port {port}"
    rule_line = rule_body + "\n"

    lines = _read_anchor()
    if any(rule_body in l for l in lines):
        return {"success": True, "message": f"端口 {port}/{protocol} 规则已存在"}

    lines.append(rule_line)
    w = _write_anchor(lines)
    if not w["success"]:
        return w

    _ensure_anchor_in_pf_conf()
    r = _reload_pf()
    if not r["success"]:
        return {"success": False,
                "message": f"规则已写入，但重载 pf 失败：{r['message']}"}
    return {"success": True, "message": f"已开放端口 {port}/{protocol}"}


def remove_rule(port: int, protocol: str = "tcp") -> Dict:
    """Close port: remove matching rules from anchor."""
    lines = _read_anchor()
    pat = re.compile(rf'proto\s+{re.escape(protocol)}.*port\s+{port}\b')
    new_lines = [l for l in lines if not pat.search(l)]

    if len(new_lines) == len(lines):
        return {"success": False, "message": f"未找到端口 {port}/{protocol} 的规则"}

    w = _write_anchor(new_lines)
    if not w["success"]:
        return w
    r = _reload_pf()
    if not r["success"]:
        return {"success": False,
                "message": f"规则已删除，但重载 pf 失败：{r['message']}"}
    return {"success": True, "message": f"已关闭端口 {port}/{protocol}"}


def get_rules() -> List[Dict]:
    """Return structured rule list (live pfctl preferred, file fallback)."""
    rules: List[Dict] = []

    # Live pfctl
    try:
        r = subprocess.run(
            ["sudo", "-n", "pfctl", "-a", ANCHOR_NAME, "-s", "rules"],
            capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            for line in r.stdout.strip().splitlines():
                m = re.search(r'proto\s+(\w+).*port\s+=?\s*(\d+)', line)
                if m:
                    src_m = re.search(r'from\s+(\S+)', line)
                    rules.append({
                        "port":      int(m.group(2)),
                        "protocol":  m.group(1),
                        "direction": "in" if " in " in line else "out",
                        "source":    src_m.group(1) if src_m else "any",
                        "rule":      line.strip(),
                    })
            if rules:
                return rules
    except Exception:
        pass

    # Fallback: anchor file
    for line in _read_anchor():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.search(r'proto\s+(\w+).*port\s+(\d+)', line)
        if m:
            src_m = re.search(r'from\s+(\S+)', line)
            rules.append({
                "port":      int(m.group(2)),
                "protocol":  m.group(1),
                "direction": "in" if " in " in line else "out",
                "source":    src_m.group(1) if src_m else "any",
                "rule":      line,
            })
    return rules


def get_raw_info() -> Dict:
    """Diagnostic: raw anchor rules + pf status text."""
    try:
        r = subprocess.run(
            ["sudo", "-n", "pfctl", "-a", ANCHOR_NAME, "-s", "rules"],
            capture_output=True, text=True, timeout=10)
        anchor_rules = r.stdout.strip() or "(空)"
    except Exception as e:
        anchor_rules = f"(获取失败: {e})"

    status = check_pf_status()
    return {"anchor_rules": anchor_rules, "pf_info": status.get("info", "")}


# ---------------------------------------------------------------------------
# Preset port definitions
# ---------------------------------------------------------------------------

COMMON_PORTS = [
    {"port": 22,    "protocol": "tcp", "label": "SSH",        "icon": "terminal-fill"},
    {"port": 80,    "protocol": "tcp", "label": "HTTP",       "icon": "globe"},
    {"port": 443,   "protocol": "tcp", "label": "HTTPS",      "icon": "shield-lock-fill"},
    {"port": 3306,  "protocol": "tcp", "label": "MySQL",      "icon": "database-fill"},
    {"port": 5432,  "protocol": "tcp", "label": "PostgreSQL", "icon": "database-fill"},
    {"port": 6379,  "protocol": "tcp", "label": "Redis",      "icon": "lightning-fill"},
    {"port": 27017, "protocol": "tcp", "label": "MongoDB",    "icon": "database-fill"},
    {"port": 8080,  "protocol": "tcp", "label": "HTTP-ALT",   "icon": "globe2"},
    {"port": 8443,  "protocol": "tcp", "label": "HTTPS-ALT",  "icon": "shield-fill"},
    {"port": 53,    "protocol": "udp", "label": "DNS",        "icon": "diagram-3-fill"},
]
