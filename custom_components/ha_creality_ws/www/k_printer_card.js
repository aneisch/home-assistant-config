const CARD_TAG = "k-printer-card";
const EDITOR_TAG = "k-printer-card-editor";

const I18N_URL_BASE = "/ha_creality_ws/i18n/";
const _i18nData = {};
const _i18nPromises = {};
function _loadI18n(lang) {
  if (_i18nData[lang]) return Promise.resolve(_i18nData[lang]);
  if (_i18nPromises[lang]) return _i18nPromises[lang];
  _i18nPromises[lang] = fetch(`${I18N_URL_BASE}${lang}.json`)
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      if (data) _i18nData[lang] = data;
      else _i18nPromises[lang] = null;
      return data;
    })
    .catch(() => { _i18nPromises[lang] = null; return null; });
  return _i18nPromises[lang];
}
function _resolveLang(hass) {
  return hass?.locale?.language || hass?.language || "en";
}
function _translate(hass, section, fallbackDict, key, vars) {
  const lang = _resolveLang(hass);
  const short = lang.split("-")[0];
  const remote = _i18nData[lang]?.[section] ?? _i18nData[short]?.[section];
  const remoteEn = _i18nData["en"]?.[section];
  let text = (remote && key in remote) ? remote[key]
    : (remoteEn && key in remoteEn) ? remoteEn[key]
      : (fallbackDict[lang]?.[key] ?? fallbackDict[short]?.[key] ?? fallbackDict["en"]?.[key] ?? key);
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replace(new RegExp(`\\{${name}\\}`, "g"), value);
    }
  }
  return text;
}
function _requestI18n(instance, hass, onLoaded) {
  if (instance._i18nRequested) return;
  instance._i18nRequested = true;
  const lang = _resolveLang(hass).split("-")[0];
  Promise.all([_loadI18n("en"), lang !== "en" ? _loadI18n(lang) : null]).then(onLoaded);
}

// Per-card-id throttle for ll-rebuild dispatches. ll-rebuild may cause Lovelace to
// recreate the element, in which case instance state (this._cardSize) is reset. A
// module-level record survives recreation and prevents a measure→dispatch→recreate
// loop if size measurement on the fresh instance keeps producing the same delta.
const LL_REBUILD_MIN_INTERVAL_MS = 2000;
const _lastCardRebuildDispatch = new Map();

// How much wider, in px, the telemetry row has to get before the units it
// dropped are worth retrying. Retrying at the width that rejected them would
// restore them, wrap the row, and hide them again on the next measurement, for
// as long as the card stayed that size.
const TELEMETRY_COMPACT_HYSTERESIS = 8;

const INTEGRATION_DOMAIN = "ha_creality_ws";
// The name a card carries until the user (or the device picker) names it.
const DEFAULT_CARD_NAME = "3D Printer";

/**
 * Card roles the printer's own device can fill, keyed by the translation_key
 * the integration gives each entity.
 *
 * A translation_key survives renaming the entity, so picking a device wires the
 * card up by role rather than by whatever the entity ids happen to be -- the
 * same trick ha_washdata uses to auto-wire its siblings. The domain is checked
 * too, because a key is only unique within one.
 *
 * `power` is deliberately absent: the integration exposes no power switch, so
 * that field is always the user's own smart plug and cannot be guessed.
 */
const DEVICE_ROLE_ENTITIES = {
  camera: { translationKey: "printer_camera", domain: "camera" },
  status: { translationKey: "print_status", domain: "sensor" },
  progress: { translationKey: "print_progress", domain: "sensor" },
  time_left: { translationKey: "print_left_time", domain: "sensor" },
  nozzle: { translationKey: "nozzle_temperature", domain: "sensor" },
  bed: { translationKey: "bed_temperature", domain: "sensor" },
  box: { translationKey: "chamber_temperature", domain: "sensor" },
  layer: { translationKey: "current_layer", domain: "sensor" },
  total_layers: { translationKey: "total_layers", domain: "sensor" },
  light: { translationKey: "light", domain: "light" },
  pause_btn: { translationKey: "pause_print", domain: "button" },
  resume_btn: { translationKey: "resume_print", domain: "button" },
  stop_btn: { translationKey: "stop_print", domain: "button" },
};

/**
 * Find this integration's entities for one device, by card role.
 * @param {?Object} hass
 * @param {string} deviceId
 * @return {!Object<string, string>} Role -> entity id. Roles the device does
 *     not expose are omitted rather than blanked: a KE has no chamber sensor,
 *     and a printer with the camera disabled has no camera entity.
 */
function entitiesForDevice(hass, deviceId) {
  const registry = hass?.entities || {};
  const found = {};
  if (!deviceId) return found;
  for (const [entityId, entry] of Object.entries(registry)) {
    if (!entry || entry.device_id !== deviceId) continue;
    if (entry.platform && entry.platform !== INTEGRATION_DOMAIN) continue;
    const domain = entityId.split(".")[0];
    for (const [role, want] of Object.entries(DEVICE_ROLE_ENTITIES)) {
      if (found[role]) continue;
      if (entry.translation_key !== want.translationKey) continue;
      if (domain !== want.domain) continue;
      found[role] = entityId;
    }
  }
  return found;
}

const clamp = (v, a, b) => Math.min(Math.max(v, a), b);
const mdi = (name) => `mdi:${name}`;
const normStr = (x) => String(x ?? "").toLowerCase();

// Theme persistence utilities
const THEME_STORAGE_KEY = "k-printer-card-themes";

// Colour conversion utilities.
//
// Theme values live in the card config as CSS colour strings so an existing
// YAML config keeps working, while the editor's colour controls speak
// [r, g, b] plus a separate opacity. These two functions are that boundary,
// and alpha survives the round trip -- the pair they replace parsed only
// 6-digit hex and `rgb(...)`, so `#fff` and every alpha the defaults ship
// with were silently rewritten to black at 90% on the first edit.

/**
 * Parse a CSS colour the editor can round-trip.
 * @param {string} value Colour string, or "auto"/""/`var(...)`.
 * @return {?{rgb: !Array<number>, alpha: number}} Null when there is no
 *     literal colour to edit, which is how "auto" reaches the form as empty.
 */
function parseColor(value) {
  const raw = String(value ?? "").trim();
  if (!raw || raw === "auto" || raw.startsWith("var(")) return null;

  const hex = /^#([0-9a-fA-F]+)$/.exec(raw);
  if (hex) {
    const digits = hex[1];
    const nibble = (s) => parseInt(s.length === 1 ? s + s : s, 16);
    if (digits.length === 3 || digits.length === 4) {
      return {
        rgb: [nibble(digits[0]), nibble(digits[1]), nibble(digits[2])],
        alpha: digits.length === 4 ? nibble(digits[3]) / 255 : 1,
      };
    }
    if (digits.length === 6 || digits.length === 8) {
      return {
        rgb: [nibble(digits.slice(0, 2)), nibble(digits.slice(2, 4)), nibble(digits.slice(4, 6))],
        alpha: digits.length === 8 ? nibble(digits.slice(6, 8)) / 255 : 1,
      };
    }
    return null;
  }

  const fn = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]*\d)\s*)?\)$/.exec(raw);
  if (!fn) return null;
  const rgb = [fn[1], fn[2], fn[3]].map((n) => Number(n));
  if (rgb.some((n) => !Number.isFinite(n))) return null;
  const alpha = fn[4] === undefined ? 1 : Number(fn[4]);
  return {
    rgb: rgb.map((n) => clamp(Math.round(n), 0, 255)),
    alpha: Number.isFinite(alpha) ? clamp(alpha, 0, 1) : 1,
  };
}

/**
 * Render [r, g, b] plus an alpha back into the config's colour string form.
 * @param {!Array<number>} rgb Channel values, 0-255.
 * @param {number=} alpha 0-1. A fully opaque colour is written as hex so the
 *     config stays readable; anything translucent needs rgba().
 * @return {string} The colour string, or "auto" when rgb is not a triple.
 */
