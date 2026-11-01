/*
 * power-flow-pipes-card
 * Plumbing-style animated power flow card for Home Assistant.
 * Sources (solar, grid, battery) feed an inverter hub, which feeds the house,
 * which feeds a manifold of metered circuits. Dot speed and pipe width scale
 * with power. Vanilla custom element, no build step.
 *
 * Sign conventions (override with invert: true):
 *   battery.power  positive = discharging, negative = charging
 *   grid.power     positive = importing,   negative = exporting
 */

const VB_W = 1000;
const VB_H = 560;

const COLORS = {
  solar: "#F4C430",
  gridImport: "#E5534B",
  gridExport: "#3FB950",
  batteryDischarge: "#A371F7",
  batteryCharge: "#3FB950",
  home: "#4FC3F7",
  load: "#4FC3F7",
  idle: "rgba(127,127,127,0.35)",
};

// Node centers / sizes in viewBox units
const N = {
  solar: { x: 380, y: 80, w: 170, h: 110 },
  grid: { x: 110, y: 280, w: 140, h: 120 },
  inverter: { x: 380, y: 280, w: 120, h: 90 },
  battery: { x: 380, y: 480, w: 170, h: 120 },
  home: { x: 600, y: 280, w: 120, h: 120 },
};
const SPINE_X = 705;
const LOAD_X = 790; // left edge of load tiles
const LOAD_W = 200;

const fmtW = (w) => {
  if (w == null || isNaN(w)) return "—";
  const a = Math.abs(w);
  if (a >= 1000) return `${(w / 1000).toFixed(a >= 10000 ? 1 : 2)} kW`;
  return `${Math.round(w)} W`;
};
const fmtKwh = (v) => (v == null || isNaN(v) ? "—" : `${(+v).toFixed(1)} kWh`);
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

class PowerFlowPipesCard extends HTMLElement {
  setConfig(config) {
    if (!config.home || !config.home.power) throw new Error("home.power is required");
    this._config = {
      threshold: 20,
      max_power: 12000,
      show_other: true,
      sort_loads: false,
      ...config,
    };
    this._built = false;
    this._flows = {};
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    if (!this._built) this._build();
    this._update();
  }

  getCardSize() {
    return 7;
  }

  connectedCallback() {
    this._reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    this._last = performance.now();
    const tick = (t) => {
      const dt = Math.min(0.1, (t - this._last) / 1000);
      this._last = t;
      for (const f of Object.values(this._flows)) {
        if (!f.speed) continue;
        f.offset = (f.offset - f.speed * dt) % 1000;
        f.dots.style.strokeDashoffset = f.offset;
      }
      this._raf = requestAnimationFrame(tick);
    };
    if (!this._reduceMotion) this._raf = requestAnimationFrame(tick);
  }

  disconnectedCallback() {
    cancelAnimationFrame(this._raf);
  }

  // ---------- helpers ----------
  _num(entity) {
    if (!entity || !this._hass) return null;
    const s = this._hass.states[entity];
    if (!s) return null;
    const v = parseFloat(s.state);
    return isNaN(v) ? null : v;
  }

  _moreInfo(entityId) {
    if (!entityId) return;
    const ev = new Event("hass-more-info", { bubbles: true, composed: true });
    ev.detail = { entityId };
    this.dispatchEvent(ev);
  }

  _loads() {
    return (this._config.loads || []).map((l) => (typeof l === "string" ? { entity: l } : l));
  }

