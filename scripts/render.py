"""HTML 渲染模块 — 从数据生成进化日志页面"""
import json
import os
import sys

# 确保项目根目录在导入路径中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.config import HTML_FILE, VERSION_FILE


def get_version():
    """读取 VERSION 文件中的版本号"""
    try:
        with open(VERSION_FILE) as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        return "0.0.0"


def generate_html(history):
    snapshots = history["snapshots"]
    milestones = history.get("milestones", [])
    latest = snapshots[-1] if snapshots else {}
    first = snapshots[0] if len(snapshots) > 1 else latest
    
    skills_total = latest.get("skills", {}).get("total", 0)
    skills_list = latest.get("skills", {}).get("list", [])
    
    days_active = len(snapshots)
    first_skills = first.get("skills", {}).get("total", 0) if first != latest else skills_total
    skills_growth = skills_total - first_skills
    
    wiki_pages = latest.get("wiki", {}).get("pages", 0)
    first_wiki = first.get("wiki", {}).get("pages", 0)
    wiki_growth = wiki_pages - first_wiki
    
    services = latest.get("services", [])
    active_svcs = sum(1 for s in services if s.get("status") == "active")
    mem_size = latest.get("memory", {}).get("size", "N/A")
    
    # 系统维度
    sysinfo = latest.get("system", {})
    uptime = sysinfo.get("uptime", "N/A")
    disk_usage = sysinfo.get("disk", "N/A")
    total_commits = int(sysinfo.get("commits", 0) or 0)
    raw_sources = latest.get("wiki", {}).get("raw_sources", 0)
    
    version = get_version()
    
    # 技能分组（带描述）
    skills_by_cat = {}
    for s in skills_list:
        cat = s.get("category", "other")
        if cat not in skills_by_cat:
            skills_by_cat[cat] = []
        skills_by_cat[cat].append(s)
    
    # 趋势数据（最多30天）
    recent = snapshots[-30:]
    dates_json = json.dumps([s["date"][:10] for s in recent])
    skill_counts_json = json.dumps([s["skills"]["total"] for s in recent])
    wiki_counts_json = json.dumps([s["wiki"]["pages"] for s in recent])
    
    # 技能卡片 HTML
    skills_html = ""
    for cat, skills in sorted(skills_by_cat.items()):
        cat_display = cat.replace("-", " ").title()
        skills_html += f'\n          <div class="skills-category"><div class="cat-header">{cat_display} ({len(skills)})</div><div class="skills-grid2">'
        for s in skills:
            name = s["name"]
            desc = s.get("description", "")
            if desc:
                skills_html += f'<div class="skill-card"><div class="sk-name">{name}</div><div class="sk-desc">{desc}</div></div>'
            else:
                skills_html += f'<div class="skill-card"><div class="sk-name">{name}</div></div>'
        skills_html += '</div></div>'
    
    # 服务HTML
    svc_html = "".join(
        f'<div class="service-item"><span>{"🟢" if s.get("status") == "active" else "🔴"} {s["name"]}</span></div>'
        for s in services
    )
    
    # 变化时间线
    changes_html = ""
    has_changes = False
    for s in reversed(snapshots[-14:]):
        ch = s.get("changes_since_last", {})
        if ch:
            has_changes = True
            date_str = s["date"][:10]
            for k, v in ch.items():
                changes_html += f'''
          <div class="tl-item">
            <div class="tl-dot"></div>
            <div class="tl-body">
              <div class="tl-date">{date_str}</div>
              <div class="tl-text">⚡ {k}: <strong>{v}</strong></div>
            </div>
          </div>'''
    if not has_changes:
        changes_html += '''
          <div class="tl-item">
            <div class="tl-dot" style="background:#555"></div>
            <div class="tl-body">
              <div class="tl-text" style="color:#888">首次记录完成，明天开始追踪变化</div>
            </div>
          </div>'''
    
    # 里程碑
    ms_html = "".join(
        f'''
          <div class="tl-item">
            <div class="tl-dot ms"></div>
            <div class="tl-body">
              <div class="tl-date">{m.get("date","")[:10]}</div>
              <div class="tl-text"><strong>{m.get("title","")}</strong></div>
              <div class="tl-desc">{m.get("desc","")}</div>
            </div>
          </div>'''
        for m in milestones[-10:]
    )
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Hermes 进化记录 · {latest.get('date','')[:10]}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans SC',-apple-system,sans-serif;background:linear-gradient(135deg,#0a0a0f 0%,#1a1a2e 50%,#16213e 100%);min-height:100vh;color:#e0e0e0;line-height:1.6}}
.header{{text-align:center;padding:60px 20px 40px}}
.avatar{{width:120px;height:120px;border-radius:50%;margin:0 auto 24px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border:3px solid rgba(102,126,234,0.5);box-shadow:0 0 60px rgba(102,126,234,0.4);animation:pulse 3s ease-in-out infinite;display:flex;align-items:center;justify-content:center;font-size:3rem}}
@keyframes pulse{{0%,100%{{box-shadow:0 0 60px rgba(102,126,234,0.4)}}50%{{box-shadow:0 0 80px rgba(102,126,234,0.6)}}}}
.header h1{{font-size:2.5rem;background:linear-gradient(135deg,#667eea 0%,#764ba2 50%,#f093fb 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.header .subtitle{{color:#888;font-size:1rem;margin-top:4px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;max-width:900px;margin:0 auto 40px;padding:0 20px}}
.stat-card{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;text-align:center;backdrop-filter:blur(10px);transition:all 0.3s ease}}
.stat-card:hover{{transform:translateY(-4px);border-color:rgba(102,126,234,0.5)}}
.stat-number{{font-size:2.5rem;font-weight:700;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.stat-number.green{{background:linear-gradient(135deg,#34d399,#3fb950);-webkit-background-clip:text;background-clip:text}}
.stat-number.purple{{background:linear-gradient(135deg,#a78bfa,#8b5cf6);-webkit-background-clip:text;background-clip:text}}
.stat-number.orange{{background:linear-gradient(135deg,#fbbf24,#f59e0b);-webkit-background-clip:text;background-clip:text}}
.stat-label{{font-size:0.85rem;color:#888;margin-top:4px}}
.evo-card{{max-width:900px;margin:0 auto 40px;padding:32px 20px;background:linear-gradient(135deg,rgba(102,126,234,0.1),rgba(118,75,162,0.1));border:1px solid rgba(102,126,234,0.2);border-radius:20px;text-align:center}}
.evo-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:700px;margin:0 auto}}
.evo-item{{text-align:center}}
.evo-icon{{font-size:2rem;margin-bottom:8px}}
.evo-number{{font-size:1.8rem;font-weight:700;color:#fff}}
.evo-label{{font-size:0.8rem;color:#888}}
.section{{max-width:1000px;margin:0 auto 50px;padding:0 20px}}
.section-title{{display:flex;align-items:center;gap:10px;font-size:1.4rem;font-weight:600;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.1)}}
.chart-box{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;margin-bottom:30px}}
.timeline{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;position:relative}}
.timeline::before{{content:'';position:absolute;left:32px;top:60px;bottom:30px;width:2px;background:linear-gradient(to bottom,#667eea,#764ba2,transparent)}}
.tl-item{{display:flex;gap:16px;padding:8px 0 16px;position:relative}}
.tl-dot{{width:14px;height:14px;border-radius:50%;background:linear-gradient(135deg,#667eea,#764ba2);box-shadow:0 0 16px rgba(102,126,234,0.4);flex-shrink:0;margin-top:4px;z-index:1}}
.tl-dot.ms{{background:linear-gradient(135deg,#f093fb,#f59e0b)}}
.tl-body{{flex:1}}
.tl-date{{font-size:0.8rem;color:#666}}
.tl-text{{font-size:0.95rem;color:#ccc;margin:2px 0}}
.tl-desc{{font-size:0.85rem;color:#888}}
.cat-header{{font-size:0.8rem;font-weight:600;color:#a5b4fc;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.05)}}
.skills-row{{display:flex;flex-wrap:wrap;gap:6px}}
.skill-badge{{font-size:0.8rem;padding:4px 12px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:20px;color:#ccc;transition:all 0.2s ease}}
.skill-badge:hover{{border-color:rgba(102,126,234,0.4);color:#fff;background:rgba(102,126,234,0.1)}}
.skills-grid2{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}}
.skill-card{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:12px 14px;transition:all 0.2s ease}}
.skill-card:hover{{transform:translateY(-2px);border-color:rgba(102,126,234,0.3)}}
.sk-name{{font-size:0.85rem;font-weight:600;color:#e0e0e0}}
.sk-desc{{font-size:0.75rem;color:#888;margin-top:4px;line-height:1.4}}
.services-box{{display:flex;flex-wrap:wrap;gap:12px}}
.service-item{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:12px 20px;font-size:0.9rem}}
.idea-card{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;margin-bottom:16px;transition:all 0.3s ease}}
.idea-card:hover{{transform:translateY(-2px);border-color:rgba(102,126,234,0.3)}}
.idea-card h4{{color:#a5b4fc;font-size:1rem;margin-bottom:8px}}
.idea-card p{{color:#888;font-size:0.9rem}}
.footer{{text-align:center;padding:40px 20px;color:#555;font-size:0.8rem}}
@media(max-width:600px){{.header h1{{font-size:1.8rem}}.stats{{grid-template-columns:repeat(2,1fr)}}.evo-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>

<div class="header">
  <div class="avatar">🧠</div>
  <h1>Hermes 进化记录</h1>
  <p class="subtitle">AI 能力成长追踪 · 最后更新 {latest.get('date','')}</p>
</div>

<div class="stats">
  <div class="stat-card"><div class="stat-number">{skills_total}</div><div class="stat-label">技能数</div></div>
  <div class="stat-card"><div class="stat-number green">{wiki_pages}</div><div class="stat-label">Wiki 页面</div></div>
  <div class="stat-card"><div class="stat-number purple">{active_svcs}</div><div class="stat-label">运行服务</div></div>
  <div class="stat-card"><div class="stat-number orange">{days_active}</div><div class="stat-label">追踪天数</div></div>
  <div class="stat-card"><div class="stat-number" style="background:linear-gradient(135deg,#f093fb,#f59e0b);-webkit-background-clip:text;background-clip:text">{total_commits}</div><div class="stat-label">Git 提交</div></div>
  <div class="stat-card"><div class="stat-number" style="background:linear-gradient(135deg,#34d399,#3fb950);-webkit-background-clip:text;background-clip:text">{raw_sources}</div><div class="stat-label">原始资料</div></div>
</div>

<div class="evo-card">
  <div class="evo-grid">
    <div class="evo-item"><div class="evo-icon">📈</div><div class="evo-number">+{skills_growth}</div><div class="evo-label">技能增长</div></div>
    <div class="evo-item"><div class="evo-icon">📚</div><div class="evo-number">+{wiki_growth}</div><div class="evo-label">知识增长</div></div>
    <div class="evo-item"><div class="evo-icon">🧠</div><div class="evo-number">{mem_size}</div><div class="evo-label">记忆库</div></div>
  </div>
</div>

<!-- 系统信息 -->
<div class="section">
  <h2 class="section-title"><span>💻</span> 系统状态</h2>
  <div style="display:flex;flex-wrap:wrap;gap:12px">
    <div class="service-item">⏱ 运行 {uptime}</div>
    <div class="service-item">💾 磁盘 {disk_usage}</div>
    <div class="service-item">📦 {total_commits} 次提交</div>
    <div class="service-item">📄 {raw_sources} 篇资料</div>
  </div>
</div>

<div class="section">
  <h2 class="section-title"><span>📈</span> 成长趋势</h2>
  <div class="chart-box"><canvas id="chart" height="80"></canvas></div>
</div>

<div class="section">
  <h2 class="section-title"><span>⚡</span> 最近变化</h2>
  <div class="timeline">{changes_html}</div>
</div>

<div class="section">
  <h2 class="section-title"><span>🛠️</span> 已掌握的 Skills</h2>
  <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px">{skills_html}</div>
</div>

<div class="section">
  <h2 class="section-title"><span>🔧</span> 系统服务</h2>
  <div class="services-box">{svc_html}</div>
</div>

<div class="section">
  <h2 class="section-title"><span>🏆</span> 里程碑</h2>
  <div class="timeline">{ms_html if ms_html else '<div style="color:#666;padding:16px;text-align:center">暂无里程碑 · 告诉 Hermes 添加一个吧</div>'}</div>
</div>

<div class="section">
  <h2 class="section-title"><span>🔮</span> 未来方向</h2>
  <div class="idea-card">
    <h4>📦 接入更多消息平台</h4>
    <p>配置 Telegram / Discord 等平台</p>
  </div>
  <div class="idea-card">
    <h4>🧩 集成更多工具链</h4>
    <p>gstack、Oh My Pi 等生态工具集成</p>
  </div>
</div>

<div class="footer">
  <p>v{version} · Hermes 进化记录 · 每日 9:00 自动更新</p>
  <p style="margin-top:4px">始于 {first.get('date','')[:10]} · 共 {days_active} 天</p>
</div>

<script>
const ctx=document.getElementById('chart').getContext('2d');
new Chart(ctx,{{
  type:'line',
  data:{{
    labels:{dates_json},
    datasets:[
      {{label:'技能数',data:{skill_counts_json},borderColor:'#667eea',backgroundColor:'rgba(102,126,234,0.1)',tension:0.3,fill:true,pointRadius:3,pointBackgroundColor:'#667eea'}},
      {{label:'Wiki 页面',data:{wiki_counts_json},borderColor:'#a78bfa',backgroundColor:'rgba(167,139,250,0.1)',tension:0.3,fill:true,pointRadius:3,pointBackgroundColor:'#a78bfa',yAxisID:'y1'}}
    ]
  }},
  options:{{
    responsive:true,
    plugins:{{legend:{{labels:{{color:'#888',font:{{size:12}}}},position:'top'}}}},
    scales:{{
      x:{{ticks:{{color:'#666',maxTicksLimit:10}},grid:{{color:'rgba(255,255,255,0.05)'}}}},
      y:{{beginAtZero:true,ticks:{{color:'#666'}},grid:{{color:'rgba(255,255,255,0.05)'}}}},
      y1:{{beginAtZero:true,position:'right',ticks:{{color:'#666'}},grid:{{display:false}}}}
    }}
  }}
}});
</script>
</body>
</html>"""
    
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
