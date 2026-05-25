#!/home/rng/.hermes/hermes-agent/venv/bin/python3
"""Hermes 进化数据采集 — 每天定时收集系统快照"""

import json
import os
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

# 确保项目根目录在导入路径中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.config import (
    PROJECT_DIR, DATA_FILE,
    HERMES_SKILLS, WIKI_DIR, STATE_DB, SERVICES
)

NOW = datetime.now()
TODAY = NOW.strftime("%Y-%m-%d %H:%M")


def run(cmd):
    """执行 shell 命令并返回 stdout，超时 15 秒，失败返回空字符串"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if r.returncode != 0 and r.stderr.strip():
            print(f"  ⚠️ 命令失败: {cmd[:60]} → {r.stderr.strip()[:100]}")
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ 命令超时: {cmd[:60]}")
        return "N/A"
    except Exception as e:
        print(f"  ⚠️ 命令异常: {cmd[:60]} → {e}")
        return "N/A"


def count_files(path, ext=".md"):
    """递归统计目录下指定扩展名的文件数"""
    if not os.path.isdir(path):
        return 0
    return sum(1 for f in Path(path).rglob(f"*{ext}"))


def get_skills_data():
    """
    扫描 ~/.hermes/skills/ 下所有已安装的 Hermes 技能。
    返回列表，每个元素含 name / category / description / updated。
    """
    skills = []
    if os.path.isdir(HERMES_SKILLS):
        # HERMES_SKILLS 结构：<category>/<skill-name>/SKILL.md
        for cat in sorted(os.listdir(HERMES_SKILLS)):
            cat_path = os.path.join(HERMES_SKILLS, cat)
            if os.path.isdir(cat_path):
                for skill in sorted(os.listdir(cat_path)):
                    skill_path = os.path.join(cat_path, skill)
                    skill_md = os.path.join(skill_path, "SKILL.md")
                    if os.path.isdir(skill_path) and os.path.isfile(skill_md):
                        mtime = os.path.getmtime(skill_md)
                        desc = _parse_skill_description(skill_md)
                        skills.append({
                            "name": skill,
                            "category": cat,
                            "description": desc,
                            "updated": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"),
                        })
    return skills


def _parse_skill_description(skill_md):
    """从 SKILL.md 的 YAML 前置元数据中提取 description 字段"""
    try:
        with open(skill_md, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        in_frontmatter = False
        for line in lines[:20]:  # 只看前 20 行（YAML 块通常在开头）
            stripped = line.strip()
            if stripped == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter and stripped.startswith("description:"):
                val = stripped[len("description:"):].strip().strip('"').strip("'")
                if len(val) > 80:
                    val = val[:77] + "..."
                return val
    except Exception:
        pass
    return ""


def get_memory_data():
    """获取 Hermes 状态数据库大小和记忆文件数"""
    memory_count = 0
    memory_size = "N/A"
    if os.path.isfile(STATE_DB):
        size = os.path.getsize(STATE_DB)
        memory_size = f"{size // 1024} KB"
    # 统计 skills/memory 目录下的文件数
    memory_skill_dir = os.path.join(HERMES_SKILLS, "memory")
    if os.path.isdir(memory_skill_dir):
        memory_count = count_files(memory_skill_dir)
    return {"size": memory_size, "files": memory_count}


def get_service_status():
    """检查所有关键系统服务的运行状态（systemctl is-active）"""
    result = []
    for s in SERVICES:
        status = run(f"systemctl is-active {s} 2>/dev/null")
        result.append({"name": s, "status": status if status else "inactive"})
    return result


def get_wiki_data():
    """统计 Wiki 知识库的页面数、原始资料数和最后更新时间"""
    if not os.path.isdir(WIKI_DIR):
        return {"pages": 0, "raw_sources": 0, "last_update": "N/A"}
    # 页面分布在 concepts/ entities/ meta/ 三个子目录
    pages = count_files(os.path.join(WIKI_DIR, "concepts")) + \
            count_files(os.path.join(WIKI_DIR, "entities")) + \
            count_files(os.path.join(WIKI_DIR, "meta"))
    # 原始资料放在 raw/articles/
    raw = count_files(os.path.join(WIKI_DIR, "raw", "articles"))
    # 取 log.md 的修改时间作为最后更新时间
    log_file = os.path.join(WIKI_DIR, "log.md")
    last_update = "N/A"
    if os.path.isfile(log_file):
        mtime = os.path.getmtime(log_file)
        last_update = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    return {"pages": pages, "raw_sources": raw, "last_update": last_update}


def load_history():
    """读取 evolution.json，返回历史快照数据"""
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"snapshots": [], "milestones": []}


def main():
    history = load_history()
    
    # ── 采集当前快照 ──
    # 每个 snapshot 是一次完整的系统状态记录
    snapshot = {
        "date": TODAY,
        "skills": {
            "total": len(get_skills_data()),
            "list": get_skills_data(),
        },
        "memory": get_memory_data(),
        "wiki": get_wiki_data(),
        "services": get_service_status(),
        "tools": {
            "node": run("node --version 2>/dev/null"),
            "python": run("python3 --version 2>/dev/null"),
            "npm": run("npm --version 2>/dev/null"),
            "uv": run("uv --version 2>/dev/null | cut -d' ' -f2"),
        },
        "system": {
            "uptime": run("uptime -p 2>/dev/null | sed 's/up //'"),
            "disk": run("df -h / 2>/dev/null | tail -1 | awk '{print $5}'"),
            "commits": run("cd " + PROJECT_DIR + " && git rev-list --count HEAD 2>/dev/null"),
        },
        "hermes_version": run("hermes --version 2>/dev/null | head -1"),
    }
    
    # ── 计算与上一次快照的变化量 ──
    # 对比 skills/wiki/commits 等数值指标，记录增减
    prev = history["snapshots"][-1] if history["snapshots"] else None
    changes = {}
    if prev:
        # 逐个指标对比
        for key in ["skills", "wiki_pages", "wiki_sources", "commits"]:
            # 从当前快照中取对应值
            if key == "commits":
                curr_val = int(snapshot.get("system", {}).get("commits", 0) or 0)
                prev_val = int(prev.get("system", {}).get("commits", 0) or 0)
            elif key == "wiki_pages":
                curr_val = snapshot.get("wiki", {}).get("pages", 0)
                prev_val = prev.get("wiki", {}).get("pages", 0)
            elif key == "wiki_sources":
                curr_val = snapshot.get("wiki", {}).get("raw_sources", 0)
                prev_val = prev.get("wiki", {}).get("raw_sources", 0)
            else:
                curr_val = snapshot.get(key, {}).get("total", 0)
                prev_val = prev.get(key, {}).get("total", 0)

            label = {"skills": "技能数", "wiki_pages": "Wiki 页面", "wiki_sources": "原始资料", "commits": "Git 提交"}.get(key, key)
            if curr_val != prev_val:
                changes[key] = f"{prev_val} → {curr_val}"
        # 服务状态变化（整体对比）
        if prev.get("services") != snapshot["services"]:
            changes["services"] = "服务状态变化"
    
    snapshot["changes_since_last"] = changes
    
    # ── 去重：同一天已存在则替换，否则追加 ──
    # 防止一天内多次运行 cron 产生重复数据
    today_key = TODAY[:10]
    existing_idx = None
    for i, s in enumerate(history["snapshots"]):
        if s["date"][:10] == today_key:
            existing_idx = i
            break
    if existing_idx is not None:
        history["snapshots"][existing_idx] = snapshot
    else:
        history["snapshots"].append(snapshot)
    
    # 只保留最近 365 条
    if len(history["snapshots"]) > 365:
        history["snapshots"] = history["snapshots"][-365:]
    
    # ── 保存数据 ──
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    # 如果首次运行，初始化未来计划占位
    if "future_plans" not in history:
        history["future_plans"] = [
            {"title": "📦 接入更多消息平台", "desc": "配置 Telegram / Discord 等平台"},
            {"title": "🧩 集成更多工具链", "desc": "gstack、Oh My Pi 等生态工具集成"},
        ]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Evolution updated: {TODAY}")
    if changes:
        for k, v in changes.items():
            print(f"   Change - {k}: {v}")


if __name__ == "__main__":
    main()
