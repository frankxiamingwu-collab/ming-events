#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重绘明末历史地图底图 -> web/ming_units.js / web/ming_units.geojson

- 明末行政区划：两京（南、北直隶）+ 十三布政使司（山东山西河南陕西浙江江西湖广四川福建广东广西云南贵州）
  + 辽东都司、奴儿干都司、乌思藏都司、朵甘都司、西域诸部、漠南蒙古、台湾
- 邻国（着色并标注）：朝鲜、日本、琉球（手工绘制岛链）、缅甸、越南
- 其余周边：塞外诸部（灰色）
"""
import glob, json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROV = os.path.join(BASE, "data", "china_provinces_v3.json")
WORLD = os.path.join(BASE, "data", "world")
OUT_JS = os.path.join(BASE, "web", "ming_units.js")
OUT_GJ = os.path.join(BASE, "web", "ming_units.geojson")

# 现代省份 -> 明末政区
MING_UNITS = {
    "北直隶": (["北京市", "天津市", "河北省"], "#e8d8b0"),
    "南直隶": (["上海市", "江苏省", "安徽省"], "#d5e3c8"),
    "山东": (["山东省"], "#e5c9a8"),
    "山西": (["山西省"], "#ddd0b8"),
    "河南": (["河南省"], "#e3d4a2"),
    "陕西": (["陕西省", "甘肃省", "宁夏回族自治区"], "#cfc6a8"),
    "浙江": (["浙江省"], "#c9dcc9"),
    "江西": (["江西省"], "#d8cdb2"),
    "湖广": (["湖北省", "湖南省"], "#d2d8b0"),
    "四川": (["四川省", "重庆市"], "#c7d2bb"),
    "福建": (["福建省"], "#cfd9c2"),
    "广东": (["广东省", "海南省", "香港特别行政区", "澳门特别行政区"], "#d9d3ac"),
    "广西": (["广西壮族自治区"], "#ccc6a4"),
    "云南": (["云南省"], "#c2cdb4"),
    "贵州": (["贵州省"], "#c9c2a6"),
    "辽东都司": (["辽宁省"], "#d9c4b3"),
    "奴儿干都司": (["吉林省", "黑龙江省"], "#cfc0b2"),
    "乌思藏都司": (["西藏自治区"], "#c8c3ab"),
    "朵甘都司": (["青海省"], "#c6c7a9"),
    "西域诸部": (["新疆维吾尔自治区"], "#d3cdb2"),
    "漠南蒙古": (["内蒙古自治区"], "#d8d3bd"),
    "台湾": (["台湾省"], "#bfd3c6"),
}
# 着色并标注的邻国
NAMED = {
    "朝鲜": (["KOR", "PRK"], "#d3c7a2"),
    "日本": (["JPN"], "#c6c3a2"),
    "缅甸": (["MMR"], "#cdb9a3"),
    "越南": (["VNM"], "#c2cdb4"),
}
# 其余周边（灰色）
OTHERS = ["MNG", "RUS", "KAZ", "KGZ", "TJK", "AFG", "UZB", "TKM", "IND", "PAK",
          "NPL", "BGD", "BTN", "LKA", "THA", "LAO", "KHM", "PHL", "MYS", "IDN", "BRN"]

# 琉球王国岛链（示意多边形，沿琉球弧）
RYUKYU = [[[
    [129.5, 31.9], [130.0, 30.3], [129.5, 28.3], [128.5, 27.3], [127.8, 26.3],
    [125.4, 24.8], [124.0, 24.2], [123.3, 23.9],
    [123.0, 24.6], [124.5, 25.3], [127.2, 26.7], [128.9, 27.8], [130.3, 29.5],
    [130.6, 31.2], [129.5, 31.9],
]]]


def polys_of(geom):
    g = geom or {}
    t, cs = g.get("type"), g.get("coordinates") or []
    if t == "Polygon":
        return [cs]
    if t == "MultiPolygon":
        return cs
    return []


def load_world(code):
    for f in (os.path.join(WORLD, f"{code}.geo.json"),):
        if os.path.exists(f):
            d = json.load(open(f, encoding="utf-8"))
            feats = d["features"] if d.get("type") == "FeatureCollection" else [d]
            out = []
            for ft in feats:
                out.extend(polys_of(ft.get("geometry")))
            return out
    return []


def main():
    features = []
    src = json.load(open(PROV, encoding="utf-8"))

    # 1) 明末政区
    prov2unit = {}
    for unit, (provs, _c) in MING_UNITS.items():
        for p in provs:
            prov2unit[p] = unit
    geoms, missing = {}, []
    for feat in src["features"]:
        name = feat["properties"].get("name", "")
        unit = prov2unit.get(name)
        if unit is None:
            missing.append(name)
            continue
        geoms.setdefault(unit, []).extend(polys_of(feat.get("geometry")))
    for unit, (_provs, color) in MING_UNITS.items():
        if unit not in geoms:
            continue
        features.append({
            "type": "Feature",
            "properties": {"name": unit, "label": unit, "color": color, "kind": "ming"},
            "geometry": {"type": "MultiPolygon", "coordinates": geoms[unit]},
        })

    # 2) 着色邻国
    for label, (codes, color) in NAMED.items():
        polys = []
        for c in codes:
            polys.extend(load_world(c))
        if polys:
            features.append({
                "type": "Feature",
                "properties": {"name": label, "label": label, "color": color, "kind": "country"},
                "geometry": {"type": "MultiPolygon", "coordinates": polys},
            })

    # 3) 琉球（手工）
    features.append({
        "type": "Feature",
        "properties": {"name": "琉球", "label": "琉球", "color": "#bfcfbc", "kind": "country"},
        "geometry": {"type": "MultiPolygon", "coordinates": RYUKYU},
    })

    # 4) 塞外诸部（灰）
    others = []
    for c in OTHERS:
        others.extend(load_world(c))
    if others:
        features.append({
            "type": "Feature",
            "properties": {"name": "塞外诸部", "label": "塞外诸部", "color": "#dcdcdc", "kind": "other"},
            "geometry": {"type": "MultiPolygon", "coordinates": others},
        })

    fc = {"type": "FeatureCollection", "features": features}
    with open(OUT_GJ, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("window.MING_UNITS=")
        json.dump(fc, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    n = sum(len(v) for v in geoms.values())
    print(f"wrote {OUT_JS}")
    print(f"  明末政区 {sum(1 for f in features if f['properties']['kind']=='ming')} 个（{n} 面）")
    print(f"  邻国 {sum(1 for f in features if f['properties']['kind']=='country')} 个（含琉球）")
    print(f"  塞外诸部 {sum(1 for f in features if f['properties']['kind']=='other')} 个")
    if missing:
        print("  未归类省份:", missing)


if __name__ == "__main__":
    main()
