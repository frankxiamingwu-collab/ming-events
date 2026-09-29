/* 明清易代历史事件地图 — 交互逻辑
 * 数据: window.EVENTS = [[id, date_raw, month_idx, lat, lon, cat, place, summary, persons, precision, ming_province], ...]
 *       window.META  = {total, mapped, year_min, year_max, cats, periods}
 *       window.MING_UNITS = GeoJSON (明代大区)
 */
(function () {
  "use strict";

  const META = window.META;
  const EVENTS = window.EVENTS || [];
  const Y0 = META.year_min, Y1 = META.year_max;
  const MONTHS = (Y1 - Y0 + 1) * 12;          // 432
  const IDX = { id: 0, date: 1, m: 2, lat: 3, lon: 4, cat: 5, place: 6, sum: 7, per: 8, prec: 9, prov: 10 };

  /* ---------------- 地图 ---------------- */
  const map = L.map("map", { zoomControl: true, preferCanvas: true, minZoom: 4, maxZoom: 12 })
    .setView([32.5, 110.5], 5);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap 贡献者 | 明代政区为示意',
  }).addTo(map);

  // 明代大区着色
  if (window.MING_UNITS) {
    L.geoJSON(window.MING_UNITS, {
      style: (f) => ({
        fillColor: f.properties.color,
        fillOpacity: 0.32,
        color: f.properties.color,
        weight: 1.2,
        opacity: 0.9,
      }),
      onEachFeature: (f, layer) => {
        const b = layer.getBounds();
        if (b.isValid()) {
          L.marker(b.getCenter(), {
            icon: L.divIcon({ className: "unit-label", html: f.properties.label }),
            interactive: false,
          }).addTo(map);
        }
      },
    }).addTo(map);
  }

  const markerLayer = L.layerGroup().addTo(map);

  /* ---------------- 状态 ---------------- */
  let sliderIdx = MONTHS - 1;
  let mode = "cumulative";
  let query = "";
  const activeCats = new Set(META.cats);
  const activePeriods = new Set(META.periods.map((p) => p.id));
  const shown = new Map();   // id -> circleMarker
  let filtered = [];
  let playing = false, timer = null;

  const periodColor = (year) => {
    for (const p of META.periods) if (year >= p.from && year <= p.to) return p.color;
    return "#666";
  };
  const yearOf = (ev) => parseInt(ev[IDX.date], 10);
  const periodIdOf = (year) => {
    for (const p of META.periods) if (year >= p.from && year <= p.to) return p.id;
    return 0;
  };

  /* 确定性抖动：同城多事件散开，避免完全重叠 */
  function jitter(ev) {
    const h = (ev[IDX.id] * 2654435761) % 4294967296;
    const ang = ((h % 3600) / 3600) * Math.PI * 2;
    const rad = (((h >> 4) % 100) / 100) * 0.22 + 0.03;
    return [ev[IDX.lat] + Math.sin(ang) * rad * 0.62, ev[IDX.lon] + Math.cos(ang) * rad];
  }

  function passes(ev) {
    const cat = ev[IDX.cat];
    if (!activeCats.has(cat)) return false;
    if (!activePeriods.has(periodIdOf(yearOf(ev)))) return false;
    if (query) {
      const hay = (ev[IDX.sum] + " " + ev[IDX.per] + " " + ev[IDX.place] + " " + ev[IDX.date]).toLowerCase();
      if (!hay.includes(query)) return false;
    }
    return true;
  }

  function inTime(ev) {
    const m = ev[IDX.m];
    if (mode === "single") return m === sliderIdx;
    if (mode === "decade") return m <= sliderIdx && m > sliderIdx - 120;
    return m <= sliderIdx;
  }

  function popupHTML(ev) {
    return (
      '<div><span class="pop-date">' + ev[IDX.date] + '</span>' +
      '<span class="pop-cat">' + ev[IDX.cat] + "</span></div>" +
      '<div class="pop-place">' + ev[IDX.place] +
      (ev[IDX.prov] ? "（" + ev[IDX.prov] + "）" : "") + "</div>" +
      '<div class="pop-sum">' + ev[IDX.sum] + "</div>" +
      (ev[IDX.per] ? '<div class="pop-persons">人物：' + ev[IDX.per].split("|").join("、") + "</div>" : "")
    );
  }

  function makeMarker(ev) {
    const [la, lo] = jitter(ev);
    const y = yearOf(ev);
    return L.circleMarker([la, lo], {
      radius: 4.5,
      color: "#3a2c1e",
      weight: 0.6,
      fillColor: periodColor(y),
      fillOpacity: 0.85,
    }).bindPopup(popupHTML(ev), { maxWidth: 300 });
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
      div.style.borderLeftColor = periodColor(yearOf(ev));
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
    activePeriods.clear();
    META.periods.forEach((p) => activePeriods.add(p.id));
    sliderIdx = MONTHS - 1;
    timeline.value = sliderIdx;
    timeLabel.textContent = monthLabel(sliderIdx);
    mode = "cumulative";
    document.getElementById("mode").value = "cumulative";
    buildCatFilters();
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

  // 分类筛选
  function buildCatFilters() {
    const box = document.getElementById("cat-filters");
    box.innerHTML = "";
    for (const c of META.cats) {
      const div = document.createElement("div");
      div.className = "chip" + (activeCats.has(c) ? " active" : "");
      div.textContent = c;
      div.addEventListener("click", () => {
        if (activeCats.has(c)) activeCats.delete(c);
        else activeCats.add(c);
        div.classList.toggle("active", activeCats.has(c));
        applyFilters();
      });
      box.appendChild(div);
    }
  }

  // 图例
  function updateLegend() {
    const box = document.getElementById("period-legend");
    box.innerHTML = "";
    for (const p of META.periods) {
      const n = filtered.filter((ev) => periodIdOf(yearOf(ev)) === p.id).length;
      const div = document.createElement("div");
      div.className = "legend-item" + (activePeriods.has(p.id) ? "" : " off");
      div.innerHTML =
        '<span class="legend-swatch" style="background:' + p.color + '"></span>' +
        "<span>" + p.label + '</span><span class="legend-count">' + n + "</span>";
      div.addEventListener("click", () => {
        if (activePeriods.has(p.id)) activePeriods.delete(p.id);
        else activePeriods.add(p.id);
        applyFilters();
      });
      box.appendChild(div);
    }
  }

  // 模态框
  document.getElementById("btn-about").addEventListener("click", () =>
    document.getElementById("about-modal").classList.remove("hidden"));
  document.getElementById("btn-close-about").addEventListener("click", () =>
    document.getElementById("about-modal").classList.add("hidden"));

  /* ---------------- 启动 ---------------- */
  timeLabel.textContent = monthLabel(sliderIdx);
  buildCatFilters();
  applyFilters();
  const loading = document.getElementById("loading");
  if (loading) loading.remove();
  console.log("events loaded:", EVENTS.length);
})();
