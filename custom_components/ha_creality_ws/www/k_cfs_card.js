
const CARD_TAG = "k-cfs-card";
const EDITOR_TAG = "k-cfs-card-editor";

const mdi = (name) => `mdi:${name}`;

class KCFSCard extends HTMLElement {
  constructor() {
    super();
    this._selectedCFS = 0; // Track selected CFS tab in normal mode
  }

  static _sanitizeColor(value) {
    const raw = String(value || "").trim();
    if (!raw || ["unknown", "unavailable", "—"].includes(raw.toLowerCase())) {
      return "#cccccc";
    }
    const hex = raw.startsWith("#") ? raw.slice(1) : raw;
    if (hex.length === 6 && /^[0-9a-fA-F]+$/.test(hex)) {
      return `#${hex.toLowerCase()}`;
    }
    if (hex.length === 3 && /^[0-9a-fA-F]+$/.test(hex)) {
      return `#${hex.toLowerCase()}`;
    }
    if (hex.length === 7 && hex.startsWith("0") && /^[0-9a-fA-F]+$/.test(hex)) {
      return `#${hex.slice(1).toLowerCase()}`;
    }
    return "#cccccc";
  }

  static _parsePercent(percentObj) {
    if (!percentObj) return null;
    const state = percentObj.state;
    if (state === undefined || state === null) return null;
    const s = String(state);
    if (s === "unknown" || s === "unavailable") return null;
    const n = Number(s);
    if (Number.isNaN(n) || !Number.isFinite(n)) return null;
    return Math.max(0, Math.min(100, n));
  }

  static _getHumidityColor(humidityStr) {
    if (!humidityStr || humidityStr === "—") return '#64b5f6'; // default blue
    
    const match = String(humidityStr).match(/(\d+\.?\d*)/);
    if (!match) return '#64b5f6';
    
    const value = parseFloat(match[1]);
    if (value < 40) return '#4caf50';   // Green (0-39%) - Ideal
    if (value < 60) return '#ff9800';   // Orange (40-59%) - Attention
    return '#f44336';                    // Red (60-100%) - Critical
  }

  static getStubConfig() {
    const cfg = {
      name: "CFS",
      compact_view: false,
      show_type_in_mini: false,
      external_filament: "",
      external_color: "",
      external_percent: "",
    };

    for (let box = 0; box < 4; box += 1) {
      cfg[`box${box}_temp`] = "";
      cfg[`box${box}_humidity`] = "";
      for (let slot = 0; slot < 4; slot += 1) {
        cfg[`box${box}_slot${slot}_filament`] = "";
        cfg[`box${box}_slot${slot}_color`] = "";
        cfg[`box${box}_slot${slot}_percent`] = "";
      }
    }

    return cfg;
  }

  static getConfigElement() {
    return document.createElement(EDITOR_TAG);
  }

