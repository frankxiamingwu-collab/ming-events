#!/usr/bin/env python3
"""把 data/raw/*.jsonl 事件数据与 gazetteer 地名库合并，构建 SQLite 数据库 events.db。

表结构：
  events(id, date_raw, precision, year, month, day, month_idx, place, ming_province,
         lat, lon, persons, category, summary, batch)
  places(name, aliases, ming_province, lat, lon)
  events_fts(summary, persons, place, content='events')   -- FTS5 全文检索
"""
import csv, glob, json, os, re, sqlite3, sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "data", "raw")
DB_PATH = os.path.join(BASE, "events.db")
GAZ_FILES = [
    os.path.join(BASE, "data", "gazetteer_core.csv"),
    os.path.join(BASE, "data", "gazetteer_north.csv"),
    os.path.join(BASE, "data", "gazetteer_south.csv"),
    os.path.join(BASE, "data", "gazetteer_extra.csv"),
]
YEAR_MIN, YEAR_MAX = 1627, 1662


def bigrams(s):
    """中文二元组索引串：'扬州之战' -> '扬州 州之 之战'"""
    s = re.sub(r"\s+", "", s or "")
    if len(s) < 2:
        return s
    return " ".join(s[i:i + 2] for i in range(len(s) - 1))


def load_gazetteer():
    name2geo = {}      # 主名/别名 -> (主名, lat, lon, province)
    canonical = {}     # 主名 -> (lat, lon, province, aliases)
    for path in GAZ_FILES:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) < 5:
                    continue
                name, aliases, prov, lat, lon = [c.strip() for c in row[:5]]
                if not name or name == "name":
                    continue
                try:
                    lat, lon = float(lat), float(lon)
                except ValueError:
                    continue
                canonical[name] = (lat, lon, prov, aliases)
                name2geo[name] = (name, lat, lon, prov)
                for a in aliases.split("|"):
                    a = a.strip()
                    if a:
                        name2geo.setdefault(a, (name, lat, lon, prov))
    return name2geo, canonical


def norm_place(place, name2geo):
    """返回 (主名, lat, lon, province) 或 None。"""
    p = place.strip().replace("（", "(").replace("）", ")")
    p = re.sub(r"\(.*?\)", "", p).strip()
    if not p:
        return None
    if p in name2geo:
        return name2geo[p]
    # 去掉常见后缀再试
    for suf in ("府", "州", "县", "卫", "所", "厅", "镇", "城"):
        if p.endswith(suf) and len(p) > 2:
            q = p[:-1]
            if q in name2geo:
                return name2geo[q]
            if q + "府" in name2geo:
                return name2geo[q + "府"]
            if q + "州" in name2geo:
                return name2geo[q + "州"]
            break
    # 加后缀
    for suf in ("府", "州", "县", "卫"):
        if p + suf in name2geo:
            return name2geo[p + suf]
    # 别名包含匹配（取最长别名命中）
    best = None
    for key, val in name2geo.items():
        if len(key) >= 2 and (key in p or p in key):
            if best is None or len(key) > len(best[0]):
                best = (key, val)
    if best and abs(len(best[0]) - len(p)) <= 4:
        return best[1]
    return None


