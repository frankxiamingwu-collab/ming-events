/* 明清易代历史事件地图 — 交互逻辑
 * 底图：自绘明末历史地图（政区设色 / 明代河流 / 明长城九边，无在线瓦片）
 * 数据: window.EVENTS = [[id, date_raw, month_idx, lat, lon, cat, place, summary, persons, precision, ming_province], ...]
 *       window.META  = {total, mapped, year_min, year_max, cats, cat_colors}
 */
(function () {
  "use strict";

  const META = window.META;
  const EVENTS = window.EVENTS || [];
  const Y0 = META.year_min, Y1 = META.year_max;
  const MONTHS = (Y1 - Y0 + 1) * 12;          // 432
  const IDX = { id: 0, date: 1, m: 2, lat: 3, lon: 4, cat: 5, place: 6, sum: 7, per: 8, prec: 9, prov: 10 };
  const CAT_COLOR = META.cat_colors || {};

  /* ---------------- 地图（自绘明末历史地图风格） ---------------- */
  const map = L.map("map", { zoomControl: true, preferCanvas: true, minZoom: 4, maxZoom: 10 })
    .setView([32.5, 110.5], 5);

  // 明代大区：设色底
  if (window.MING_UNITS) {
    L.geoJSON(window.MING_UNITS, {
      interactive: false,
      style: (f) => ({
        fillColor: f.properties.color,
        fillOpacity: 0.55,
        color: "#a9946c",
        weight: 1.1,
        opacity: 0.9,
      }),
      onEachFeature: (f, layer) => {
        // 标注置于最大图块的中心（多块政区/国家避免标注漂移）
        let best = null, bestA = -1;
        const geom = f.geometry;
        const polys = geom.type === "MultiPolygon" ? geom.coordinates : [geom.coordinates];
        for (const poly of polys) {
          const ring = poly[0];
          let a = 0;
          for (let i = 0; i < ring.length; i++) {
            const [x1, y1] = ring[i], [x2, y2] = ring[(i + 1) % ring.length];
            a += x1 * y2 - x2 * y1;
          }
          a = Math.abs(a / 2);
          if (a > bestA) { bestA = a; best = ring; }
        }
        if (!best) return;
        let x0 = Infinity, x1v = -Infinity, y0 = Infinity, y1v = -Infinity;
        for (const [px, py] of best) {
          if (px < x0) x0 = px; if (px > x1v) x1v = px;
          if (py < y0) y0 = py; if (py > y1v) y1v = py;
        }
        const c = [(y0 + y1v) / 2, (x0 + x1v) / 2];
        L.marker(c, {
          icon: L.divIcon({ className: f.properties.kind === "country" ? "country-label" : "unit-label", html: f.properties.label }),
          interactive: false,
        }).addTo(map);
      },
    }).addTo(map);
  }

  // 明代主要河流（示意走向，含明末黄河夺淮入海河道）
  const RIVERS = [
    { name: "黄河", pts: [[34.80, 113.70], [34.95, 114.40], [34.75, 115.55], [34.35, 117.15], [34.15, 118.15], [33.85, 118.90], [33.60, 119.30], [34.05, 119.60], [34.35, 119.85]] },
    { name: "长江", pts: [[30.70, 111.29], [30.35, 112.24], [29.72, 112.95], [30.59, 114.31], [29.71, 116.00], [30.51, 117.05], [30.96, 117.79], [31.34, 118.43], [32.06, 118.80], [32.19, 119.45], [32.20, 120.20], [31.90, 121.20], [31.50, 121.80]] },
    { name: "淮河", pts: [[32.37, 113.41], [32.62, 114.60], [32.87, 115.55], [32.63, 116.26], [32.87, 117.20], [33.05, 118.10], [33.35, 118.95], [33.55, 119.45]] },
    { name: "汉水", pts: [[30.58, 114.27], [31.20, 113.30], [32.01, 112.12], [32.55, 111.55], [33.00, 109.50], [33.07, 107.02]] },
    { name: "西江", pts: [[23.13, 113.26], [23.05, 112.47], [23.25, 111.60], [23.48, 111.28], [23.39, 110.08]] },
    { name: "郁江", pts: [[23.39, 110.08], [23.10, 109.20], [22.82, 108.32]] },
    { name: "赣江", pts: [[28.68, 115.86], [27.80, 115.30], [27.11, 114.99], [26.20, 114.80], [25.83, 114.94], [25.35, 114.35]] },
    { name: "运河", pts: [[39.90, 116.40], [39.13, 117.20], [37.50, 116.40], [36.84, 115.71], [35.41, 116.59], [34.26, 117.19], [33.60, 119.02], [32.39, 119.42], [32.19, 119.45], [31.38, 120.30], [30.75, 120.76], [30.27, 120.16]] },
    { name: "辽河", pts: [[41.80, 123.43], [41.27, 123.18], [40.90, 122.30], [40.75, 121.80]] },
    { name: "湘江", pts: [[28.23, 112.94], [27.83, 112.95], [26.89, 112.57], [26.42, 111.61], [25.79, 111.20]] },
    { name: "珠江", pts: [[23.13, 113.26], [22.78, 113.63], [22.53, 113.92]] },
    { name: "怒江", pts: [[25.50, 98.80], [24.60, 99.20], [23.50, 99.00], [22.20, 98.50]] },
    { name: "澜沧江", pts: [[26.00, 99.50], [24.00, 100.10], [22.50, 100.50], [21.20, 101.20]] },
  ];
  const riverPane = map.createPane("rivers");
  riverPane.style.zIndex = 450;
  for (const r of RIVERS) {
    L.polyline(r.pts, { pane: "rivers", color: "#6d8fa0", weight: 1.8, opacity: 0.85, interactive: false }).addTo(map);
    if (["黄河", "长江", "运河"].includes(r.name)) {
      L.marker(r.pts[Math.floor(r.pts.length / 2)], {
        icon: L.divIcon({ className: "river-label", html: r.name }),
        interactive: false,
        pane: "rivers",
      }).addTo(map);
    }
  }

  // 明长城（九边，示意）
  L.polyline(
    [[39.80, 98.27], [39.20, 100.30], [38.30, 102.50], [37.90, 104.20], [38.10, 106.50],
     [38.00, 107.80], [38.80, 109.70], [39.50, 111.50], [39.95, 112.40], [40.30, 113.30],
     [40.82, 114.90], [41.25, 115.75], [40.68, 117.12], [40.40, 117.20], [40.10, 118.30], [40.00, 119.75]],
    { color: "#8c5a2b", weight: 2.2, dashArray: "7 5", opacity: 0.9, interactive: false }
  ).addTo(map);
  L.marker([39.55, 111.60], {
    icon: L.divIcon({ className: "river-label", html: "长城 · 九边" }), interactive: false,
  }).addTo(map);

  const markerLayer = L.layerGroup().addTo(map);

  /* ---------------- 状态 ---------------- */
  let sliderIdx = MONTHS - 1;          // 默认 1662 年
  let mode = "recent3m";               // 默认显示长度：近三月内
  let query = "";
  const activeCats = new Set(META.cats);
  const shown = new Map();             // id -> circleMarker
  let filtered = [];
  let playing = false, timer = null;

  const yearOf = (ev) => parseInt(ev[IDX.date], 10);
  const catColor = (ev) => CAT_COLOR[ev[IDX.cat]] || "#666";

  /* 确定性抖动：同城多事件散开 */
  function jitter(ev) {
    const h = (ev[IDX.id] * 2654435761) % 4294967296;
    const ang = ((h % 3600) / 3600) * Math.PI * 2;
    const rad = (((h >> 4) % 100) / 100) * 0.22 + 0.03;
    return [ev[IDX.lat] + Math.sin(ang) * rad * 0.62, ev[IDX.lon] + Math.cos(ang) * rad];
  }

  function passes(ev) {
    if (!activeCats.has(ev[IDX.cat])) return false;
    if (query) {
      const hay = (ev[IDX.sum] + " " + ev[IDX.per] + " " + ev[IDX.place] + " " + ev[IDX.date]).toLowerCase();
      if (!hay.includes(query)) return false;
    }
    return true;
  }

  function inTime(ev) {
    const m = ev[IDX.m];
    switch (mode) {
      case "recent3m": return m <= sliderIdx && m > sliderIdx - 3;    // 近三月内
      case "recent3y": return m <= sliderIdx && m > sliderIdx - 36;   // 近三年内
      case "decade": return m <= sliderIdx && m > sliderIdx - 120;    // 近十年内
      default: return m <= sliderIdx;                                 // 累计出现
    }
  }

  function popupHTML(ev) {
    return (
      '<div><span class="pop-date">' + ev[IDX.date] + '</span>' +
      '<span class="pop-cat" style="background:' + catColor(ev) + '">' + ev[IDX.cat] + "</span></div>" +
      '<div class="pop-place">' + ev[IDX.place] +
      (ev[IDX.prov] ? "（" + ev[IDX.prov] + "）" : "") + "</div>" +
      '<div class="pop-sum">' + ev[IDX.sum] + "</div>" +
      (ev[IDX.per] ? '<div class="pop-persons">人物：' + ev[IDX.per].split("|").join("、") + "</div>" : "")
    );
  }

  function makeMarker(ev) {
    const [la, lo] = jitter(ev);
    const mk = L.circleMarker([la, lo], {
      radius: 5.5,
      color: "#3a2c1e",
      weight: 0.6,
      fillColor: catColor(ev),
      fillOpacity: 0.85,
    }).bindPopup(popupHTML(ev), { maxWidth: 300, closeButton: false, autoPan: false });
    return mk;
  }

  /* ---------------- 渲染 ---------------- */
  function render() {
    const wanted = new Set();
    for (const ev of filtered) {
      if (!inTime(ev)) continue;
      wanted.add(ev[IDX.id]);
      if (!shown.has(ev[IDX.id])) {
        const mk = makeMarker(ev);
        mk.addTo(markerLayer);
        shown.set(ev[IDX.id], mk);
      }
    }
    for (const [id, mk] of shown) {
      if (!wanted.has(id)) {
        markerLayer.removeLayer(mk);
        shown.delete(id);
      }
    }
    updateStats(wanted.size);
    renderList();
    hitCache = null;
  }

  function updateStats(visible) {
    document.getElementById("stats").innerHTML =
      "<span>收录事件 <b>" + META.total + "</b> 条</span>" +
      "<span>地图绘制 <b>" + META.mapped + "</b> 条</span>" +
      "<span>当前显示 <b>" + visible + "</b> 条</span>";
  }

  function renderList() {
    const box = document.getElementById("event-list");
    const items = filtered.filter(inTime).sort((a, b) => a[IDX.m] - b[IDX.m] || a[IDX.id] - b[IDX.id]);
    const recent = items.slice(-200).reverse();
    document.getElementById("list-count").textContent =
      "（" + items.length + " 条，显示最近 " + recent.length + " 条）";
    if (!recent.length) {
      box.innerHTML = '<div class="more-hint">当前条件下没有事件</div>';
      return;
    }
    const frag = document.createDocumentFragment();
    for (const ev of recent) {
      const div = document.createElement("div");
      div.className = "ev-item";
      div.style.borderLeftColor = catColor(ev);
      div.innerHTML =
        '<div><span class="ev-date">' + ev[IDX.date] + '</span><span class="ev-place">' +
        ev[IDX.place] + " · " + ev[IDX.cat] + "</span></div>" +
        '<div class="ev-sum">' + ev[IDX.sum] + "</div>" +
        (ev[IDX.per] ? '<div class="ev-persons">' + ev[IDX.per].split("|").join("、") + "</div>" : "");
      div.addEventListener("click", () => {
        map.setView([ev[IDX.lat], ev[IDX.lon]], Math.max(map.getZoom(), 7));
        const mk = shown.get(ev[IDX.id]);
        if (mk) mk.openPopup();
      });
      frag.appendChild(div);
    }
    box.innerHTML = "";
    box.appendChild(frag);
  }

  function applyFilters() {
    filtered = EVENTS.filter(passes);
    render();
    updateLegend();
  }

  /* ---------------- 控件 ---------------- */
  function monthLabel(idx) {
    const y = Y0 + Math.floor(idx / 12);
    return y + "年" + ((idx % 12) + 1) + "月";
  }

  const timeline = document.getElementById("timeline");
  const timeLabel = document.getElementById("time-label");
  timeline.max = MONTHS - 1;
  timeline.value = sliderIdx;

  timeline.addEventListener("input", () => {
    sliderIdx = parseInt(timeline.value, 10);
    timeLabel.textContent = monthLabel(sliderIdx);
    render();
  });

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" && e.target.type === "text") return;
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      sliderIdx = Math.max(0, Math.min(MONTHS - 1, sliderIdx + (e.key === "ArrowRight" ? 1 : -1)));
      timeline.value = sliderIdx;
      timeLabel.textContent = monthLabel(sliderIdx);
      render();
    }
    if (e.key === " ") { e.preventDefault(); togglePlay(); }
  });

  // 年份刻度
  const ticks = document.getElementById("ticks");
  for (let y = Y0; y <= Y1; y += 5) {
    const t = document.createElement("div");
    t.className = "tick";
    t.style.left = (((y - Y0) * 12) / (MONTHS - 1)) * 100 + "%";
    t.textContent = y;
    ticks.appendChild(t);
  }

  function togglePlay() {
    const btn = document.getElementById("btn-play");
    if (playing) {
      playing = false;
      clearInterval(timer);
      btn.textContent = "▶ 播放";
      return;
    }
    if (sliderIdx >= MONTHS - 1) {
      sliderIdx = 0;
      timeline.value = 0;
      timeLabel.textContent = monthLabel(0);
      render();
    }
    playing = true;
    btn.textContent = "⏸ 暂停";
    const step = parseInt(document.getElementById("speed").value, 10);
    timer = setInterval(() => {
      sliderIdx = Math.min(MONTHS - 1, sliderIdx + step);
      timeline.value = sliderIdx;
      timeLabel.textContent = monthLabel(sliderIdx);
      render();
      if (sliderIdx >= MONTHS - 1) togglePlay();
    }, 220);
  }
  document.getElementById("btn-play").addEventListener("click", togglePlay);
  document.getElementById("mode").addEventListener("change", (e) => {
    mode = e.target.value;
    render();
  });

  document.getElementById("btn-reset").addEventListener("click", () => {
    query = "";
    document.getElementById("search").value = "";
    activeCats.clear();
    META.cats.forEach((c) => activeCats.add(c));
    sliderIdx = MONTHS - 1;
    timeline.value = sliderIdx;
    timeLabel.textContent = monthLabel(sliderIdx);
    mode = "recent3m";
    document.getElementById("mode").value = "recent3m";
    applyFilters();
    map.setView([32.5, 110.5], 5);
  });

  // 搜索
  let searchTimer = null;
  document.getElementById("search").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      query = e.target.value.trim().toLowerCase();
      applyFilters();
    }, 180);
  });

  // 分类图例（着色 + 计数 + 开关）
  function updateLegend() {
    const box = document.getElementById("cat-legend");
    box.innerHTML = "";
    for (const c of META.cats) {
      const n = filtered.filter((ev) => ev[IDX.cat] === c).length;
      const div = document.createElement("div");
      div.className = "legend-item" + (activeCats.has(c) ? "" : " off");
      div.innerHTML =
        '<span class="legend-swatch" style="background:' + (CAT_COLOR[c] || "#666") + '"></span>' +
        "<span>" + c + '</span><span class="legend-count">' + n + "</span>";
      div.addEventListener("click", () => {
        if (activeCats.has(c)) activeCats.delete(c);
        else activeCats.add(c);
        applyFilters();
      });
      box.appendChild(div);
    }
  }

  /* --------- 命中检测：悬停弹出说明，移开自动关闭；点击（触屏）打开 --------- */
  let hitCache = null;      // [[x, y, marker], ...] 依当前视图缓存
  let hoveredMk = null;
  function nearestMarker(latlng, tolPx) {
    if (!hitCache) {
      hitCache = [];
      for (const mk of shown.values()) {
        const p = map.latLngToContainerPoint(mk.getLatLng());
        hitCache.push([p.x, p.y, mk]);
      }
    }
    const p = map.latLngToContainerPoint(latlng);
    let best = null, bestD = tolPx;
    for (const [x, y, mk] of hitCache) {
      const dx = x - p.x, dy = y - p.y;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d < bestD) { bestD = d; best = mk; }
    }
    return best;
  }
  map.on("zoomend moveend", () => { hitCache = null; });
  map.on("mousemove", (e) => {
    const mk = nearestMarker(e.latlng, 14);
    if (mk !== hoveredMk) {
      if (hoveredMk) hoveredMk.closePopup();
      hoveredMk = mk;
      if (mk) mk.openPopup();          // 悬停自动弹出
    }
  });
  map.on("mouseout", () => {
    if (hoveredMk) { hoveredMk.closePopup(); hoveredMk = null; }   // 移出地图自动关闭
  });
  map.on("click", (e) => {
    const mk = nearestMarker(e.latlng, 16);
    if (mk) mk.openPopup();            // 触屏/点击打开
  });

  // 模态框
  document.getElementById("btn-about").addEventListener("click", () =>
    document.getElementById("about-modal").classList.remove("hidden"));
  document.getElementById("btn-close-about").addEventListener("click", () =>
    document.getElementById("about-modal").classList.add("hidden"));

  /* ---------------- 启动 ---------------- */
  window.__APP__ = { map, shown };   // 供自动化测试/调试使用
  timeLabel.textContent = monthLabel(sliderIdx);
  applyFilters();
  const loading = document.getElementById("loading");
  if (loading) loading.remove();
  console.log("events loaded:", EVENTS.length);
})();