function formatColor(rgb, alpha = 1) {
  if (!Array.isArray(rgb) || rgb.length < 3) return "auto";
  const [r, g, b] = rgb.map((n) => clamp(Math.round(Number(n) || 0), 0, 255));
  const a = clamp(Number.isFinite(Number(alpha)) ? Number(alpha) : 1, 0, 1);
  if (a >= 1) {
    return `#${[r, g, b].map((n) => n.toString(16).padStart(2, "0")).join("")}`;
  }
  return `rgba(${r}, ${g}, ${b}, ${Number(a.toFixed(3))})`;
}

/**
 * Split a formatted state into its value and unit halves.
 *
 * Home Assistant's formatter returns them as one string; the telemetry row
 * needs them apart so the unit can be dropped when the pills stop fitting on
 * one line.
 * @param {string} text Formatted state, e.g. "210.0 \u00b0C".
 * @param {?Object} stateObj The state the text came from.
 * @return {{value: string, unit: string}}
 */
function splitUnit(text, stateObj) {
  const s = String(text ?? "");
  const unit = String(stateObj?.attributes?.unit_of_measurement ?? "").trim();
  if (unit && s.length > unit.length && s.endsWith(unit)) {
    const head = s.slice(0, s.length - unit.length);
    // The unit has to be preceded by a digit or a space. A bare suffix
    // match truncates a word that merely ends in the unit's letters:
    // "idle" on a sensor whose unit is "e" rendered as "idl". Tested on
    // the character rather than by parsing the remainder, because a
    // locale that groups digits ("1 234,5") is not a number to Number().
    if (/[\d\s]$/.test(head)) {
      return { value: head.trimEnd(), unit };
    }
  }
  return { value: s, unit: "" };
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

// Home Assistant rewrites a DURATION sensor's state into whichever display unit
// the user picked in the entity settings, so the seconds sensor this card expects
// arrives as 0.2 once someone switches it to hours. Scale back to seconds before
// formatting; an unrecognised or missing unit is taken as seconds, which is the
// integration's own native unit.
const DURATION_UNIT_SECONDS = {
  "\u00b5s": 1e-6, "\u03bcs": 1e-6, us: 1e-6, ms: 1e-3,
  s: 1, sec: 1, secs: 1, second: 1, seconds: 1,
  min: 60, mins: 60, minute: 60, minutes: 60,
  h: 3600, hr: 3600, hrs: 3600, hour: 3600, hours: 3600,
  d: 86400, day: 86400, days: 86400,
  w: 604800, week: 604800, weeks: 604800,
};
function durationToSeconds(stateObj) {
  const n = Number(stateObj?.state);
  if (!Number.isFinite(n)) return 0;
  const unit = String(stateObj?.attributes?.unit_of_measurement ?? "").trim();
  const scale = DURATION_UNIT_SECONDS[unit] ?? DURATION_UNIT_SECONDS[unit.toLowerCase()];
  return n * (scale ?? 1);
}
function fmtTimeLeft(seconds) {
  // Floor to whole seconds so a fractional value (some firmwares report a float)
  // renders as e.g. 2:25 instead of 2:25.6789 and doesn't reflow the row every poll.
  const s = Math.floor(Number(seconds) || 0);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  if (m > 0) return `${m}:${String(sec).padStart(2, "0")}`;
  return `${sec}s`;
}
// Every state utils.derive_print_state can return. Mirrored here so a state
// added on the Python side cannot silently fall through to a default, and so
// impossible states cannot creep back in -- test_printer_card_layout.py
// cross-checks this list against derive_print_state.
const PRINT_STATES = new Set([
  "off",
  "unknown",
  "error",
  "self-testing",
  "completed",
  "paused",
  "stopped",
  "printing",
  "processing",
  "idle",
]);

function computeIcon(status) {
  const st = normStr(status);
  if (["off", "unknown", "stopped"].includes(st)) return mdi("printer-3d-off");
  // `processing` is the warm-up before `printing` and is in BUSY_PRINT_STATES,
  // so it gets the active icon too -- computeColor already treats it as active.
  if (["printing", "paused", "processing"].includes(st)) return mdi("printer-3d-nozzle");
  if (st === "error") return mdi("close-octagon");
  if (st === "self-testing") return mdi("cogs");
  return mdi("printer-3d");
}
function computeColor(status) {
  const st = normStr(status);
  if (["off", "unknown", "stopped"].includes(st)) return "var(--secondary-text-color)";
  if (st === "paused") return "#fc6d09";
  if (st === "error") return "var(--error-color)";
  if (["printing", "processing"].includes(st)) return "var(--primary-color)";
  if (["idle", "completed"].includes(st)) return "var(--success-color, #4caf50)";
  if (st === "self-testing") return "var(--info-color, #2196f3)";
  return "var(--secondary-text-color)";
}

class KPrinterCard extends HTMLElement {
  static getStubConfig() {
    return {
      name: DEFAULT_CARD_NAME,
      // Device the entity fields were filled from. Stored so the editor's
      // "fill from device" button has something to re-read; the card itself
      // resolves nothing from it, so a config written by hand needs no device.
      device: "",
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
        // Off-state colours for the custom button, used when it drives a
        // toggleable entity (switch/light/input_boolean).
        custom_off_bg: "rgba(150,150,150,.35)",
        custom_icon_off: "#000",
        // Power button. The chip CSS has always read these, but nothing ever
        // set them, so the button was the one chip the theme could not reach.
        power_on_bg: "rgba(76, 175, 80, .90)",
        power_off_bg: "rgba(150,150,150,.35)",
        power_icon_on: "#fff",
        power_icon_off: "#000",
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

  /**
   * Bring an older card config up to something the editor can round-trip.
   *
   * Not about shape: no config key has ever been renamed or removed, and new
   * ones pick up their defaults from the merge in setConfig. It is about
   * values. The previous editor saved every colour through
   * `hexToRgba(hex, 0.9)`, so colours that can only be solid -- every icon
   * colour, none of which has an opacity control -- were stored at 90%
   * regardless. The editor cannot show that, so without this the form and the
   * card quietly disagree about a colour until someone happens to touch it.
   *
   * Anything this cannot parse (`var(--accent-color)`, a named colour, an
   * hsl()) is left exactly as it is. The card writes those straight into CSS
   * and they work; guessing at them would throw away a deliberate choice.
   * @param {?Object} config
   * @return {!Object}
   */
  static _migrateConfig(config) {
    const cfg = { ...(config || {}) };
    if (!cfg.theme || typeof cfg.theme !== "object") return cfg;
    cfg.theme = KPrinterCard._migrateTheme(cfg.theme);
    return cfg;
  }

  /** Normalise one theme object. Split out so the storage path shares it. */
  static _migrateTheme(theme) {
    const out = { ...theme };
    for (const [key, field] of THEME_COLOR_FIELDS) {
      const value = out[key];
      if (value === undefined || value === "auto") continue;
      const parsed = parseColor(value);
      if (!parsed) continue;
      out[key] = formatColor(parsed.rgb, field.alpha ? parsed.alpha : 1);
    }
    return out;
  }

  setConfig(config) {
    const defaultConfig = KPrinterCard.getStubConfig();
    const migrated = KPrinterCard._migrateConfig(config);
    this._cfg = { ...defaultConfig, ...migrated };
    // Init optimistic state overrides map
    if (!this._optimisticStates) this._optimisticStates = {};

    // Generate card ID for theme persistence
    this._cardId = generateCardId(this._cfg);

    // Load saved theme if no theme is provided in config
    if (!config?.theme) {
      const savedTheme = loadThemeFromStorage(this._cardId);
      if (savedTheme) {
        // Migrated too: a theme saved by the old editor is just as stale here
        // as one that came from YAML.
        this._cfg.theme = { ...defaultConfig.theme, ...KPrinterCard._migrateTheme(savedTheme) };
      }
    } else {
      // Deep merge theme configuration
      this._cfg.theme = { ...defaultConfig.theme, ...migrated.theme };
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

  // i18n helpers -------------------------------------------------------
  _resolveLanguage() {
    return _resolveLang(this._hass);
  }
  _t(key) {
    return _translate(this._hass, "printer_card", CARD_TRANSLATIONS, key);
  }
  // ---------------------------------------------------------------------

  set hass(hass) {
    this._hass = hass;
    _requestI18n(this, hass, () => { if (this._root) this._update(); });
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
  getCardSize() { return this._cardSize || 3; }

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
        --power-on-bg: ${theme.power_on_bg || 'rgba(76, 175, 80, .90)'};
        --power-off-bg: ${theme.power_off_bg || 'rgba(150,150,150,.35)'};
        --power-icon-on: ${theme.power_icon_on || '#fff'};
        --power-icon-off: ${theme.power_icon_off || '#000'};
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
        color: var(--primary-text-color);
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
        display:flex; gap:8px; justify-content:flex-end; flex-wrap:wrap;
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


      /* telemetry row – one line that scales with the card, then wraps.
         .telemetry-wrap is the query container, so the pills size themselves
         from the room the row actually has rather than from the viewport. The
         sizes are continuous (clamp over cqi) instead of stepped at a
         breakpoint on purpose: the row's line count feeds getCardSize(), and a
         breakpoint makes that measurement jump. */
      .telemetry-wrap { container-type: inline-size; min-width:0; }
      .telemetry {
        display:flex;
        gap:6px;
        justify-content:center;
        flex-wrap:wrap;
        padding: 0 var(--row-xpad);
        min-width:0;
        /* The ceilings used to be reached at ~470px, so on any normal card the
           pills sat pinned at their smallest while the card around them grew.
           These ranges put the whole scale inside the widths a Lovelace column
           actually takes (roughly 330px to 520px), which is where the change is
           worth seeing. The cap stays just under .name's .95rem so the readings
           never outshout the printer's own name. */
        --pill-font: clamp(.65rem, 3.1cqi, .92rem);
        --pill-pad-x: clamp(7px, 2.4cqi, 14px);
        --pill-pad-y: clamp(5px, 1.5cqi, 9px);
        --pill-gap: clamp(4px, 1.3cqi, 8px);
        --pill-icon: clamp(13px, 3.9cqi, 19px);
      }
      .pill {
        display:inline-flex; align-items:center; justify-content:center;
        gap:var(--pill-gap, 6px);
        padding:var(--pill-pad-y, 6px) var(--pill-pad-x, 10px); border-radius:999px;
        background:rgba(127,127,127,.12);
        font-size:var(--pill-font, .8rem); border:1px solid rgba(255,255,255,0.08);
        /* Grow to share out whatever the row has spare, so the pills reach the
           same right edge as the action chips above instead of huddling in the
           middle. Never shrink: with nowrap text that would overflow the pill
           rather than make it fit. */
        white-space:nowrap; flex:1 0 auto;
        color: var(--telemetry-text, var(--primary-text-color));
      }
      .pill ha-icon {
        --mdc-icon-size:var(--pill-icon, 16px);
        width:var(--pill-icon, 16px); height:var(--pill-icon, 16px);
        color: var(--telemetry-icon, var(--secondary-text-color));
      }
      /* The unit suffix is the first thing to go once shrinking alone no longer
         keeps the row on one line; _updateTelemetryDensity owns the class. */
      .pill .unit { margin-left:.25em; }
      .telemetry.compact .pill .unit { display:none; }

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

        <div class="telemetry-wrap">
          <div class="telemetry">
            <div class="pill"><ha-icon icon="mdi:printer-3d-nozzle-heat"></ha-icon><span id="nozzle"></span><span class="unit" id="nozzle-unit"></span></div>
            <div class="pill"><ha-icon icon="mdi:heating-coil"></ha-icon><span id="bed"></span><span class="unit" id="bed-unit"></span></div>
            <div class="pill" id="box-pill"><ha-icon icon="mdi:thermometer"></ha-icon><span id="box"></span><span class="unit" id="box-unit"></span></div>
            <div class="pill"><ha-icon icon="mdi:progress-clock"></ha-icon><span id="time"></span></div>
            <div class="pill"><ha-icon icon="mdi:layers-triple"></ha-icon><span id="layers"></span></div>
          </div>
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
        // Confirm only when the press would turn the printer OFF (not when
        // turning it on), with a stronger warning while a print is in progress
        // so an accidental tap can't kill a running job.
        if (this._hass?.states?.[eid]?.state === "on") {
          const st = normStr(this._hass?.states?.[this._cfg.status]?.state);
          // `processing` means a job is on the bed and starting, so it needs
          // the stronger warning as much as a running print does.
          const printing = ["printing", "paused", "processing"].includes(st);
          const msg = printing ? this._t("confirm_power_off_printing") : this._t("confirm_power_off");
          if (!confirm(msg)) return;
        }
        this._toggleEntity(eid);
      } else if (id === "light") {
        const eid = this._resolveEntityId(this._cfg.light, ["light", "switch"]);
        this._toggleEntity(eid);
      } else if (id === "pause") {
        this._pressButtonEntity(this._cfg.pause_btn);
      } else if (id === "resume") {
        this._pressButtonEntity(this._cfg.resume_btn);
      } else if (id === "stop") {
        if (confirm(this._t("confirm_stop"))) {
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

    // The row is new, so anything measured off the old one is stale.
    this._telemetryUnitsFailedAt = 0;
    this._telemetrySignature = null;

    this._update();
    this._setupTelemetrySizeObserver();
  }

  connectedCallback() {
    // The card may be re-attached without setConfig firing again (e.g. when Lovelace
    // moves the element between containers). _render() -- which normally wires up the
    // telemetry observer -- only runs from setConfig/hass paths, so reinstate the
    // observer here whenever a previously-rendered card returns to the DOM.
    if (this._root) {
      this._setupTelemetrySizeObserver();
    }
  }

  disconnectedCallback() {
    clearTimeout(this._initialUpdateTimer);
    if (this._telemetryResizeObserver) {
      if (this._telemetryObservedNode) {
        this._telemetryResizeObserver.unobserve(this._telemetryObservedNode);
        this._telemetryObservedNode = null;
      }
      this._telemetryResizeObserver.disconnect();
      this._telemetryResizeObserver = null;
    }
    if (this._telemetrySizeFrame) {
      cancelAnimationFrame(this._telemetrySizeFrame);
      this._telemetrySizeFrame = null;
    }
  }

  _setupTelemetrySizeObserver() {
    const telemetry = this._root?.querySelector(".telemetry");
    if (!telemetry) return;

    if (typeof ResizeObserver !== "function") {
      this._scheduleTelemetrySizeUpdate();
      return;
    }

    if (!this._telemetryResizeObserver) {
      this._telemetryResizeObserver = new ResizeObserver(() => this._scheduleTelemetrySizeUpdate());
    }

    if (this._telemetryObservedNode && this._telemetryObservedNode !== telemetry) {
      this._telemetryResizeObserver.unobserve(this._telemetryObservedNode);
    }

    if (this._telemetryObservedNode !== telemetry) {
      this._telemetryResizeObserver.observe(telemetry);
      this._telemetryObservedNode = telemetry;
    }
    this._scheduleTelemetrySizeUpdate();
  }

  _scheduleTelemetrySizeUpdate() {
    if (this._telemetrySizeFrame) {
      cancelAnimationFrame(this._telemetrySizeFrame);
    }
    this._telemetrySizeFrame = requestAnimationFrame(() => {
      this._telemetrySizeFrame = null;
      // Density first: dropping the units can pull the row back onto one line,
      // and it is that final line count getCardSize() has to report.
      this._updateTelemetryDensity();
      this._updateTelemetryCardSize();
    });
  }

  /** The pills currently taking up space, in DOM order. */
  _visibleTelemetryPills(telemetry) {
    return Array.from(telemetry.children).filter((pill) => {
      const style = getComputedStyle(pill);
      return style.display !== "none" && style.visibility !== "hidden";
    });
  }

  /** How many lines the telemetry row occupies right now. */
  _telemetryLineCount(telemetry) {
    return new Set(
      this._visibleTelemetryPills(telemetry).map((pill) => Math.round(pill.offsetTop)),
    ).size;
  }

  /**
   * Drop the unit suffixes when the pills would otherwise wrap.
   *
   * The decision is made from the line count rather than from summed widths,
   * because the pills grow to fill the row: their widths always add up to the
   * row's, whether the content fits or not. Wrapping is the only honest signal
   * left, so this asks the question by trying it.
   *
   * Which makes the retry the delicate part. Restoring the units at the width
   * that just rejected them wraps the row, hides them again, and repeats for
   * as long as the card is that size -- so the width they failed at is
   * remembered, and they only get another go once the row is meaningfully
   * wider than it.
   */
  _updateTelemetryDensity() {
    const telemetry = this._root?.querySelector(".telemetry");
    if (!telemetry) return;

    const style = getComputedStyle(telemetry);
    const available = telemetry.clientWidth
      - (parseFloat(style.paddingLeft) || 0)
      - (parseFloat(style.paddingRight) || 0);
    // A detached or not-yet-laid-out row measures 0; leave it alone rather than
    // compacting it on a width that means nothing.
    if (!(available > 0)) return;

    if (!telemetry.classList.contains("compact")) {
      if (this._telemetryLineCount(telemetry) > 1) {
        this._telemetryUnitsFailedAt = available;
        telemetry.classList.add("compact");
      }
      return;
    }

    if (available <= (this._telemetryUnitsFailedAt ?? 0) + TELEMETRY_COMPACT_HYSTERESIS) return;
    telemetry.classList.remove("compact");
    if (this._telemetryLineCount(telemetry) > 1) {
      this._telemetryUnitsFailedAt = available;
      telemetry.classList.add("compact");
    }
  }

  _updateTelemetryCardSize() {
    const telemetry = this._root?.querySelector(".telemetry");
    if (!telemetry) return;

    const nextSize = Math.max(3, 2 + this._telemetryLineCount(telemetry));
    const currentSize = this._cardSize ?? 3;
    if (nextSize === currentSize) return;

    const cardKey = this._cardId || CARD_TAG;
    const now = Date.now();
    const lastDispatch = _lastCardRebuildDispatch.get(cardKey) || 0;
    // Defer the _cardSize update until the throttle clears: otherwise a throttled
    // call would record the new size locally without telling Lovelace, and the
    // next measurement would short-circuit on the equality check above -- leaving
    // the rebuild permanently suppressed.
    if (now - lastDispatch < LL_REBUILD_MIN_INTERVAL_MS) return;
    _lastCardRebuildDispatch.set(cardKey, now);
    this._cardSize = nextSize;

    this.dispatchEvent(new CustomEvent("ll-rebuild", { bubbles: true, composed: true }));
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
      if (!st) return "-";
      const v = st.state;
      if (v === undefined || v === null) return "-";
      const s = String(v);
      if (s === "unknown" || s === "unavailable") return "-";
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

    const name = this._cfg.name || DEFAULT_CARD_NAME;
    const status = g(this._cfg.status) ?? "unknown";
    const pct = clamp(Number.isFinite(gNum(this._cfg.progress)) ? gNum(this._cfg.progress) : 0, 0, 100);
    const timeLeft = durationToSeconds(gObj(this._cfg.time_left));
    const nozzleStr = splitUnit(fmtWithUnit(this._cfg.nozzle), gObj(this._cfg.nozzle));
    const bedStr = splitUnit(fmtWithUnit(this._cfg.bed), gObj(this._cfg.bed));
    const boxStr = splitUnit(fmtWithUnit(this._cfg.box), gObj(this._cfg.box));
    const _rawLayer = g(this._cfg.layer);
    const layer = (_rawLayer && _rawLayer !== "unavailable" && _rawLayer !== "unknown" ? _rawLayer : "") + "";
    const _rawTotalLayers = g(this._cfg.total_layers);
    const totalLayers = (_rawTotalLayers && _rawTotalLayers !== "unavailable" && _rawTotalLayers !== "unknown" ? _rawTotalLayers : "") + "";
    const resolvedLight = this._resolveEntityId(this._cfg.light, ["light", "switch"]);
    const lightState = this._hass?.states?.[resolvedLight]?.state;
    const resolvedPower = this._resolveEntityId(this._cfg.power, ["switch"]);
    const powerState = g(resolvedPower);

    const st = normStr(status);
    const isPrinting = st === "printing";
    const isPaused = st === "paused";
    // A job exists and is progressing. Pause stays restricted to `printing`
    // and Stop to the states below; this is only the visual presentation.
    const isActivePrint = ["printing", "paused", "processing"].includes(st);
    const showStop = isPrinting || isPaused || st === "self-testing";
    // Show Light chip only when the light entity exists in HA state and power (if configured) is not OFF
    const showLight = Boolean(resolvedLight && this._hass?.states?.[resolvedLight]) && !(resolvedPower && powerState === "off");
    // Show the Power button whenever configured, independent of printer status
    const showPower = Boolean(this._cfg.show_power_button) && Boolean(this._cfg.power);

    // Title/status
    this._root.getElementById("name").textContent = name;
    const proper = (!status || status === "unavailable" || status === "unknown") ? this._t("status_unknown") : (fmtState(gObj(this._cfg.status)) || status[0].toUpperCase() + status.slice(1));
    const sec = isActivePrint ? `${pct}% ${proper}` : proper;
    this._root.getElementById("secondary").textContent = sec;

    // Icon & ring
    const iconEl = this._root.getElementById("icon");
    iconEl.setAttribute("icon", computeIcon(status));
    const theme = this._cfg.theme || {};
    const iconColor = theme.status_icon === "auto" ? computeColor(status) : theme.status_icon;
    iconEl.style.setProperty("--icon-color", iconColor);
    const ring = this._root.getElementById("ring");
    ring.style.setProperty("--ring-pct", isActivePrint ? `${pct}%` : "0%");
    const ringColor = theme.progress_ring === "auto" ? computeColor(status) : theme.progress_ring;
    ring.style.setProperty("--ring-color", ringColor);

    const chipsContainer = this._root.getElementById("chips-container");

    // Define button definitions
    const buttons = {
      pause: {
        hidden: !isPrinting,
        class: "warn",
        icon: this._cfg.pause_btn_icon || "mdi:pause",
        title: this._t("chip_pause")
      },
      resume: {
        hidden: !isPaused,
        class: "ok",
        icon: this._cfg.resume_btn_icon || "mdi:play",
        title: this._t("chip_resume")
      },
      stop: {
        hidden: !showStop,
        class: "danger",
        icon: this._cfg.stop_btn_icon || "mdi:stop",
        title: this._t("chip_stop")
      },
      light: {
        hidden: !showLight,
        class: lightState === "on" ? "light-on" : "light-off",
        icon: this._cfg.light_btn_icon || "mdi:lightbulb",
        title: this._t("chip_light")
      },
      power: {
        hidden: !showPower,
        class: "unknown", // Calculated below
        icon: this._cfg.power_btn_icon || "mdi:power",
        title: this._t("chip_power")
      },
      custom: {
        hidden: Boolean(this._cfg.custom_btn_hidden) || !this._cfg.custom_btn,
        class: "custom",
        icon: this._cfg.custom_btn_icon || "mdi:gesture-tap",
        title: this._t("chip_custom")
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
    for (const [id, parts] of [["nozzle", nozzleStr], ["bed", bedStr], ["box", boxStr]]) {
      this._root.getElementById(id).textContent = parts.value;
      this._root.getElementById(`${id}-unit`).textContent = parts.unit;
    }
    const timeText = fmtTimeLeft(timeLeft);
    const layersText = `${layer || "-"}/${totalLayers || "-"}`;
    this._root.getElementById("time").textContent = timeText;
    this._root.getElementById("layers").textContent = layersText;

    // A shorter reading -- 2:25 where 1:02:25 was, or a temperature dropping
    // below 100 -- can free up the room the units needed, so let them have
    // another go whenever the text changes rather than waiting for a resize
    // that may never come.
    const signature = [
      nozzleStr.value, bedStr.value, boxStr.value, timeText, layersText,
    ].join("|");
    if (signature !== this._telemetrySignature) {
      this._telemetrySignature = signature;
      this._telemetryUnitsFailedAt = 0;
    }

    // Toggle Chamber Temp visibility.
    // Hide when explicitly hidden, when no chamber entity is configured, or when
    // the configured entity does not exist in HA (printers without a chamber,
    // e.g. Ender 3 V3 KE) so we don't render a stray thermometer icon that
    // offsets the adjacent telemetry. A configured-but-unavailable entity stays
    // visible and shows "-", matching the nozzle/bed pills.
    const boxPill = this._root.getElementById("box-pill");
    if (boxPill) {
      const boxConfigured = Boolean(this._cfg.box) && Boolean(this._hass?.states?.[this._cfg.box]);
      boxPill.style.display = (this._cfg.hide_box_temp || !boxConfigured) ? "none" : "";
    }
    this._scheduleTelemetrySizeUpdate();
  }
}
const CARD_TRANSLATIONS = {
  en: {
    status_unknown: "Unknown",
    confirm_stop: "Are you sure you want to stop the print?",
    confirm_power_off: "Are you sure you want to power off the printer?",
    confirm_power_off_printing: "A print is in progress. Are you sure you want to power off the printer?",
    chip_pause: "Pause",
    chip_resume: "Resume",
    chip_stop: "Stop",
    chip_light: "Light",
    chip_power: "Power",
    chip_custom: "Custom Action",
    editor_title: "Creality Printer Card Configuration",
    tab_entities: "Entities",
    tab_theme: "Theme",
    group_device: "Printer",
    group_entities: "Entities",
    group_layout: "Layout & Icons",
    group_action_colors: "Action Button Colors",
    group_toggle_colors: "Toggle Button Colors",
    group_status_area: "Status Area",
    group_telemetry: "Telemetry",
    note_device: "Picking a device fills in the fields below that are still empty. Use the button to replace every field, including ones you set yourself. The power switch is never filled in, because the integration does not provide one.",
    note_clear_resets: "Use Reset to Defaults at the bottom to undo these.",
    note_auto_colors: "Turn Automatic off to choose a color yourself.",
    btn_refill_from_device: "Fill all fields from device",
    btn_reset: "Reset to Defaults",
    status_device_filled: "Filled {filled} of {total} fields.",
    status_device_empty: "No entities from this integration were found on that device.",
    color_pause_bg: "Pause Button Background",
    color_pause_icon: "Pause Button Icon",
    color_resume_bg: "Resume Button Background",
    color_resume_icon: "Resume Button Icon",
    color_stop_bg: "Stop Button Background",
    color_stop_icon: "Stop Button Icon",
    color_light_on_bg: "Light Button Background (On)",
    color_light_off_bg: "Light Button Background (Off)",
    color_light_icon_on: "Light Button Icon (On)",
    color_light_icon_off: "Light Button Icon (Off)",
    color_power_on_bg: "Power Button Background (On)",
    color_power_off_bg: "Power Button Background (Off)",
    color_power_icon_on: "Power Button Icon (On)",
    color_power_icon_off: "Power Button Icon (Off)",
    color_custom_bg: "Custom Button Background (On)",
    color_custom_icon: "Custom Button Icon (On)",
    color_custom_off_bg: "Custom Button Background (Off)",
    color_custom_icon_off: "Custom Button Icon (Off)",
    color_status_icon: "Status Icon Color",
    color_progress_ring: "Progress Ring Color",
    color_status_bg: "Status Background",
    color_telemetry_icon: "Telemetry Icon Color",
    color_telemetry_text: "Telemetry Text Color",
    label_opacity: "Opacity",
    label_color_auto: "Automatic",
    helper_auto_status_icon: "Automatic: follows the print state, orange while paused, red on error, green when idle or finished.",
    helper_auto_progress_ring: "Automatic: follows the print state, matching the status icon.",
    helper_auto_status_bg: "Automatic: blends into the card background.",
    helper_auto_telemetry_icon: "Automatic: uses the theme's secondary text color.",
    helper_auto_telemetry_text: "Automatic: uses the theme's primary text color.",
    label_device: "Printer device",
    label_name: "Printer Name",
    label_camera: "Camera",
    label_status: "Print Status Sensor",
    label_progress: "Print Progress Sensor (%)",
    label_time_left: "Time Left Sensor",
    label_nozzle: "Nozzle Temperature Sensor",
    label_bed: "Bed Temperature Sensor",
    label_box: "Chamber Temperature Sensor",
    label_power: "Power Switch",
    label_show_power_button: "Show Power Button",
    label_layer: "Current Layer Sensor",
    label_total_layers: "Total Layers Sensor",
    label_light: "Light Switch",
    label_pause_btn: "Pause Button",
    label_resume_btn: "Resume Button",
    label_stop_btn: "Stop Button",
    label_custom_btn: "Custom Action Entity",
    label_custom_btn_icon: "Custom Button Icon",
    label_custom_btn_hidden: "Hide Custom Button",
    label_button_order: "Button Order (list)",
    label_hide_box_temp: "Hide Chamber Temperature",
    label_pause_btn_icon: "Pause Icon Override",
    label_resume_btn_icon: "Resume Icon Override",
    label_stop_btn_icon: "Stop Icon Override",
    label_light_btn_icon: "Light Icon Override",
    label_power_btn_icon: "Power Icon Override",
    helper_device: "Your printer, as set up by this integration",
    helper_name: "Display name for the printer card",
    helper_camera: "Camera entity for live video feed",
    helper_status: "Sensor showing current print status",
    helper_progress: "Sensor showing print progress (0-100%)",
    helper_time_left: "Sensor showing remaining print time (seconds)",
    helper_nozzle: "Sensor showing nozzle temperature",
    helper_bed: "Sensor showing bed temperature",
    helper_box: "Sensor showing chamber/enclosure temperature (optional)",
    helper_power: "Your own smart plug for the printer, if you have one (shows a Power button when set). Not filled in from the device.",
    helper_show_power_button: "Show the Power button when a power switch entity is configured",
    helper_layer: "Sensor showing current print layer",
    helper_total_layers: "Sensor showing total print layers",
    helper_light: "Switch entity for printer light control",
    helper_pause_btn: "Button entity to pause printing",
    helper_resume_btn: "Button entity to resume printing",
    helper_stop_btn: "Button entity to stop printing",
    helper_custom_btn: "Any entity to trigger (Button, Script, Switch, etc.)",
    helper_custom_btn_icon: "Icon for the custom button",
    helper_custom_btn_hidden: "Hide the custom button",
    helper_button_order: "List of buttons to show in order (pause, resume, stop, light, power, custom)",
    helper_hide_box_temp: "Hide the chamber temperature pill even when a sensor is configured",
    editor_error_title: "Editor Error",
    editor_error_msg: "There was an error loading the visual editor. You can still edit your configuration using YAML.",
    editor_error_prefix: "Error:",
  },
};

/**
 * Register a custom element at most once.
 *
 * A dashboard can end up importing this module twice -- two Lovelace resource
 * entries, or a page that was open across a Home Assistant restart picking up
 * the new `?v=` alongside the copy it already had. A bare define() throws on
 * the second pass, which aborts the rest of that module: the tag then keeps
 * whichever class won the race while the functions around it come from the
 * other copy, and the mismatch shows up as methods that exist in the source
 * but not on the instance.
 * @param {string} tag
 * @param {!Function} cls
 */
function defineOnce(tag, cls) {
  if (customElements.get(tag)) return;
  try {
    customElements.define(tag, cls);
  } catch (err) {
    console.error(`ha_creality_ws: could not define <${tag}>`, err);
  }
}

defineOnce(CARD_TAG, KPrinterCard);

/**
 * Colour controls in the theme tab, grouped the way they are rendered.
 *
 * `alpha` gives the field an opacity slider -- a background needs one, an icon
 * colour does not. `auto` marks the fields where clearing the colour means
 * something ("work it out yourself") rather than merely "reset", and each of
 * those carries helper text saying what the card does instead -- the one thing
 * the previous editor never told anyone, even though five fields defaulted to
 * it.
 */
const THEME_COLOR_GROUPS = [
  {
    title: "group_action_colors",
    note: "note_clear_resets",
    fields: [
      { key: "pause_bg", alpha: true },
      { key: "pause_icon" },
      { key: "resume_bg", alpha: true },
      { key: "resume_icon" },
      { key: "stop_bg", alpha: true },
      { key: "stop_icon" },
    ],
  },
  {
    title: "group_toggle_colors",
    note: "note_clear_resets",
    fields: [
      { key: "light_on_bg", alpha: true },
      { key: "light_icon_on" },
      { key: "light_off_bg", alpha: true },
      { key: "light_icon_off" },
      { key: "power_on_bg", alpha: true },
      { key: "power_icon_on" },
      { key: "power_off_bg", alpha: true },
      { key: "power_icon_off" },
      { key: "custom_bg", alpha: true },
      { key: "custom_icon" },
      { key: "custom_off_bg", alpha: true },
      { key: "custom_icon_off" },
    ],
  },
  {
    title: "group_status_area",
    note: "note_auto_colors",
    fields: [
      { key: "status_icon", auto: true, seed: "#4caf50" },
      { key: "progress_ring", auto: true, seed: "#2196f3" },
      { key: "status_bg", alpha: true, auto: true, seed: "rgba(128, 128, 128, 0.2)" },
    ],
  },
  {
    title: "group_telemetry",
    note: "note_auto_colors",
    fields: [
      { key: "telemetry_icon", auto: true, seed: "#9e9e9e" },
      { key: "telemetry_text", auto: true, seed: "#9e9e9e" },
    ],
  },
];

/** Every theme colour field by key, for label and helper lookups. */
const THEME_COLOR_FIELDS = new Map(
  THEME_COLOR_GROUPS.flatMap((group) => group.fields.map((field) => [field.key, field])),
);

/** Suffix that turns a colour field name into its opacity companion. */
const OPACITY_SUFFIX = "_opacity";

/**
 * Suffix for a colour field's "Automatic" switch.
 *
 * Automatic cannot be expressed as an empty colour: the color_rgb selector
 * renders a native `<input type="color">`, and there is no way to empty one of
 * those. Without a switch of its own, a field the user had customised could
 * never be put back.
 */
const AUTO_SUFFIX = "_auto";

/** Top-level config keys the theme tab owns, and so the reset button clears. */
const LAYOUT_RESET_KEYS = [
  "button_order", "custom_btn_hidden", "hide_box_temp",
  "pause_btn_icon", "resume_btn_icon", "stop_btn_icon",
  "light_btn_icon", "power_btn_icon", "custom_btn_icon",
];

/** Last-resort label for a field nobody has written a translation for yet. */
const humanizeName = (name) =>
  String(name).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

const EDITOR_STYLE = `
  :host { display: block; }
  .editor-container { padding: 16px; max-width: 1200px; margin: 0 auto; }
  .editor-title { margin: 0 0 16px 0; font-size: 18px; color: var(--primary-text-color); }
  .tabs { display: flex; border-bottom: 1px solid var(--divider-color); margin-bottom: 16px; }
  .tab { padding: 8px 16px; cursor: pointer; border-bottom: 2px solid transparent; }
  .tab.active { border-bottom-color: var(--primary-color); color: var(--primary-color); }
  .tab-content { display: none; }
  .tab-content.active { display: block; }
  .control-group {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
  }
  .group-title { font-size: 14px; font-weight: 600; margin-bottom: 4px; color: var(--primary-text-color); }
  .group-note { font-size: 12px; color: var(--secondary-text-color); margin-bottom: 8px; }
  .group-note:empty { display: none; }
  .row-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 8px; }
  .ghost-btn {
    background: transparent; color: var(--primary-color); font: inherit; font-size: 13px;
    border: 1px solid var(--primary-color); border-radius: 4px; padding: 6px 12px; cursor: pointer;
  }
  .ghost-btn:disabled { color: var(--disabled-text-color); border-color: var(--divider-color); cursor: default; }
  .status { font-size: 12px; color: var(--secondary-text-color); }
  .status:empty { display: none; }
  .reset-btn {
    background: var(--error-color); color: white; border: none; font: inherit;
    padding: 8px 16px; border-radius: 4px; cursor: pointer; width: 100%;
  }
  .reset-btn:hover { opacity: 0.8; }
  ha-form { display: block; }
`;


/**
 * The editor's schemas and form data, as plain functions of the config.
 *
 * These were instance methods, which made every one of them a `this` lookup at
 * render time. In one Safari install `this._layoutData` came back undefined
 * even though the method was demonstrably on the prototype and the module had
 * been fetched exactly once -- a state nothing in this file can produce. They
 * never needed the instance for anything but `_cfg`, so they no longer ask it:
 * a module-scope call resolves lexically and cannot be interfered with from
 * outside.
 */

function deviceSchema() {
  // `filter`, not the top-level `integration` shorthand: that one is
  // deprecated and only still works because ha-selector rewrites it.
  return [{
    name: "device",
    selector: { device: { filter: [{ integration: INTEGRATION_DOMAIN }] } },
  }];
}

function entitiesSchema() {
  return [
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
}

function layoutSchema() {
  return [
    { name: "button_order", selector: { text: {} } },
    { name: "custom_btn_hidden", selector: { boolean: {} } },
    { name: "hide_box_temp", selector: { boolean: {} } },
    { name: "pause_btn_icon", selector: { icon: {} } },
    { name: "resume_btn_icon", selector: { icon: {} } },
    { name: "stop_btn_icon", selector: { icon: {} } },
    { name: "light_btn_icon", selector: { icon: {} } },
    { name: "power_btn_icon", selector: { icon: {} } },
    { name: "custom_btn_icon", selector: { icon: {} } },
  ];
}

/**
 * Whether `field` is currently letting the card choose the colour.
 *
 * Keyed on the literal "auto", not on "this is not a colour I can parse".
 * A hand-written `var(--accent-color)` is also unparseable, and reading that
 * as automatic would show the switch on and then overwrite the value with
 * "auto" the next time anything in the group changed.
 */
function isAutoColor(cfg, field) {
  if (!field.auto) return false;
  const value = cfg?.theme?.[field.key];
  return value === undefined || value === "" || value === "auto";
}

/**
 * Colour rows for one group.
 *
 * A field with an opacity slider gets the pair side by side in a grid; the
 * grid is flattened so both values stay top-level keys of the form data,
 * whichever Home Assistant version is reading the schema.
 */
function colorSchema(cfg, group) {
  const rows = [];
  for (const field of group.fields) {
    if (field.auto) {
      rows.push({ name: `${field.key}${AUTO_SUFFIX}`, selector: { boolean: {} } });
      // While a field is automatic there is no colour to show, and showing a
      // picker that does nothing invites the user to prove it does nothing.
      if (isAutoColor(cfg, field)) continue;
    }
    const color = { name: field.key, selector: { color_rgb: {} } };
    if (!field.alpha) {
      rows.push(color);
      continue;
    }
    rows.push({
      name: "",
      type: "grid",
      flatten: true,
      column_min_width: "170px",
      schema: [
        color,
        {
          name: `${field.key}${OPACITY_SUFFIX}`,
          selector: {
            number: { min: 0, max: 100, step: 1, mode: "slider", unit_of_measurement: "%" },
          },
        },
      ],
    });
  }
  return rows;
}

function entitiesData(cfg) {
  const data = {};
  for (const item of entitiesSchema()) data[item.name] = cfg[item.name];
  return data;
}

function layoutData(cfg) {
  const data = {};
  for (const item of layoutSchema()) data[item.name] = cfg[item.name];
  // The card stores an ordered list; the text field edits it as prose.
  data.button_order = Array.isArray(cfg.button_order)
    ? cfg.button_order.join(", ")
    : cfg.button_order;
  return data;
}

/**
 * Split each stored colour string into the [r, g, b] the picker wants and the
 * 0-100 opacity the slider wants. An automatic field has no colour of its own,
 * so its key is left out and only the Automatic switch is rendered.
 */
function colorData(cfg, group) {
  const theme = cfg.theme || {};
  const data = {};
  for (const field of group.fields) {
    if (field.auto) {
      data[`${field.key}${AUTO_SUFFIX}`] = isAutoColor(cfg, field);
      if (isAutoColor(cfg, field)) continue;
    }
    const parsed = parseColor(theme[field.key]);
    if (parsed) data[field.key] = parsed.rgb;
    if (field.alpha) {
      data[`${field.key}${OPACITY_SUFFIX}`] = Math.round((parsed?.alpha ?? 1) * 100);
    }
  }
  return data;
}

/* Visual editor: entity wiring on one tab, appearance on the other. */
class KPrinterCardEditor extends HTMLElement {
  // i18n helpers -------------------------------------------------------
  _resolveLanguage() {
    return _resolveLang(this._hass);
  }
  _t(key, vars) {
    return _translate(this._hass, "printer_card", CARD_TRANSLATIONS, key, vars);
  }
  /** Translate, falling back to `fallback` rather than to the raw key. */
  _tOr(key, fallback) {
    const text = this._t(key);
    return text === key ? fallback : text;
  }
  // ---------------------------------------------------------------------

  set hass(hass) {
    this._hass = hass;
    _requestI18n(this, hass, () => this._refresh());
    this._refresh();
  }

  setConfig(config) {
    const defaults = KPrinterCard.getStubConfig();
    this._cfg = { ...defaults, ...KPrinterCard._migrateConfig(config) };
    this._cfg.theme = { ...defaults.theme, ...(this._cfg.theme || {}) };
    this._refresh();
  }

  connectedCallback() {
    if (!this._root) this._root = this.attachShadow({ mode: "open" });
    this._refresh();
  }

  disconnectedCallback() {
    // Flush rather than drop: closing the editor within the debounce window
    // would otherwise lose whatever the user changed last.
    if (this._debounceTimer) {
      clearTimeout(this._debounceTimer);
      this._debounceTimer = null;
      this._emitConfig();
    }
  }

  // Shell ---------------------------------------------------------------

  /**
   * Build the editor's DOM once.
   *
   * Everything after this only reassigns `schema` and `data`. Rebuilding the
   * markup on each change -- which is what the editor used to do, because
   * Lovelace answers every config-changed with a fresh setConfig -- threw away
   * the focused field on every keystroke and took the tab selection with it.
   */
  _build() {
    const colorGroups = THEME_COLOR_GROUPS.map((_, index) => `
          <div class="control-group">
            <div class="group-title" id="group-color-${index}"></div>
            <div class="group-note" id="note-color-${index}"></div>
            <ha-form id="color-form-${index}"></ha-form>
          </div>`).join("");

    this._root.innerHTML = `
      <style>${EDITOR_STYLE}</style>
      <div class="editor-container">
        <h2 class="editor-title" id="editor-title"></h2>
        <div class="tabs">
          <div class="tab active" data-tab="entities" id="tab-entities"></div>
          <div class="tab" data-tab="theme" id="tab-theme"></div>
        </div>

        <div class="tab-content active" id="entities-tab">
          <div class="control-group">
            <div class="group-title" id="group-device"></div>
            <div class="group-note" id="note-device"></div>
            <ha-form id="device-form"></ha-form>
            <div class="row-actions">
              <button type="button" class="ghost-btn" id="refill"></button>
              <span class="status" id="refill-status"></span>
            </div>
          </div>
          <div class="control-group">
            <div class="group-title" id="group-entities"></div>
            <ha-form id="entities-form"></ha-form>
          </div>
        </div>

        <div class="tab-content" id="theme-tab">
          <div class="control-group">
            <div class="group-title" id="group-layout"></div>
            <ha-form id="layout-form"></ha-form>
          </div>
          ${colorGroups}
          <button type="button" class="reset-btn" id="reset-theme"></button>
        </div>
      </div>`;

    this._formEls = {};
    this._appliedSchema = {};
    this._appliedData = {};

    this._bindForm("device-form", (value) => this._onDeviceChanged(value));
    this._bindForm("entities-form", (value) => this._onEntitiesChanged(value));
    this._bindForm("layout-form", (value) => this._onLayoutChanged(value));
    THEME_COLOR_GROUPS.forEach((group, index) => {
      this._bindForm(`color-form-${index}`, (value) => this._onColorChanged(group, value));
    });

    for (const tab of this._root.querySelectorAll(".tab")) {
      tab.addEventListener("click", () => this._selectTab(tab.dataset.tab));
    }
    this._root.getElementById("refill")
      .addEventListener("click", () => this._applyDeviceFill(true));
    this._root.getElementById("reset-theme")
      .addEventListener("click", () => this._resetTheme());
  }

  /**
   * Wire one ha-form up.
   *
   * computeLabel and computeHelper are assigned unconditionally. ha-form leaves
   * both undefined until someone sets them, so the `if (form.computeLabel)`
   * guard this replaces was never true and every label in the editor rendered
   * as its raw config key.
   * @param {string} id
   * @param {function(!Object)} onChange
   */
  _bindForm(id, onChange) {
    const form = this._root.getElementById(id);
    // Seeded before anything else can render it. _refresh assigns the real
    // schema on the very next statement, but a throw in between would
    // otherwise leave a form that crashes rather than one that renders empty.
    form.schema = [];
    form.data = {};
    form.computeLabel = (schema) => this._label(schema);
    form.computeHelper = (schema) => this._helper(schema);
    form.addEventListener("value-changed", (ev) => {
      ev.stopPropagation();
      const value = ev.detail?.value || {};
      // The form is now showing `value`, so record it as applied. Without this
      // the echoed setConfig would see a difference against the last value we
      // pushed and reassign `data` mid-edit, jogging the control under the
      // user's finger.
      this._appliedData[id] = JSON.stringify(value);
      onChange(value);
    });
    this._formEls[id] = form;
  }

  _selectTab(name) {
    for (const tab of this._root.querySelectorAll(".tab")) {
      tab.classList.toggle("active", tab.dataset.tab === name);
    }
    for (const content of this._root.querySelectorAll(".tab-content")) {
      content.classList.toggle("active", content.id === `${name}-tab`);
    }
  }

  _showBuildError(error) {
    this._root.innerHTML =
      '<div class="editor-error" style="padding:16px;color:var(--error-color);"><h3></h3><p></p><p></p></div>';
    const [heading, message, detail] = this._root.querySelectorAll("h3, p");
    heading.textContent = this._t("editor_error_title");
    message.textContent = this._t("editor_error_msg");
    detail.textContent = `${this._t("editor_error_prefix")} ${error?.message || error}`;
  }

  // Labels ---------------------------------------------------------------

  _label(schema) {
    const name = schema?.name || "";
    if (!name) return "";
    if (name.endsWith(OPACITY_SUFFIX)) return this._t("label_opacity");
    if (name.endsWith(AUTO_SUFFIX)) return this._t("label_color_auto");
    const key = THEME_COLOR_FIELDS.has(name) ? `color_${name}` : `label_${name}`;
    return this._tOr(key, humanizeName(name));
  }

  _helper(schema) {
    const name = schema?.name || "";
    if (!name || name.endsWith(OPACITY_SUFFIX)) return "";
    // The explanation belongs on the switch, which is the control that acts on
    // it; the colour picker below only appears once automatic is off.
    if (name.endsWith(AUTO_SUFFIX)) {
      return this._tOr(`helper_auto_${name.slice(0, -AUTO_SUFFIX.length)}`, "");
    }
    if (THEME_COLOR_FIELDS.has(name)) return "";
    return this._tOr(`helper_${name}`, "");
  }

  // Schemas --------------------------------------------------------------

  // Refresh --------------------------------------------------------------

  _refresh() {
    // The shell is built here, not in connectedCallback, and only once there is
    // a config: Home Assistant attaches the editor to the DOM before it calls
    // setConfig (hui-element-editor assigns _configElement, which renders, and
    // only then calls setConfig). An ha-form reads `schema` unguarded in its
    // own render(), so attaching one before the schema exists throws out of
    // Lit's update and takes the whole editor down.
    if (!this._root || !this._cfg) return;
    if (!this._formEls) {
      try {
        this._build();
      } catch (error) {
        console.error("Error building K-Printer Card editor:", error);
        this._showBuildError(error);
        return;
      }
    }

    // A refresh runs from the hass setter, which Home Assistant calls out of
    // hui-element-editor's own Lit update. Throwing from there breaks that
    // update rather than just this editor, so a failure is reported in place
    // instead of being allowed to escape.
    try {
      this._refreshForms();
    } catch (error) {
      // Dump what the instance actually looked like: the one failure of this
      // kind reported so far was a method missing from an instance while
      // present on its prototype, and that is only diagnosable after the fact.
      console.error("Error refreshing K-Printer Card editor:", error, {
        constructor: this.constructor?.name,
        own: Object.getOwnPropertyNames(this).join(" "),
        proto: Object.getOwnPropertyNames(Object.getPrototypeOf(this) || {}).join(" "),
      });
      this._showBuildError(error);
      this._formEls = null;
    }
  }

  _refreshForms() {

    const text = {
      "editor-title": this._t("editor_title"),
      "tab-entities": this._t("tab_entities"),
      "tab-theme": this._t("tab_theme"),
      "group-device": this._t("group_device"),
      "note-device": this._t("note_device"),
      "group-entities": this._t("group_entities"),
      "group-layout": this._t("group_layout"),
      refill: this._t("btn_refill_from_device"),
      "reset-theme": this._t("btn_reset"),
    };
    for (const [id, value] of Object.entries(text)) {
      const el = this._root.getElementById(id);
      if (el) el.textContent = value;
    }
    this._root.getElementById("refill").disabled = !this._cfg.device;

    this._applyForm("device-form", deviceSchema(), { device: this._cfg.device || "" });
    this._applyForm("entities-form", entitiesSchema(), entitiesData(this._cfg));
    this._applyForm("layout-form", layoutSchema(), layoutData(this._cfg));

    THEME_COLOR_GROUPS.forEach((group, index) => {
      this._root.getElementById(`group-color-${index}`).textContent = this._t(group.title);
      this._root.getElementById(`note-color-${index}`).textContent = this._t(group.note);
      this._applyForm(`color-form-${index}`, colorSchema(this._cfg, group), colorData(this._cfg, group));
    });
  }

  /**
   * Push schema and data at a form, skipping assignments that change nothing.
   *
   * Lovelace answers every config-changed by calling setConfig again, so a
   * refresh runs on every keystroke and every drag of the opacity slider.
   * Reassigning identical data would make the control fight whatever the user
   * is doing to it.
   */
  _applyForm(id, schema, data) {
    const form = this._formEls[id];
    if (!form) return;
    if (this._hass) form.hass = this._hass;

    const schemaJson = JSON.stringify(schema);
    if (this._appliedSchema[id] !== schemaJson) {
      this._appliedSchema[id] = schemaJson;
      form.schema = schema;
    }
    const dataJson = JSON.stringify(data);
    if (this._appliedData[id] !== dataJson) {
      this._appliedData[id] = dataJson;
      form.data = data;
    }
  }

  // Changes --------------------------------------------------------------

  _onEntitiesChanged(value) {
    this._cfg = { ...this._cfg, ...value };
    this._dispatchConfigChange();
  }

  _onLayoutChanged(value) {
    const next = { ...value };
    if (typeof next.button_order === "string") {
      next.button_order = next.button_order.split(",").map((s) => s.trim()).filter(Boolean);
    }
    this._cfg = { ...this._cfg, ...next };
    this._dispatchConfigChange();
  }

  _onColorChanged(group, value) {
    const defaults = KPrinterCard.getStubConfig().theme;
    const theme = { ...this._cfg.theme };
    const wasAuto = new Map(group.fields.map((field) => [field.key, isAutoColor(this._cfg, field)]));
    for (const field of group.fields) {
      if (field.auto) {
        // Absent means the switch was not rendered, which only happens while
        // the field is already automatic.
        if (value[`${field.key}${AUTO_SUFFIX}`] !== false) {
          theme[field.key] = "auto";
          continue;
        }
        if (wasAuto.get(field.key) && !Array.isArray(value[field.key])) {
          // Automatic was just switched off and there is no colour yet. Seed a
          // plausible one rather than leaving the picker on black, which looks
          // like a bug on every theme.
          theme[field.key] = field.seed;
          continue;
        }
      }
      const rgb = value[field.key];
      if (!Array.isArray(rgb) || rgb.length < 3) {
        // Nothing the picker can express: a var() or a named colour written by
        // hand, which reaches the form as no value at all. Every field in the
        // group is rewritten on any change here, so leaving it alone is what
        // keeps an edit to one colour from eating another.
        continue;
      }
      const alpha = field.alpha
        ? clamp(Number(value[`${field.key}${OPACITY_SUFFIX}`] ?? 100), 0, 100) / 100
        : 1;
      theme[field.key] = formatColor(rgb, alpha);
    }
    this._cfg = { ...this._cfg, theme };
    // Switching a field to or from automatic adds or removes its colour rows,
    // so the form has to be rebuilt now rather than waiting for the debounced
    // config-changed to come back round as a setConfig. Every other edit
    // leaves the shape alone and is left for the control itself to show.
    if (group.fields.some((field) => isAutoColor(this._cfg, field) !== wasAuto.get(field.key))) {
      this._refresh();
    }
    this._dispatchConfigChange();
  }

  _onDeviceChanged(value) {
    const deviceId = value.device || "";
    if (deviceId === (this._cfg.device || "")) return;
    this._cfg = { ...this._cfg, device: deviceId };
    if (deviceId) {
      // Picking a device fills what is still blank; replacing a field the user
      // already chose is what the button next to it is for.
      this._applyDeviceFill(false);
      return;
    }
    this._setRefillStatus("");
    this._refresh();
    this._dispatchConfigChange();
  }

  // Device prefill -------------------------------------------------------

  /**
   * Entity ids the chosen device can supply, as a config patch.
   * @param {boolean} overwrite Replace fields that already hold a value.
   * @return {!Object<string, string>}
   */
  _prefillFromDevice(overwrite) {
    const deviceId = this._cfg.device;
    const patch = {};
    for (const [role, entityId] of Object.entries(entitiesForDevice(this._hass, deviceId))) {
      if (overwrite || !this._cfg[role]) patch[role] = entityId;
    }
    const device = this._hass?.devices?.[deviceId];
    const deviceName = device?.name_by_user || device?.name || "";
    // Every card starts life named "3D Printer", so that counts as unset --
    // otherwise the field the user most expects to be filled never would be.
    const nameUnset = !this._cfg.name || this._cfg.name === DEFAULT_CARD_NAME;
    if (deviceName && (overwrite || nameUnset)) patch.name = deviceName;
    return patch;
  }

  _applyDeviceFill(overwrite) {
    // The card name is filled too but is not counted: it is the one field
    // right above the button, so "13 of 13" reads as a claim about the entity
    // list rather than an off-by-one.
    const roles = Object.keys(DEVICE_ROLE_ENTITIES);
    const available = Object.keys(entitiesForDevice(this._hass, this._cfg.device)).length;
    const patch = this._prefillFromDevice(overwrite);
    const filled = roles.filter((role) => role in patch).length;

    this._cfg = { ...this._cfg, ...patch };
    this._setRefillStatus(available
      ? this._t("status_device_filled", { filled, total: roles.length })
      : this._t("status_device_empty"));
    this._refresh();
    this._dispatchConfigChange();
  }

  _setRefillStatus(text) {
    const el = this._root?.getElementById("refill-status");
    if (el) el.textContent = text;
  }

  // Reset ----------------------------------------------------------------

  _resetTheme() {
    const defaults = KPrinterCard.getStubConfig();
    const cfg = { ...this._cfg, theme: { ...defaults.theme } };
    for (const key of LAYOUT_RESET_KEYS) cfg[key] = defaults[key];

    // Clear the localStorage copy too: setConfig falls back to it for a config
    // that carries no theme of its own, so leaving it behind would resurrect
    // the old colours on the next load.
    try {
      const themes = JSON.parse(localStorage.getItem(THEME_STORAGE_KEY) || "{}");
      delete themes[generateCardId(cfg)];
      localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(themes));
    } catch (err) {
      console.warn("Failed to clear theme from localStorage:", err);
    }

    this._cfg = cfg;
    this._refresh();
    this._dispatchConfigChange();
  }

  _dispatchConfigChange() {
    clearTimeout(this._debounceTimer);
    this._debounceTimer = setTimeout(() => {
      this._debounceTimer = null;
      this._emitConfig();
    }, 120);
  }

  _emitConfig() {
    // The theme is persisted here rather than at each change: an opacity slider
    // emits on every pointer move, and each one would otherwise be a
    // localStorage write. The card saves the same thing again from setConfig.
    saveThemeToStorage(generateCardId(this._cfg), this._cfg.theme);
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: this._cfg },
      bubbles: true,
      composed: true,
    }));
  }
}
defineOnce(EDITOR_TAG, KPrinterCardEditor);

try {
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TAG,
    name: "Creality Printer Card",
    description: "Standalone card for Creality K-Series printers",
    preview: true,
  });
} catch (_) { }
