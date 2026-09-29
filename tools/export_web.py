#!/usr/bin/env python3
"""从 events.db 导出网页用数据文件 web/data.js。"""
import json, os, sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "events.db")
OUT = os.path.join(BASE, "web", "data.js")

# 分类固定顺序
CATS = ["战争", "起义", "政治", "南明", "清朝", "外交", "灾害", "社会", "文化", "人物"]
# 时间段配色（与网页图例一致）
PERIODS = [
    {"id": 0, "label": "崇祯初政 1627–1635", "from": 1627, "to": 1635, "color": "#2c7fb8"},
    {"id": 1, "label": "崇祯中衰 1636–1641", "from": 1636, "to": 1641, "color": "#41ab5d"},
    {"id": 2, "label": "明末剧变 1642–1643", "from": 1642, "to": 1643, "color": "#f16913"},
    {"id": 3, "label": "甲申之变 1644", "from": 1644, "to": 1644, "color": "#d7301f"},
    {"id": 4, "label": "乙酉丙戌 1645–1646", "from": 1645, "to": 1646, "color": "#7b3294"},
    {"id": 5, "label": "永历前期 1647–1652", "from": 1647, "to": 1652, "color": "#c51b7d"},
    {"id": 6, "label": "永历后期 1653–1658", "from": 1653, "to": 1658, "color": "#8c510a"},
    {"id": 7, "label": "南明覆亡 1659–1662", "from": 1659, "to": 1662, "color": "#252525"},
]


def period_of(year):
    for p in PERIODS:
        if p["from"] <= year <= p["to"]:
            return p["id"]
    return 0


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, date_raw, precision, year, month, month_idx, place_norm, ming_province,"
        " lat, lon, persons, category, summary FROM events ORDER BY year, month_idx, id").fetchall()

    evs = []
    dropped = 0
    for r in rows:
        if r["lat"] is None or r["lon"] is None:
            dropped += 1
            continue
        evs.append([
            r["id"], r["date_raw"], r["month_idx"],
            round(r["lat"], 3), round(r["lon"], 3),
            r["category"], r["place_norm"], r["summary"], r["persons"],
            r["precision"], r["ming_province"],
        ])
    places = [dict(p) for p in con.execute("SELECT name, aliases, ming_province, lat, lon FROM places").fetchall()]
    total = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    con.close()

    meta = {
        "total": total, "mapped": len(evs), "dropped": dropped,
        "year_min": 1627, "year_max": 1662,
        "cats": CATS, "periods": PERIODS,
        "generated": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.META=" + json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + ";\n")
        f.write("window.EVENTS=" + json.dumps(evs, ensure_ascii=False, separators=(",", ":")) + ";\n")
        f.write("window.PLACES=" + json.dumps(places, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT}: {len(evs)} mapped events ({dropped} without coordinates), "
          f"{os.path.getsize(OUT)/1e6:.2f} MB")


if __name__ == "__main__":
    main()