  // ---------- DOM build ----------
  _build() {
    this._built = true;
    const c = this._config;
    const loads = this._loads();
    const rows = loads.length + (c.show_other ? 1 : 0);
    const top = 34;
    const bottom = VB_H - 34;
    const step = rows > 1 ? (bottom - top) / (rows - 1) : 0;
    this._rowY = Array.from({ length: rows }, (_, i) => (rows > 1 ? top + i * step : N.home.y));
    this._rowH = clamp(step - 8, 30, 56);

    const root = this.shadowRoot || this.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>${this._css()}</style>
      <ha-card>
        ${c.title ? `<div class="title">${c.title}</div>` : ""}
        <div class="stage">
          <svg viewBox="0 0 ${VB_W} ${VB_H}" preserveAspectRatio="xMidYMid meet"></svg>
          <div class="nodes"></div>
        </div>
      </ha-card>`;
    this._svg = root.querySelector("svg");
    this._nodes = root.querySelector(".nodes");

    // Pipes (drawn first so nodes sit on top)
    const sv = N.solar, iv = N.inverter, bv = N.battery, gv = N.grid, hv = N.home;
    if (c.solar) this._pipe("solar", `M${sv.x},${sv.y + sv.h / 2} V${iv.y - iv.h / 2}`);
    if (c.grid) this._pipe("grid", `M${gv.x + gv.w / 2},${gv.y} H${iv.x - iv.w / 2}`);
    if (c.battery) this._pipe("battery", `M${bv.x},${bv.y - bv.h / 2} V${iv.y + iv.h / 2}`);
    this._pipe("home", `M${iv.x + iv.w / 2},${iv.y} H${hv.x - hv.w / 2}`);

    // Manifold: home -> spine (up and down) -> branches
    const hx = hv.x + hv.w / 2;
    const r = 14;
    const yTop = this._rowY[0];
    const yBot = this._rowY[rows - 1];
    if (yTop < hv.y - r) this._pipe("spineUp", `M${hx},${hv.y} H${SPINE_X - r} Q${SPINE_X},${hv.y} ${SPINE_X},${hv.y - r} V${yTop}`);
    if (yBot > hv.y + r) this._pipe("spineDown", `M${hx},${hv.y} H${SPINE_X - r} Q${SPINE_X},${hv.y} ${SPINE_X},${hv.y + r} V${yBot}`);
    this._rowY.forEach((y, i) => this._pipe(`load${i}`, `M${SPINE_X},${y} H${LOAD_X}`, true));

    // Spine junction caps
    const ns = "http://www.w3.org/2000/svg";
    const cap = document.createElementNS(ns, "circle");
    cap.setAttribute("cx", SPINE_X);
    cap.setAttribute("cy", hv.y);
    cap.setAttribute("r", 9);
    cap.setAttribute("class", "joint");
    this._svg.appendChild(cap);

    // Nodes
    if (c.solar) this._node("solar", "mdi:solar-power-variant", "Solar", [].concat(c.solar.power)[0]);
    if (c.grid) this._node("grid", "mdi:transmission-tower", "Grid", c.grid.power);
    if (c.battery) this._node("battery", "mdi:battery-high", "Battery", c.battery.soc || c.battery.power);
    this._node("inverter", "mdi:sine-wave", "Inverter", c.inverter?.power);
    this._node("home", "mdi:home-lightning-bolt", "Home", c.home.power);

    // Summary (top-left) and forecast (bottom-left)
    this._summary = this._el("div", "summary", `
      <div class="stat"><span class="k">Self-powered now</span><span class="v" data-k="selfNow">—</span></div>
      <div class="stat"><span class="k">Self-powered today</span><span class="v" data-k="selfDay">—</span></div>`);
    this._place(this._summary, 20, 22, null, null, false);
    this._extra = this._el("div", "summary bottom", `
      <div class="stat"><span class="k">Solar remaining today</span><span class="v" data-k="remaining">—</span></div>
      <div class="stat"><span class="k">Net grid today</span><span class="v" data-k="netGrid">—</span></div>`);
    this._place(this._extra, 20, VB_H - 22, null, null, false, true);

    // Load tiles
    this._loadEls = this._rowY.map((y, i) => {
      const el = this._el("div", "load", `
        <ha-icon></ha-icon>
        <div class="ltext"><div class="lname"></div><div class="lsub"></div></div>
        <div class="lval"></div>
        <div class="lbar"><div></div></div>`);
      el.style.left = `${(LOAD_X / VB_W) * 100}%`;
      el.style.top = `${((y - this._rowH / 2) / VB_H) * 100}%`;
      el.style.width = `${(LOAD_W / VB_W) * 100}%`;
      el.style.height = `${(this._rowH / VB_H) * 100}%`;
      el.addEventListener("click", () => this._moreInfo(el._entity));
      this._nodes.appendChild(el);
      return el;
    });
  }

  _pipe(key, d, branch = false) {
    const ns = "http://www.w3.org/2000/svg";
    const g = document.createElementNS(ns, "g");
    g.setAttribute("class", `pipe${branch ? " branch" : ""}`);
    const mk = (cls) => {
      const p = document.createElementNS(ns, "path");
      p.setAttribute("d", d);
      p.setAttribute("class", cls);
      g.appendChild(p);
      return p;
    };
    const wall = mk("wall");
    const glow = mk("glow");
    const core = mk("core");
    const dots = mk("dots");
    this._svg.appendChild(g);
    this._flows[key] = { g, wall, glow, core, dots, offset: 0, speed: 0 };
  }

  _setFlow(key, watts, color, reverse = false) {
    const f = this._flows[key];
    if (!f) return;
    const c = this._config;
    const a = Math.abs(watts || 0);
    const active = a >= c.threshold;
    const frac = clamp(a / c.max_power, 0, 1);
    const isBranch = f.g.classList.contains("branch");
    const base = isBranch ? 5 : 8;
    const w = base + (isBranch ? 7 : 12) * Math.sqrt(frac);
    f.wall.style.strokeWidth = w + 6;
    f.core.style.strokeWidth = w;
    f.glow.style.strokeWidth = w + 14;
    f.dots.style.strokeWidth = Math.max(3, w * 0.55);
    const gap = Math.max(16, w * 2.2);
    f.dots.style.strokeDasharray = `0 ${gap}`;
    f.core.style.stroke = active ? color : COLORS.idle;
    f.glow.style.stroke = color;
    f.glow.style.opacity = active ? 0.12 + 0.25 * Math.sqrt(frac) : 0;
    f.core.style.opacity = active ? 0.55 + 0.35 * Math.sqrt(frac) : 0.5;
    f.dots.style.opacity = active ? 1 : 0;
    // px/s along the path; sqrt keeps small loads visibly moving
    const speed = active ? 18 + 260 * Math.sqrt(frac) : 0;
    f.speed = reverse ? -speed : speed;
    if (this._reduceMotion) f.speed = 0;
  }

  _el(tag, cls, html) {
    const el = document.createElement(tag);
    el.className = cls;
    if (html) el.innerHTML = html;
    return el;
  }

  _place(el, x, y, w, h, center = true, fromBottom = false) {
    el.style.left = `${(x / VB_W) * 100}%`;
    if (fromBottom) el.style.bottom = `${((VB_H - y) / VB_H) * 100}%`;
    else el.style.top = `${(y / VB_H) * 100}%`;
    if (w) el.style.width = `${(w / VB_W) * 100}%`;
    if (h) el.style.height = `${(h / VB_H) * 100}%`;
    if (center) el.style.transform = "translate(-50%, -50%)";
    this._nodes.appendChild(el);
  }

  _node(key, icon, label, entity) {
    const n = N[key];
    const el = this._el("div", `node ${key}`, `
      ${key === "battery" ? `<div class="soc"></div>` : ""}
      <div class="head"><ha-icon icon="${icon}"></ha-icon><span>${label}</span></div>
      <div class="val">—</div>
      <div class="sub"></div>`);
    el.addEventListener("click", () => this._moreInfo(entity));
    this._place(el, n.x, n.y, n.w, n.h);
    this[`_${key}El`] = el;
  }

  // ---------- update ----------
  _update() {
    const c = this._config;
    const set = (el, sel, txt) => {
      const t = el.querySelector(sel);
      if (t && t.textContent !== txt) t.textContent = txt;
    };

    // Solar
    let pv = 0;
    if (c.solar) {
      const ents = [].concat(c.solar.power);
      const parts = ents.map((e) => this._num(e) || 0);
      pv = parts.reduce((a, b) => a + b, 0);
      set(this._solarEl, ".val", fmtW(pv));
      const names = c.solar.names || ents.map((_, i) => `PV${i + 1}`);
      const strings = ents.length > 1 ? parts.map((p, i) => `${names[i]} ${fmtW(p)}`).join(" · ") : "";
      const day = c.solar.daily ? `Today ${fmtKwh(this._num(c.solar.daily))}` : "";
      set(this._solarEl, ".sub", [strings, day].filter(Boolean).join("\n"));
      this._solarEl.classList.toggle("active", pv >= c.threshold);
      this._setFlow("solar", pv, COLORS.solar);
    }

    // Grid (positive = import)
    let grid = 0;
    if (c.grid) {
      grid = (this._num(c.grid.power) || 0) * (c.grid.invert ? -1 : 1);
      const importing = grid >= 0;
      const connected = c.grid.connected ? this._hass.states[c.grid.connected]?.state !== "off" : true;
      set(this._gridEl, ".val", connected ? fmtW(Math.abs(grid)) : "Off-grid");
      const dir = Math.abs(grid) < c.threshold ? "Idle" : importing ? "Importing" : "Exporting";
      const imp = this._num(c.grid.daily_import);
      const exp = this._num(c.grid.daily_export);
      const today = imp != null || exp != null ? `↓ ${fmtKwh(imp)}  ↑ ${fmtKwh(exp)}` : "";
      set(this._gridEl, ".sub", [dir, today].filter(Boolean).join("\n"));
      this._gridEl.classList.toggle("offgrid", !connected);
      this._gridEl.style.setProperty("--accent", importing ? COLORS.gridImport : COLORS.gridExport);
      this._gridEl.classList.toggle("active", Math.abs(grid) >= c.threshold);
      this._setFlow("grid", grid, importing ? COLORS.gridImport : COLORS.gridExport, !importing);
    }

    // Battery (positive = discharge)
    if (c.battery) {
      const bp = (this._num(c.battery.power) || 0) * (c.battery.invert ? -1 : 1);
      const soc = this._num(c.battery.soc);
      const discharging = bp >= 0;
      const color = discharging ? COLORS.batteryDischarge : COLORS.batteryCharge;
      set(this._batteryEl, ".val", `${soc != null ? Math.round(soc) + "%" : ""}  ${fmtW(Math.abs(bp))}`.trim());
      let eta = "";
      if (c.battery.capacity_wh && soc != null && Math.abs(bp) >= c.threshold) {
        const floor = c.battery.shutdown_soc || 0;
        const wh = discharging
          ? ((soc - floor) / 100) * c.battery.capacity_wh
          : ((100 - soc) / 100) * c.battery.capacity_wh;
        const hrs = wh / Math.abs(bp);
        if (hrs > 0 && hrs < 100) {
          const h = Math.floor(hrs);
          const m = Math.round((hrs - h) * 60);
          eta = `${discharging ? "Empty" : "Full"} in ${h}h ${m}m`;
        }
      }
      const dir = Math.abs(bp) < c.threshold ? "Idle" : discharging ? "Discharging" : "Charging";
      const chg = this._num(c.battery.daily_charge);
      const dis = this._num(c.battery.daily_discharge);
      const today = chg != null || dis != null ? `+${fmtKwh(chg)}  −${fmtKwh(dis)}` : "";
      set(this._batteryEl, ".sub", [eta ? `${dir} · ${eta}` : dir, today].filter(Boolean).join("\n"));
      const socEl = this._batteryEl.querySelector(".soc");
      socEl.style.height = `${clamp(soc || 0, 0, 100)}%`;
      socEl.style.background = soc < 20 ? COLORS.gridImport : soc < 50 ? COLORS.solar : COLORS.batteryCharge;
      const icon = this._batteryEl.querySelector("ha-icon");
      const lvl = clamp(Math.round((soc || 0) / 10) * 10, 10, 100);
      icon.setAttribute("icon", !discharging && Math.abs(bp) >= c.threshold
        ? `mdi:battery-charging-${lvl}`
        : lvl === 100 ? "mdi:battery" : `mdi:battery-${lvl}`);
      this._batteryEl.style.setProperty("--accent", color);
      this._batteryEl.classList.toggle("active", Math.abs(bp) >= c.threshold);
      this._setFlow("battery", bp, color, !discharging);
    }

    // Inverter
    const inv = this._num(c.inverter?.power);
    const temp = this._num(c.inverter?.temperature);
    const tUnit = c.inverter?.temperature ? this._hass.states[c.inverter.temperature]?.attributes.unit_of_measurement || "" : "";
    set(this._inverterEl, ".val", inv != null ? fmtW(inv) : "");
    set(this._inverterEl, ".sub", temp != null ? `${Math.round(temp)}${tUnit}` : "");

    // Home
    const home = this._num(c.home.power) || 0;
    set(this._homeEl, ".val", fmtW(home));
    set(this._homeEl, ".sub", c.home.daily ? `Today ${fmtKwh(this._num(c.home.daily))}` : "");
    this._homeEl.classList.toggle("active", home >= c.threshold);
    this._setFlow("home", home, COLORS.home);

    // Summary
    const gridIn = Math.max(0, grid);
    const selfNow = home > 0 ? clamp(1 - gridIn / home, 0, 1) : null;
    const dayLoad = this._num(c.home.daily);
    const dayImp = this._num(c.grid?.daily_import);
    const selfDay = dayLoad ? clamp(1 - (dayImp || 0) / dayLoad, 0, 1) : null;
    set(this._summary, '[data-k="selfNow"]', selfNow == null ? "—" : `${Math.round(selfNow * 100)}%`);
    set(this._summary, '[data-k="selfDay"]', selfDay == null ? "—" : `${Math.round(selfDay * 100)}%`);
    const rem = this._num(c.solar?.forecast_remaining);
    set(this._extra, '[data-k="remaining"]', rem == null ? "—" : fmtKwh(rem));
    const dayExp = this._num(c.grid?.daily_export);
    const net = dayImp != null || dayExp != null ? (dayImp || 0) - (dayExp || 0) : null;
    set(this._extra, '[data-k="netGrid"]', net == null ? "—" : `${net > 0 ? "+" : ""}${fmtKwh(net)}`);

    // Loads
    let rows = this._loads().map((l) => {
      const p = Math.max(0, this._num(l.entity) || 0);
      const st = this._hass.states[l.entity];
      return {
        entity: l.entity,
        name: l.name || st?.attributes.friendly_name || l.entity,
        icon: l.icon || st?.attributes.icon || "mdi:flash",
        power: p,
        daily: l.daily ? this._num(l.daily) : null,
        color: l.color || COLORS.load,
      };
    });
    if (c.sort_loads) rows.sort((a, b) => b.power - a.power);
    if (c.show_other) {
      const metered = rows.reduce((a, r) => a + r.power, 0);
      rows.push({
        entity: c.home.power,
        name: "Other",
        icon: "mdi:dots-horizontal-circle-outline",
        power: Math.max(0, home - metered),
        daily: null,
        color: "#8B949E",
        other: true,
      });
    }

    let up = 0;
    let down = 0;
    rows.forEach((r, i) => {
      const el = this._loadEls[i];
      if (!el) return;
      el._entity = r.entity;
      const icon = el.querySelector("ha-icon");
      if (icon.getAttribute("icon") !== r.icon) icon.setAttribute("icon", r.icon);
      set(el, ".lname", r.name);
      set(el, ".lsub", r.daily != null ? fmtKwh(r.daily) : r.other ? "unmetered" : "");
      set(el, ".lval", fmtW(r.power));
      const share = home > 0 ? clamp(r.power / home, 0, 1) : 0;
      const bar = el.querySelector(".lbar > div");
      bar.style.width = `${share * 100}%`;
      bar.style.background = r.color;
      el.style.setProperty("--accent", r.color);
      el.classList.toggle("active", r.power >= c.threshold);
      this._setFlow(`load${i}`, r.power, r.color);
      if (this._rowY[i] < N.home.y) up += r.power;
      else down += r.power;
    });
    this._setFlow("spineUp", up, COLORS.home);
    this._setFlow("spineDown", down, COLORS.home);
  }

  _render() {
    this._built = false;
    this._flows = {};
    this._build();
    this._update();
  }

  _css() {
    return `
      :host { display: block; }
      ha-card { padding: 12px; overflow: hidden; height: 100%; box-sizing: border-box; }
      .title { font-size: 1.2rem; font-weight: 500; padding: 0 4px 8px; color: var(--primary-text-color); }
      .stage {
        position: relative; width: 100%; aspect-ratio: ${VB_W} / ${VB_H};
        container-type: inline-size; max-height: calc(100vh - 120px); margin: 0 auto;
      }
      svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
      .nodes { position: absolute; inset: 0; }

      .pipe path { fill: none; stroke-linecap: round; stroke-linejoin: round; transition: stroke-width .6s, opacity .6s, stroke .6s; }
      .pipe .wall { stroke: var(--divider-color, rgba(127,127,127,.25)); opacity: .9; }
      .pipe .glow { stroke-opacity: 1; }
      .pipe .dots { stroke: rgba(255,255,255,.92); transition: opacity .6s, stroke-width .6s; }
      .joint { fill: var(--card-background-color, #1c1c1c); stroke: var(--divider-color, rgba(127,127,127,.4)); stroke-width: 4; }

      .node {
        position: absolute; box-sizing: border-box; cursor: pointer; overflow: hidden;
        border-radius: 1.4cqw; padding: .8cqw 1cqw;
        background: var(--card-background-color, #1c1c1c);
        border: .25cqw solid var(--divider-color, rgba(127,127,127,.3));
        color: var(--primary-text-color);
        display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
        transition: border-color .6s, box-shadow .6s;
        --accent: ${COLORS.home};
      }
      .node.solar { --accent: ${COLORS.solar}; }
      .node.inverter { --accent: #959595; border-radius: 50%/40%; }
      .node.active { border-color: var(--accent); box-shadow: 0 0 1.6cqw -0.4cqw var(--accent); }
      .node.offgrid { opacity: .55; }
      .node .head { display: flex; align-items: center; gap: .5cqw; font-size: 1.35cqw; color: var(--secondary-text-color); position: relative; }
      .node ha-icon { --mdc-icon-size: 2.2cqw; color: var(--accent); }
      .node .val { font-size: 2.3cqw; font-weight: 600; line-height: 1.2; white-space: nowrap; position: relative; }
      .node .sub { font-size: 1.15cqw; color: var(--secondary-text-color); white-space: pre-line; line-height: 1.35; position: relative; }
      .node .soc { position: absolute; left: 0; right: 0; bottom: 0; opacity: .14; transition: height 1s, background 1s; }

      .summary { position: absolute; display: flex; flex-direction: column; gap: .6cqw; }
      .summary.bottom { justify-content: flex-end; }
      .stat { display: flex; flex-direction: column; }
      .stat .k { font-size: 1.15cqw; color: var(--secondary-text-color); }
      .stat .v { font-size: 2.1cqw; font-weight: 600; color: var(--primary-text-color); }

      .load {
        position: absolute; box-sizing: border-box; cursor: pointer;
        display: grid; grid-template-columns: auto 1fr auto; align-items: center; column-gap: .8cqw;
        padding: 0 1cqw; border-radius: 1cqw;
        background: var(--card-background-color, #1c1c1c);
        border: .2cqw solid var(--divider-color, rgba(127,127,127,.3));
        color: var(--primary-text-color); overflow: hidden;
        transition: border-color .6s, opacity .6s;
        --accent: ${COLORS.load};
      }
      .load:not(.active) { opacity: .6; }
      .load.active { border-color: color-mix(in srgb, var(--accent) 60%, transparent); }
      .load ha-icon { --mdc-icon-size: 2cqw; color: var(--accent); }
      .load .ltext { min-width: 0; }
      .load .lname { font-size: 1.3cqw; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .load .lsub { font-size: 1.0cqw; color: var(--secondary-text-color); }
      .load .lval { font-size: 1.5cqw; font-weight: 600; white-space: nowrap; }
      .load .lbar { position: absolute; left: 0; right: 0; bottom: 0; height: .35cqw; }
      .load .lbar > div { height: 100%; opacity: .7; transition: width 1s; }

      @media (prefers-reduced-motion: reduce) { .pipe .dots { opacity: 0 !important; } }
    `;
  }
}

customElements.define("power-flow-pipes-card", PowerFlowPipesCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "power-flow-pipes-card",
  name: "Power Flow Pipes Card",
  description: "Plumbing-style animated power flow: solar, grid, battery, home and circuits.",
});
