const CARD_TAG = "k-printer-card";
const EDITOR_TAG = "k-printer-card-editor";

const clamp = (v, a, b) => Math.min(Math.max(v, a), b);
const mdi = (name) => `mdi:${name}`;
const normStr = (x) => String(x ?? "").toLowerCase();

// Theme persistence utilities
const THEME_STORAGE_KEY = "k-printer-card-themes";

// Color conversion utilities
function rgbaToHex(rgba) {
  if (!rgba || rgba.startsWith('#')) return rgba;

  // Handle rgba() format
  const match = rgba.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)/);
  if (match) {
    const r = parseInt(match[1]);
    const g = parseInt(match[2]);
    const b = parseInt(match[3]);
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }

  // Handle CSS variables
  if (rgba.startsWith('var(')) {
    return '#000000'; // fallback
  }

  return '#000000';
}

function hexToRgba(hex, alpha = 1) {
  if (!hex || !hex.startsWith('#')) return hex;

  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Save theme configuration to localStorage for persistence across card updates
 * @param {string} cardId - Unique identifier for the card
 * @param {Object} theme - Theme configuration object
 */
function saveThemeToStorage(cardId, theme) {
  try {
    const themes = JSON.parse(localStorage.getItem(THEME_STORAGE_KEY) || "{}");
    themes[cardId] = theme;
    localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(themes));
  } catch (e) {
    console.warn("Failed to save theme to localStorage:", e);
  }
}

/**
 * Load theme configuration from localStorage
 * @param {string} cardId - Unique identifier for the card
 * @returns {Object|null} Theme configuration or null if not found
 */
function loadThemeFromStorage(cardId) {
  try {
    const themes = JSON.parse(localStorage.getItem(THEME_STORAGE_KEY) || "{}");
    return themes[cardId] || null;
  } catch (e) {
    console.warn("Failed to load theme from localStorage:", e);
    return null;
  }
}

/**
 * Generate a unique card ID based on configuration
 * @param {Object} config - Card configuration
 * @returns {string} Unique card identifier
 */
function generateCardId(config) {
  // Generate a unique ID based on the card configuration
  const key = `${config.name || "printer"}-${config.status || "unknown"}`;
  return btoa(key).replace(/[^a-zA-Z0-9]/g, '').substring(0, 16);
}

function fmtTimeLeft(seconds) {
  const s = Number(seconds) || 0;
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  if (m > 0) return `${m}:${String(sec).padStart(2, "0")}`;
  return `${sec}s`;
}
function computeIcon(status) {
  const st = normStr(status);
  if (["off", "unknown", "stopped"].includes(st)) return mdi("printer-3d-off");
  if (["printing", "resuming", "pausing", "paused"].includes(st)) return mdi("printer-3d-nozzle");
  if (st === "error") return mdi("close-octagon");
  if (st === "self-testing") return mdi("cogs");
  return mdi("printer-3d");
}
function computeColor(status) {
  const st = normStr(status);
  if (["off", "unknown", "stopped"].includes(st)) return "var(--secondary-text-color)";
  if (["paused", "pausing"].includes(st)) return "#fc6d09";
  if (st === "error") return "var(--error-color)";
  if (["printing", "resuming", "processing"].includes(st)) return "var(--primary-color)";
  if (["idle", "completed"].includes(st)) return "var(--success-color, #4caf50)";
  if (st === "self-testing") return "var(--info-color, #2196f3)";
  return "var(--secondary-text-color)";
}

class KPrinterCard extends HTMLElement {
  static getStubConfig() {
    return {
      name: "3D Printer",
      camera: "", status: "", progress: "", time_left: "",
      nozzle: "", bed: "", box: "",
      // Optional power switch entity and visibility flag for a Power button
      power: "",
      show_power_button: true,
      layer: "", total_layers: "",
      light: "", pause_btn: "", resume_btn: "", stop_btn: "",
      // Theme customization options
      theme: {
        // Button backgrounds
        pause_bg: "rgba(252, 109, 9, .90)",
        resume_bg: "rgba(76, 175, 80, .90)",
        stop_bg: "rgba(244, 67, 54, .95)",
        light_on_bg: "rgba(255, 235, 59, .95)",
        light_off_bg: "rgba(150,150,150,.35)",
        // Button icon colors
        pause_icon: "#fff",
        resume_icon: "#fff",
        stop_icon: "#fff",
        light_icon_on: "#000",
        light_icon_off: "#000",
        // Status icon and progress circle
        status_icon: "auto", // auto, or specific color
        progress_ring: "auto", // auto, or specific color
        status_bg: "auto", // auto (transparent), or specific color
        // Telemetry colors
        telemetry_icon: "auto", // auto (inherit theme), or specific color
        telemetry_text: "auto", // auto (inherit theme), or specific color
        // Custom button colors
        custom_bg: "rgba(33, 150, 243, .90)",
        custom_icon: "#fff",
      },
      // Config for custom button
      custom_btn: "",
      custom_btn_icon: "", // Moved to theme editor but stored here
      custom_btn_hidden: false,
      // Order of buttons
      button_order: ['pause', 'resume', 'stop', 'light', 'power', 'custom'],
      // Icon overrides
      pause_btn_icon: "",
      resume_btn_icon: "",
      stop_btn_icon: "",
      light_btn_icon: "",
      power_btn_icon: "",

      // Feature toggles
      hide_box_temp: false
    };
  }
  static getConfigElement() {
    const editor = document.createElement(EDITOR_TAG);
    return editor;
  }

