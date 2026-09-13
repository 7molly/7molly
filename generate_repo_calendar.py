"""
Генерирует SVG-теплокарту (календарь) дат, когда репозитории пользователя
GitHub были запушены/обновлены (поле `pushed_at`), за последние 53 недели.

Переменные окружения:
    GH_USERNAME  - логин GitHub, чьи репозитории анализируем (обязательно)
    GH_TOKEN     - токен для авторизованных запросов к API (опционально,
                   но повышает лимит запросов; в Actions обычно
                   secrets.GITHUB_TOKEN)

Результат: assets/repo-calendar.svg
"""

import os
import sys
import datetime
import collections
import urllib.request
import json

USERNAME = os.environ.get("GH_USERNAME")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

if not USERNAME:
    print("GH_USERNAME env var is required", file=sys.stderr)
    sys.exit(1)

API_URL = "https://api.github.com"


def gh_get(path):
    req = urllib.request.Request(API_URL + path)
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def fetch_all_repos(username):
    repos = []
    page = 1
    while True:
        batch = gh_get(f"/users/{username}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def build_counts(repos):
    """date(YYYY-MM-DD) -> number of repos pushed that day"""
    counts = collections.Counter()
    for r in repos:
        pushed_at = r.get("pushed_at")
        if not pushed_at:
            continue
        day = pushed_at[:10]
        counts[day] += 1
    return counts


COLORS = ["#161b22", "#3730a3", "#4f46e5", "#6366f1", "#a5b4fc"]


def level_for(count):
    if count == 0:
        return 0
    if count == 1:
        return 1
    if count == 2:
        return 2
    if count <= 4:
        return 3
    return 4


def render_svg(counts, weeks=53):
    cell = 11
    gap = 3
    top_pad = 20
    left_pad = 30

    today = datetime.date.today()
    # Align to the most recent Saturday to keep a full grid
    end = today
    start = end - datetime.timedelta(days=weeks * 7 - 1)
    # shift start back to a Sunday
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)

    width = left_pad + weeks * (cell + gap) + 10
    height = top_pad + 7 * (cell + gap) + 10

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Segoe UI, Helvetica, Arial, sans-serif">',
        f'<rect width="100%" height="100%" fill="#0d1117" rx="8" />',
    ]

    day_labels = ["", "Mon", "", "Wed", "", "Fri", ""]
    for i, label in enumerate(day_labels):
        if label:
            y = top_pad + i * (cell + gap) + cell - 2
            svg_parts.append(
                f'<text x="4" y="{y}" font-size="9" fill="#8b949e">{label}</text>'
            )

    last_month = None
    current = start
    for week in range(weeks):
        x = left_pad + week * (cell + gap)
        month_label = current.strftime("%b")
        if month_label != last_month:
            svg_parts.append(
                f'<text x="{x}" y="12" font-size="9" fill="#8b949e">{month_label}</text>'
            )
            last_month = month_label
        for day in range(7):
            date = current + datetime.timedelta(days=day)
            if date > end:
                continue
            key = date.isoformat()
            count = counts.get(key, 0)
            color = COLORS[level_for(count)]
            y = top_pad + day * (cell + gap)
            title = f"{key}: {count} репо запушено"
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{color}"><title>{title}</title></rect>'
            )
        current += datetime.timedelta(days=7)

    # legend
    legend_x = left_pad
    legend_y = height - 4
    svg_parts.append(f'<text x="{legend_x}" y="{legend_y}" font-size="9" fill="#8b949e">Меньше</text>')
    lx = legend_x + 45
    for lvl, color in enumerate(COLORS):
        svg_parts.append(
            f'<rect x="{lx}" y="{legend_y - 9}" width="9" height="9" rx="2" fill="{color}" />'
        )
        lx += 12
    svg_parts.append(f'<text x="{lx + 4}" y="{legend_y}" font-size="9" fill="#8b949e">Больше</text>')

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def main():
    repos = fetch_all_repos(USERNAME)
    counts = build_counts(repos)
    svg = render_svg(counts)

    os.makedirs("assets", exist_ok=True)
    with open("assets/repo-calendar.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"OK: {len(repos)} repos processed, calendar written to assets/repo-calendar.svg")


if __name__ == "__main__":
    main()
