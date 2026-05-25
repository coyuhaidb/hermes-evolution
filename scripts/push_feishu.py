#!/home/rng/.hermes/hermes-agent/venv/bin/python3
"""推送 Hermes 进化日报到飞书"""

import json
import os
import subprocess
import sys
from datetime import datetime

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.config import DATA_FILE, FEISHU_CHAT_ID, LARK_CLI


def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


def build_markdown(data):
    """从 evolution.json 组装飞书消息（Markdown 格式）"""
    snapshots = data.get("snapshots", [])
    plans = data.get("future_plans", [])
    today = datetime.now().strftime("%m/%d")
    total_snapshots = len(snapshots)

    if not snapshots:
        latest = {}
        changes = {}
    else:
        latest = snapshots[-1]
        changes = latest.get("changes_since_last", {})

    lines = []

    # ── 标题 ──
    lines.append(f"**🤖 Hermes 进化日报 · {today}**\n")

    # ── 今日概览 ──
    lines.append("**📊 今日概览**")

    # 技能变化
    skills_str = changes.get("skills", "")
    if skills_str:
        old_s, new_s = skills_str.split(" → ") if " → " in str(skills_str) else ("?", "?")
        lines.append(f"• 技能数: {new_s}  (累计)")
    else:
        total_skills = latest.get("skills", {}).get("total", 0)
        lines.append(f"• 技能数: {total_skills}")

    # Wiki 变化
    wiki_str = changes.get("wiki_pages", "")
    if wiki_str:
        old_w, new_w = wiki_str.split(" → ") if " → " in str(wiki_str) else ("?", "?")
        lines.append(f"• Wiki 页面: {new_w}")
    else:
        wiki_pages = latest.get("wiki", {}).get("pages", 0)
        lines.append(f"• Wiki 页面: {wiki_pages}")

    # Commits 变化
    commit_str = changes.get("commits", "")
    if commit_str:
        old_c, new_c = commit_str.split(" → ") if " → " in str(commit_str) else ("?", "?")
        lines.append(f"• Commits: {new_c}")

    # 服务状态
    services = latest.get("services", [])
    if services:
        status_icons = {"active": "✅", "inactive": "❌", "failed": "🔴"}
        service_line = "  ".join(
            f"{status_icons.get(s.get('status', ''), '❓')} {s['name']}"
            for s in services
        )
        lines.append(f"• 服务: {service_line}")

    # 工具版本
    tools = latest.get("tools", {})
    if tools:
        tools_info = " | ".join(f"{k} {v}" for k, v in tools.items())
        lines.append(f"• 环境: {tools_info}")

    lines.append("")

    # ── 活跃技能排行 ──
    skills_list = latest.get("skills", {}).get("list", [])
    if skills_list:
        # 按 category 分组统计
        from collections import Counter
        cat_count = Counter(s.get("category", "其他") for s in skills_list)
        top_cats = cat_count.most_common(5)

        lines.append("**🛠️ 技能分类 Top 5**")
        for cat, count in top_cats:
            bar = "█" * min(count // 5 + 1, 10)
            lines.append(f"• {cat}: {count}  {bar}")
        lines.append("")

    # ── Hermes 版本 ──
    ver = latest.get("hermes_version", "")
    if ver:
        lines.append(f"**🔧 系统版本**  \n{ver}\n")

    # ── 未来计划 ──
    if plans:
        lines.append("**📋 未来计划**")
        for plan in plans:
            lines.append(f"• {plan.get('title', '?')} — {plan.get('desc', '')}")
        lines.append("")

    # ── 快照天数 ──
    lines.append(f"_📅 已记录 {total_snapshots} 天进化数据_\n")

    return "\n".join(lines)


def send_message(markdown_text):
    """通过 lark-cli 发送消息到飞书群"""
    result = subprocess.run(
        [LARK_CLI, "im", "+messages-send",
         "--chat-id", FEISHU_CHAT_ID,
         "--markdown", markdown_text],
        capture_output=True, text=True, timeout=30,
    )

    if result.returncode != 0:
        print(f"❌ 推送失败: {result.stderr}")
        return False

    # 检查返回 JSON
    try:
        resp = json.loads(result.stdout)
        if resp.get("ok"):
            print(f"✅ 推送成功 (message_id: {resp['data']['message_id']})")
            return True
        else:
            print(f"❌ 推送失败: {resp}")
            return False
    except json.JSONDecodeError:
        print(f"❌ 解析返回失败: {result.stdout[:200]}")
        return False


def main():
    data = load_data()
    markdown = build_markdown(data)

    # 调试：打印消息预览
    print("=" * 40)
    print("📨 消息预览:")
    print(markdown)
    print("=" * 40)

    if send_message(markdown):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
