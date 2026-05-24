#!/home/rng/.hermes/hermes-agent/venv/bin/python3
"""Hermes 进化数据采集 + HTML 生成"""

import json
import os
import subprocess
import shutil
from datetime import datetime, date
from pathlib import Path

HOME = os.environ["HOME"]
PROJECT = os.path.join(HOME, "projects", "hermes-evolution")
DATA_FILE = os.path.join(PROJECT, "data", "evolution.json")
HTML_FILE = os.path.join(PROJECT, "index.html")
HERMES_SKILLS = os.path.join(HOME, ".hermes", "skills")
WIKI_DIR = os.path.join(HOME, "wiki")
NOW = datetime.now()
TODAY = NOW.strftime("%Y-%m-%d %H:%M")


def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return r.stdout.strip()
    except Exception:
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
                    if os.path.isdir(skill_path) and os.path.isfile(os.path.join(skill_path, "SKILL.md")):
                        mtime = os.path.getmtime(os.path.join(skill_path, "SKILL.md"))
                        skills.append({
                            "name": skill,
                            "category": cat,
                            "updated": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"),
                        })
    return skills


def get_memory_data():
    # Estimate memory size from hermes state database
    state_db = os.path.join(HOME, ".hermes", "state.db")
    memory_count = 0
    memory_size = "N/A"
    if os.path.isfile(state_db):
        size = os.path.getsize(state_db)
        memory_size = f"{size // 1024} KB"
    # Count from the skills/memory
    memory_skill_dir = os.path.join(HERMES_SKILLS, "memory")
    if os.path.isdir(memory_skill_dir):
        memory_count = count_files(memory_skill_dir)
    return {"size": memory_size, "files": memory_count}


def get_service_status():
    services = ["hermes-gateway", "hermes-dashboard", "hermes-web-ui"]
    result = []
    for s in services:
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
        "hermes_version": run("hermes --version 2>/dev/null | head -1"),
    }
    
    # 计算变化（和上一次对比）
    prev = history["snapshots"][-1] if history["snapshots"] else None
    changes = {}
    if prev:
        if snapshot["skills"]["total"] != prev["skills"]["total"]:
            changes["skills"] = f"{prev['skills']['total']} → {snapshot['skills']['total']}"
        if snapshot["wiki"]["pages"] != prev["wiki"]["pages"]:
            changes["wiki_pages"] = f"{prev['wiki']['pages']} → {snapshot['wiki']['pages']}"
        if snapshot["wiki"]["raw_sources"] != prev["wiki"]["raw_sources"]:
            changes["wiki_sources"] = f"{prev['wiki']['raw_sources']} → {snapshot['wiki']['raw_sources']}"
    
    snapshot["changes_since_last"] = changes
    history["snapshots"].append(snapshot)
    
    # 只保留最近 365 条
    if len(history["snapshots"]) > 365:
        history["snapshots"] = history["snapshots"][-365:]
    
    # 保存数据
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    # 生成 HTML
    generate_html(history)
    
    print(f"✅ Evolution updated: {TODAY}")
    if changes:
        for k, v in changes.items():
            print(f"   Change - {k}: {v}")


def generate_html(history):
    import sys, importlib
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    _render = importlib.import_module("scripts.render").generate_html
    _render(history)


if __name__ == "__main__":
    main()
