#!/usr/bin/env python3
"""把现代省界 GeoJSON 合并为明代布政使司（大区）单元，输出 web/ming_units.geojson。
同一大区内的省共享同一填充色，视觉上内部省界不显，大区界线以配色差异呈现。"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "data", "china_provinces_v3.json")
OUT = os.path.join(BASE, "web", "ming_units.geojson")

# 现代省级名 -> 明代单元
MING_UNITS = {
    "北直隶": ["北京市", "天津市", "河北省"],
    "南直隶": ["上海市", "江苏省", "安徽省"],
    "山东": ["山东省"],
    "辽东": ["辽宁省", "吉林省"],
    "山西": ["山西省"],
    "河南": ["河南省"],
    "陕西": ["陕西省", "甘肃省", "宁夏回族自治区", "青海省"],
    "浙江": ["浙江省"],
    "江西": ["江西省"],
    "湖广": ["湖北省", "湖南省"],
    "四川": ["四川省", "重庆市"],
    "福建": ["福建省"],
    "广东": ["广东省", "海南省"],
    "广西": ["广西壮族自治区"],
    "云南": ["云南省"],
    "贵州": ["贵州省"],
    "台湾": ["台湾省"],
}
# 不在明代版图内的周边区域（淡色作底）
OUTSIDE = ["内蒙古自治区", "黑龙江省", "新疆维吾尔自治区", "西藏自治区",
           "香港特别行政区", "澳门特别行政区"]

COLORS = {
    "北直隶": "#e8d8b0", "南直隶": "#d5e3c8", "山东": "#e5c9a8", "辽东": "#d9c4b3",
    "山西": "#ddd0b8", "河南": "#e3d4a2", "陕西": "#cfc6a8", "浙江": "#c9dcc9",
    "江西": "#d8cdb2", "湖广": "#d2d8b0", "四川": "#c7d2bb", "福建": "#cfd9c2",
    "广东": "#d9d3ac", "广西": "#ccc6a4", "云南": "#c2cdb4", "贵州": "#c9c2a6",
    "台湾": "#bfd3c6", "域外": "#dcdcdc",
}

def main():
    with open(SRC, encoding="utf-8") as f:
        src = json.load(f)

    prov2unit = {}
    for unit, provs in MING_UNITS.items():
        for p in provs:
            prov2unit[p] = unit
    for p in OUTSIDE:
        prov2unit[p] = "域外"

    geoms = {}   # unit -> list of polygons (each polygon = list of rings)
    missing = []
    for feat in src["features"]:
        name = feat["properties"].get("name", "")
        unit = prov2unit.get(name)
        if unit is None:
            missing.append(name)
            continue
        geom = feat.get("geometry") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates") or []
        polys = []
        if gtype == "Polygon":
            polys = [coords]
        elif gtype == "MultiPolygon":
            polys = coords
        geoms.setdefault(unit, []).extend(polys)

    out_features = []
    for unit, polys in geoms.items():
        out_features.append({
            "type": "Feature",
            "properties": {"name": unit, "label": unit, "color": COLORS.get(unit, "#cccccc")},
            "geometry": {"type": "MultiPolygon", "coordinates": polys},
        })
    fc = {"type": "FeatureCollection", "features": out_features}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    js = os.path.join(BASE, "web", "ming_units.js")
    with open(js, "w", encoding="utf-8") as f:
        f.write("window.MING_UNITS=")
        json.dump(fc, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    n = sum(len(v) for v in geoms.values())
    print(f"wrote {OUT}: {len(out_features)} units, {n} polygons")
    if missing:
        print("unassigned provinces:", missing)

if __name__ == "__main__":
    main()