  setConfig(config) {
    const defaultConfig = KPrinterCard.getStubConfig();
    this._cfg = { ...defaultConfig, ...(config || {}) };
    // Init optimistic state overrides map
    if (!this._optimisticStates) this._optimisticStates = {};

    // Generate card ID for theme persistence
    this._cardId = generateCardId(this._cfg);

    // Load saved theme if no theme is provided in config
    if (!config?.theme) {
      const savedTheme = loadThemeFromStorage(this._cardId);
      if (savedTheme) {
        this._cfg.theme = { ...defaultConfig.theme, ...savedTheme };
      }
    } else {
      // Deep merge theme configuration
      this._cfg.theme = { ...defaultConfig.theme, ...config.theme };
      // Save theme to storage
      saveThemeToStorage(this._cardId, this._cfg.theme);
    }

    if (!this._root) {
      this._root = this.attachShadow({ mode: "open" });
    }

    // Always re-render when config changes to apply new theme
    this._render();

    // Apply theme after render to ensure DOM is ready
    this._applyTheme();
  }
  _applyTheme() {
    if (!this._root || !this._cfg.theme) {
      return;
    }

    // Re-render with updated CSS to apply theme changes
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._root) {
      // Apply theme first, then update
      this._applyTheme();
      this._update();
      // Schedule a follow-up update shortly after initial attach to absorb entity states once Home Assistant populates them
      clearTimeout(this._initialUpdateTimer);
      this._initialUpdateTimer = setTimeout(() => {
        try { this._update(); } catch (_) { }
      }, 150);
    }
  }
  getCardSize() { return 3; }

  _render() {
    if (!this._root) return;

    // Ensure theme is always properly initialized
    const defaultConfig = KPrinterCard.getStubConfig();
    this._cfg.theme = { ...defaultConfig.theme, ...(this._cfg.theme || {}) };

    // Apply theme variables to CSS custom properties
    const theme = this._cfg.theme;

    // Theme CSS custom properties - embedded directly in CSS
    const themeCSS = `
      :host {
        --pause-bg: ${theme.pause_bg || 'rgba(252, 109, 9, .90)'};
        --resume-bg: ${theme.resume_bg || 'rgba(76, 175, 80, .90)'};
        --stop-bg: ${theme.stop_bg || 'rgba(244, 67, 54, .95)'};
        --light-on-bg: ${theme.light_on_bg || 'rgba(255, 235, 59, .95)'};
        --light-off-bg: ${theme.light_off_bg || 'rgba(150,150,150,.35)'};
        --pause-icon: ${theme.pause_icon || '#fff'};
        --resume-icon: ${theme.resume_icon || '#fff'};
        --stop-icon: ${theme.stop_icon || '#fff'};
        --light-icon-on: ${theme.light_icon_on || '#000'};
        --light-icon-off: ${theme.light_icon_off || '#000'};
        --status-bg: ${theme.status_bg === 'auto' ? 'radial-gradient(var(--card-background-color) 62%, transparent 0)' : (theme.status_bg || 'radial-gradient(var(--card-background-color) 62%, transparent 0)')};
        --telemetry-icon: ${theme.telemetry_icon === 'auto' ? 'var(--secondary-text-color)' : (theme.telemetry_icon || 'var(--secondary-text-color)')};
        --telemetry-text: ${theme.telemetry_text === 'auto' ? 'var(--primary-text-color)' : (theme.telemetry_text || 'var(--primary-text-color)')};
        --custom-bg: ${theme.custom_bg || 'rgba(33, 150, 243, .90)'};
        --custom-on-bg: ${theme.custom_on_bg || theme.custom_bg || 'rgba(33, 150, 243, .90)'};
        --custom-off-bg: ${theme.custom_off_bg || 'rgba(150,150,150,.35)'};
        --custom-icon: ${theme.custom_icon || '#fff'};
        --custom-icon-off: ${theme.custom_icon_off || '#000'};
      }
    `;


    const style = `
      /* Theme CSS custom properties */
      ${themeCSS}
      
      /* inherit HA fonts & typography */
      :host { font: inherit; color: var(--primary-text-color); }

      /* unify horizontal padding so right edges line up */
      :host { --row-xpad: 6px; }

      .card {
        border-radius: var(--ha-card-border-radius, 12px);
        background: var(--card-background-color);
        color: var(--primary-text-color);
        box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,.2));
        padding: 10px var(--row-xpad) 10px var(--row-xpad);
        display: grid;
        grid-template-rows: auto auto;
        gap: 6px;
      }

      /* top row */
      .row-top {
        display: grid;
        grid-template-columns: 1fr auto;
        align-items: center;
        gap: 8px;
        padding: 0 var(--row-xpad);
      }
      .title { display:flex; align-items:center; gap:10px; min-height:44px; }

      /* icon + progress ring */
      .shape { position:relative; width:40px; height:40px; border-radius:50%;
        display:grid; place-items:center;
        background: var(--status-bg, radial-gradient(var(--card-background-color) 62%, transparent 0));
      }
      .ring { position:absolute; inset:0; border-radius:50%;
        mask: radial-gradient(circle at 50% 50%, transparent 54%, black 55%);
        -webkit-mask: radial-gradient(circle at 50% 50%, transparent 54%, black 55%);
        background: conic-gradient(var(--ring-color, var(--primary-color)) var(--ring-pct,0%),
                                  rgba(128,128,128,.25) var(--ring-pct,0%));
      }
      ha-icon { --mdc-icon-size:24px; width:24px; height:24px; color: var(--icon-color); }

      .name { font-weight:600; font-size:.95rem; line-height:1.2; }
      .secondary { color:var(--secondary-text-color); font-size:.8rem; }

      /* action chips – align right edge to telemetry via the same side padding */
      .chips {
        display:flex; gap:8px; justify-content:flex-end; flex-wrap:nowrap;
        padding: 0 var(--row-xpad);
      }
      .chip {
        display:inline-flex; align-items:center; justify-content:center;
        gap:6px; min-width:38px; height:34px;
        border-radius:18px; padding:0 10px;
        font-size:.8rem; background:var(--chip-bg, rgba(128,128,128,.14));
        color:var(--chip-fg, var(--primary-text-color));
        cursor:pointer; user-select:none; border:none; outline:none;
      }
      .chip[hidden]{ display:none !important; }
      .chip:active { transform: translateY(1px); }
      .chip.danger { --chip-bg: var(--stop-bg, rgba(244, 67, 54, .95)); --chip-fg: var(--stop-icon, #fff); }
      .chip.warn   { --chip-bg: var(--pause-bg, rgba(252, 109, 9, .90));  --chip-fg: var(--pause-icon, #fff); }
      .chip.ok     { --chip-bg: var(--resume-bg, rgba(76, 175, 80, .90));  --chip-fg: var(--resume-icon, #fff); }
      .chip.light-on  { --chip-bg: var(--light-on-bg, rgba(255, 235, 59, .95)); --chip-fg: var(--light-icon-on, #000); }
      .chip.light-off { --chip-bg: var(--light-off-bg, rgba(150,150,150,.35)); --chip-fg: var(--light-icon-off, #000); }
      .chip.power-on  { --chip-bg: var(--power-on-bg, rgba(76, 175, 80, .90));  --chip-fg: var(--power-icon-on, #fff); }
      .chip.power-off { --chip-bg: var(--power-off-bg, rgba(150,150,150,.35)); --chip-fg: var(--power-icon-off, #000); }
  .chip.unknown   { --chip-bg: rgba(128,128,128,.14); --chip-fg: var(--primary-text-color); }
      .chip.custom    { --chip-bg: var(--custom-bg, rgba(33, 150, 243, .90)); --chip-fg: var(--custom-icon, #fff); }
      .chip.custom-on { --chip-bg: var(--custom-on-bg, var(--custom-bg, rgba(33, 150, 243, .90))); --chip-fg: var(--custom-icon, #fff); }
      .chip.custom-off{ --chip-bg: var(--custom-off-bg, rgba(150,150,150,.35)); --chip-fg: var(--custom-icon-off, #000); }
      /* Order is handled by flex order style or DOM order */


      /* telemetry row – single line, same right padding, tighter pills */
      .telemetry {
        display:flex;
        gap:6px;
        justify-content:center;   /* was: flex-start */
        flex-wrap:nowrap;
        padding: 0 var(--row-xpad);
        min-width:0;
        overflow:hidden;
      }
      .pill {
        display:inline-flex; align-items:center; gap:6px;
        padding:6px 10px; border-radius:14px;
        background:rgba(127,127,127,.12);
        font-size:.8rem; border:1px solid rgba(255,255,255,0.08);
        white-space:nowrap; flex:0 0 auto;
        color: var(--telemetry-text, var(--primary-text-color));
      }
      .pill ha-icon { --mdc-icon-size:16px; width:16px; height:16px; color: var(--telemetry-icon, var(--secondary-text-color)); }

      .click { cursor:pointer; }

    `;

    this._root.innerHTML = `
      <ha-card class="card">
        <style>${style}</style>
        <div class="row-top">
          <div class="title click" id="more" role="button" tabindex="0">
            <div class="shape">
              <div class="ring" id="ring"></div>
              <ha-icon id="icon"></ha-icon>
            </div>
            <div>
              <div class="name" id="name"></div>
              <div class="secondary" id="secondary"></div>
            </div>
          </div>
          <div class="chips" id="chips-container">
            <!-- Buttons will be injected here based on order -->
          </div>
        </div>

        <div class="telemetry">
          <div class="pill"><ha-icon icon="mdi:printer-3d-nozzle-heat"></ha-icon><span id="nozzle"></span></div>
          <div class="pill"><ha-icon icon="mdi:heating-coil"></ha-icon><span id="bed"></span></div>
          <div class="pill" id="box-pill"><ha-icon icon="mdi:thermometer"></ha-icon><span id="box"></span></div>
          <div class="pill"><ha-icon icon="mdi:progress-clock"></ha-icon><span id="time"></span></div>
          <div class="pill"><ha-icon icon="mdi:layers-triple"></ha-icon><span id="layers"></span></div>
        </div>
      </ha-card>
    `;

    // events
    const fireMoreInfo = (eid) => {
      if (!eid) return;
      this.dispatchEvent(new CustomEvent("hass-more-info", {
        detail: { entityId: eid },
        bubbles: true,
        composed: true,
      }));
    };

    this._root.getElementById("more")?.addEventListener("click", () => {
      const eid = this._cfg.camera || this._cfg.status || this._cfg.progress;
      fireMoreInfo(eid);
    });
    this._root.getElementById("more")?.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        const eid = this._cfg.camera || this._cfg.status || this._cfg.progress;
        fireMoreInfo(eid);
      }
    });



    // --- Chip/Button Event Delegation ---
    const chipsContainer = this._root.getElementById("chips-container");
    chipsContainer.addEventListener("click", (e) => {
      const btn = e.target.closest("button.chip");
      if (!btn) return;
      const id = btn.id;

      if (id === "power") {
        const eid = this._resolveEntityId(this._cfg.power, ["switch"]);
        this._toggleEntity(eid);
      } else if (id === "light") {
        const eid = this._resolveEntityId(this._cfg.light, ["light", "switch"]);
        this._toggleEntity(eid);
      } else if (id === "pause") {
        this._pressButtonEntity(this._cfg.pause_btn);
      } else if (id === "resume") {
        this._pressButtonEntity(this._cfg.resume_btn);
      } else if (id === "stop") {
        if (confirm("Are you sure you want to stop the print?")) {
          this._pressButtonEntity(this._cfg.stop_btn);
        }
      } else if (id === "custom") {
        // Custom button can be a button (press), script (turn_on/run), switch (toggle), automation (trigger), etc.
        // For simplicity, treat as toggle if switch/light/input_boolean, else press/turn_on
        const eid = this._cfg.custom_btn;
        const domain = eid ? (eid.split(".")[0] || "").toLowerCase() : "";
        if (["switch", "light", "input_boolean"].includes(domain)) {
          this._toggleEntity(eid);
        } else {
          this._pressButtonEntity(eid);  // Fallback to press (works for button domain, or generic turn_on if mapped)
        }
      }
    });

    this._update();
  }

  // Re-implement _pressButtonEntity to be smarter about non-button domains if needed, 
  // but existing implementation calls button.press. 
  // For custom buttons (e.g. scripts), we might want to default to homeassistant.turn_on if button.press fails is overkill, 
  // but let's keep it simple: if it's a script/automation, button.press might not work.
  // Let's refine _pressButtonEntity to handle more types or create a generic helper.

  async _pressButtonEntity(eid) {
    if (!this._hass || !eid) return;
    const domain = eid.split(".")[0];
    if (domain === "button" || domain === "input_button") {
      await this._hass.callService(domain, "press", { entity_id: eid });
    } else {
      // Fallback for scripts, automations, scenes which act like "press" via turn_on
      await this._hass.callService("homeassistant", "turn_on", { entity_id: eid });
    }
  }
  async _toggleEntity(eid) {
    if (!this._hass || !eid) return;
    const st = this._hass.states[eid];
    const domain = (eid.split(".")[0] || "").toLowerCase();
    if (domain === "switch" || domain === "light") {
      const next = st?.state === "on" ? "off" : "on";
      // Only apply optimistic UI to the power switch; Light strictly reflects HA state
      const resolvedPower = this._resolveEntityId(this._cfg.power, ["switch"]);
      if (resolvedPower && eid === resolvedPower) {
        const now = Date.now();
        this._optimisticStates = this._optimisticStates || {};
        this._optimisticStates[eid] = { state: next, until: now + 2000 };
        this._update();
      }
      await this._hass.callService(domain, next === "on" ? "turn_on" : "turn_off", { entity_id: eid });
    } else {
      await this._hass.callService("homeassistant", "toggle", { entity_id: eid });
    }
  }

  _resolveEntityId(eid, preferredDomains = []) {
    if (!eid || !this._hass) return eid;
    if (this._hass.states[eid]) return eid;
    const parts = String(eid).split(".");
    if (parts.length === 2) {
      const id = parts[1];
      for (const dom of preferredDomains) {
        const candidate = `${dom}.${id}`;
        if (this._hass.states[candidate]) return candidate;
      }
    } else if (parts.length === 1) {
      const id = parts[0];
      for (const dom of preferredDomains) {
        const candidate = `${dom}.${id}`;
        if (this._hass.states[candidate]) return candidate;
      }
    }
    return eid;
  }

  _update() {
    if (!this._root) return;
    const now = Date.now();
    // Purge expired optimistic entries
    if (this._optimisticStates) {
      for (const [key, val] of Object.entries(this._optimisticStates)) {
        if (!val || val.until <= now) delete this._optimisticStates[key];
      }
    }
    const g = (eid) => {
      if (!eid) return undefined;
      const ov = this._optimisticStates?.[eid];
      if (ov && ov.until > now && (eid.startsWith("switch.") || eid.startsWith("light."))) {
        return ov.state;
      }
      return this._hass?.states?.[eid]?.state;
    };
    const gObj = (eid) => this._hass?.states?.[eid];
    const gNum = (eid) => Number(g(eid));
    const fmtState = (st) => {
      if (!st) return "—";
      const v = st.state;
      if (v === undefined || v === null) return "—";
      const s = String(v);
      if (s === "unknown" || s === "unavailable") return "—";
      // Prefer HA's built-in formatter to honor per-entity precision and units
      if (this._hass && typeof this._hass.formatEntityState === 'function') {
        try { return this._hass.formatEntityState(st); } catch (_) { }
      }
      // Fallback: number-aware formatting with (suggested_)display_precision when present
      const unit = st.attributes?.unit_of_measurement;
      const n = Number(s);
      if (!Number.isNaN(n) && Number.isFinite(n)) {
        const dp = (typeof st.attributes?.display_precision === 'number') ? st.attributes.display_precision
          : (typeof st.attributes?.suggested_display_precision === 'number') ? st.attributes.suggested_display_precision
            : (unit && /°|c|f/i.test(unit)) ? 1
              : 2;
        const out = n.toFixed(Math.max(0, Math.min(6, dp)));
        return unit ? `${out} ${unit}` : out;
      }
      return unit ? `${s} ${unit}` : s;
    };
    const fmtWithUnit = (eid) => fmtState(gObj(eid));

    const name = this._cfg.name || "3D Printer";
    const status = g(this._cfg.status) ?? "unknown";
    const pct = clamp(Number.isFinite(gNum(this._cfg.progress)) ? gNum(this._cfg.progress) : 0, 0, 100);
    const timeLeft = gNum(this._cfg.time_left) || 0;
    const nozzleStr = fmtWithUnit(this._cfg.nozzle);
    const bedStr = fmtWithUnit(this._cfg.bed);
    const boxStr = fmtWithUnit(this._cfg.box);
    const layer = (g(this._cfg.layer) ?? "") + "";
    const totalLayers = (g(this._cfg.total_layers) ?? "") + "";
    const resolvedLight = this._resolveEntityId(this._cfg.light, ["light", "switch"]);
    const lightState = this._hass?.states?.[resolvedLight]?.state;
    const resolvedPower = this._resolveEntityId(this._cfg.power, ["switch"]);
    const powerState = g(resolvedPower);

    const st = normStr(status);
    const isPrinting = ["printing", "resuming", "pausing"].includes(st);
    const isPaused = st === "paused";
    const showStop = isPrinting || isPaused || st === "self-testing";
    // Show Light chip only when the light entity exists in HA state and power (if configured) is not OFF
    const showLight = Boolean(resolvedLight && this._hass?.states?.[resolvedLight]) && !(resolvedPower && powerState === "off");
    // Show the Power button whenever configured, independent of printer status
    const showPower = Boolean(this._cfg.show_power_button) && Boolean(this._cfg.power);

    // Title/status
    this._root.getElementById("name").textContent = name;
    const proper = status ? status[0].toUpperCase() + status.slice(1) : "Unknown";
    const sec = (isPrinting || isPaused) ? `${pct}% ${proper}` : proper;
    this._root.getElementById("secondary").textContent = sec;

    // Icon & ring
    const iconEl = this._root.getElementById("icon");
    iconEl.setAttribute("icon", computeIcon(status));
    const theme = this._cfg.theme || {};
    const iconColor = theme.status_icon === "auto" ? computeColor(status) : theme.status_icon;
    iconEl.style.setProperty("--icon-color", iconColor);
    const ring = this._root.getElementById("ring");
    ring.style.setProperty("--ring-pct", isPrinting || isPaused ? `${pct}%` : "0%");
    const ringColor = theme.progress_ring === "auto" ? computeColor(status) : theme.progress_ring;
    ring.style.setProperty("--ring-color", ringColor);

    const chipsContainer = this._root.getElementById("chips-container");

    // Define button definitions
    const buttons = {
      pause: {
        hidden: !isPrinting,
        class: "warn",
        icon: this._cfg.pause_btn_icon || "mdi:pause",
        title: "Pause"
      },
      resume: {
        hidden: !isPaused,
        class: "ok",
        icon: this._cfg.resume_btn_icon || "mdi:play",
        title: "Resume"
      },
      stop: {
        hidden: !showStop,
        class: "danger",
        icon: this._cfg.stop_btn_icon || "mdi:stop",
        title: "Stop"
      },
      light: {
        hidden: !showLight,
        class: lightState === "on" ? "light-on" : "light-off",
        icon: this._cfg.light_btn_icon || "mdi:lightbulb",
        title: "Light"
      },
      power: {
        hidden: !showPower,
        class: "unknown", // Calculated below
        icon: this._cfg.power_btn_icon || "mdi:power",
        title: "Power"
      },
      custom: {
        hidden: Boolean(this._cfg.custom_btn_hidden) || !this._cfg.custom_btn,
        class: "custom",
        icon: this._cfg.custom_btn_icon || "mdi:gesture-tap",
        title: "Custom Action"
      }
    };

    // Calculate Custom Button Class based on state
    if (!buttons.custom.hidden) {
      const customEid = this._cfg.custom_btn;
      const dom = customEid ? customEid.split(".")[0] : "";
      const state = g(customEid);
      // Only use on/off styling for stateful domains
      if (["switch", "light", "input_boolean", "fan", "cover", "binary_sensor"].includes(dom)) {
        const isOn = state === "on" || state === "open"; // cover uses open/closed
        buttons.custom.class = isOn ? "custom-on" : "custom-off";
      }
    }

    // Calculate Power Class Logic
    if (!buttons.power.hidden) {
      this._lastPowerState = this._lastPowerState || null;
      if (powerState === "on" || powerState === "off") {
        this._lastPowerState = powerState;
      }
      const isOn = powerState === "on" || (!powerState && this._lastPowerState === "on");
      const isOff = powerState === "off" || (!powerState && this._lastPowerState === "off");
      buttons.power.class = isOn ? "power-on" : (isOff ? "power-off" : "unknown");
    }

    // Reconstruct DOM only if order or visibility needs update (or simple clear/redraw for robustness)
    // To avoid losing focus or animation, we could diff, but for this card, clear/redraw is fast enough 
    // IF we don't do it every frame. However, we're in _update().
    // Let's build the HTML string for buttons based on order.

    const order = Array.isArray(this._cfg.button_order) ? this._cfg.button_order : ['pause', 'resume', 'stop', 'light', 'power', 'custom'];

    // Filter duplicates and ensure valid keys
    const uniqueOrder = [...new Set(order)].filter(k => buttons[k]);

    // Add any missing standard buttons to the end if not present (backward compat)
    ['pause', 'resume', 'stop', 'light', 'power'].forEach(k => {
      if (!uniqueOrder.includes(k) && buttons[k]) uniqueOrder.push(k);
    });

    let chipsHtml = "";
    uniqueOrder.forEach(key => {
      const btn = buttons[key];
      if (btn && !btn.hidden) {
        chipsHtml += `<button class="chip ${btn.class}" id="${key}" title="${btn.title}"><ha-icon icon="${btn.icon}"></ha-icon></button>`;
      }
    });

    if (chipsContainer.innerHTML !== chipsHtml) {
      chipsContainer.innerHTML = chipsHtml;
    }

    // Telemetry
    this._root.getElementById("nozzle").textContent = nozzleStr;
    this._root.getElementById("bed").textContent = bedStr;
    this._root.getElementById("box").textContent = boxStr;
    this._root.getElementById("time").textContent = fmtTimeLeft(timeLeft);
    this._root.getElementById("layers").textContent = `${layer || "?"}/${totalLayers || "?"}`;

    // Toggle Chamber Temp visibility
    const boxPill = this._root.getElementById("box-pill");
    if (boxPill) {
      if (this._cfg.hide_box_temp) {
        boxPill.style.display = "none";
      } else {
        boxPill.style.display = "";
      }
    }
  }
}
customElements.define(CARD_TAG, KPrinterCard);

