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


def sparkline(values):
    """把一组数值转成文字迷你趋势线"""
    if not values or len(values) < 2:
        return ""
    mn, mx = min(values), max(values)
    rng = max(mx - mn, 1)
    chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    n = len(chars) - 1
    return "".join(chars[min(n, int((v - mn) / rng * n))] for v in values)


def extract_trends(snapshots):
    """从快照中提取趋势数据"""
    skills = []
    wikis = []
    for s in snapshots:
        skills.append(s["skills"]["total"])
        wikis.append(s["wiki"]["pages"])
    return skills, wikis


def build_markdown(data):
    """从 evolution.json 组装飞书消息"""
    snapshots = data.get("snapshots", [])
    plans = data.get("future_plans", [])
    today = datetime.now().strftime("%m/%d")
    total_snapshots = len(snapshots)
    latest = snapshots[-1] if snapshots else {}
    changes = latest.get("changes_since_last", {})

    # 趋势数据
    skill_vals, wiki_vals = extract_trends(snapshots)

    lines = []

    # ── 标题 ──
    lines.append(f"**🤖 Hermes 进化日报 · {today}**\n")

    # ── 今日概览 ──
    lines.append("**📊 今日概览**")

    skills_str = changes.get("skills", "")
    total_skills = latest.get("skills", {}).get("total", 0)
    lines.append(f"• 技能数: **{total_skills}**  {sparkline(skill_vals)}")

    wiki_pages = latest.get("wiki", {}).get("pages", 0)
    lines.append(f"• Wiki 页面: **{wiki_pages}**  {sparkline(wiki_vals)}")

    commit_str = changes.get("commits", "")
    if commit_str and "→" in str(commit_str):
        new_c = str(commit_str).split("→")[1].strip()
        lines.append(f"• Commits: **{new_c}**")

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

    # ── 技能分类 ──
    skills_list = latest.get("skills", {}).get("list", [])
    if skills_list:
        from collections import Counter
        cat_count = Counter(s.get("category", "其他") for s in skills_list)
        top_cats = cat_count.most_common(5)

        CAT_CN = {
            "creative": "创意创作", "superpowers-zh": "中文方法论",
            "software-development": "软件开发", "productivity": "效率工具",
            "devops": "运维部署", "github": "GitHub 工具",
            "research": "研究检索", "apple": "Apple 生态",
            "autonomous-ai-agents": "自主 AI 代理", "media": "媒体处理",
            "gaming": "游戏", "data-science": "数据科学",
            "email": "邮件", "mcp": "MCP 集成",
            "mlops": "MLOps", "note-taking": "笔记",
            "red-teaming": "红队安全", "smart-home": "智能家居",
            "social-media": "社交媒体",
        }

        lines.append("**🛠️ 技能分类 Top 5**")
        for cat, count in top_cats:
            cn = CAT_CN.get(cat, cat)
            lines.append(f"• {cn}: **{count}**")
        lines.append("")

    # ── 系统版本 ──
    ver = latest.get("hermes_version", "")
    if ver:
        lines.append(f"**🔧 系统**  \n{ver}\n")

    # ── 未来计划 ──
    if plans:
        lines.append("**📋 未来计划**")
        for plan in plans:
            lines.append(f"• {plan.get('title', '?')} — {plan.get('desc', '')}")
        lines.append("")

    # ── 页脚 ──
    lines.append(f"_📅 已记录 {total_snapshots} 天_")

    return "\n".join(lines)


def send_message(markdown_text):
    """通过 lark-cli 发送消息到飞书群"""
    cmd = [
        LARK_CLI, "im", "+messages-send",
        "--chat-id", FEISHU_CHAT_ID,
        "--markdown", markdown_text,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True, text=True, timeout=30,
    )

    if result.returncode != 0:
        print(f"❌ 推送失败: {result.stderr}")
        return False

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

    print("=" * 40)
    print("📨 消息预览:")
    print(markdown)
    print("=" * 40)

    if send_message(markdown):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