def parse_date(d):
    m = re.match(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?$", d.strip())
    if not m:
        return None
    y = int(m.group(1))
    if not (YEAR_MIN <= y <= YEAR_MAX):
        return None
    mo = int(m.group(2)) if m.group(2) else None
    day = int(m.group(3)) if m.group(3) else None
    if mo is not None and not (1 <= mo <= 12):
        return None
    if day is not None and not (1 <= day <= 31):
        day = None
    if day:
        prec = "day"
    elif mo:
        prec = "month"
    else:
        prec = "year"
    mi_mo = mo if mo else 6  # 仅知年份者按年中处理
    month_idx = (y - YEAR_MIN) * 12 + (mi_mo - 1)
    return y, mo, day, prec, month_idx


def main():
    name2geo, canonical = load_gazetteer()
    print(f"gazetteer: {len(canonical)} canonical places, {len(name2geo)} keys")

    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.jsonl")))
    if not files:
        sys.exit("no raw jsonl files found")

    events = []
    unmatched = Counter()
    bad = []
    seen = set()
    for path in files:
        batch = os.path.basename(path).replace(".jsonl", "")
        with open(path, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError as e:
                    bad.append((batch, ln, str(e)))
                    continue
                d = parse_date(str(o.get("d", "")))
                if not d:
                    bad.append((batch, ln, f"bad date {o.get('d')}"))
                    continue
                y, mo, day, prec, mi = d
                place = str(o.get("p", "")).strip()
                cat = str(o.get("c", "")).strip()
                summ = str(o.get("s", "")).strip()
                persons = str(o.get("n", "")).strip()
                if not place or not summ:
                    bad.append((batch, ln, "missing place/summary"))
                    continue
                geo = norm_place(place, name2geo)
                if geo:
                    pname, lat, lon, prov = geo
                else:
                    pname, lat, lon, prov = place, None, None, ""
                    unmatched[place] += 1
                key = (y, mo, day, place, summ)
                if key in seen:
                    continue
                seen.add(key)
                events.append({
                    "date_raw": f"{y}-{mo:02d}-{day:02d}" if day else (f"{y}-{mo:02d}" if mo else str(y)),
                    "precision": prec, "year": y, "month": mo, "day": day, "month_idx": mi,
                    "place": place, "place_norm": pname, "ming_province": prov,
                    "lat": lat, "lon": lon, "persons": persons, "category": cat,
                    "summary": summ, "batch": batch,
                })

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE events (
        id INTEGER PRIMARY KEY,
        date_raw TEXT, precision TEXT,
        year INTEGER, month INTEGER, day INTEGER, month_idx INTEGER,
        place TEXT, place_norm TEXT, ming_province TEXT,
        lat REAL, lon REAL,
        persons TEXT, category TEXT, summary TEXT, batch TEXT
    );
    CREATE TABLE places (
        name TEXT PRIMARY KEY, aliases TEXT, ming_province TEXT, lat REAL, lon REAL
    );
    CREATE INDEX idx_events_month ON events(month_idx);
    CREATE INDEX idx_events_year ON events(year);
    CREATE INDEX idx_events_cat ON events(category);
    CREATE INDEX idx_events_place ON events(place_norm);
    CREATE INDEX idx_events_geo ON events(lat, lon);
    """)
    cur.executemany(
        "INSERT INTO events (date_raw,precision,year,month,day,month_idx,place,place_norm,"
        "ming_province,lat,lon,persons,category,summary,batch) VALUES "
        "(:date_raw,:precision,:year,:month,:day,:month_idx,:place,:place_norm,"
        ":ming_province,:lat,:lon,:persons,:category,:summary,:batch)", events)
    cur.executemany("INSERT OR REPLACE INTO places (name,aliases,ming_province,lat,lon) VALUES (?,?,?,?,?)",
                    [(n, a, p, la, lo) for n, (la, lo, p, a) in canonical.items()])
    try:
        # 中文子串检索：把文本拆成二元组(bigram)建索引，查询串同样拆成二元组成短语，
        # 可匹配任意长度（≥2字）的中文子串。
        cur.execute("CREATE VIRTUAL TABLE events_fts USING fts5(txt)")
        cur.executemany(
            "INSERT INTO events_fts(rowid, txt) VALUES (?, ?)",
            [(rid, bigrams(" ".join([s, p, pl])) ) for rid, s, p, pl in
             cur.execute("SELECT id, summary, persons, place FROM events").fetchall()])
    except sqlite3.OperationalError as e:
        print("FTS5 unavailable:", e)
    con.commit()

    n_geo = sum(1 for e in events if e["lat"] is not None)
    print(f"events: {len(events)} (geocoded {n_geo}, {n_geo*100.0/max(len(events),1):.1f}%)")
    print("bad rows:", len(bad))
    for b in bad[:10]:
        print("  ", b)
    print("unmatched places:", sum(unmatched.values()), "distinct:", len(unmatched))
    for p, c in unmatched.most_common(60):
        print(f"   {p}: {c}")
    print("\nby year:")
    for y in range(YEAR_MIN, YEAR_MAX + 1):
        n = sum(1 for e in events if e["year"] == y)
        if n:
            print(f"  {y}: {n}")
    print("\nby category:", dict(Counter(e["category"] for e in events)))
    con.close()
    print("wrote", DB_PATH)


if __name__ == "__main__":
    main()