/* Interactive theme editor */
class KPrinterCardEditor extends HTMLElement {
  set hass(hass) { this._hass = hass; if (this._entitiesForm) this._entitiesForm.hass = hass; }
  setConfig(config) {
    const defaultConfig = KPrinterCard.getStubConfig();
    this._cfg = { ...defaultConfig, ...(config || {}) };

    // Always ensure theme is properly initialized
    this._cfg.theme = { ...defaultConfig.theme, ...(this._cfg.theme || {}) };

    if (this._root) {
      this._render();
    }
  }
  connectedCallback() { if (!this._root) { this._root = this.attachShadow({ mode: "open" }); this._render(); } }

  _render() {
    if (!this._root || !this._cfg) return;

    try {

      const style = `
      :host { display: block; }
      .editor-container { padding: 16px; max-width: 1200px; margin: 0 auto; }
      .tabs { display: flex; border-bottom: 1px solid var(--divider-color); margin-bottom: 16px; }
      .tab { padding: 8px 16px; cursor: pointer; border-bottom: 2px solid transparent; }
      .tab.active { border-bottom-color: var(--primary-color); color: var(--primary-color); }
      .tab-content { display: none; }
      .tab-content.active { display: block; }
      
      .theme-editor { display: block; }
      
      .theme-controls { 
        display: flex; 
        flex-direction: column; 
        gap: 16px;
      }
      
      .control-group {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 12px;
      }
      
      .group-title {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 8px;
        color: var(--primary-text-color);
      }
      
      .clickable-element {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px;
        border: 1px solid transparent;
        border-radius: 4px;
        cursor: pointer;
        margin: 4px 0;
        transition: all 0.2s;
      }
      
      .clickable-element:hover {
        border-color: var(--primary-color);
        background: rgba(var(--rgb-primary-color), 0.1);
      }
      
      .element-preview {
        width: 24px;
        height: 24px;
        border-radius: 4px;
        border: 1px solid var(--divider-color);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
      }
      
      .element-label {
        font-size: 12px;
        color: var(--primary-text-color);
        flex: 1;
      }
      
      .color-picker-inline {
        background: var(--card-background-color, #ffffff);
        border: 1px solid var(--divider-color, #ccc);
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        display: none;
        position: relative;
        z-index: 10;
      }
      
      .color-picker-inline.active {
        display: block;
      }
      
      
      .reset-btn { 
        background: var(--error-color);
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        margin-top: 16px;
        width: 100%;
      }
      
      .reset-btn:hover {
        opacity: 0.8;
      }
      
      .input-row { margin-bottom: 12px; }
      .input-label { display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--primary-text-color); }
      .text-input { width: 100%; padding: 8px; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color); box-sizing: border-box;}
      .input-helper { font-size: 11px; color: var(--secondary-text-color); margin-top: 2px; }
      .checkbox-row { display: flex; align-items: center; justify-content: space-between; }
    `;

      this._root.innerHTML = `
      <style>${style}</style>
      <div class="editor-container">
        <h2 style="margin: 0 0 16px 0; font-size: 18px; color: var(--primary-text-color);">Creality Printer Card Configuration</h2>
        <div class="tabs">
          <div class="tab active" data-tab="entities">Entities</div>
          <div class="tab" data-tab="theme">Theme</div>
        </div>
        
        <div class="tab-content active" id="entities-tab">
          <ha-form id="entities-form"></ha-form>
        </div>
        
        <div class="tab-content" id="theme-tab">
          <div class="theme-editor">
            <div class="theme-controls">
              <div class="control-group">
                <div class="group-title">Layout & Icons</div>
                <ha-form id="theme-settings-form"></ha-form>
              </div>

              <div class="control-group">
                <div class="group-title">Action Colors</div>
                <div class="clickable-element" data-theme="pause_bg" data-label="Pause Button Background">
                  <div class="element-preview" style="background: ${this._cfg.theme.pause_bg}"></div>
                  <div class="element-label">Pause Button Background</div>
                </div>
                <div class="color-picker-inline" id="color-picker-pause_bg">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.pause_bg)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.pause_bg)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="pause_bg" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="pause_icon" data-label="Pause Button Icon">
                  <div class="element-preview" style="background: ${this._cfg.theme.pause_icon}; color: ${this._cfg.theme.pause_icon}">⏸</div>
                  <div class="element-label">Pause Button Icon</div>
                </div>
                <div class="color-picker-inline" id="color-picker-pause_icon">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.pause_icon)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.pause_icon)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="pause_icon" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="resume_bg" data-label="Resume Button Background">
                  <div class="element-preview" style="background: ${this._cfg.theme.resume_bg}"></div>
                  <div class="element-label">Resume Button Background</div>
                </div>
                <div class="color-picker-inline" id="color-picker-resume_bg">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.resume_bg)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.resume_bg)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="resume_bg" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="resume_icon" data-label="Resume Button Icon">
                  <div class="element-preview" style="background: ${this._cfg.theme.resume_icon}; color: ${this._cfg.theme.resume_icon}">▶</div>
                  <div class="element-label">Resume Button Icon</div>
                </div>
                <div class="color-picker-inline" id="color-picker-resume_icon">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.resume_icon)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.resume_icon)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="resume_icon" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="stop_bg" data-label="Stop Button Background">
                  <div class="element-preview" style="background: ${this._cfg.theme.stop_bg}"></div>
                  <div class="element-label">Stop Button Background</div>
                </div>
                <div class="color-picker-inline" id="color-picker-stop_bg">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.stop_bg)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.stop_bg)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="stop_bg" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="stop_icon" data-label="Stop Button Icon">
                  <div class="element-preview" style="background: ${this._cfg.theme.stop_icon}; color: ${this._cfg.theme.stop_icon}">⏹</div>
                  <div class="element-label">Stop Button Icon</div>
                </div>
                <div class="color-picker-inline" id="color-picker-stop_icon">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.stop_icon)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.stop_icon)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="stop_icon" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="light_on_bg" data-label="Light On Background">
                  <div class="element-preview" style="background: ${this._cfg.theme.light_on_bg}"></div>
                  <div class="element-label">Light On Background</div>
                </div>
                <div class="color-picker-inline" id="color-picker-light_on_bg">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.light_on_bg)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.light_on_bg)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="light_on_bg" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="light_off_bg" data-label="Light Off Background">
                  <div class="element-preview" style="background: ${this._cfg.theme.light_off_bg}"></div>
                  <div class="element-label">Light Off Background</div>
                </div>
                <div class="color-picker-inline" id="color-picker-light_off_bg">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.light_off_bg)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.light_off_bg)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="light_off_bg" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="light_icon_on" data-label="Light Button Icon (On)">
                  <div class="element-preview" style="background: ${this._cfg.theme.light_icon_on}; color: ${this._cfg.theme.light_icon_on}">💡</div>
                  <div class="element-label">Light Button Icon (On)</div>
                </div>
                <div class="color-picker-inline" id="color-picker-light_icon_on">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.light_icon_on)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.light_icon_on)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="light_icon_on" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="light_icon_off" data-label="Light Button Icon (Off)">
                  <div class="element-preview" style="background: ${this._cfg.theme.light_icon_off}; color: ${this._cfg.theme.light_icon_off}">💡</div>
                  <div class="element-label">Light Button Icon (Off)</div>
                </div>
                <div class="color-picker-inline" id="color-picker-light_icon_off">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.light_icon_off)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.light_icon_off)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="light_icon_off" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="custom_bg" data-label="Custom Button Background">
                  <div class="element-preview" style="background: ${this._cfg.theme.custom_bg}"></div>
                  <div class="element-label">Custom Button Background</div>
                </div>
                <div class="color-picker-inline" id="color-picker-custom_bg">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.custom_bg)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.custom_bg)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="custom_bg" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="custom_icon" data-label="Custom Button Icon">
                  <div class="element-preview" style="background: ${this._cfg.theme.custom_icon}; color: ${this._cfg.theme.custom_icon}">★</div>
                  <div class="element-label">Custom Button Icon</div>
                </div>
                <div class="color-picker-inline" id="color-picker-custom_icon">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${rgbaToHex(this._cfg.theme.custom_icon)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${rgbaToHex(this._cfg.theme.custom_icon)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="custom_icon" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
              </div>
              
              <div class="control-group">
                <div class="group-title">Status Area</div>
                <div class="clickable-element" data-theme="status_icon" data-label="Status Icon Color">
                  <div class="element-preview" style="background: ${this._cfg.theme.status_icon === 'auto' ? 'var(--primary-color)' : this._cfg.theme.status_icon}">🖨</div>
                  <div class="element-label">Status Icon Color</div>
                </div>
                <div class="color-picker-inline" id="color-picker-status_icon">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${this._cfg.theme.status_icon === 'auto' ? '#000000' : rgbaToHex(this._cfg.theme.status_icon)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${this._cfg.theme.status_icon === 'auto' ? 'auto' : rgbaToHex(this._cfg.theme.status_icon)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="status_icon" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="progress_ring" data-label="Progress Ring Color">
                  <div class="element-preview" style="background: ${this._cfg.theme.progress_ring === 'auto' ? 'var(--primary-color)' : this._cfg.theme.progress_ring}">⭕</div>
                  <div class="element-label">Progress Ring Color</div>
                </div>
                <div class="color-picker-inline" id="color-picker-progress_ring">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${this._cfg.theme.progress_ring === 'auto' ? '#000000' : rgbaToHex(this._cfg.theme.progress_ring)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${this._cfg.theme.progress_ring === 'auto' ? 'auto' : rgbaToHex(this._cfg.theme.progress_ring)}" placeholder="#000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="progress_ring" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="status_bg" data-label="Status Background">
                  <div class="element-preview" style="background: ${this._cfg.theme.status_bg}">🎯</div>
                  <div class="element-label">Status Background</div>
                </div>
                <div class="color-picker-inline" id="color-picker-status_bg">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${this._cfg.theme.status_bg === 'auto' ? 'var(--card-background-color)' : rgbaToHex(this._cfg.theme.status_bg)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${this._cfg.theme.status_bg === 'auto' ? 'auto' : rgbaToHex(this._cfg.theme.status_bg)}" placeholder="auto or #000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="status_bg" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
              </div>
              
              <div class="control-group">
                <div class="group-title">Telemetry</div>
                <div class="clickable-element" data-theme="telemetry_icon" data-label="Telemetry Icon Color">
                  <div class="element-preview" style="background: ${this._cfg.theme.telemetry_icon}">🌡</div>
                  <div class="element-label">Telemetry Icon Color</div>
                </div>
                <div class="color-picker-inline" id="color-picker-telemetry_icon">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${this._cfg.theme.telemetry_icon === 'auto' ? 'var(--secondary-text-color)' : rgbaToHex(this._cfg.theme.telemetry_icon)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${this._cfg.theme.telemetry_icon === 'auto' ? 'auto' : rgbaToHex(this._cfg.theme.telemetry_icon)}" placeholder="auto or #000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="telemetry_icon" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
                <div class="clickable-element" data-theme="telemetry_text" data-label="Telemetry Text Color">
                  <div class="element-preview" style="background: ${this._cfg.theme.telemetry_text}">📝</div>
                  <div class="element-label">Telemetry Text Color</div>
                </div>
                <div class="color-picker-inline" id="color-picker-telemetry_text">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="color-preview" style="width: 30px; height: 30px; border: 2px solid #ccc; border-radius: 4px; background: ${this._cfg.theme.telemetry_text === 'auto' ? 'var(--primary-text-color)' : rgbaToHex(this._cfg.theme.telemetry_text)}; cursor: pointer;" title="Click to open color picker"></div>
                    <input type="text" class="color-text" value="${this._cfg.theme.telemetry_text === 'auto' ? 'auto' : rgbaToHex(this._cfg.theme.telemetry_text)}" placeholder="auto or #000000" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 12px;">
                    <button class="save-color-btn" data-theme="telemetry_text" style="padding: 6px 12px; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Save</button>
                  </div>
                </div>
              </div>
              
              <button class="reset-btn" id="reset-theme">Reset to Defaults</button>
            </div>
          </div>
        </div>
      </div>
    `;

      this._setupTabs();
      this._setupEntitiesForm();
      this._setupThemeEditor();

    } catch (error) {
      console.error('Error rendering K-Printer Card Editor:', error);
      this._root.innerHTML = `
        <div style="padding: 16px; color: var(--error-color);">
          <h3>Editor Error</h3>
          <p>There was an error loading the visual editor. You can still edit your configuration using YAML.</p>
          <p>Error: ${error.message}</p>
        </div>
      `;
    }
  }

