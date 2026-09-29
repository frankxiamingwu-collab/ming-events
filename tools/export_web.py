#!/usr/bin/env python3
"""从 events.db 导出网页用数据文件 web/data.js。"""
import json, os, sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "events.db")
OUT = os.path.join(BASE, "web", "data.js")

# 通用事件分类（跨时代适用）与配色
CATS = ["战争", "政治", "起义", "外交", "社会", "灾害", "文化", "人物"]
CAT_COLORS = {
    "战争": "#b03a2e",
    "政治": "#2c5f8a",
    "起义": "#d98324",
    "外交": "#23856d",
    "社会": "#7d5ba6",
    "灾害": "#8a6d1f",
    "文化": "#b0447a",
    "人物": "#5d6d7d",
}


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
        "cats": CATS, "cat_colors": CAT_COLORS,
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
