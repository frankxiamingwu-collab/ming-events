#!/usr/bin/env python3
"""数据质检报告：抽样检查事件的日期/分类/地点/人物字段，输出统计。"""
import glob, json, os, random, re
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "*.jsonl")
CATS = {"战争", "起义", "政治", "南明", "清朝", "外交", "灾害", "社会", "文化", "人物"}

rows = []
for path in sorted(glob.glob(RAW)):
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                print("BAD JSON:", os.path.basename(path), ln)
                continue
            rows.append((os.path.basename(path), ln, o))

print("total rows:", len(rows))
problems = Counter()
for fn, ln, o in rows:
    d, p, n, c, s = (str(o.get(k, "")).strip() for k in ("d", "p", "n", "c", "s"))
    if not re.match(r"^\d{4}(-\d{1,2})?(-\d{1,2})?$", d):
        problems["bad date format"] += 1
    else:
        y = int(d[:4])
        if not (1627 <= y <= 1662):
            problems["date out of range"] += 1
    if not p:
        problems["missing place"] += 1
    if c not in CATS:
        problems["bad category: " + c] += 1
    if not s:
        problems["missing summary"] += 1
    if len(s) > 60:
        problems["summary too long"] += 1
    if n.count("|") > 8:
        problems["too many persons"] += 1

print("problems:", dict(problems) if problems else "none")
print("\nby year:")
years = Counter(int(str(o["d"])[:4]) for _, _, o in rows)
for y in range(1627, 1663):
    if years.get(y):
        print(f"  {y}: {years[y]}")
print("\nby category:", dict(Counter(o.get("c", "?") for _, _, o in rows)))
print("\nsample rows (5 random):")
for fn, ln, o in random.sample(rows, min(5, len(rows))):
    print(f"  [{fn}:{ln}] {o.get('d')} | {o.get('p')} | {o.get('n')} | {o.get('c')} | {o.get('s')[:40]}")