  setConfig(config) {
    this._cfg = { ...KCFSCard.getStubConfig(), ...config };
    if (!this._root) {
      this._root = this.attachShadow({ mode: "open" });
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  _render() {
    if (!this._root) return;

    const isCompact = this._cfg.compact_view;

    const style = `
      ha-card {
        padding: 20px;
        background: rgba(var(--rgb-card-background-color), 0.95);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 24px;
        border: 1px solid rgba(var(--rgb-primary-text-color), 0.08);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
      }

      /* === NORMAL MODE === */
      .normal-mode {}

      .header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 24px;
      }
      .title-section {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .title {
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.5px;
      }
      .subtitle {
        font-size: 12px;
        color: var(--secondary-text-color);
        font-weight: 500;
      }
      .env-info {
        font-size: 11px;
        background: rgba(var(--rgb-primary-text-color), 0.08);
        padding: 6px 10px;
        border-radius: 12px;
        color: var(--secondary-text-color);
      }

      .unit-selector {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
        background: rgba(var(--rgb-primary-text-color), 0.05);
        padding: 4px;
        border-radius: 14px;
        width: fit-content;
      }
      .unit-btn {
        padding: 6px 16px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        border: none;
        color: var(--secondary-text-color);
        background: transparent;
      }
      .unit-btn.active {
        background: rgba(var(--rgb-primary-text-color), 0.1);
        color: var(--primary-text-color);
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
      }

      .spool-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }

      .spool-card {
        background: rgba(var(--rgb-primary-text-color), 0.04);
        border-radius: 18px;
        padding: 16px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        position: relative;
        border: 1px solid transparent;
        transition: all 0.3s ease;
        cursor: pointer;
      }

      .spool-card:hover {
        background: rgba(var(--rgb-primary-text-color), 0.06);
      }

      .spool-card.active {
        background: rgba(var(--rgb-primary-text-color), 0.08);
        border: 1px solid rgba(var(--rgb-primary-color), 0.3);
        box-shadow: 0 0 20px rgba(var(--rgb-primary-color), 0.2);
      }

      .ring-container {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        position: relative;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 10px;
      }

      .ring-outer {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        position: absolute;
        background: conic-gradient(
          var(--spool-color) var(--spool-pct),
          rgba(var(--rgb-primary-text-color), 0.08) 0
        );
      }

      .ring-inner {
        width: 66px;
        height: 66px;
        background: var(--card-background-color);
        border-radius: 50%;
        position: relative;
        z-index: 2;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
      }

      .spool-label {
        font-size: 10px;
        color: var(--secondary-text-color);
        text-transform: uppercase;
      }
      .spool-pct {
        font-size: 16px;
        font-weight: 700;
      }

      .material-name {
        font-size: 13px;
        font-weight: 600;
        text-align: center;
      }
      .color-name {
        font-size: 11px;
        color: var(--secondary-text-color);
        text-align: center;
      }

      .status-badge {
        position: absolute;
        top: 8px;
        right: 8px;
        width: 8px;
        height: 8px;
        background: var(--success-color, #4caf50);
        border-radius: 50%;
        box-shadow: 0 0 8px var(--success-color, #4caf50);
        animation: pulse-badge 2s infinite;
      }

      @keyframes pulse-badge {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.1); }
      }

      /* === COMPACT MODE === */
      .compact-mode {
        padding: 14px;
      }

      .compact-mode .header {
        margin-bottom: 12px;
      }

      .cfs-rows {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .cfs-row {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .cfs-label {
        width: 48px;
        font-size: 11px;
        color: var(--secondary-text-color);
        font-weight: 600;
      }

      .spools-inline {
        display: flex;
        gap: 10px;
        flex: 1;
      }

      .spool-mini {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.2s;
      }

      .spool-mini:hover {
        transform: scale(1.05);
      }

      .spool-mini::before {
        content: '';
        position: absolute;
        inset: 0;
        border-radius: 50%;
        background: conic-gradient(
          var(--spool-color) var(--spool-pct),
          rgba(var(--rgb-primary-text-color), 0.08) 0
        );
      }

      .spool-mini::after {
        content: '';
        position: absolute;
        inset: 4px;
        background: var(--card-background-color);
        border-radius: 50%;
        z-index: 1;
      }

      .spool-mini span {
        position: relative;
        z-index: 2;
      }

      .spool-mini.active {
        box-shadow: 0 0 10px var(--spool-color);
      }

      .spool-mini.active::after {
        inset: 3px;
      }

      .spool-mini-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
      }

      .spool-mini-type {
        font-size: 8px;
        color: var(--secondary-text-color);
        text-transform: uppercase;
        font-weight: 600;
        max-width: 40px;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .env-mini {
        width: 56px;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        font-size: 10px;
        line-height: 1.4;
        gap: 2px;
      }

      .env-mini .temp {
        color: #ffb74d;
        font-weight: 600;
      }

      .env-mini .hum {
        font-weight: 600;
        /* Cor aplicada dinamicamente via inline style */
      }

      /* === EXTERNAL SECTION === */
      .external-section {
        margin-top: 16px;
        padding-top: 14px;
        border-top: 1px solid rgba(var(--rgb-primary-text-color), 0.08);
      }

      .external-normal {
        background: rgba(var(--rgb-primary-text-color), 0.03);
        border-radius: 16px;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .ext-icon {
        width: 30px;
        height: 30px;
        background: var(--primary-color);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: bold;
        color: white;
      }

      .ext-info {
        flex-grow: 1;
      }

      .ext-name {
        font-size: 12px;
        font-weight: 600;
      }

      .ext-bar {
        height: 4px;
        background: rgba(var(--rgb-primary-text-color), 0.1);
        border-radius: 2px;
        margin-top: 6px;
        overflow: hidden;
      }

      .ext-fill {
        height: 100%;
        background: var(--primary-color);
        transition: width 0.3s ease;
      }

      .ext-percent {
        font-size: 12px;
        color: var(--secondary-text-color);
        font-weight: 600;
      }

      .external-compact {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      .ext-dot {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: conic-gradient(var(--primary-color) 100%, rgba(var(--rgb-primary-text-color), 0.1) 0);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 600;
        color: white;
      }

      .ext-compact-info {
        flex: 1;
      }

      .ext-compact-info div:first-child {
        font-size: 12px;
        font-weight: 600;
      }

      .ext-compact-info div:last-child {
        font-size: 10px;
        color: var(--secondary-text-color);
      }

      .no-data {
        text-align: center;
        color: var(--secondary-text-color);
        padding: 20px;
      }
    `;

    this._root.innerHTML = `
      <ha-card class="${isCompact ? 'compact-mode' : 'normal-mode'}">
        <style>${style}</style>
        <div id="content"></div>
      </ha-card>
    `;
  }

  _update() {
    if (!this._root || !this._hass) return;

    const contentContainer = this._root.getElementById("content");
    if (!contentContainer) return;

    const states = this._hass.states || {};
    const gObj = (eid) => (eid ? states?.[eid] : undefined);
    const fmtState = (st) => {
      if (!st) return "—";
      const v = st.state;
      if (v === undefined || v === null) return "—";
      const s = String(v);
      if (s === "unknown" || s === "unavailable") return "—";
      if (this._hass && typeof this._hass.formatEntityState === "function") {
        try { return this._hass.formatEntityState(st); } catch (_) { }
      }
      const unit = st.attributes?.unit_of_measurement;
      const n = Number(s);
      if (!Number.isNaN(n) && Number.isFinite(n)) {
        const dp = (typeof st.attributes?.display_precision === "number") ? st.attributes.display_precision
          : (typeof st.attributes?.suggested_display_precision === "number") ? st.attributes.suggested_display_precision
            : (unit && /°|c|f/i.test(unit)) ? 1
              : 2;
        const out = n.toFixed(Math.max(0, Math.min(6, dp)));
        return unit ? `${out} ${unit}` : out;
      }
      return unit ? `${s} ${unit}` : s;
    };

    // Collect box data
    const boxes = {};
    for (let boxId = 0; boxId < 4; boxId += 1) {
      const tempEid = this._cfg[`box${boxId}_temp`];
      const humidityEid = this._cfg[`box${boxId}_humidity`];
      const slots = [];

      for (let slotId = 0; slotId < 4; slotId += 1) {
        const filamentEid = this._cfg[`box${boxId}_slot${slotId}_filament`];
        const colorEid = this._cfg[`box${boxId}_slot${slotId}_color`];
        const percentEid = this._cfg[`box${boxId}_slot${slotId}_percent`];
        if (!filamentEid && !colorEid && !percentEid) {
          slots.push(null);
          continue;
        }

        const filamentObj = gObj(filamentEid);
        const colorObj = gObj(colorEid);
        const percentObj = gObj(percentEid);
        const name = filamentObj?.state;
        const type = filamentObj?.attributes?.type;
        const selected = filamentObj?.attributes?.selected;
        const rawColor = colorObj?.state || filamentObj?.attributes?.color_hex;
        const color = KCFSCard._sanitizeColor(rawColor);
        const percent = KCFSCard._parsePercent(percentObj);
        const percentText = fmtState(percentObj);

        slots[slotId] = {
          id: slotId,
          boxId,
          entity_id: filamentEid || colorEid || percentEid,
          name,
          type,
          selected,
          color,
          percent,
          percentText,
        };
      }

      if (tempEid || humidityEid || slots.some((slot) => slot)) {
        const humidityFormatted = fmtState(gObj(humidityEid));
        boxes[boxId] = {
          id: boxId,
          temp: fmtState(gObj(tempEid)),
          humidity: humidityFormatted,
          humidityColor: KCFSCard._getHumidityColor(humidityFormatted),
          slots,
        };
      }
    }

    // Collect external data
    const external = {
      filament: this._cfg.external_filament,
      color: this._cfg.external_color,
      percent: this._cfg.external_percent,
    };
    const hasExternal = external.filament || external.color || external.percent;
    let externalData = null;
    if (hasExternal) {
      const filamentObj = gObj(external.filament);
      const colorObj = gObj(external.color);
      const percentObj = gObj(external.percent);
      const name = filamentObj?.state;
      const type = filamentObj?.attributes?.type;
      const selected = filamentObj?.attributes?.selected;
      const rawColor = colorObj?.state || filamentObj?.attributes?.color_hex;
      const color = KCFSCard._sanitizeColor(rawColor);
      const percent = KCFSCard._parsePercent(percentObj);
      const percentText = fmtState(percentObj);

      externalData = {
        id: 0,
        boxId: -1,
        entity_id: external.filament || external.color || external.percent,
        name,
        type,
        selected,
        color,
        percent,
        percentText,
      };
    }

    const boxValues = Object.values(boxes);
    if (boxValues.length === 0 && !hasExternal) {
      contentContainer.innerHTML = `<div class="no-data">No CFS data available</div>`;
      return;
    }

    // Render based on mode
    if (this._cfg.compact_view) {
      contentContainer.innerHTML = this._renderCompactMode(boxValues, externalData);
    } else {
      contentContainer.innerHTML = this._renderNormalMode(boxValues, externalData);
    }

    this._attachEventHandlers();
  }

  _renderNormalMode(boxes, external) {
    // Ensure we have at least one box
    if (boxes.length === 0 && !external) {
      return `<div class="no-data">No CFS data available</div>`;
    }

    // Unit selector (only if we have multiple boxes)
    let unitSelector = '';
    if (boxes.length > 1) {
      unitSelector = `
        <div class="unit-selector">
          ${boxes.map((box, idx) => `
            <button class="unit-btn ${idx === this._selectedCFS ? 'active' : ''}" data-cfs="${idx}">
              CFS ${box.id + 1}
            </button>
          `).join('')}
        </div>
      `;
    }

    // Get the selected box
    const selectedBox = boxes[this._selectedCFS] || boxes[0];
    if (!selectedBox && !external) {
      return `<div class="no-data">No CFS data available</div>`;
    }

    // Header with environment info
    let envInfo = '';
    if (selectedBox) {
      const tempStr = selectedBox.temp !== "—" ? selectedBox.temp : '';
      const humStr = selectedBox.humidity !== "—" ? selectedBox.humidity : '';
      
      if (tempStr || humStr) {
        const tempHtml = tempStr ? `<span class="env-temp">${tempStr}</span>` : '';
        const humHtml = humStr ? `<span class="env-hum" style="color: ${selectedBox.humidityColor}">${humStr}</span>` : '';
        const separator = tempStr && humStr ? ' <span style="color: var(--divider-color)">•</span> ' : '';
        envInfo = `<div class="env-info">${tempHtml}${separator}${humHtml}</div>`;
      }
    }

    const header = `
      <div class="header">
        <div class="title-section">
          <div class="title">${this._cfg.name || 'Creality CFS'}</div>
        </div>
        ${envInfo}
      </div>
    `;

    // Spool grid
    let spoolGrid = '';
    if (selectedBox) {
      spoolGrid = `
        <div class="spool-grid">
          ${selectedBox.slots.map((slot) => this._renderSpoolCard(slot)).join('')}
        </div>
      `;
    }

    // External section
    let externalSection = '';
    if (external) {
      const safeType = external.type && !["unknown", "unavailable", "—", "-"].includes(String(external.type).toLowerCase()) ? external.type : "—";
      const safeName = external.name && !["unknown", "unavailable", "—", "-"].includes(String(external.name).toLowerCase()) ? external.name : "—";
      const hasFilament = safeType !== "—" && safeName !== "—";
      const pct = hasFilament && external.percent !== null ? external.percent : 0;
      const percentTextDisplay = hasFilament ? (external.percentText || '—') : '—';
      const displayName = hasFilament ? `${safeName} ${safeType}` : '—';
      externalSection = `
        <div class="external-section">
          <div class="external-normal" data-eid="${external.entity_id}">
            <div class="ext-icon">EXT</div>
            <div class="ext-info">
              <div class="ext-name">${displayName}</div>
              <div class="ext-bar">
                <div class="ext-fill" style="width: ${pct}%"></div>
              </div>
            </div>
            <div class="ext-percent">${percentTextDisplay}</div>
          </div>
        </div>
      `;
    }

    return `${unitSelector}${header}${spoolGrid}${externalSection}`;
  }

  _renderCompactMode(boxes, external) {
    if (boxes.length === 0 && !external) {
      return `<div class="no-data">No CFS data available</div>`;
    }

    // CFS rows
    let cfsRows = '';
    if (boxes.length > 0) {
      cfsRows = `
        <div class="cfs-rows">
          ${boxes.map((box) => this._renderCFSRow(box)).join('')}
        </div>
      `;
    }

    // External section
    let externalSection = '';
    if (external) {
      const safeType = external.type && !["unknown", "unavailable", "—", "-"].includes(String(external.type).toLowerCase()) ? external.type : "—";
      const safeName = external.name && !["unknown", "unavailable", "—", "-"].includes(String(external.name).toLowerCase()) ? external.name : "—";
      const hasFilament = safeType !== "—" && safeName !== "—";
      const percentTextDisplay = hasFilament ? (external.percentText || '—') : '—';
      const displayName = hasFilament ? `${safeName} ${safeType}` : '—';
      externalSection = `
        <div class="external-section">
          <div class="external-compact" data-eid="${external.entity_id}">
            <div class="ext-dot">EXT</div>
            <div class="ext-compact-info">
              <div>${displayName}</div>
              <div>${percentTextDisplay}</div>
            </div>
          </div>
        </div>
      `;
    }

    return `${cfsRows}${externalSection}`;
  }

  _renderCFSRow(box) {
    const tempStr = box.temp !== "—" ? box.temp : '';
    const humStr = box.humidity !== "—" ? box.humidity : '';

    let envHtml = '';
    if (tempStr || humStr) {
      envHtml = `
        <div class="env-mini">
          ${tempStr ? `<div class="temp">${tempStr}</div>` : ''}
          ${humStr ? `<div class="hum" style="color: ${box.humidityColor}">${humStr}</div>` : ''}
        </div>
      `;
    }

    return `
      <div class="cfs-row">
        <div class="cfs-label">CFS ${box.id + 1}</div>
        <div class="spools-inline">
          ${box.slots.map((slot) => this._renderSpoolMini(slot)).join('')}
        </div>
        ${envHtml}
      </div>
    `;
  }

  _renderSpoolCard(slot) {
    if (!slot) {
      return `<div class="spool-card"></div>`;
    }

    const isActive = slot.selected === 1 || slot.selected === true;
    const color = slot.color || '#cccccc';
    const safeType = slot.type && !["unknown", "unavailable", "—", "-"].includes(String(slot.type).toLowerCase()) ? slot.type : "—";
    const safeName = slot.name && !["unknown", "unavailable", "—", "-"].includes(String(slot.name).toLowerCase()) ? slot.name : "—";
    
    // If no filament (type is "—" or name is "—"), show 0% regardless of actual value
    const hasFilament = safeType !== "—" && safeName !== "—";
    const pct = hasFilament && slot.percent !== null ? slot.percent : 0;
    const pctDisplay = hasFilament && slot.percent !== null ? Math.round(slot.percent) : 0;
    const percentTextDisplay = hasFilament ? (slot.percentText || '—') : '—';

    const badge = isActive ? '<div class="status-badge"></div>' : '';

    return `
      <div class="spool-card ${isActive ? 'active' : ''}" data-eid="${slot.entity_id}">
        ${badge}
        <div class="ring-container">
          <div class="ring-outer" style="--spool-color: ${color}; --spool-pct: ${pct}%"></div>
          <div class="ring-inner">
            <span class="spool-pct">${pctDisplay}%</span>
            <span class="spool-label">${safeType}</span>
          </div>
        </div>
        <div class="material-name">${safeName}</div>
        <div class="color-name">${percentTextDisplay}</div>
      </div>
    `;
  }

  _renderSpoolMini(slot) {
    const showType = this._cfg.show_type_in_mini;
    
    if (!slot) {
      if (showType) {
        return `<div class="spool-mini-wrapper"><div class="spool-mini" style="--spool-color: #333; --spool-pct: 0%"><span>—</span></div><div class="spool-mini-type">—</div></div>`;
      }
      return `<div class="spool-mini" style="--spool-color: #333; --spool-pct: 0%"><span>—</span></div>`;
    }

    const isActive = slot.selected === 1 || slot.selected === true;
    const color = slot.color || '#cccccc';
    const safeType = slot.type && !["unknown", "unavailable", "—", "-"].includes(String(slot.type).toLowerCase()) ? slot.type : "—";
    const safeName = slot.name && !["unknown", "unavailable", "—", "-"].includes(String(slot.name).toLowerCase()) ? slot.name : null;
    
    // If no filament (type is "—" or name is empty/dash), show 0% regardless of actual value
    const hasFilament = safeType !== "—" && safeName !== null;
    const pct = hasFilament && slot.percent !== null ? slot.percent : 0;
    const pctDisplay = hasFilament && slot.percent !== null ? Math.round(slot.percent) : 0;

    if (showType) {
      return `
        <div class="spool-mini-wrapper">
          <div class="spool-mini ${isActive ? 'active' : ''}" 
               style="--spool-color: ${color}; --spool-pct: ${pct}%" 
               data-eid="${slot.entity_id}">
            <span>${pctDisplay}</span>
          </div>
          <div class="spool-mini-type">${safeType}</div>
        </div>
      `;
    }

    return `
      <div class="spool-mini ${isActive ? 'active' : ''}" 
           style="--spool-color: ${color}; --spool-pct: ${pct}%" 
           data-eid="${slot.entity_id}">
        <span>${pctDisplay}</span>
      </div>
    `;
  }

  _attachEventHandlers() {
    // Unit selector buttons
    this._root.querySelectorAll('.unit-btn').forEach(btn => {
      btn.onclick = () => {
        const cfsIdx = parseInt(btn.dataset.cfs, 10);
        if (!isNaN(cfsIdx)) {
          this._selectedCFS = cfsIdx;
          this._update();
        }
      };
    });

    // Spool cards and mini spools - show more info
    this._root.querySelectorAll('.spool-card, .spool-mini, .spool-mini-wrapper .spool-mini, .external-normal, .external-compact').forEach(el => {
      const eid = el.dataset.eid;
      if (!eid) return;
      
      el.onclick = () => {
        this.dispatchEvent(new CustomEvent("hass-more-info", {
          detail: { entityId: eid },
          bubbles: true,
          composed: true,
        }));
      };
    });
  }

  getCardSize() {
    return 3;
  }
}

customElements.define(CARD_TAG, KCFSCard);

class KCFSCardEditor extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (this._form) {
      this._form.hass = hass;
    }
  }

