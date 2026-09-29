# 明清易代历史事件数据库 (1627–1662)

收录 **崇祯帝即位（1627）至南明永历帝遇难（1662）** 期间的重要历史事件，包含时间、地域、人名、分类四类信息，
存入本地 SQLite 数据库，并提供可交互网页：在明末中国地图上按时间轴逐步展示事件、按时间段着色。

## 目录结构

```
ming-events/
├── events.db              # 本地 SQLite 数据库（最终数据）
├── data/
│   ├── raw/*.jsonl        # 各批次事件原始数据（JSONL）
│   ├── gazetteer_north.csv / gazetteer_south.csv / gazetteer_extra.csv
│   │                      # 明代地名-坐标库（name,aliases,province,lat,lon）
│   └── china_provinces_v3.json   # 省界底图数据（DataV）
├── tools/
│   ├── build_map_data.py  # 省界 → 明代大区 GeoJSON
│   ├── build_db.py        # JSONL + gazetteer → events.db
│   ├── export_web.py      # events.db → web/data.js
│   └── qa_report.py       # 数据质检
├── web/
│   ├── index.html         # 交互网页入口（双击即可打开）
│   ├── app.js / style.css / data.js / ming_units.js
│   └── vendor/            # Leaflet 离线资源
└── serve.py               # 可选本地服务器
```

## 数据规模与内容

- 事件总数：__ 条（地图绘制 __ 条，其余缺坐标）
- 时间跨度：1627–1662（432 个月，时间轴按月滑动）
- 字段：日期（公历年月日/月/年，三级精度）、地点（明代地名+经纬度+布政使司）、人物、分类、摘要
- 分类：战争 / 起义 / 政治 / 南明 / 清朝 / 外交 / 灾害 / 社会 / 文化 / 人物

## 使用方法

1. **查看网页**：直接双击 `web/index.html`；或运行 `python3 serve.py` 后访问 <http://127.0.0.1:8686/web/>
2. **查询数据库**：
   ```bash
   python3 -c "import sqlite3; con=sqlite3.connect('events.db'); print(con.execute('select count(*) from events').fetchone())"
   ```
   常用查询：按年份 `SELECT * FROM events WHERE year=1644;`、全文检索 `SELECT * FROM events WHERE rowid IN (SELECT rowid FROM events_fts WHERE events_fts MATCH '李定国');`
3. **重新构建**：`python3 tools/build_db.py && python3 tools/export_web.py`

## 网页功能

- **时间轴滑动**（1627年1月–1662年12月）：事件按时间顺序在地图上出现；支持播放/暂停、速度（1月/3月/1年每步）、三种显示模式（累计出现 / 仅当前月 / 近十年内）
- **按时间段着色**：8 个时段各有专属颜色（崇祯初政→南明覆亡），图例可点击开关
- **分类筛选与关键词检索**（人名/地名/事件）
- **点击标记点**查看时间、地点、分类、人物、摘要；左侧列表可定位跳转
- 底图为 OpenStreetMap，叠加明代两京十三布政使司示意大区

## 数据说明

事件数据为明末清初史料（《明史》《明季北略》《南明野史》《清实录》《小腆纪年》等）整理汇编，
日期按公历标注，月份容有一两月误差；个别史籍记载有歧义者从通行说法。地图大区界线为示意性简化，
不代表精确的历史疆域。

## 验证

- `python3 tools/qa_report.py`：字段合法性、年份分布、分类分布、抽样
- `python3 tools/build_db.py`：输出地理编码命中率、未匹配地名清单
