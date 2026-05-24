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
    snapshots = history["snapshots"]
    milestones = history.get("milestones", [])
    latest = snapshots[-1] if snapshots else {}
    first = snapshots[0] if len(snapshots) > 1 else latest
    
    skills_total = latest.get("skills", {}).get("total", 0)
    skills_list = latest.get("skills", {}).get("list", [])
    
    # 计算增长
    days_active = len(snapshots)
    first_skills = first.get("skills", {}).get("total", 0) if first != latest else skills_total
    skills_growth = skills_total - first_skills
    
    wiki_pages = latest.get("wiki", {}).get("pages", 0)
    first_wiki = first.get("wiki", {}).get("pages", 0)
    wiki_growth = wiki_pages - first_wiki
    
    # 按类别分组技能
    skills_by_cat = {}
    for s in skills_list:
        cat = s.get("category", "other")
        if cat not in skills_by_cat:
            skills_by_cat[cat] = []
        skills_by_cat[cat].append(s["name"])
    
    # 上月里程碑
    month_milestones = [m for m in milestones if m.get("date", "")[:7] == TODAY[:7]]
    
    # 生成历史趋势数据
    dates_json = json.dumps([s["date"][:10] for s in snapshots[-30:]])
    skill_counts_json = json.dumps([s["skills"]["total"] for s in snapshots[-30:]])
    wiki_counts_json = json.dumps([s["wiki"]["pages"] for s in snapshots[-30:]])
    
    # 最近变化
    recent_changes = [s.get("changes_since_last", {}) for s in snapshots[-7:] if s.get("changes_since_last")]
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hermes 进化日志</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --orange: #d29922;
    --purple: #bc8cff;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 20px;
    line-height: 1.6;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  
  /* Header */
  header {{
    text-align: center;
    padding: 40px 0 30px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 30px;
  }}
  header h1 {{
    font-size: 2.5em;
    background: linear-gradient(135deg, var(--accent), var(--purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }}
  header .subtitle {{ color: var(--text-dim); font-size: 1.1em; }}
  header .live {{ 
    display: inline-block;
    background: var(--green);
    color: #000;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75em;
    font-weight: bold;
    margin-left: 8px;
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.6; }}
  }}
  
  /* Stats Grid */
  .stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 30px;
  }}
  .stat-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }}
  .stat-card .value {{
    font-size: 2.2em;
    font-weight: bold;
    color: var(--accent);
  }}
  .stat-card .value.green {{ color: var(--green); }}
  .stat-card .value.purple {{ color: var(--purple); }}
  .stat-card .value.orange {{ color: var(--orange); }}
  .stat-card .label {{ color: var(--text-dim); font-size: 0.85em; margin-top: 4px; }}
  .stat-card .growth {{ font-size: 0.8em; color: var(--green); margin-top: 2px; }}
  
  /* Chart */
  .chart-container {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
  }}
  .chart-container h3 {{ margin-bottom: 12px; color: var(--text); }}
  
  /* Timeline */
  .timeline {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
  }}
  .timeline h3 {{ margin-bottom: 16px; }}
  .timeline-item {{
    display: flex;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
  }}
  .timeline-item:last-child {{ border: none; }}
  .timeline-date {{ color: var(--text-dim); font-size: 0.85em; min-width: 80px; }}
  .timeline-dot {{
    width: 10px; height: 10px;
    border-radius: 50%;
    background: var(--green);
    margin-top: 6px;
    flex-shrink: 0;
  }}
  .timeline-dot.skill {{ background: var(--accent); }}
  .timeline-dot.wiki {{ background: var(--purple); }}
  .timeline-dot.milestone {{ background: var(--orange); }}
  .timeline-content {{ color: var(--text); }}
  .timeline-content .tag {{
    display: inline-block;
    padding: 1px 8px;
    border-radius: 8px;
    font-size: 0.75em;
    margin-right: 6px;
  }}
  .tag-skill {{ background: #1f3a5f; color: var(--accent); }}
  .tag-wiki {{ background: #2d1f5e; color: var(--purple); }}
  .tag-milestone {{ background: #3d2e00; color: var(--orange); }}
  
  /* Skills Grid */
  .skills-section {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
  }}
  .skills-section h3 {{ margin-bottom: 16px; }}
  .skills-cat {{
    margin-bottom: 16px;
  }}
  .skills-cat h4 {{
    color: var(--accent);
    margin-bottom: 8px;
    font-size: 0.9em;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .skills-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}
  .skill-tag {{
    background: #1f3a5f;
    color: var(--accent);
    padding: 3px 10px;
    border-radius: 8px;
    font-size: 0.85em;
    border: 1px solid #2a4a7f;
  }}
  
  /* Services */
  .services {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
  }}
  .service-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
  }}
  .service-row:last-child {{ border: none; }}
  .service-status {{
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 8px;
  }}
  .status-active {{ background: var(--green); }}
  .status-inactive {{ background: #484f58; }}
  
  .footer {{
    text-align: center;
    color: var(--text-dim);
    font-size: 0.8em;
    padding: 30px 0;
  }}
  
  /* Milestone form */
  .milestone-form {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 24px;
  }}
  .milestone-form h3 {{ margin-bottom: 12px; }}
  .milestone-form input, .milestone-form textarea {{
    width: 100%;
    background: #0d1117;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 12px;
    color: var(--text);
    margin-bottom: 8px;
    font-family: inherit;
  }}
  .milestone-form button {{
    background: var(--accent);
    color: #000;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    cursor: pointer;
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Hermes 进化日志</h1>
    <div class="subtitle">
      我的 AI 助手成长记录
      <span class="live">● LIVE</span>
    </div>
    <div style="margin-top: 8px; font-size: 0.85em; color: var(--text-dim);">
      最后更新：{latest.get("date", "N/A")} ｜ 
      已记录 {days_active} 天 ｜ 
      {skills_total} 个技能
    </div>
  </header>
  
  <!-- 统计面板 -->
  <div class="stats">
    <div class="stat-card">
      <div class="value">{skills_total}</div>
      <div class="label">技能数</div>
      <div class="growth">+{skills_growth} 累计</div>
    </div>
    <div class="stat-card">
      <div class="value green">{wiki_pages}</div>
      <div class="label">Wiki 页面</div>
      <div class="growth">+{wiki_growth} 累计</div>
    </div>
    <div class="stat-card">
      <div class="value purple">{latest.get("memory", {}).get("size", "N/A")}</div>
      <div class="label">记忆库</div>
    </div>
    <div class="stat-card">
      <div class="value orange">{days_active}</div>
      <div class="label">追踪天数</div>
    </div>
  </div>
  
  <!-- 趋势图 -->
  <div class="chart-container">
    <h3>📈 成长趋势（近 30 天）</h3>
    <canvas id="growthChart" height="80"></canvas>
  </div>
  
  <!-- 最近变化 -->
  <div class="timeline">
    <h3>⚡ 最近变化</h3>
'''

    # 最近变化列表
    changes_found = False
    for s in reversed(snapshots[-7:]):
        ch = s.get("changes_since_last", {})
        if ch:
            changes_found = True
            date_str = s["date"][:10]
            for k, v in ch.items():
                tag = "skill" if "skill" in k else "wiki"
                label = "技能" if "skill" in k else "知识库"
                html += f'''
    <div class="timeline-item">
      <div class="timeline-date">{date_str}</div>
      <div class="timeline-dot {tag}"></div>
      <div class="timeline-content">
        <span class="tag tag-{tag}">{label}</span>
        {v}
      </div>
    </div>'''
    
    if not changes_found:
        html += '''
    <div class="timeline-item">
      <div class="timeline-content" style="color: var(--text-dim);">
        暂无变化，新的进化将从明天开始记录
      </div>
    </div>'''
    
    html += '''
  </div>
  
  <!-- 技能分类 -->
  <div class="skills-section">
    <h3>🧠 已掌握的技能</h3>
'''
    for cat, names in sorted(skills_by_cat.items()):
        html += f'''
    <div class="skills-cat">
      <h4>📁 {cat}</h4>
      <div class="skills-tags">
'''
        for name in names:
            html += f'        <span class="skill-tag">{name}</span>\n'
        html += '      </div>\n    </div>\n'
    
    if not skills_by_cat:
        html += '    <div style="color: var(--text-dim);">暂无技能数据</div>\n'
    
    html += '''
  </div>
  
  <!-- 服务状态 -->
  <div class="services">
    <h3>🔧 系统服务</h3>
'''
    for svc in latest.get("services", []):
        is_active = svc["status"] == "active"
        status_class = "status-active" if is_active else "status-inactive"
        status_text = "🟢 运行中" if is_active else "⭕ 已停止"
        html += f'''
    <div class="service-row">
      <span><span class="service-status {status_class}"></span>{svc["name"]}</span>
      <span>{status_text}</span>
    </div>'''
    
    html += '''
  </div>
  
  <!-- 里程碑（可手动添加） -->
  <div class="milestone-form">
    <h3>🏆 添加里程碑</h3>
    <p style="color: var(--text-dim); font-size: 0.9em; margin-bottom: 12px;">
      想记录一个重要的进化时刻？告诉 Hermes 就行，它会帮你加到这里。
    </p>
  </div>
  
  <footer class="footer">
    Hermes Evolution Log · 由每日定时任务自动更新<br>
    始于 {first.get("date", TODAY)[:10]}
  </footer>
</div>

<script>
const ctx = document.getElementById('growthChart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {dates_json},
    datasets: [
      {{
        label: '技能数',
        data: {skill_counts_json},
        borderColor: '#58a6ff',
        backgroundColor: 'rgba(88, 166, 255, 0.1)',
        tension: 0.3,
        fill: true,
        pointRadius: 2,
      }},
      {{
        label: 'Wiki 页面',
        data: {wiki_counts_json},
        borderColor: '#bc8cff',
        backgroundColor: 'rgba(188, 140, 255, 0.1)',
        tension: 0.3,
        fill: true,
        pointRadius: 2,
        yAxisID: 'y1',
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        labels: {{ color: '#8b949e', font: {{ size: 12 }} }},
        position: 'top',
      }}
    }},
    scales: {{
      x: {{
        ticks: {{ color: '#8b949e', maxTicksLimit: 10 }},
        grid: {{ color: '#30363d' }},
      }},
      y: {{
        beginAtZero: true,
        ticks: {{ color: '#8b949e', stepSize: 1 }},
        grid: {{ color: '#30363d' }},
      }},
      y1: {{
        beginAtZero: true,
        position: 'right',
        ticks: {{ color: '#8b949e', stepSize: 1 }},
        grid: {{ display: false }},
      }}
    }}
  }}
}});
</script>
</body>
</html>'''
    
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    main()