  _setupTabs() {
    const tabs = this._root.querySelectorAll('.tab');
    const contents = this._root.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        contents.forEach(c => c.classList.remove('active'));

        tab.classList.add('active');
        const tabId = tab.dataset.tab + '-tab';
        this._root.getElementById(tabId).classList.add('active');
      });
    });
  }

  _setupEntitiesForm() {
    this._entitiesForm = this._root.getElementById('entities-form');
    this._entitiesForm.hass = this._hass;

    // Helper text mapping for form fields
    const helperText = {
      "name": "Display name for the printer card",
      "camera": "Camera entity for live video feed",
      "status": "Sensor showing current print status",
      "progress": "Sensor showing print progress (0-100%)",
      "time_left": "Sensor showing remaining print time (seconds)",
      "nozzle": "Sensor showing nozzle temperature",
      "bed": "Sensor showing bed temperature",
      "box": "Sensor showing chamber/enclosure temperature (optional)",
      "power": "Optional power switch entity for the printer (shows a Power button when set)",
      "show_power_button": "Show the Power button when a power switch entity is configured",
      "layer": "Sensor showing current print layer",
      "total_layers": "Sensor showing total print layers",
      "light": "Switch entity for printer light control",
      "pause_btn": "Button entity to pause printing",
      "resume_btn": "Button entity to resume printing",
      "stop_btn": "Button entity to stop printing",
      "custom_btn": "Any entity to trigger (Button, Script, Switch, etc.)",
      "custom_btn_icon": "Icon for the custom button",
      "custom_btn_hidden": "Hide the custom button",
      "button_order": "List of buttons to show in order (pause, resume, stop, light, power, custom)"
    };

    this._entitiesForm.schema = [
      { name: "name", selector: { text: {} } },
      { name: "camera", selector: { entity: { domain: "camera" } } },
      { name: "status", selector: { entity: { domain: "sensor" } } },
      { name: "progress", selector: { entity: { domain: "sensor" } } },
      { name: "time_left", selector: { entity: { domain: "sensor" } } },
      { name: "nozzle", selector: { entity: { domain: "sensor" } } },
      { name: "bed", selector: { entity: { domain: "sensor" } } },
      { name: "box", selector: { entity: { domain: "sensor" } } },
      { name: "power", selector: { entity: { domain: ["switch", "input_boolean"] } } },
      { name: "show_power_button", selector: { boolean: {} } },
      { name: "layer", selector: { entity: { domain: "sensor" } } },
      { name: "total_layers", selector: { entity: { domain: "sensor" } } },
      { name: "light", selector: { entity: { domain: ["switch", "light"] } } },
      { name: "pause_btn", selector: { entity: { domain: "button" } } },
      { name: "resume_btn", selector: { entity: { domain: "button" } } },
      { name: "stop_btn", selector: { entity: { domain: "button" } } },
      { name: "custom_btn", selector: { entity: {} } },
    ];

    // Label text mapping for form fields
    const labelText = {
      "name": "Printer Name",
      "camera": "Camera",
      "status": "Print Status Sensor",
      "progress": "Print Progress Sensor (%)",
      "time_left": "Time Left Sensor",
      "nozzle": "Nozzle Temperature Sensor",
      "bed": "Bed Temperature Sensor",
      "box": "Chamber Temperature Sensor",
      "power": "Power Switch",
      "show_power_button": "Show Power Button",
      "layer": "Current Layer Sensor",
      "total_layers": "Total Layers Sensor",
      "light": "Light Switch",
      "pause_btn": "Pause Button",
      "resume_btn": "Resume Button",
      "stop_btn": "Stop Button",
      "custom_btn": "Custom Action Entity",
      "custom_btn_icon": "Custom Button Icon",
      "custom_btn_hidden": "Hide Custom Button",
      "button_order": "Button Order (list)"
    };

    // Add label computation using computeLabel if supported
    if (this._entitiesForm.computeLabel) {
      const originalComputeLabel = this._entitiesForm.computeLabel.bind(this._entitiesForm);
      this._entitiesForm.computeLabel = (schema) => {
        return labelText[schema.name] || originalComputeLabel(schema);
      };
    }

    // Add helper text using computeHelper if supported
    if (this._entitiesForm.computeHelper) {
      const originalComputeHelper = this._entitiesForm.computeHelper.bind(this._entitiesForm);
      this._entitiesForm.computeHelper = (schema) => {
        return helperText[schema.name] || originalComputeHelper(schema);
      };
    }

    this._entitiesForm.data = this._cfg;

    this._entitiesForm.addEventListener("value-changed", (ev) => {
      const val = ev.detail?.value || {};
      this._cfg = { ...this._cfg, ...val };
      this._dispatchConfigChange();
    });
  }

  _setupThemeEditor() {

    // Setup generic config form (Layout & Icons)
    this._themeSettingsForm = this._root.getElementById('theme-settings-form');
    this._themeSettingsForm.hass = this._hass;

    const themeSettingsSchema = [
      { name: "button_order", selector: { text: {} }, label: "Button Order (pause, resume, stop, light, power, custom)" },
      { name: "custom_btn_hidden", selector: { boolean: {} }, label: "Hide Custom Button" },
      { name: "hide_box_temp", selector: { boolean: {} }, label: "Hide Chamber Temperature" },
      { name: "pause_btn_icon", selector: { icon: {} }, label: "Pause Icon Override" },
      { name: "resume_btn_icon", selector: { icon: {} }, label: "Resume Icon Override" },
      { name: "stop_btn_icon", selector: { icon: {} }, label: "Stop Icon Override" },
      { name: "light_btn_icon", selector: { icon: {} }, label: "Light Icon Override" },
      { name: "power_btn_icon", selector: { icon: {} }, label: "Power Icon Override" },
      { name: "custom_btn_icon", selector: { icon: {} }, label: "Custom Button Icon" },
    ];

    // Polyfill label if needed or rely on 'label' property in schema if HA supports it (HA Form supports 'label' in schema usually? No, it uses computeLabel)
    // Let's use computeLabel for this form too.
    this._themeSettingsForm.schema = themeSettingsSchema;

    // Prepare data for the form. button_order needs to be stringified if it's an array, or handled as list.
    // Text input expects string.
    const prepareFormData = (cfg) => {
      return {
        ...cfg,
        button_order: Array.isArray(cfg.button_order) ? cfg.button_order.join(', ') : cfg.button_order
      };
    };

    this._themeSettingsForm.data = prepareFormData(this._cfg);

    this._themeSettingsForm.addEventListener("value-changed", (ev) => {
      const val = ev.detail?.value || {};

      // Post-process button_order back to array
      if (val.button_order && typeof val.button_order === 'string') {
        val.button_order = val.button_order.split(',').map(s => s.trim()).filter(s => s);
      }

      this._cfg = { ...this._cfg, ...val };
      this._dispatchConfigChange();
    });

    // Setup clickable elements to toggle inline color pickers
    const clickableElements = this._root.querySelectorAll('.clickable-element');
    clickableElements.forEach(element => {
      element.addEventListener('click', () => {
        const themeKey = element.dataset.theme;
        this._toggleColorPicker(themeKey);
      });
    });

    // Setup color picker interactions
    this._setupColorPickerInteractions();

    // Setup reset button
    this._root.getElementById('reset-theme').addEventListener('click', () => {
      const defaultConfig = KPrinterCard.getStubConfig();
      // Reset Theme
      this._cfg.theme = { ...defaultConfig.theme };

      // Reset Layout & Icons
      ['button_order', 'custom_btn_hidden', 'pause_btn_icon', 'resume_btn_icon', 'stop_btn_icon', 'light_btn_icon', 'power_btn_icon', 'custom_btn_icon'].forEach(k => {
        this._cfg[k] = defaultConfig[k];
      });

      // Clear saved theme from storage
      const cardId = generateCardId(this._cfg);
      try {
        const themes = JSON.parse(localStorage.getItem(THEME_STORAGE_KEY) || "{}");
        delete themes[cardId];
        localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(themes));
      } catch (e) {
        console.warn("Failed to clear theme from localStorage:", e);
      }

      this._updateThemeControls();

      // Update config inputs as well
      if (this._themeSettingsForm) {
        this._themeSettingsForm.data = prepareFormData(this._cfg);
      }

      this._dispatchConfigChange();
    });
  }

  _toggleColorPicker(themeKey) {
    const picker = this._root.getElementById(`color-picker-${themeKey}`);
    if (!picker) return;

    // If this picker is already active, close it
    if (picker.classList.contains('active')) {
      picker.classList.remove('active');
      return;
    }

    // Hide all other color pickers
    const allPickers = this._root.querySelectorAll('.color-picker-inline');
    allPickers.forEach(p => {
      p.classList.remove('active');
    });

    // Show the clicked color picker
    picker.classList.add('active');
  }

  _setupColorPickerInteractions() {
    // Setup color preview clicks to open native color picker
    const colorPreviews = this._root.querySelectorAll('.color-preview');
    colorPreviews.forEach(preview => {
      preview.addEventListener('click', () => {
        const picker = preview.closest('.color-picker-inline');
        if (picker) {
          const textInput = picker.querySelector('.color-text');
          if (textInput) {
            // Create a visible color input that stays in the editor
            const input = document.createElement('input');
            input.type = 'color';
            input.value = textInput.value === 'auto' ? '#000000' : textInput.value;

            // Style the input to be visible and positioned within the picker
            input.style.position = 'absolute';
            input.style.left = '0';
            input.style.top = '0';
            input.style.width = '100%';
            input.style.height = '100%';
            input.style.opacity = '0';
            input.style.cursor = 'pointer';
            input.style.zIndex = '10';

            // Add the input to the picker container
            picker.style.position = 'relative';
            picker.appendChild(input);

            // Focus and click the input
            input.focus();
            input.click();

            // Handle color change
            input.addEventListener('change', () => {
              const newColor = input.value;
              textInput.value = newColor;
              preview.style.background = newColor;

              // Remove the input after color selection
              if (picker.contains(input)) {
                picker.removeChild(input);
              }
            });

            // Handle escape key
            const handleKeyDown = (e) => {
              if (e.key === 'Escape') {
                if (picker.contains(input)) {
                  picker.removeChild(input);
                }
                document.removeEventListener('keydown', handleKeyDown);
              }
            };
            document.addEventListener('keydown', handleKeyDown);

            // Handle clicks outside the picker
            const handleClickOutside = (e) => {
              if (!picker.contains(e.target)) {
                if (picker.contains(input)) {
                  picker.removeChild(input);
                }
                document.removeEventListener('click', handleClickOutside);
              }
            };

            // Add click outside handler after a delay
            setTimeout(() => {
              document.addEventListener('click', handleClickOutside);
            }, 100);
          }
        }
      });
    });

    // Setup text input changes
    const colorTexts = this._root.querySelectorAll('.color-text');
    colorTexts.forEach(textInput => {
      textInput.addEventListener('input', () => {
        const value = textInput.value;
        if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
          const picker = textInput.closest('.color-picker-inline');
          if (picker) {
            const preview = picker.querySelector('.color-preview');
            if (preview) {
              preview.style.background = value;
            }
          }
        }
      });
    });

    // Setup save buttons
    const saveButtons = this._root.querySelectorAll('.save-color-btn');
    saveButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();

        const themeKey = button.dataset.theme;
        const picker = button.closest('.color-picker-inline');
        if (picker) {
          const textInput = picker.querySelector('.color-text');
          if (textInput) {
            let newValue;
            const inputValue = textInput.value;

            // Handle special cases for auto-supported fields
            if ((themeKey === 'status_icon' || themeKey === 'progress_ring' ||
              themeKey === 'status_bg' || themeKey === 'telemetry_icon' ||
              themeKey === 'telemetry_text') && inputValue === 'auto') {
              newValue = 'auto';
            } else if (/^#[0-9A-Fa-f]{6}$/.test(inputValue)) {
              newValue = hexToRgba(inputValue, 0.9);
            } else {
              // Keep existing value if input is invalid
              newValue = this._cfg.theme[themeKey];
            }


            this._cfg.theme = { ...this._cfg.theme, [themeKey]: newValue };

            // Save to storage
            const cardId = generateCardId(this._cfg);
            saveThemeToStorage(cardId, this._cfg.theme);

            this._updateThemeControls();

            // Hide the color picker first
            picker.classList.remove('active');

            // Dispatch config change after a small delay to prevent tab switching
            setTimeout(() => {
              this._dispatchConfigChange();
            }, 100);
          }
        }
      });
    });
  }



  _updateThemeControls() {
    // Update all preview elements with new colors
    const clickableElements = this._root.querySelectorAll('.clickable-element');
    clickableElements.forEach(element => {
      const themeKey = element.dataset.theme;
      const preview = element.querySelector('.element-preview');
      const currentValue = this._cfg.theme[themeKey] || '';

      if (themeKey === 'status_icon' || themeKey === 'progress_ring') {
        preview.style.background = currentValue === 'auto' ? 'var(--primary-color)' : currentValue;
      } else {
        preview.style.background = currentValue;
      }

      if (['pause_icon', 'resume_icon', 'stop_icon', 'light_icon_on', 'light_icon_off', 'custom_icon'].includes(themeKey)) {
        preview.style.color = currentValue;
      }
    });

    // Update color picker previews and text inputs
    const colorPickers = this._root.querySelectorAll('.color-picker-inline');
    colorPickers.forEach(picker => {
      const themeKey = picker.id.replace('color-picker-', '');
      const themeValue = this._cfg.theme[themeKey];
      const preview = picker.querySelector('.color-preview');
      const textInput = picker.querySelector('.color-text');

      if (preview && textInput) {
        if (themeKey === 'status_icon' || themeKey === 'progress_ring' ||
          themeKey === 'status_bg' || themeKey === 'telemetry_icon' ||
          themeKey === 'telemetry_text') {
          if (themeValue === 'auto') {
            // Show appropriate theme color for auto values
            if (themeKey === 'status_bg') {
              preview.style.background = 'var(--card-background-color)';
            } else if (themeKey === 'telemetry_icon') {
              preview.style.background = 'var(--secondary-text-color)';
            } else if (themeKey === 'telemetry_text') {
              preview.style.background = 'var(--primary-text-color)';
            } else {
              preview.style.background = '#000000';
            }
            textInput.value = 'auto';
          } else {
            preview.style.background = rgbaToHex(themeValue);
            textInput.value = rgbaToHex(themeValue);
          }
        } else {
          preview.style.background = rgbaToHex(themeValue);
          textInput.value = rgbaToHex(themeValue);
        }
      }
    });
  }

  _dispatchConfigChange() {
    clearTimeout(this._t);
    this._t = setTimeout(() => {
      // Preserve current tab state
      const activeTab = this._root.querySelector('.tab.active');
      const activeTabId = activeTab ? activeTab.dataset.tab : 'entities';

      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._cfg } }));

      // Restore tab state after a brief delay
      setTimeout(() => {
        this._restoreTabState(activeTabId);
      }, 50);
    }, 120);
  }

  _restoreTabState(activeTabId) {
    // Switch to the preserved tab
    const tabs = this._root.querySelectorAll('.tab');
    const tabContents = this._root.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
      tab.classList.remove('active');
      if (tab.dataset.tab === activeTabId) {
        tab.classList.add('active');
      }
    });

    tabContents.forEach(content => {
      content.classList.remove('active');
      if (content.id === `${activeTabId}-tab`) {
        content.classList.add('active');
      }
    });
  }
}
customElements.define(EDITOR_TAG, KPrinterCardEditor);

try {
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TAG,
    name: "Creality Printer Card",
    description: "Standalone card for Creality K-Series printers",
    preview: true,
  });
} catch (_) { }
