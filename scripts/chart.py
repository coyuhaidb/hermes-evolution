"""纯 Python 生成 SVG 趋势图，无需任何第三方库"""

import json
import os
import subprocess
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.config import PROJECT_DIR, DATA_FILE

# 颜色方案（深色主题）
BG_COLOR = "#1a1a2e"
TEXT_COLOR = "#e0e0e0"
GRID_COLOR = "#2a2a4e"
SKILL_COLOR = "#00d4aa"
WIKI_COLOR = "#7c6cf0"

WIDTH = 800
HEIGHT = 400
MARGIN = 60
PLOT_W = WIDTH - 2 * MARGIN
PLOT_H = HEIGHT - 2 * MARGIN


def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


def extract_series(data):
    snapshots = data["snapshots"]
    dates = []
    skill_counts = []
    wiki_counts = []
    for s in snapshots:
        dates.append(s["date"][5:10])
        skill_counts.append(s["skills"]["total"])
        wiki_counts.append(s["wiki"]["pages"])
    return dates, skill_counts, wiki_counts


def draw_line_svg(dates, series_list, labels, colors, title):
    """生成 SVG 折线图。series_list = [([vals],), ([vals],)]"""
    n = len(dates)
    if n < 2:
        return None

    all_vals = [v for series in series_list for v in series[0]]
    y_min = min(all_vals) - 1
    y_max = max(all_vals) + 1
    y_range = max(y_max - y_min, 2)

    def x_pos(i):
        return MARGIN + (i / (n - 1)) * PLOT_W if n > 1 else MARGIN + PLOT_W / 2

    def y_pos(v):
        return MARGIN + PLOT_H - ((v - y_min) / y_range) * PLOT_H

    lines = ""
    dots = ""

    for series, label, color in zip(series_list, labels, colors):
        vals = series[0]
        points = []
        for i, v in enumerate(vals):
            x = x_pos(i)
            y = y_pos(v)
            points.append(f"{x:.1f},{y:.1f}")
            dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}" />\n'
        lines += f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>\n'

    # X 轴标签
    x_labels = ""
    for i, d in enumerate(dates):
        if i % max(1, n // 8) == 0 or i == n - 1:
            x = x_pos(i)
            x_labels += f'<text x="{x:.1f}" y="{HEIGHT - MARGIN + 20}" text-anchor="middle" fill="{TEXT_COLOR}" font-size="11">{d}</text>\n'

    # Y 轴标签 + 网格线
    y_labels = ""
    for j in range(6):
        v = y_min + (j / 5) * y_range
        y = y_pos(v)
        y_labels += f'<text x="{MARGIN - 10}" y="{y + 4}" text-anchor="end" fill="{TEXT_COLOR}" font-size="11">{int(v)}</text>\n'
        y_labels += f'<line x1="{MARGIN}" y1="{y:.1f}" x2="{WIDTH - MARGIN}" y2="{y:.1f}" stroke="{GRID_COLOR}" stroke-width="0.5"/>\n'

    # 图例
    legend_x = WIDTH - MARGIN - 120
    legend_y = MARGIN + 10
    legend = ""
    for j, (label, color) in enumerate(zip(labels, colors)):
        ly = legend_y + j * 22
        legend += f'<line x1="{legend_x}" y1="{ly + 6}" x2="{legend_x + 18}" y2="{ly + 6}" stroke="{color}" stroke-width="2"/>\n'
        legend += f'<text x="{legend_x + 24}" y="{ly + 10}" fill="{TEXT_COLOR}" font-size="12">{label}</text>\n'

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="{WIDTH}" height="{HEIGHT}" fill="{BG_COLOR}"/>
  <text x="{WIDTH / 2}" y="25" text-anchor="middle" fill="{TEXT_COLOR}" font-size="14" font-weight="bold">{title}</text>
  {y_labels}
  {x_labels}
  {lines}
  {dots}
  {legend}
</svg>'''
    return svg


def generate_chart():
    data = load_data()
    dates, skills, wikis = extract_series(data)

    svg = draw_line_svg(
        dates,
        [(skills,), (wikis,)],
        ["技能数", "Wiki 页面"],
        [SKILL_COLOR, WIKI_COLOR],
        "📈 Hermes 进化趋势",
    )

    if svg is None:
        print("❌ 数据不足，无法生成图表")
        return None

    svg_path = os.path.join(PROJECT_DIR, "data", "trend.svg")
    png_path = os.path.join(PROJECT_DIR, "data", "trend.png")

    with open(svg_path, "w") as f:
        f.write(svg)

    # 转 PNG
    result = subprocess.run(
        ["convert", "-background", BG_COLOR, "-flatten", svg_path, png_path],
        capture_output=True, text=True, timeout=30,
    )

    os.remove(svg_path)

    if result.returncode == 0:
        size = os.path.getsize(png_path)
        print(f"✅ 趋势图已生成: {png_path} ({size / 1024:.0f}KB)")
        return png_path
    else:
        print(f"❌ PNG 转换失败: {result.stderr}")
        return None


if __name__ == "__main__":
    generate_chart()