  setConfig(config) {
    this._cfg = { ...KCFSCard.getStubConfig(), ...config };
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  _render() {
    if (!this._root) {
      this._root = this.attachShadow({ mode: "open" });
    }

    const style = `
      .editor-container { padding: 16px; }
      .tabs { display: flex; border-bottom: 1px solid var(--divider-color); margin-bottom: 16px; }
      .tab { padding: 8px 16px; cursor: pointer; border-bottom: 2px solid transparent; }
      .tab.active { border-bottom-color: var(--primary-color); color: var(--primary-color); }
      .tab-content { display: none; }
      .tab-content.active { display: block; }
      .input-helper { font-size: 0.9em; color: var(--secondary-text-color); margin-top: 4px; padding: 0 8px; }
    `;

    this._root.innerHTML = `
      <style>${style}</style>
      <div class="editor-container">
        <div class="tabs">
          <div class="tab active" data-tab="entities">Entities</div>
          <div class="tab" data-tab="theme">Theme</div>
        </div>
        <div class="tab-content active" id="entities-tab">
          <ha-form id="form"></ha-form>
        </div>
        <div class="tab-content" id="theme-tab">
          <ha-form id="theme-form"></ha-form>
        </div>
      </div>
    `;

    this._setupTabs();
    this._setupEntitiesForm();
    this._setupThemeForm();
  }

  _setupTabs() {
    const tabs = this._root.querySelectorAll(".tab");
    const contents = this._root.querySelectorAll(".tab-content");
    tabs.forEach((tab) => {
      tab.onclick = () => {
        tabs.forEach((t) => t.classList.remove("active"));
        contents.forEach((c) => c.classList.remove("active"));
        tab.classList.add("active");
        this._root.getElementById(`${tab.dataset.tab}-tab`).classList.add("active");
      };
    });
  }

  _setupEntitiesForm() {
    this._form = this._root.getElementById("form");
    this._form.hass = this._hass;
    this._form.data = this._cfg;
    const schema = [
      { name: "name", selector: { text: {} } },
      { name: "external_filament", selector: { entity: { domain: "sensor" } } },
      { name: "external_color", selector: { entity: { domain: "sensor" } } },
      { name: "external_percent", selector: { entity: { domain: "sensor" } } },
    ];

    for (let box = 0; box < 4; box += 1) {
      schema.push({ name: `box${box}_temp`, selector: { entity: { domain: "sensor" } } });
      schema.push({ name: `box${box}_humidity`, selector: { entity: { domain: "sensor" } } });
      for (let slot = 0; slot < 4; slot += 1) {
        schema.push({ name: `box${box}_slot${slot}_filament`, selector: { entity: { domain: "sensor" } } });
        schema.push({ name: `box${box}_slot${slot}_color`, selector: { entity: { domain: "sensor" } } });
        schema.push({ name: `box${box}_slot${slot}_percent`, selector: { entity: { domain: "sensor" } } });
      }
    }

    this._form.schema = schema;
    this._form.computeLabel = (s) => {
      if (s.name === "name") return "Card Title";
      if (s.name === "external_filament") return "External Filament";
      if (s.name === "external_color") return "External Color";
      if (s.name === "external_percent") return "External Percent";

      const boxMatch = s.name.match(/^box(\d+)_(temp|humidity)$/);
      if (boxMatch) {
        const [, boxId, metric] = boxMatch;
        return `Box ${Number(boxId) + 1} ${metric === "temp" ? "Temperature" : "Humidity"}`;
      }

      const slotMatch = s.name.match(/^box(\d+)_slot(\d+)_(filament|color|percent)$/);
      if (slotMatch) {
        const [, boxId, slotId, metric] = slotMatch;
        const labelMap = {
          filament: "Filament",
          color: "Color",
          percent: "Remaining Percent",
        };
        return `Box ${Number(boxId) + 1} Slot ${Number(slotId) + 1} ${labelMap[metric]}`;
      }

      return s.name;
    };
    if (this._form.computeHelper) {
      this._form.computeHelper = () => "";
    }

    this._form.addEventListener("value-changed", (ev) => {
      this._cfg = { ...this._cfg, ...ev.detail.value };
      this._dispatchConfigChange();
    });
  }

  _setupThemeForm() {
    const themeForm = this._root.getElementById("theme-form");
    themeForm.hass = this._hass;
    themeForm.data = this._cfg;
    themeForm.schema = [
      { name: "compact_view", selector: { boolean: {} } },
      { name: "show_type_in_mini", selector: { boolean: {} } },
    ];
    themeForm.computeLabel = (s) => ({
      compact_view: "Compact View (Mini Mode)",
      show_type_in_mini: "Show Filament Type in Mini Mode",
    }[s.name] || s.name);

    themeForm.addEventListener("value-changed", (ev) => {
      this._cfg = { ...this._cfg, ...ev.detail.value };
      this._dispatchConfigChange();
    });
  }

  _dispatchConfigChange() {
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: this._cfg },
      bubbles: true,
      composed: true,
    }));
  }
}

customElements.define(EDITOR_TAG, KCFSCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "k-cfs-card",
  name: "Creality CFS Card",
  preview: true,
  description: "A card to control the Creality Filament System (CFS)"
});
