#!/home/rng/.hermes/hermes-agent/venv/bin/python3
"""Hermes 进化数据采集 + HTML 生成"""

import json
import os
import subprocess
import shutil
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
    if not os.path.isdir(path):
        return 0
    return sum(1 for f in Path(path).rglob(f"*{ext}"))


def get_skills_data():
    skills = []
    if os.path.isdir(HERMES_SKILLS):
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
    """从 SKILL.md 的 YAML 前置元数据中提取 description"""
    try:
        with open(skill_md, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        in_frontmatter = False
        for line in lines[:20]:  # 只看前 20 行
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
    memory_count = 0
    memory_size = "N/A"
    if os.path.isfile(STATE_DB):
        size = os.path.getsize(STATE_DB)
        memory_size = f"{size // 1024} KB"
    # Count from the skills/memory
    memory_skill_dir = os.path.join(HERMES_SKILLS, "memory")
    if os.path.isdir(memory_skill_dir):
        memory_count = count_files(memory_skill_dir)
    return {"size": memory_size, "files": memory_count}


def get_service_status():
    result = []
    for s in SERVICES:
        status = run(f"systemctl is-active {s} 2>/dev/null")
        result.append({"name": s, "status": status if status else "inactive"})
    return result


def get_wiki_data():
    if not os.path.isdir(WIKI_DIR):
        return {"pages": 0, "raw_sources": 0, "last_update": "N/A"}
    pages = count_files(os.path.join(WIKI_DIR, "concepts")) + \
            count_files(os.path.join(WIKI_DIR, "entities")) + \
            count_files(os.path.join(WIKI_DIR, "meta"))
    raw = count_files(os.path.join(WIKI_DIR, "raw", "articles"))
    log_file = os.path.join(WIKI_DIR, "log.md")
    last_update = "N/A"
    if os.path.isfile(log_file):
        mtime = os.path.getmtime(log_file)
        last_update = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    return {"pages": pages, "raw_sources": raw, "last_update": last_update}


def load_history():
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"snapshots": [], "milestones": []}


def main():
    history = load_history()
    
    # 采集当前快照
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
    
    # 计算变化（和上一次对比）
    prev = history["snapshots"][-1] if history["snapshots"] else None
    changes = {}
    if prev:
        for key in ["skills", "wiki_pages", "wiki_sources", "commits"]:
            curr_val = snapshot.get(key if key != "wiki_pages" else "wiki", {}).get("total" if key != "wiki_pages" else "pages", 0) if key != "commits" else int(snapshot.get("system", {}).get("commits", 0) or 0)
            prev_val = prev.get(key if key != "wiki_pages" else "wiki", {}).get("total" if key != "wiki_pages" else "pages", 0) if key != "commits" else int(prev.get("system", {}).get("commits", 0) or 0)
            key2 = key
            label = {"skills": "技能数", "wiki_pages": "Wiki 页面", "wiki_sources": "原始资料", "commits": "Git 提交"}.get(key, key)
            if curr_val != prev_val:
                changes[key2] = f"{prev_val} → {curr_val}"
        if prev.get("services") != snapshot["services"]:
            changes["services"] = "服务状态变化"
    
    snapshot["changes_since_last"] = changes
    
    # 去重：同一天已存在则替换，否则追加
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
    
    # 保存数据
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    # 初始化未来方向（如果没有的话）
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
