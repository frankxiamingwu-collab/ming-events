#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 batch_09.jsonl：1646–1650 年（隆武二年至永历四年）历史事件。

格式见 ming-events/PROJECT.md：每行 {"d","p","n","c","s"}。
事件以元组 (d, p, n, c, s) 写入 EVENTS，脚本统一 json.dumps 输出。
分段追加：本文件按主题/年代多次编辑扩充。
"""
import json
import os
import sys

CATS = {"战争", "起义", "政治", "南明", "清朝", "外交", "灾害", "社会", "文化", "人物"}
YEARS = ("1646", "1647", "1648", "1649", "1650")

EVENTS = []

# === APPEND POINT ===


def main() -> int:
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "batch_09.jsonl"
    )
    out_path = os.path.normpath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    problems = []
    seen = set()
    with open(out_path, "w", encoding="utf-8") as f:
        for i, (d, p, n, c, s) in enumerate(EVENTS, 1):
            if c not in CATS:
                problems.append(f"line {i}: bad c={c}")
            if d[:4] not in YEARS:
                problems.append(f"line {i}: bad d={d}")
            if len(d) not in (4, 7, 10):
                problems.append(f"line {i}: odd date format {d}")
            if not (15 <= len(s) <= 45):
                problems.append(f"line {i}: s length {len(s)}: {s}")
            if not p:
                problems.append(f"line {i}: empty p")
            key = (d, p, n, s)
            if key in seen:
                problems.append(f"line {i}: duplicate {key}")
            seen.add(key)
            f.write(
                json.dumps({"d": d, "p": p, "n": n, "c": c, "s": s}, ensure_ascii=False)
                + "\n"
            )
    from collections import Counter

    yc = Counter(e[0][:4] for e in EVENTS)
    mc = Counter(e[0][:7] for e in EVENTS if len(e[0]) >= 7)
    print(f"wrote {len(EVENTS)} events -> {out_path}")
    print("year dist:", dict(sorted(yc.items())))
    missing_months = [f"{y}-{m:02d}" for y in YEARS for m in range(1, 13)
                      if mc.get(f"{y}-{m:02d}", 0) == 0]
    if missing_months:
        print("months with zero events:", missing_months)
    print("month counts:", dict(sorted(mc.items())))
    cc = Counter(e[3] for e in EVENTS)
    print("category dist:", dict(cc))
    if problems:
        print("PROBLEMS:", file=sys.stderr)
        for x in problems:
            print(" ", x, file=sys.stderr)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
