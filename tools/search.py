#!/usr/bin/env python3
"""中文全文检索 events.db：python3 tools/search.py 关词 [条数]

例：python3 tools/search.py 李定国
    python3 tools/search.py 扬州 20
实现：FTS5 二元组(bigram)索引 + 短语查询，支持任意长度中文子串。"""
import os, re, sqlite3, sys

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "events.db")


def bigrams(s):
    s = re.sub(r"\s+", "", s or "")
    return " ".join(s[i:i + 2] for i in range(len(s) - 1)) if len(s) >= 2 else s


def search(kw, limit=10):
    con = sqlite3.connect(DB)
    if len(re.sub(r"\s+", "", kw)) < 2:
        rows = con.execute(
            "SELECT date_raw, place, persons, category, summary FROM events "
            "WHERE summary LIKE ? OR persons LIKE ? OR place LIKE ? ORDER BY year, month_idx LIMIT ?",
            (f"%{kw}%", f"%{kw}%", f"%{kw}%", limit)).fetchall()
    else:
        phrase = '"' + bigrams(kw) + '"'
        rows = con.execute(
            "SELECT e.date_raw, e.place, e.persons, e.category, e.summary FROM events e "
            "JOIN events_fts f ON f.rowid = e.id WHERE events_fts MATCH ? "
            "ORDER BY e.year, e.month_idx LIMIT ?", (phrase, limit)).fetchall()
    total = con.execute(
        "SELECT COUNT(*) FROM events WHERE summary LIKE ? OR persons LIKE ? OR place LIKE ?",
        (f"%{kw}%", f"%{kw}%", f"%{kw}%")).fetchone()[0]
    return total, rows


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    kw = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    total, rows = search(kw, limit)
    print(f"「{kw}」共 {total} 条，显示前 {len(rows)} 条：")
    for d, p, n, c, s in rows:
        print(f"  {d:11s} {p:6s} [{c}] {s}   ({n})")
