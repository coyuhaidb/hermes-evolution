#!/home/rng/.hermes/hermes-agent/venv/bin/python3
"""Hermes 系统监控 — 异常实时告警"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.config import FEISHU_CHAT_ID, LARK_CLI, PROJECT_DIR

# 监控的服务列表
SERVICES = [
    ("hermes-gateway", "Hermes 消息网关"),
    ("hermes-dashboard", "Hermes 仪表盘"),
    ("hermes-web-ui", "Hermes Web 面板"),
    ("agentmemory", "持久化记忆服务"),
    ("wsl-keepalive", "WSL2 保活服务"),
]

# 状态文件（记录上次状态，仅状态变化时告警）
STATE_FILE = os.path.join(PROJECT_DIR, "data", "monitor_state.json")

# 阈值
DISK_WARN_PCT = 85       # 磁盘使用 > 85% 告警
MEM_WARN_PCT = 85        # 内存使用 > 85% 告警


def load_state():
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def check_services():
    """检查所有关键服务状态"""
    issues = []
    for svc, name in SERVICES:
        try:
            status = subprocess.run(
                ["systemctl", "is-active", svc],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
        except Exception:
            status = "unknown"
        issues.append((svc, name, status))
    return issues


def check_disk():
    """检查磁盘使用率"""
    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True, text=True, timeout=10,
        )
        line = result.stdout.strip().split("\n")[-1]
        parts = line.split()
        # 找百分比那列
        for p in parts:
            if p.endswith("%"):
                pct = int(p.rstrip("%"))
                used = parts[4] if len(parts) > 4 else parts[3]
                return pct, used
    except Exception:
        pass
    return 0, "?"


def check_memory():
    """检查内存使用率"""
    try:
        result = subprocess.run(
            ["free", "-m"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().split("\n")
        parts = lines[1].split()
        total = int(parts[1])
        available = int(parts[6]) if len(parts) > 6 else int(parts[3])
        used_pct = round((total - available) / total * 100)
        return used_pct, total, available
    except Exception:
        return 0, 0, 0


def build_alert(alerts):
    """组装告警消息"""
    now = datetime.now().strftime("%m/%d %H:%M")
    lines = [f"**🚨 系统告警 · {now}**\n"]

    for level, msg in alerts:
        lines.append(f"{level} {msg}")

    lines.append(f"\n_🕐 {datetime.now().strftime('%H:%M:%S')}_")
    return "\n".join(lines)


def push_alert(markdown_text):
    """推送到飞书"""
    result = subprocess.run(
        [LARK_CLI, "im", "+messages-send",
         "--chat-id", FEISHU_CHAT_ID,
         "--markdown", markdown_text],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        try:
            resp = json.loads(result.stdout)
            if resp.get("ok"):
                print(f"🚨 告警已推送: {resp['data']['message_id']}")
                return
        except json.JSONDecodeError:
            pass
    print(f"❌ 告警推送失败: {result.stderr[:200]}")


def main():
    state = load_state()
    now_key = datetime.now().strftime("%Y-%m-%d %H:%M")
    alerts = []

    # ── 1. 服务检查 ──
    services = check_services()
    prev_services = state.get("services", {})
    current_services = {}

    for svc, name, status in services:
        current_services[svc] = status
        prev = prev_services.get(svc, status)
        if status != "active":
            # 服务挂了或未知
            if prev == "active":
                # 从正常→异常，新告警
                alerts.append(("🔴 高危", f"**{name}** ({svc}) 已停止"))
            elif status == "inactive":
                alerts.append(("🟡 警告", f"**{name}** ({svc}) 未运行"))
        elif prev != "active" and svc in prev_services:
            # 从异常→正常，恢复通知
            alerts.append(("✅ 恢复", f"**{name}** ({svc}) 已恢复"))

    # ── 2. 磁盘检查 ──
    disk_pct, disk_used = check_disk()
    prev_disk = state.get("disk_pct", 0)
    if disk_pct >= DISK_WARN_PCT:
        if prev_disk < DISK_WARN_PCT or prev_disk == 0:
            alerts.append(("🟡 警告", f"磁盘使用率 **{disk_pct}%** ({disk_used})"))
    elif prev_disk >= DISK_WARN_PCT and disk_pct < DISK_WARN_PCT:
        alerts.append(("✅ 恢复", f"磁盘已回落至 **{disk_pct}%**"))

    # ── 3. 内存检查 ──
    mem_pct, mem_total, mem_avail = check_memory()
    prev_mem = state.get("mem_pct", 0)
    if mem_pct >= MEM_WARN_PCT:
        if prev_mem < MEM_WARN_PCT or prev_mem == 0:
            alerts.append(("🟡 警告", f"内存使用率 **{mem_pct}%** (剩余 {mem_avail}MB/{mem_total}MB)"))
    elif prev_mem >= MEM_WARN_PCT and mem_pct < MEM_WARN_PCT:
        alerts.append(("✅ 恢复", f"内存已回落至 **{mem_pct}%**"))

    # ── 保存状态 ──
    state["services"] = current_services
    state["disk_pct"] = disk_pct
    state["mem_pct"] = mem_pct
    state["last_check"] = now_key
    save_state(state)

    # ── 推送 ──
    if alerts:
        msg = build_alert(alerts)
        print("=" * 40)
        print("🚨 发现异常:")
        for level, msg in alerts:
            print(f"  {level} {msg}")
        print("=" * 40)
        push_alert(msg)
    else:
        print(f"✅ 一切正常 ({now_key})")


if __name__ == "__main__":
    main()
