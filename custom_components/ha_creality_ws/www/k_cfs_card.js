
const CARD_TAG = "k-cfs-card";
const EDITOR_TAG = "k-cfs-card-editor";

const mdi = (name) => `mdi:${name}`;

const ASSET_URL_BASE = "/ha_creality_ws/";
const I18N_URL_BASE = `${ASSET_URL_BASE}i18n/`;
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
    Object.entries(vars).forEach(([k, v]) => {
      text = text.replace(new RegExp(`\\{${k}\\}`, "g"), v);
    });
  }
  return text;
}
function _requestI18n(instance, hass, onLoaded) {
  if (instance._i18nRequested) return;
  instance._i18nRequested = true;
  const lang = _resolveLang(hass).split("-")[0];
  Promise.all([_loadI18n("en"), lang !== "en" ? _loadI18n(lang) : null]).then(onLoaded);
}

// Creality's standard filament colours. Deliberately untranslated: the names are
// part of the product's identity, and twelve colour words per language is poor
// value. They surface as tooltips only.
const CREALITY_STANDARD_COLOURS = {
  Black: "#000000",
  White: "#ffffff",
  Grey: "#9e9e9e",
  Red: "#e53935",
  Orange: "#fb8c00",
  Yellow: "#fdd835",
  Green: "#06c84f",
  Cyan: "#00acc1",
  Blue: "#1e88e5",
  Purple: "#8e24aa",
  Pink: "#ec407a",
  Lime: "#9ccc65",
};

const PRESETS_STORAGE_KEY = "k-cfs-colour-presets";

/**
 * Escape a value for interpolation into markup.
 *
 * Filament names, colours and entity ids reach the renderers straight from
 * printer telemetry, and the renderers build strings that are assigned to
 * innerHTML. A `"` or `<` in any of them would otherwise close the attribute or
 * element it sits in and inject markup into the dashboard.
 * @param {*} value
 * @returns {string}
 */
function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Whether a value is a hex colour: 3 or 6 digits, `#` optional.
 * @param {*} value
 * @returns {boolean}
 */
function isHexColour(value) {
  return /^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(String(value ?? "").trim());
}

/**
 * Expand a hex colour to the six-digit form, or "" if it is not one.
 *
 * The service only accepts six digits, so a preset stored as `#abc` would be
 * selectable and then rejected on save.
 * @param {*} value
 * @returns {string}
 */
function toSixDigitHex(value) {
  if (!isHexColour(value)) return "";
  const hex = String(value).trim().replace(/^#/, "").toLowerCase();
  return hex.length === 3 ? `#${hex.replace(/./g, (c) => c + c)}` : `#${hex}`;
}

/**
 * User-defined colour presets, persisted in localStorage.
 *
 * Deliberately browser-local rather than stored in the card config: presets are
 * a personal palette, and writing them into the dashboard would make every
 * change a config edit visible to every user of that dashboard.
 */
class ColourPresetsManager {
  constructor() {
    this.presets = ColourPresetsManager._load();
  }

  static _load() {
    try {
      const stored = localStorage.getItem(PRESETS_STORAGE_KEY);
      const parsed = stored ? JSON.parse(stored) : {};
      // Guard against a hand-edited or corrupted value.
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch (_) {
      return {};
    }
  }

  _persist() {
    try {
      localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(this.presets));
    } catch (_) {
      // Private browsing or a full quota. The presets stay in memory for this
      // session; losing them is not worth interrupting a save for.
    }
  }

  /** @returns {boolean} whether the preset was stored */
  save(name, colour) {
    const key = String(name || "").trim();
    // Validate the input, not the output: _sanitizeColor returns #cccccc both
    // for "unparseable" and for the real grey #cccccc, so comparing against it
    // would refuse to store that colour.
    const value = toSixDigitHex(colour);
    if (!key || !value) return false;
    this.presets[key] = value;
    this._persist();
    return true;
  }

  rename(from, to) {
    const target = String(to || "").trim();
    if (!target || !(from in this.presets) || target === from) return false;
    this.presets[target] = this.presets[from];
    delete this.presets[from];
    this._persist();
    return true;
  }

  remove(name) {
    if (!(name in this.presets)) return false;
    delete this.presets[name];
    this._persist();
    return true;
  }

  /** Standard colours first, then the user's own. @returns {Array<[string, string]>} */
  entries() {
    return [
      ...Object.entries(CREALITY_STANDARD_COLOURS),
      ...Object.entries(this.presets),
    ];
  }

  isCustom(name) {
    return name in this.presets;
  }
}

/**
 * The one presets store for this page.
 *
 * Per-card instances each cached localStorage in their own constructor, so
 * saving or deleting in one card's dialog left every other card on the dashboard
 * serving a stale copy until reload. Created lazily: rendering a card must not
 * touch storage, only opening a dialog does.
 * @returns {ColourPresetsManager}
 */
let _sharedPresets = null;
function sharedPresets() {
  if (!_sharedPresets) _sharedPresets = new ColourPresetsManager();
  return _sharedPresets;
}

// The values that mean "no reading", in one place. Home Assistant renders an
// entity with no value as "unknown" and an unavailable one as "unavailable", and
// the integration writes "-" for an empty CFS slot. Trimmed before comparing, so
// a padded " unknown " is caught everywhere rather than only in the edit form --
// each caller keeps its own fallback, since the display wants "-" and the form
// wants "".
const SENTINEL_VALUES = new Set(["unknown", "unavailable", "-"]);
function isSentinel(value) {
  if (value === undefined || value === null) return true;
  const text = String(value).trim();
  return text === "" || SENTINEL_VALUES.has(text.toLowerCase());
}

const BUSY_PRINT_STATES = new Set([
  "printing",
  "paused",
  "processing",
  "self-testing",
]);

const CFS_TRANSLATIONS = {
  en: {
    no_data: "No CFS data available",
    ext_label: "EXT",
    cfs_label: "CFS",
    cfs_number_label: "CFS {number}",
    // Editor
    label_card_title: "Card Title",
    label_external_filament: "External Filament",
    label_external_color: "External Color",
    label_external_percent: "External Percent",
    label_box_temp: "Box {box} Temperature",
    label_box_humidity: "Box {box} Humidity",
    label_slot_filament: "Box {box} Slot {slot} Filament",
    label_slot_color: "Box {box} Slot {slot} Color",
    label_slot_percent: "Box {box} Slot {slot} Remaining Percent",
    label_color_presets: "Presets",
    label_preset_name: "Preset name",
    btn_save_preset: "Save preset",
    toast_preset_saved: "Preset “{name}” saved",
    toast_preset_deleted: "Preset “{name}” deleted",
    toast_preset_name_required: "Give the preset a name first",
    hint_delete_preset: "Dashed swatches are your own presets; right-click one to delete it.",
    btn_edit: "Edit material",
    tooltip_edit_locked: "Editing is disabled while the printer is busy",
    tooltip_multicolour_readonly: "Multi-color spools cannot be edited",
    dialog_edit_title: "Edit material",
    dialog_edit_target: "Writing to box {box}, slot {slot}",
    label_material_type: "Material type",
    label_material_name: "Material name",
    label_material_vendor: "Vendor",
    label_material_color: "Color",
    label_material_min_temp: "Minimum temperature",
    label_material_max_temp: "Maximum temperature",
    label_material_pressure: "Pressure advance",
    btn_cancel: "Cancel",
    btn_save: "Save",
    btn_saving: "Saving…",
    toast_saved: "Material saved",
    toast_save_failed: "Could not save material: {error}",
    toast_temp_range_invalid: "Maximum temperature must not be below the minimum",
    toast_colour_invalid: "Color must be six hex digits, for example #06c84f",
    toast_type_required: "Material type is required",
    toast_external_not_supported: "This printer does not report a box id for the external spool, so it cannot be edited",
    warn_box_id_guessed: "The target box or slot was inferred from the card layout; check both match the printer before saving",
    toast_no_device: "Could not identify the printer for this card. Check the entities in the card configuration.",
    toast_multiple_devices: "This card mixes entities from more than one printer, so material editing is disabled.",
    toast_printer_busy: "Cannot edit material while the printer is busy",
    schema_view_mode: "Display Mode",
    view_mode_box: "Box (visual)",
    alt_cfs_box: "Creality CFS unit",
    view_mode_full: "Full",
    view_mode_compact: "Compact",
    schema_show_type_in_mini: "Show Filament Type in Mini Mode",
    // Editor tab/header
    tab_entities: "Entities",
    tab_theme: "Theme",
  },
};

class KCFSCard extends HTMLElement {
  constructor() {
    super();
    this._selectedCFS = 0; // Track selected CFS tab in normal mode
  }

  /** The colour the printer reported, or null when it reported none usable.
   *
   * Split out from `_sanitizeColor` so that "no colour" and "grey" stay
   * distinguishable. The display grey is a placeholder, and the edit dialog
   * used to prefill it like a real value -- so changing only the material type
   * and saving wrote `#cccccc` to the spool as though the printer had said so.
   */
  static _parseColor(value) {
    if (isSentinel(value)) return null;
    const raw = String(value).trim();
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
    return null;
  }

  static _sanitizeColor(value) {
    return KCFSCard._parseColor(value) ?? "#cccccc";
  }

  /**
   * Bring a stored config up to date.
   *
   * compact_view was a boolean; view_mode is "full" | "compact" | "box". The
   * legacy key is translated once and then dropped, so the first visual edit
   * writes clean YAML back.
   * @param {object} config
   * @returns {object}
   */
  static _migrateConfig(config) {
    const cfg = { ...(config || {}) };
    if (cfg.compact_view !== undefined && cfg.view_mode === undefined) {
      cfg.view_mode = cfg.compact_view ? "compact" : "full";
    }
    delete cfg.compact_view;
    return cfg;
  }

  /** Map a view mode to its ha-card class. "full" is historically "normal-mode". */
  static _modeClass(viewMode) {
    if (viewMode === "compact") return "compact-mode";
    if (viewMode === "box") return "box-mode";
    return "normal-mode";
  }

  /**
   * True when the printer reports several colours for one spool, e.g.
   * "#0ffa800,#0ff97e1". _sanitizeColor renders those as grey, and a single
   * colour cannot represent them, so editing has to leave the value alone
   * rather than flatten it.
   * @param {*} value raw colour as reported
   * @returns {boolean}
   */
  static _isMultiColour(value) {
    return /[,;]/.test(String(value || ""));
  }

  /**
   * Work out which box and slot the *printer* calls this one.
   *
   * The card's box0..box3 config keys are card positions, not printer ids -- the
   * sensors key off the id in materialBoxs[]. Three tiers, most reliable first:
   *   1. the box_id/slot_id attributes the sensors publish;
   *   2. the default entity id, which encodes them as cfs_box_N_slot_M_*;
   *   3. card position + 1, which is only right when the pickers were filled in
   *      order from box 1 -- flagged as a guess so the UI can say so.
   * @returns {{boxId: number, slotId: number, guessed: boolean}}
   */
  static _resolvePrinterTarget(filamentObj, entityId, cardBoxIndex, cardSlotIndex) {
    const attrs = filamentObj?.attributes;
    if (typeof attrs?.box_id === "number" && typeof attrs?.slot_id === "number") {
      return { boxId: attrs.box_id, slotId: attrs.slot_id, guessed: false };
    }

    const match = /cfs_box_(\d+)_slot_(\d+)_/.exec(String(entityId || ""));
    // Home Assistant builds the entity id from the entity *name*, and the name
    // counts slots from 1 for the reader ("CFS Box 1 Slot 2") while the printer
    // counts them from 0. Passing the captured number straight through
    // addressed the slot after the one on screen, so a save overwrote the
    // neighbouring spool. Only the unique id is 0-based, and that never reaches
    // the frontend.
    //
    // Guessed, unlike the attributes above: an entity id is a renameable
    // display artifact, so the warning invites the user to check the target
    // before writing to the printer. A `_slot_0_` id cannot have come from that
    // naming scheme at all, so it is left to the card-position fallback rather
    // than decremented into -1.
    if (match && Number(match[2]) >= 1) {
      return { boxId: Number(match[1]), slotId: Number(match[2]) - 1, guessed: true };
    }

    return { boxId: cardBoxIndex + 1, slotId: cardSlotIndex, guessed: true };
  }

  static _parsePercent(percentObj) {
    if (!percentObj) return null;
    const state = percentObj.state;
    // "-" is a sentinel here too: Number("-") is NaN, so it was already
    // rejected, but going through the shared helper keeps the set in one place.
    if (isSentinel(state)) return null;
    const n = Number(String(state).trim());
    if (Number.isNaN(n) || !Number.isFinite(n)) return null;
    return Math.max(0, Math.min(100, n));
  }

  // Returns one of four literals, never telemetry -- but the consumers run the
  // result through _sanitizeColor anyway. HTML escaping does not neutralise a
  // semicolon, so any value interpolated into a `style` attribute would parse a
  // second declaration; the whitelist is what makes that unreachable.
  static _getHumidityColor(humidityStr) {
    if (!humidityStr || humidityStr === "-") return '#64b5f6'; // default blue

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
      view_mode: "full",
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
    this._cfg = { ...KCFSCard.getStubConfig(), ...KCFSCard._migrateConfig(config) };
    if (!this._root) {
      this._root = this.attachShadow({ mode: "open" });
    }
    // _render() wipes #content, so the gate must not then decide nothing changed
    // and skip repopulating it -- that would leave the card blank after an edit.
    this._snapshot = null;
    // Different entities may mean a different printer. Bumping the generation
    // invalidates a _resolveDeviceId() that is already awaiting callWS: it
    // captured the previous config's entity ids before the await, and writing
    // its answer back would target the old printer for the rest of the session.
    this._deviceId = undefined;
    this._deviceIdError = null;
    this._deviceIdGeneration = (this._deviceIdGeneration || 0) + 1;
    this._deviceIdPending = false;
    this._deviceIdRetried = false;
    this._statusEid = null;
    this._render();
  }

  // i18n helpers -------------------------------------------------------
  _resolveLanguage() {
    return _resolveLang(this._hass);
  }
  _t(key, vars) {
    return _translate(this._hass, "cfs_card", CFS_TRANSLATIONS, key, vars);
  }
  // ---------------------------------------------------------------------

  set hass(hass) {
    this._hass = hass;
    // Translated strings are not part of the snapshot, so when they arrive the
    // gate has to be reset and the render forced.
    _requestI18n(this, hass, () => { this._snapshot = null; this._update(); });
    // HA does not guarantee hass.entities is populated on the first assignment.
    // A resolution that failed against an empty registry caches null, and null
    // is not undefined, so nothing would ever retry it. Reopen the question once
    // the registry actually knows about one of our entities -- but only once.
    // A card that legitimately cannot resolve (entities spanning two printers,
    // or an entity with no device at all) also sits at null with a populated
    // registry, and retrying it on every telemetry frame flipped the edit
    // buttons between pencil and lock for the whole session.
    if (
      this._deviceId === null
      && !this._deviceIdPending
      && !this._deviceIdRetried
      && this._registryHasEntities()
    ) {
      this._deviceIdRetried = true;
      this._deviceId = undefined;
      this._deviceIdError = null;
    }
    // _isPrinterBusy() is a sync cache read, so the device id has to be resolved
    // out of band once; re-render when it lands so the lock icon settles.
    if (this._deviceId === undefined && !this._deviceIdPending) {
      this._deviceIdPending = true;
      // .catch as well as .then: _resolveDeviceId can reject (a malformed config,
      // a hass assigned before setConfig), and an unhandled rejection left
      // _deviceIdPending true forever, so both gates here refused to retry and
      // the card could never resolve while still rendering its buttons enabled.
      // Generation-guarded out here too, not only inside _resolveDeviceId.
      // `hass` can be assigned before setConfig, so the first call rejects on
      // the missing config; setConfig then runs synchronously, bumps the
      // generation and clears _deviceId, and the queued rejection would
      // otherwise land afterwards and pin the *new* config to
      // "toast_no_device" with its edit buttons locked. Clearing the pending
      // flag is gated for the mirror-image reason: a stale run clearing it
      // would let a second resolution start alongside the current one.
      // Safe to skip, because setConfig has already reset it.
      const generation = this._deviceIdGeneration || 0;
      const isCurrent = () => (this._deviceIdGeneration || 0) === generation;
      this._resolveDeviceId()
        .catch((err) => {
          console.warn("k-cfs-card: device resolution failed", err);
          if (!isCurrent()) return;
          this._deviceIdError = "toast_no_device";
          this._deviceId = null;
        })
        .finally(() => {
          if (!isCurrent()) return;
          this._deviceIdPending = false;
          this._updateIfChanged();
        });
    }
    this._updateIfChanged();
  }

  _render() {
    if (!this._root) return;

    const modeClass = KCFSCard._modeClass(this._cfg.view_mode);

    const style = `
      /* inherit HA fonts & typography */
      :host { 
        font: inherit; 
        color: var(--primary-text-color);
        display: block !important;
        height: auto !important;
        contain: none !important;
        position: relative;
        z-index: 1;
      }

      /* unify horizontal padding so right edges line up */
      :host { --row-xpad: 6px; }

      ha-card {
        overflow: visible !important;
        display: block !important;
        height: auto !important;
        min-height: auto !important;
        max-height: none !important;
        contain: none !important;
        position: relative;
        z-index: 1;
      }

      ha-card.compact-mode,
      ha-card.normal-mode {
        height: auto !important;
        overflow: visible !important;
      }

      #content {
        padding: 14px;
      }

      .card {
        border-radius: var(--ha-card-border-radius, 12px);
        background: var(--card-background-color);
        color: var(--primary-text-color);
        box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,.2));
        padding: 10px var(--row-xpad) 10px var(--row-xpad);
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      /* === NORMAL MODE === */
      .normal-mode {}

      .header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 12px;
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
        border-radius: var(--ha-card-border-radius, 18px);
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
        mask: radial-gradient(circle closest-side at 50% 50%, transparent 33px, black 34px);
        -webkit-mask: radial-gradient(circle closest-side at 50% 50%, transparent 33px, black 34px);
      }

      .ring-inner {
        width: 66px;
        height: 66px;
        background: transparent;
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
        mask: radial-gradient(circle closest-side at 50% 50%, transparent 12px, black 13px);
        -webkit-mask: radial-gradient(circle closest-side at 50% 50%, transparent 12px, black 13px);
      }

      .spool-mini::after {
        content: '';
        position: absolute;
        inset: 4px;
        background: transparent;
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
        position: relative;
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
        position: relative;
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
        position: relative;
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

      /* === BOX VIEW === */
      .box-view {
        position: relative;
        width: 100%;
        margin: 4px 0;
      }
      .box-image {
        display: block;
        width: 100%;
        height: auto;
      }
      /* Four evenly spaced bays across the unit's glass section. The geometry is
         tied to cfs_box.webp, which is why the mode is gated on a 4-slot box. */
      .bays {
        position: absolute;
        /* Measured against cfs_box.webp: the enclosure interior spans 7.5%-92.5%
           horizontally with its dividers at 29/50/71%, so four equal columns
           land one per bay. The height stops at the glass floor so a spool does
           not spill onto the drawer below. */
        top: 7%;
        left: 7.5%;
        width: 85%;
        height: 45%;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
      }
      .bay {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-end;
      }
      .bay + .bay {
        /* Theme variable rather than a hardcoded white, which inverted badly in
           light themes. */
        border-left: 1px solid var(--divider-color);
      }
      .bay-spool {
        width: 50%;
        aspect-ratio: 1;
        border-radius: 50%;
        background: var(--spool-color);
        box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.25) inset;
        opacity: 0.85;
      }
      .bay-label {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-top: 4px;
        padding: 1px 4px;
        border-radius: 4px;
        /* Legible over a photo in either theme. */
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 10px;
        line-height: 1.2;
        opacity: 0.92;
      }
      .bay-type { font-weight: 500; }
      .bay-pct { color: var(--secondary-text-color); }

      /* === EDIT AFFORDANCE === */
      .edit-btn, .edit-btn-mini {
        position: absolute;
        top: 4px;
        left: 4px;
        z-index: 3;
        display: grid;
        place-items: center;
        padding: 0;
        border: none;
        border-radius: 50%;
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
        cursor: pointer;
        opacity: 1;
        transition: opacity 120ms ease-in-out;
      }
      .edit-btn { width: 26px; height: 26px; }
      .edit-btn-mini { width: 18px; height: 18px; top: -2px; left: -2px; }
      .edit-btn ha-icon { --mdc-icon-size: 16px; }
      .edit-btn-mini ha-icon { --mdc-icon-size: 12px; }
      .edit-btn[aria-disabled="true"], .edit-btn-mini[aria-disabled="true"] {
        cursor: not-allowed;
        opacity: 0.45;
      }
      /* Reveal on hover only where hovering exists. A wall tablet is the primary
         HA surface, and there the button has to be visible without one. */
      @media (hover: hover) {
        /* The [aria-disabled] selectors are repeated here on purpose: they are
           more specific than a bare .edit-btn, and a media query adds no
           specificity, so without them a locked button stays visible while the
           editable ones hide. */
        .edit-btn, .edit-btn-mini,
        .edit-btn[aria-disabled="true"], .edit-btn-mini[aria-disabled="true"] { opacity: 0; }
        .spool-card:hover .edit-btn,
        .spool-mini-wrapper:hover .edit-btn-mini,
        .bay:hover .edit-btn-mini,
        .external-normal:hover .edit-btn,
        .external-compact:hover .edit-btn { opacity: 1; }
      }
      .edit-btn:focus-visible, .edit-btn-mini:focus-visible {
        opacity: 1;
        outline: 2px solid var(--primary-color);
        outline-offset: 1px;
      }

      /* === EDIT DIALOG === */
      .edit-overlay {
        position: fixed;
        inset: 0;
        z-index: 100;
        display: grid;
        place-items: center;
        padding: 16px;
        background: rgba(0, 0, 0, 0.55);
      }
      .edit-dialog {
        width: min(420px, 100%);
        max-height: 85vh;
        overflow-y: auto;
        padding: 16px;
        border-radius: var(--ha-card-border-radius, 12px);
        background: var(--card-background-color, var(--ha-card-background));
        color: var(--primary-text-color);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      }
      .edit-dialog h2 {
        margin: 0 0 4px;
        font-size: 18px;
        font-weight: 500;
      }
      .edit-target {
        margin-bottom: 12px;
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .edit-warning {
        margin-bottom: 12px;
        padding: 8px 10px;
        border-radius: 6px;
        background: var(--warning-color, #ffa726);
        color: #000;
        font-size: 12px;
      }
      .colour-row { margin: 12px 0 4px; }
      .colour-row > label {
        display: block;
        margin-bottom: 6px;
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .colour-inputs { display: flex; gap: 8px; align-items: center; }
      .colour-inputs input[type="color"] {
        width: 44px;
        height: 34px;
        padding: 0;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        background: none;
        cursor: pointer;
      }
      .colour-inputs input[type="text"] {
        flex: 1;
        min-width: 0;
        padding: 8px;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
        font-family: monospace;
      }
      .colour-inputs input:disabled { opacity: 0.5; cursor: not-allowed; }
      .presets { margin-top: 12px; }
      .presets > label {
        display: block;
        margin-bottom: 6px;
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .swatches {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 8px;
      }
      .swatch {
        width: 24px;
        height: 24px;
        padding: 0;
        border: 1px solid var(--divider-color);
        border-radius: 50%;
        cursor: pointer;
      }
      .swatch.custom { border-style: dashed; }
      .swatch:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 1px;
      }
      .preset-save { display: flex; gap: 8px; }
      .preset-save input {
        flex: 1;
        min-width: 0;
        padding: 8px;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
      }
      .preset-hint {
        margin-top: 6px;
        font-size: 11px;
        color: var(--secondary-text-color);
      }

      .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 20px;
      }
      .dialog-btn {
        padding: 8px 16px;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        cursor: pointer;
      }
      .dialog-btn.secondary {
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
      }
      .dialog-btn.primary {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
      }
      .dialog-btn[disabled] { opacity: 0.6; cursor: default; }

      /* === TOAST === */
      .cfs-toast {
        position: absolute;
        left: 50%;
        bottom: 12px;
        transform: translateX(-50%);
        /* Above .edit-overlay (100). Both _showToast and _showEditDialog append
           to the same root, so at 10 the overlay's rgba backdrop painted over
           every toast raised from the dialog: preset saved, preset deleted,
           name required and invalid colour were all invisible. */
        z-index: 110;
        max-width: calc(100% - 24px);
        padding: 8px 14px;
        border-radius: 6px;
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
        font-size: 13px;
        line-height: 1.3;
        text-align: center;
        box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0, 0, 0, 0.3));
        pointer-events: none;
      }

      .no-data {
        text-align: center;
        color: var(--secondary-text-color);
        padding: 20px;
      }
    `;

    this._root.innerHTML = `
      <ha-card class="${modeClass}">
        <style>${style}</style>
        <div id="content"></div>
      </ha-card>
    `;
  }

  /**
   * Read every configured entity into one render-ready snapshot.
   *
   * This is the ONLY place that reads hass.states for slots. The render gate and
   * all three view modes consume what it returns, so there is exactly one copy of
   * the collection logic to keep correct.
   * @returns {{boxes: object[], external: object|null}}
   */
  _collectData() {
    const states = this._hass.states || {};
    const gObj = (eid) => (eid ? states?.[eid] : undefined);
    const fmtState = (st) => {
      if (!st) return "-";
      const v = st.state;
      if (isSentinel(v)) return "-";
      const s = String(v).trim();
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
        const parsedColor = KCFSCard._parseColor(rawColor);
        const color = parsedColor ?? "#cccccc";
        const percent = KCFSCard._parsePercent(percentObj);
        const percentText = fmtState(percentObj);
        const entityId = filamentEid || colorEid || percentEid;
        const target = KCFSCard._resolvePrinterTarget(
          filamentObj, entityId, boxId, slotId,
        );

        slots[slotId] = {
          id: slotId,
          boxId,
          entity_id: entityId,
          name,
          type,
          selected,
          color,
          // Whether `color` above is the printer's or the display placeholder.
          // Editing must not write the placeholder back as a real colour.
          colorIsKnown: parsedColor !== null,
          percent,
          percentText,
          // Editing needs the printer's own ids and the current values to
          // prefill from; see KCFSCard._resolvePrinterTarget.
          printerBoxId: target.boxId,
          printerSlotId: target.slotId,
          targetIsGuessed: target.guessed,
          vendor: filamentObj?.attributes?.vendor,
          // `name` above is the sensor *state*, i.e. the composed "vendor name"
          // label. Editing has to write back the bare material name, or the
          // vendor ends up duplicated inside it.
          materialName: filamentObj?.attributes?.name,
          rfid: filamentObj?.attributes?.rfid,
          minTemp: filamentObj?.attributes?.min_temp,
          maxTemp: filamentObj?.attributes?.max_temp,
          pressure: filamentObj?.attributes?.pressure,
          isMultiColour: KCFSCard._isMultiColour(rawColor),
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
      const parsedColor = KCFSCard._parseColor(rawColor);
      const color = parsedColor ?? "#cccccc";
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
        // Same as a box slot: the edit dialog must not offer the display grey
        // as though the printer had reported it. Omitting this left the
        // external spool's colour field always empty.
        colorIsKnown: parsedColor !== null,
        percent,
        percentText,
        // The external box's id comes from the printer via the sensor; there is
        // no card position to fall back on, so leave it null when unknown rather
        // than guessing 0.
        printerBoxId: filamentObj?.attributes?.box_id ?? null,
        printerSlotId: filamentObj?.attributes?.slot_id ?? 0,
        // Both ids, not just the box: `slot_id` falls back to 0 above, so a
        // spool reporting a box but no slot would have been written to slot 0
        // with nothing on screen saying the slot had been assumed.
        //
        // Typed, not `=== undefined`: `sensor.py` publishes
        // `data.get("id", self._slot_id)`, which is `None` when the printer
        // reports `"id": null` -- and that arrives here as `null`, which `??`
        // swallows into 0 while an `undefined` test says the id was known.
        // The box-slot path already tests `typeof === "number"`.
        targetIsGuessed:
          typeof filamentObj?.attributes?.box_id !== "number"
          || typeof filamentObj?.attributes?.slot_id !== "number",
        vendor: filamentObj?.attributes?.vendor,
        materialName: filamentObj?.attributes?.name,
        rfid: filamentObj?.attributes?.rfid,
        minTemp: filamentObj?.attributes?.min_temp,
        maxTemp: filamentObj?.attributes?.max_temp,
        pressure: filamentObj?.attributes?.pressure,
        isMultiColour: KCFSCard._isMultiColour(rawColor),
      };
    }

    return { boxes: Object.values(boxes), external: externalData };
  }

  /**
   * Cheap change detection over everything the renderers read.
   *
   * The snapshot is a fixed-shape tree of scalars built from object literals, so
   * key order is deterministic and stringifying it is both correct and much
   * cheaper than walking it recursively. Anything a renderer reads that is NOT
   * in `data` has to be included here too, or the view goes stale.
   * @param {object} data
   * @returns {string}
   */
  _fingerprint(data) {
    return JSON.stringify([
      this._cfg.view_mode,
      this._cfg.show_type_in_mini,
      this._isPrinterBusy(),
      // _renderEditButton reads this to pick the lock icon, the tooltip and the
      // disabled attribute. Device resolution finishes asynchronously, so
      // without it here the .then() below found an unchanged fingerprint and the
      // buttons stayed enabled against a card that cannot resolve its printer.
      this._deviceIdError,
      this._selectedCFS,
      data,
    ]);
  }

  /** Re-render only when something a renderer would show has actually changed. */
  _updateIfChanged() {
    if (!this._root || !this._hass) return;
    const data = this._collectData();
    const fingerprint = this._fingerprint(data);
    if (fingerprint === this._snapshot) return;
    this._snapshot = fingerprint;
    this._update(data);
  }

  _update(data) {
    if (!this._root || !this._hass) return;

    const contentContainer = this._root.getElementById("content");
    if (!contentContainer) return;

    // Callers that bypass the gate (an i18n load, the unit selector) pass nothing.
    const { boxes: boxValues, external: externalData } = data || this._collectData();

    if (boxValues.length === 0 && !externalData) {
      contentContainer.innerHTML = `<div class="no-data">${esc(this._t("no_data"))}</div>`;
      return;
    }

    // Render based on mode
    if (this._cfg.view_mode === "compact") {
      contentContainer.innerHTML = this._renderCompactMode(boxValues, externalData);
    } else if (this._cfg.view_mode === "box") {
      contentContainer.innerHTML = this._renderBoxMode(boxValues, externalData);
    } else {
      contentContainer.innerHTML = this._renderNormalMode(boxValues, externalData);
    }

    this._attachEventHandlers();
  }

  /**
   * Photo-realistic view: the CFS unit with a spool overlay per bay.
   *
   * Only offered for a four-bay unit, because the overlay geometry is tied to
   * this particular image. Anything else falls back to the full view rather than
   * drawing spools in the wrong places.
   * @param {object[]} boxes
   * @param {object|null} external
   * @returns {string}
   */
  _renderBoxMode(boxes, external) {
    const box = boxes[this._selectedCFS] || boxes[0];
    const slots = box?.slots || [];
    const filled = slots.filter(Boolean);

    if (filled.length !== 4) {
      return this._renderNormalMode(boxes, external);
    }

    const unitSelector = boxes.length > 1
      ? `
        <div class="unit-selector">
          ${boxes.map((b, idx) => `
            <button class="unit-btn ${idx === this._selectedCFS ? 'active' : ''}" data-cfs="${idx}">
              ${esc(this._t("cfs_number_label", { number: b.id + 1 }))}
            </button>
          `).join('')}
        </div>
      `
      : '';

    const bays = slots.map((slot) => {
      if (!slot) return '<div class="bay"></div>';
      const safeType = !isSentinel(slot.type) ? String(slot.type).trim() : "-";
      const hasFilament = safeType !== "-";
      const pct = hasFilament && slot.percent !== null ? Math.round(slot.percent) : 0;
      return `
        <div class="bay" data-eid="${esc(slot.entity_id)}">
          ${this._renderEditButton(slot, true)}
          <div class="bay-spool" style="--spool-color: ${esc(slot.color || '#cccccc')}"></div>
          <div class="bay-label">
            <span class="bay-type">${esc(safeType)}</span>
            <span class="bay-pct">${pct}%</span>
          </div>
        </div>
      `;
    }).join('');

    const env = [];
    if (box?.temp && box.temp !== "-") env.push(`<span class="env-temp">${esc(box.temp)}</span>`);
    if (box?.humidity && box.humidity !== "-") {
      env.push(`<span class="env-hum" style="color: ${KCFSCard._sanitizeColor(box.humidityColor)}">${esc(box.humidity)}</span>`);
    }

    return `
      ${unitSelector}
      <div class="box-view">
        <img class="box-image" src="${ASSET_URL_BASE}cfs_box.webp" alt="${esc(this._t("alt_cfs_box"))}" />
        <div class="bays">${bays}</div>
      </div>
      ${env.length ? `<div class="env-info">${env.join(' <span style="color: var(--divider-color)">•</span> ')}</div>` : ''}
      ${this._renderExternalCompact(external)}
    `;
  }

  _renderNormalMode(boxes, external) {
    // Ensure we have at least one box
    if (boxes.length === 0 && !external) {
      return `<div class="no-data">${esc(this._t("no_data"))}</div>`;
    }

    // Unit selector (only if we have multiple boxes)
    let unitSelector = '';
    if (boxes.length > 1) {
      unitSelector = `
        <div class="unit-selector">
          ${boxes.map((box, idx) => `
            <button class="unit-btn ${idx === this._selectedCFS ? 'active' : ''}" data-cfs="${idx}">
              ${esc(this._t("cfs_number_label", { number: box.id + 1 }))}
            </button>
          `).join('')}
        </div>
      `;
    }

    // Get the selected box
    const selectedBox = boxes[this._selectedCFS] || boxes[0];
    if (!selectedBox && !external) {
      return `<div class="no-data">${esc(this._t("no_data"))}</div>`;
    }

    // Header with environment info
    let envInfo = '';
    if (selectedBox) {
      const tempStr = selectedBox.temp !== "-" ? selectedBox.temp : '';
      const humStr = selectedBox.humidity !== "-" ? selectedBox.humidity : '';

      if (tempStr || humStr) {
        const tempHtml = tempStr ? `<span class="env-temp">${esc(tempStr)}</span>` : '';
        const humHtml = humStr ? `<span class="env-hum" style="color: ${KCFSCard._sanitizeColor(selectedBox.humidityColor)}">${esc(humStr)}</span>` : '';
        const separator = tempStr && humStr ? ' <span style="color: var(--divider-color)">•</span> ' : '';
        envInfo = `<div class="env-info">${tempHtml}${separator}${humHtml}</div>`;
      }
    }

    const header = `
      <div class="header">
        <div class="title-section">
          <div class="title">${esc(this._cfg.name || 'Creality CFS')}</div>
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
      const safeType = !isSentinel(external.type) ? String(external.type).trim() : "-";
      const safeName = !isSentinel(external.name) ? String(external.name).trim() : "-";
      const hasFilament = safeType !== "-" && safeName !== "-";
      const pct = hasFilament && external.percent !== null ? external.percent : 0;
      const percentTextDisplay = hasFilament ? (external.percentText || '-') : '-';
      const displayName = hasFilament ? `${safeName} ${safeType}` : '-';
      externalSection = `
        <div class="external-section">
          <div class="external-normal" data-eid="${esc(external.entity_id)}">
            ${this._renderEditButton(external)}
            <div class="ext-icon">${esc(this._t("ext_label"))}</div>
            <div class="ext-info">
              <div class="ext-name">${esc(displayName)}</div>
              <div class="ext-bar">
                <div class="ext-fill" style="width: ${Number(pct) || 0}%"></div>
              </div>
            </div>
            <div class="ext-percent">${esc(percentTextDisplay)}</div>
          </div>
        </div>
      `;
    }

    return `${unitSelector}${header}${spoolGrid}${externalSection}`;
  }

  _renderCompactMode(boxes, external) {
    if (boxes.length === 0 && !external) {
      return `<div class="no-data">${esc(this._t("no_data"))}</div>`;
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

    return `${cfsRows}${this._renderExternalCompact(external)}`;
  }

  /**
   * The external spool as a compact row, or "" when none is configured.
   *
   * Shared by compact and box mode: box mode used to return the box view alone,
   * so a configured external spool -- and its edit button -- vanished from the
   * card whenever the selected unit had four populated slots.
   * @param {object|null} external
   * @returns {string}
   */
  _renderExternalCompact(external) {
    if (!external) return '';
    const safeType = !isSentinel(external.type) ? String(external.type).trim() : "-";
    const safeName = !isSentinel(external.name) ? String(external.name).trim() : "-";
    const hasFilament = safeType !== "-" && safeName !== "-";
    const percentTextDisplay = hasFilament ? (external.percentText || '-') : '-';
    const displayName = hasFilament ? `${safeName} ${safeType}` : '-';
    return `
      <div class="external-section">
        <div class="external-compact" data-eid="${esc(external.entity_id)}">
          ${this._renderEditButton(external)}
          <div class="ext-dot">${esc(this._t("ext_label"))}</div>
          <div class="ext-compact-info">
            <div>${esc(displayName)}</div>
            <div>${esc(percentTextDisplay)}</div>
          </div>
        </div>
      </div>
    `;
  }

  _renderCFSRow(box) {
    const tempStr = box.temp !== "-" ? box.temp : '';
    const humStr = box.humidity !== "-" ? box.humidity : '';

    let envHtml = '';
    if (tempStr || humStr) {
      envHtml = `
        <div class="env-mini">
          ${tempStr ? `<div class="temp">${esc(tempStr)}</div>` : ''}
          ${humStr ? `<div class="hum" style="color: ${KCFSCard._sanitizeColor(box.humidityColor)}">${esc(humStr)}</div>` : ''}
        </div>
      `;
    }

    return `
      <div class="cfs-row">
        <div class="cfs-label">${esc(this._t("cfs_number_label", { number: box.id + 1 }))}</div>
        <div class="spools-inline">
          ${box.slots.map((slot) => this._renderSpoolMini(slot)).join('')}
        </div>
        ${envHtml}
      </div>
    `;
  }

  /**
   * The edit button for a slot, or "" when the slot cannot be edited.
   *
   * Editing is refused for the external spool until the printer actually tells
   * us its box id -- PR #75 sent a hardcoded 0, which was a guess.
   * @param {object} slot from _collectData
   * @param {boolean} mini smaller variant for the compact rows
   * @returns {string}
   */
  _renderEditButton(slot, mini = false) {
    if (!slot || !slot.entity_id) return "";

    const busy = this._isPrinterBusy();
    const unaddressable = slot.printerBoxId === null || slot.printerBoxId === undefined;
    const disabled = busy || unaddressable || Boolean(this._deviceIdError);
    const title = busy
      ? this._t("tooltip_edit_locked")
      : unaddressable
        ? this._t("toast_external_not_supported")
        : this._deviceIdError
          ? this._t(this._deviceIdError)
          : this._t("btn_edit");

    return `
      <button type="button"
              class="${mini ? "edit-btn-mini" : "edit-btn"}"
              data-edit="${esc(slot.entity_id)}"
              title="${esc(title)}"
              aria-label="${esc(title)}"
              ${disabled ? 'aria-disabled="true"' : ""}>
        <ha-icon icon="${disabled ? mdi("lock") : mdi("pencil")}"></ha-icon>
      </button>
    `;
  }

  _renderSpoolCard(slot) {
    if (!slot) {
      return `<div class="spool-card"></div>`;
    }

    const isActive = slot.selected === 1 || slot.selected === true;
    const color = slot.color || '#cccccc';
    const safeType = !isSentinel(slot.type) ? String(slot.type).trim() : "-";
    const safeName = !isSentinel(slot.name) ? String(slot.name).trim() : "-";

    // If no filament (type is "-" or name is "-"), show 0% regardless of actual value
    const hasFilament = safeType !== "-" && safeName !== "-";
    const pct = hasFilament && slot.percent !== null ? slot.percent : 0;
    const pctDisplay = hasFilament && slot.percent !== null ? Math.round(slot.percent) : 0;
    const percentTextDisplay = hasFilament ? (slot.percentText || '-') : '-';

    const badge = isActive ? '<div class="status-badge"></div>' : '';

    return `
      <div class="spool-card ${isActive ? 'active' : ''}" data-eid="${esc(slot.entity_id)}">
        ${badge}
        ${this._renderEditButton(slot)}
        <div class="ring-container">
          <div class="ring-outer" style="--spool-color: ${esc(color)}; --spool-pct: ${Number(pct) || 0}%"></div>
          <div class="ring-inner">
            <span class="spool-pct">${pctDisplay}%</span>
            <span class="spool-label">${esc(safeType)}</span>
          </div>
        </div>
        <div class="material-name">${esc(safeName)}</div>
        <div class="color-name">${esc(percentTextDisplay)}</div>
      </div>
    `;
  }

  _renderSpoolMini(slot) {
    const showType = this._cfg.show_type_in_mini;

    if (!slot) {
      if (showType) {
        return `<div class="spool-mini-wrapper"><div class="spool-mini" style="--spool-color: #333; --spool-pct: 0%"><span>-</span></div><div class="spool-mini-type">-</div></div>`;
      }
      return `<div class="spool-mini" style="--spool-color: #333; --spool-pct: 0%"><span>-</span></div>`;
    }

    const isActive = slot.selected === 1 || slot.selected === true;
    const color = slot.color || '#cccccc';
    const safeType = !isSentinel(slot.type) ? String(slot.type).trim() : "-";
    const safeName = !isSentinel(slot.name) ? String(slot.name).trim() : null;

    // If no filament (type is "-" or name is empty/dash), show 0% regardless of actual value
    const hasFilament = safeType !== "-" && safeName !== null;
    const pct = hasFilament && slot.percent !== null ? slot.percent : 0;
    const pctDisplay = hasFilament && slot.percent !== null ? Math.round(slot.percent) : 0;

    if (showType) {
      return `
        <div class="spool-mini-wrapper">
          <div class="spool-mini ${isActive ? 'active' : ''}" 
               style="--spool-color: ${esc(color)}; --spool-pct: ${Number(pct) || 0}%" 
               data-eid="${esc(slot.entity_id)}">
            <span>${pctDisplay}</span>
          </div>
          <div class="spool-mini-type">${esc(safeType)}</div>
          ${this._renderEditButton(slot, true)}
        </div>
      `;
    }

    return `
      <div class="spool-mini-wrapper">
        <div class="spool-mini ${isActive ? 'active' : ''}" 
             style="--spool-color: ${esc(color)}; --spool-pct: ${Number(pct) || 0}%" 
             data-eid="${esc(slot.entity_id)}">
          <span>${pctDisplay}</span>
        </div>
        ${this._renderEditButton(slot, true)}
      </div>
    `;
  }

  /**
   * The device id this card's entities belong to, or null.
   *
   * Fails closed on purpose. PR #75 fell back to "the first ha_creality_ws
   * device in the registry", which in a two-printer setup wrote filament data to
   * the wrong printer. A card whose entities span two printers is also refused
   * rather than silently resolved to one of them.
   *
   * Reads hass.entities (EntityRegistryDisplayEntry carries device_id, platform
   * and translation_key), so no WebSocket round trip and no admin permission is
   * needed -- unlike config/entity_registry/list.
   * @returns {Promise<string|null>}
   */
  async _resolveDeviceId() {
    if (this._deviceId !== undefined) return this._deviceId;

    const generation = this._deviceIdGeneration || 0;
    const isStale = () => (this._deviceIdGeneration || 0) !== generation;
    const entityIds = this._configuredEntityIds();
    const registry = this._hass?.entities || {};
    const devices = new Set();

    const unresolved = [];
    for (const eid of entityIds) {
      const deviceId = registry[eid]?.device_id;
      if (deviceId) devices.add(deviceId);
      else unresolved.push(eid);
    }

    // Anything hass.entities could not answer for is asked individually. It is
    // not a version fallback: hass.entities can be *partially* populated, and it
    // is absent entirely for a non-admin user, whose browser is not allowed
    // config/entity_registry/get either.
    //
    // Every unresolved entity is asked, not just enough to find one device.
    // Accepting the first answer resolved a card spanning two printers to
    // whichever replied first, so editing a slot on the other one wrote its box
    // and slot ids to the wrong machine -- the exact failure the fail-closed
    // behaviour below exists to prevent.
    //
    // Asked in parallel over the distinct ids: a fully configured card supplies
    // up to 51, and serial round trips delayed every edit button by all of them.
    let anyLookupFailed = false;
    if (unresolved.length) {
      const answers = await Promise.all([...new Set(unresolved)].map(async (eid) => {
        try {
          const entry = await this._hass.callWS({
            type: "config/entity_registry/get",
            entity_id: eid,
          });
          return { deviceId: entry?.device_id || null, failed: false };
        } catch (_) {
          // config/entity_registry/get is admin-only, so for a non-admin
          // dashboard user every one of these fails. Treating that as "this
          // entity has no device" is what let a two-printer card resolve to
          // whichever printer *was* in hass.entities, and _saveMaterial then
          // sent the other printer's box and slot ids to it.
          return { deviceId: null, failed: true };
        }
      }));
      for (const answer of answers) {
        if (answer.failed) anyLookupFailed = true;
        else if (answer.deviceId) devices.add(answer.deviceId);
      }
    }

    // setConfig ran while we were awaiting callWS: this answer is for the
    // previous config, so drop it rather than caching it.
    if (isStale()) return this._deviceId ?? null;

    // Fail closed when an entity's device could not be determined at all: this
    // card may well span two printers and we simply cannot see it.
    if (devices.size !== 1 || anyLookupFailed) {
      this._deviceIdError = devices.size > 1 ? "toast_multiple_devices" : "toast_no_device";
      this._deviceId = null;
      return null;
    }

    this._deviceIdError = null;
    [this._deviceId] = [...devices];
    return this._deviceId;
  }

  /** Whether hass.entities knows about any entity this card is configured with. */
  _registryHasEntities() {
    const registry = this._hass?.entities;
    if (!registry) return false;
    return this._configuredEntityIds().some((eid) => registry[eid]);
  }

  /** Every non-empty entity picker value in the card's config. */
  _configuredEntityIds() {
    const ids = [];
    const push = (value) => { if (value) ids.push(value); };

    for (let box = 0; box < 4; box += 1) {
      push(this._cfg[`box${box}_temp`]);
      push(this._cfg[`box${box}_humidity`]);
      for (let slot = 0; slot < 4; slot += 1) {
        push(this._cfg[`box${box}_slot${slot}_filament`]);
        push(this._cfg[`box${box}_slot${slot}_color`]);
        push(this._cfg[`box${box}_slot${slot}_percent`]);
      }
    }
    push(this._cfg.external_filament);
    push(this._cfg.external_color);
    push(this._cfg.external_percent);
    return ids;
  }

  /**
   * The print-status entity for *this* card's printer.
   *
   * PR #75 scanned all of hass.states for any id containing "_print_status", so
   * printer B printing locked printer A's card. PrintStatusSensor sets
   * translation_key="print_status", which the registry exposes, making this both
   * device-scoped and rename-proof. Memoised per device.
   * @returns {string|null}
   */
  _statusEntityId() {
    const deviceId = this._deviceId;
    if (!deviceId) return null;
    if (this._statusEid?.deviceId === deviceId) return this._statusEid.entityId;

    const registry = this._hass?.entities || {};
    let found = null;
    for (const eid in registry) {
      const entry = registry[eid];
      if (
        entry.device_id === deviceId
        && entry.platform === "ha_creality_ws"
        && entry.translation_key === "print_status"
      ) {
        found = eid;
        break;
      }
    }
    // Only a hit is memoized: late discovery can add the print_status entity
    // after this first lookup, and caching the miss would leave _isPrinterBusy()
    // permanently false -- so the lock affordance would never appear.
    if (found) this._statusEid = { deviceId, entityId: found };
    return found;
  }

  /**
   * Whether this card's printer is mid-job.
   *
   * An unresolvable state counts as not busy: the bug being fixed was false
   * positives, and blocking edits whenever the registry is thin would make the
   * feature unusable. The service re-checks server-side, so this is an
   * affordance rather than the guarantee.
   * @returns {boolean}
   */
  _isPrinterBusy() {
    const entityId = this._statusEntityId();
    if (!entityId) return false;
    const state = this._hass?.states?.[entityId]?.state;
    return state ? BUSY_PRINT_STATES.has(state) : false;
  }

  /** Brief, non-blocking feedback. Replaces PR #75's alert() calls. */
  _showToast(message) {
    if (!this._root) return;

    // Hold the reference rather than looking it back up by id -- one toast at a
    // time, and no dependency on where in the tree it was attached.
    if (this._toastEl?.remove) this._toastEl.remove();
    clearTimeout(this._toastTimer);

    const toast = document.createElement("div");
    toast.className = "cfs-toast";
    toast.textContent = message;
    this._root.appendChild(toast);
    this._toastEl = toast;
    this._toastTimer = setTimeout(() => {
      if (toast.remove) toast.remove();
      if (this._toastEl === toast) this._toastEl = null;
    }, 4000);
  }

  /**
   * Find a collected slot by its filament entity id.
   * @returns {object|null}
   */
  _findSlot(entityId) {
    const { boxes, external } = this._collectData();
    if (external?.entity_id === entityId) return external;
    for (const box of boxes) {
      for (const slot of box.slots) {
        if (slot?.entity_id === entityId) return slot;
      }
    }
    return null;
  }

  /**
   * Open the material editor for one slot.
   *
   * Rendered inside the shadow root, not document.body. PR #75 appended to
   * document.body, which put the dialog outside the reach of the injected
   * <style> -- so its 120 lines of dialog CSS never applied and everything was
   * styled with ~90 inline assignments instead. :host and ha-card already force
   * overflow:visible and contain:none, so a fixed overlay still escapes the card.
   */
  _showEditDialog(entityId) {
    if (!this._hass || !this._root) return;

    const slot = this._findSlot(entityId);
    if (!slot) return;

    // Re-check: the affordance may have been rendered before the print started.
    if (this._isPrinterBusy()) {
      this._showToast(this._t("toast_printer_busy"));
      return;
    }
    if (this._deviceIdError) {
      this._showToast(this._t(this._deviceIdError));
      return;
    }
    if (slot.printerBoxId === null || slot.printerBoxId === undefined) {
      this._showToast(this._t("toast_external_not_supported"));
      return;
    }

    const overlay = document.createElement("div");
    overlay.className = "edit-overlay";
    const dialog = document.createElement("div");
    dialog.className = "edit-dialog";
    // Modal semantics: without these the overlay is an anonymous <div> that a
    // screen reader cannot announce and a keyboard user cannot leave, since
    // click-outside was the only dismissal besides the Cancel button.
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", this._t("dialog_edit_title"));
    dialog.tabIndex = -1;
    overlay.appendChild(dialog);

    const close = () => {
      overlay.removeEventListener("keydown", onKeyDown);
      if (overlay.remove) overlay.remove();
    };
    const onKeyDown = (ev) => {
      if (ev.key === "Escape" || ev.key === "Esc") {
        ev.stopPropagation();
        close();
      }
    };
    overlay.addEventListener("keydown", onKeyDown);
    overlay.addEventListener("click", (ev) => { if (ev.target === overlay) close(); });

    dialog.appendChild(this._renderEditForm(slot, close));
    this._root.appendChild(overlay);
    // Focus the dialog itself rather than the first field: ha-form upgrades
    // asynchronously, so its inputs may not exist yet.
    if (dialog.focus) dialog.focus();
  }

  /**
   * Build the dialog body.
   *
   * The six text/number fields go through ha-form, which the editor already uses:
   * it gives HA theming, accessibility and sensible mobile keyboards for free,
   * and replaces most of PR #75's hand-rolled inputs. Colour stays hand-built
   * because HA has no hex-colour selector (color_rgb returns [r, g, b]).
   * @param {object} slot
   * @param {Function} close
   * @returns {object} the dialog content element
   */
  _renderEditForm(slot, close) {
    const container = document.createElement("div");

    const heading = document.createElement("h2");
    heading.textContent = this._t("dialog_edit_title");
    container.appendChild(heading);

    // Always show which slot is about to be written -- a mis-mapped card is then
    // visible before saving rather than after.
    const target = document.createElement("div");
    target.className = "edit-target";
    target.textContent = this._t("dialog_edit_target", {
      box: slot.printerBoxId,
      slot: slot.printerSlotId,
    });
    container.appendChild(target);

    if (slot.targetIsGuessed) {
      const warn = document.createElement("div");
      warn.className = "edit-warning";
      warn.textContent = this._t("warn_box_id_guessed");
      container.appendChild(warn);
    }

    // `slot.name` is a sensor *state*, so an entity with no value reads back as
    // the literal "unknown" -- and the type field is the only required one, so
    // filling that in and saving an otherwise untouched form wrote "unknown"
    // to the spool as its material name. Same sentinel set the display path
    // uses, rather than the "-" check this had.
    const clean = (value) => (isSentinel(value) ? "" : String(value).trim());

    const values = {
      type: clean(slot.type),
      // The bare `name` attribute only. `slot.name` is the sensor *state*, which
      // `format_filament_label` composes from vendor plus name -- or vendor plus
      // *type* when the printer reports no name at all, e.g. "Creality PLA". As
      // a fallback it prefilled that composite as the material name and
      // `_saveMaterial` wrote it back, putting the vendor inside the name, which
      // is the duplication issue #115 removed from the display path.
      name: clean(slot.materialName),
      vendor: clean(slot.vendor),
      min_temp: slot.minTemp ?? undefined,
      max_temp: slot.maxTemp ?? undefined,
      pressure: slot.pressure ?? undefined,
    };

    const form = document.createElement("ha-form");
    form.hass = this._hass;
    form.data = values;
    // Bounds mirror services.yaml and the service schema so all three agree.
    form.schema = [
      { name: "type", selector: { text: {} } },
      { name: "name", selector: { text: {} } },
      { name: "vendor", selector: { text: {} } },
      { name: "min_temp", selector: { number: { min: 150, max: 300, step: 1, unit_of_measurement: "°C", mode: "box" } } },
      { name: "max_temp", selector: { number: { min: 150, max: 350, step: 1, unit_of_measurement: "°C", mode: "box" } } },
      { name: "pressure", selector: { number: { min: 0, max: 1, step: 0.01, mode: "box" } } },
    ];
    form.computeLabel = (s) => this._t(`label_material_${s.name}`);
    form.addEventListener("value-changed", (ev) => {
      Object.assign(values, ev.detail.value);
    });
    container.appendChild(form);

    // ---- colour -----------------------------------------------------------
    const colourRow = document.createElement("div");
    colourRow.className = "colour-row";
    const colourLabel = document.createElement("label");
    colourLabel.textContent = this._t("label_material_color");
    colourRow.appendChild(colourLabel);

    const colourInputs = document.createElement("div");
    colourInputs.className = "colour-inputs";
    // _sanitizeColor preserves a three-digit colour, but input[type=color]
    // rejects #abc (falling back to #000000, so the swatch stops matching the
    // text field) and _saveMaterial demands six digits -- it would refuse a
    // colour the printer itself reported.
    // Only a colour the printer actually reported. `slot.color` falls back to
    // the display grey, and prefilling that sent `#cccccc` to the printer for
    // anyone who opened the dialog to change something else and pressed Save.
    // `_saveMaterial` already omits an empty colour from the payload.
    const prefill = slot.colorIsKnown ? toSixDigitHex(slot.color) || "" : "";
    const picker = document.createElement("input");
    picker.type = "color";
    picker.value = prefill || "#cccccc";
    const hex = document.createElement("input");
    hex.type = "text";
    hex.value = slot.isMultiColour ? "" : prefill;
    hex.placeholder = "#rrggbb";

    if (slot.isMultiColour) {
      // A two-colour spool cannot be expressed as one value, so editing the
      // colour at all would quietly discard half of it.
      picker.disabled = true;
      hex.disabled = true;
      hex.placeholder = this._t("tooltip_multicolour_readonly");
      colourRow.title = this._t("tooltip_multicolour_readonly");
    } else {
      picker.addEventListener("input", () => { hex.value = picker.value; });
      hex.addEventListener("input", () => {
        if (/^#[0-9a-fA-F]{6}$/.test(hex.value)) picker.value = hex.value;
      });
    }

    colourInputs.appendChild(picker);
    colourInputs.appendChild(hex);
    colourRow.appendChild(colourInputs);

    if (!slot.isMultiColour) {
      colourRow.appendChild(this._renderPresets(picker, hex));
    }

    container.appendChild(colourRow);

    // ---- actions ----------------------------------------------------------
    const actions = document.createElement("div");
    actions.className = "dialog-actions";

    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "dialog-btn secondary";
    cancel.textContent = this._t("btn_cancel");
    cancel.addEventListener("click", close);
    actions.appendChild(cancel);

    const save = document.createElement("button");
    save.type = "button";
    save.className = "dialog-btn primary";
    save.textContent = this._t("btn_save");
    save.addEventListener("click", async () => {
      save.disabled = true;
      save.textContent = this._t("btn_saving");
      const ok = await this._saveMaterial(slot, {
        ...values,
        color: slot.isMultiColour ? undefined : hex.value.trim(),
      });
      if (ok) {
        close();
      } else {
        save.disabled = false;
        save.textContent = this._t("btn_save");
      }
    });
    actions.appendChild(save);
    container.appendChild(actions);

    return container;
  }

  /**
   * Swatch row plus preset management, wired to the colour inputs.
   *
   * Rebuilt in place when presets change rather than by reopening the dialog:
   * PR #75 tore the whole dialog down and reopened it on a timer, which threw
   * away whatever the user had already typed into the other fields.
   * @param {object} picker the <input type="color">
   * @param {object} hex the hex text input
   * @returns {object} the presets section element
   */
  _renderPresets(picker, hex) {
    // Constructed on first use, so a dashboard full of cards does not all touch
    // localStorage just to render.
    this._presets = sharedPresets();

    const section = document.createElement("div");
    section.className = "presets";

    const label = document.createElement("label");
    label.textContent = this._t("label_color_presets");
    section.appendChild(label);

    const swatches = document.createElement("div");
    swatches.className = "swatches";
    section.appendChild(swatches);

    const apply = (colour) => {
      picker.value = colour;
      hex.value = colour;
    };

    const rebuild = () => {
      // Scoped to this row, not the document: PR #75 used a document-wide query
      // that also reset swatches in a second card's open dialog.
      swatches.innerHTML = "";

      for (const [name, colour] of this._presets.entries()) {
        const swatch = document.createElement("button");
        swatch.type = "button";
        swatch.className = "swatch";
        swatch.title = name;
        swatch.setAttribute("aria-label", name);
        swatch.style.background = colour;
        swatch.addEventListener("click", () => apply(colour));

        if (this._presets.isCustom(name)) {
          swatch.classList?.add?.("custom");
          // Long-press-free management: a modifier click removes a custom preset,
          // which keeps the row compact without a second list.
          swatch.addEventListener("contextmenu", (ev) => {
            ev.preventDefault?.();
            if (this._presets.remove(name)) {
              this._showToast(this._t("toast_preset_deleted", { name }));
              rebuild();
            }
          });
        }
        swatches.appendChild(swatch);
      }
    };
    rebuild();

    const saveRow = document.createElement("div");
    saveRow.className = "preset-save";
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.placeholder = this._t("label_preset_name");
    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "dialog-btn secondary";
    saveBtn.textContent = this._t("btn_save_preset");
    saveBtn.addEventListener("click", () => {
      const name = nameInput.value.trim();
      if (!name) {
        this._showToast(this._t("toast_preset_name_required"));
        return;
      }
      if (this._presets.save(name, hex.value)) {
        nameInput.value = "";
        this._showToast(this._t("toast_preset_saved", { name }));
        rebuild();
      } else {
        this._showToast(this._t("toast_colour_invalid"));
      }
    });
    saveRow.appendChild(nameInput);
    saveRow.appendChild(saveBtn);
    section.appendChild(saveRow);

    const hint = document.createElement("div");
    hint.className = "preset-hint";
    hint.textContent = this._t("hint_delete_preset");
    section.appendChild(hint);

    return section;
  }

  /**
   * Send one slot's edits to the service.
   * @returns {Promise<boolean>} whether the write was accepted
   */
  async _saveMaterial(slot, formData) {
    const deviceId = await this._resolveDeviceId();
    if (!deviceId) {
      this._showToast(this._t(this._deviceIdError || "toast_no_device"));
      return false;
    }

    const type = String(formData.type || "").trim();
    if (!type) {
      this._showToast(this._t("toast_type_required"));
      return false;
    }

    // Number.isFinite, not `||`: `0` is a legitimate pressure and a truthiness
    // check would silently replace it with the default.
    const num = (value) => {
      const n = Number(value);
      return Number.isFinite(n) ? n : undefined;
    };
    const minTemp = num(formData.min_temp);
    const maxTemp = num(formData.max_temp);
    if (minTemp !== undefined && maxTemp !== undefined && maxTemp < minTemp) {
      // Surfaced rather than clamped: someone who typed these wants to know.
      this._showToast(this._t("toast_temp_range_invalid"));
      return false;
    }

    const colour = String(formData.color || "").trim();
    if (colour && !/^#?[0-9a-fA-F]{6}$/.test(colour)) {
      this._showToast(this._t("toast_colour_invalid"));
      return false;
    }

    const payload = {
      device_id: deviceId,
      box_id: slot.printerBoxId,
      slot_id: slot.printerSlotId,
      type,
    };
    if (formData.name && String(formData.name).trim()) payload.name = String(formData.name).trim();
    if (formData.vendor && String(formData.vendor).trim()) payload.vendor = String(formData.vendor).trim();
    if (colour) payload.color = colour.startsWith("#") ? colour : `#${colour}`;
    if (minTemp !== undefined) payload.min_temp = minTemp;
    if (maxTemp !== undefined) payload.max_temp = maxTemp;
    const pressure = num(formData.pressure);
    if (pressure !== undefined) payload.pressure = pressure;
    // Pass the printer's existing tag id straight back; omitting the key would
    // be fine too, but sending "" would erase it.
    if (slot.rfid) payload.rfid = slot.rfid;

    try {
      await this._hass.callService("ha_creality_ws", "set_cfs_material", payload);
    } catch (err) {
      this._showToast(this._t("toast_save_failed", { error: err?.message || err }));
      return false;
    }

    this._showToast(this._t("toast_saved"));
    // Ask the printer to re-report so the card shows what actually landed.
    try {
      await this._hass.callService("ha_creality_ws", "request_cfs_info", {
        device_id: deviceId,
      });
    } catch (_) {
      // The write succeeded; a failed refresh only delays the display.
    }
    return true;
  }

  _attachEventHandlers() {
    // Unit selector buttons
    this._root.querySelectorAll('.unit-btn').forEach(btn => {
      btn.onclick = () => {
        const cfsIdx = parseInt(btn.dataset.cfs, 10);
        if (!isNaN(cfsIdx)) {
          this._selectedCFS = cfsIdx;
          // _selectedCFS is in the fingerprint, so go through the gate and keep
          // the snapshot consistent with what is on screen.
          this._updateIfChanged();
        }
      };
    });

    // Edit buttons. Bound before the more-info handler below, and stopping
    // propagation so clicking edit does not also open the entity dialog.
    this._root.querySelectorAll('.edit-btn, .edit-btn-mini').forEach(btn => {
      btn.onclick = (ev) => {
        ev.stopPropagation();
        // aria-disabled rather than the disabled property: the point of letting
        // the click through is to say why editing is blocked. _showEditDialog
        // re-checks all three conditions, so this is an explanation, not the
        // guard.
        if (btn.getAttribute("aria-disabled") === "true") {
          this._showToast(btn.title);
          return;
        }
        this._showEditDialog(btn.dataset.edit);
      };
    });

    // Spool cards and mini spools - show more info
    this._root.querySelectorAll('.spool-card, .spool-mini, .spool-mini-wrapper .spool-mini, .bay, .external-normal, .external-compact').forEach(el => {
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
    // Return a dynamic size based on compact mode and number of boxes
    if (this._cfg?.view_mode === "compact") {
      // Count configured boxes
      let boxCount = 0;
      for (let box = 0; box < 4; box++) {
        const hasBox = this._cfg[`box${box}_temp`] || this._cfg[`box${box}_humidity`] ||
          [0, 1, 2, 3].some(s => this._cfg[`box${box}_slot${s}_filament`] || this._cfg[`box${box}_slot${s}_color`] || this._cfg[`box${box}_slot${s}_percent`]);
        if (hasBox) boxCount++;
      }
      // Check for external filament
      const hasExternal = this._cfg.external_filament || this._cfg.external_color || this._cfg.external_percent;
      const externalRows = hasExternal ? 1 : 0;

      // Add extra space when more than 2 rows
      const extraPadding = (boxCount + externalRows) > 2 ? 1 : 0;

      return Math.max(1, boxCount + externalRows + extraPadding);
    }
    return 5;
  }

  getLayoutOptions() {
    // Count configured boxes for dynamic sizing
    let boxCount = 0;
    if (this._cfg) {
      for (let box = 0; box < 4; box++) {
        const hasBox = this._cfg[`box${box}_temp`] || this._cfg[`box${box}_humidity`] ||
          [0, 1, 2, 3].some(s => this._cfg[`box${box}_slot${s}_filament`] || this._cfg[`box${box}_slot${s}_color`] || this._cfg[`box${box}_slot${s}_percent`]);
        if (hasBox) boxCount++;
      }
    }

    // Check for external filament
    const hasExternal = this._cfg?.external_filament || this._cfg?.external_color || this._cfg?.external_percent;
    const externalRows = hasExternal ? 1 : 0;

    // Add extra space when more than 2 rows
    const totalRows = boxCount + externalRows;
    const extraPadding = totalRows > 2 ? 1 : 0;

    const minRows = this._cfg?.view_mode === "compact" ? Math.max(1, totalRows + extraPadding) : 5;

    return {
      grid_rows: minRows,
      grid_min_rows: minRows,
    };
  }
}

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

defineOnce(CARD_TAG, KCFSCard);

class KCFSCardEditor extends HTMLElement {
  // i18n helpers -------------------------------------------------------
  _resolveLanguage() {
    return _resolveLang(this._hass);
  }
  _t(key, vars) {
    return _translate(this._hass, "cfs_card", CFS_TRANSLATIONS, key, vars);
  }
  // ---------------------------------------------------------------------

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    _requestI18n(this, hass, () => { if (this._root) this._render(); });
  }

  setConfig(config) {
    this._cfg = { ...KCFSCard.getStubConfig(), ...KCFSCard._migrateConfig(config) };
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
          <div class="tab active" data-tab="entities">${this._t("tab_entities")}</div>
          <div class="tab" data-tab="theme">${this._t("tab_theme")}</div>
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
      if (s.name === "name") return this._t("label_card_title");
      if (s.name === "external_filament") return this._t("label_external_filament");
      if (s.name === "external_color") return this._t("label_external_color");
      if (s.name === "external_percent") return this._t("label_external_percent");

      const boxMatch = s.name.match(/^box(\d+)_(temp|humidity)$/);
      if (boxMatch) {
        const [, boxId, metric] = boxMatch;
        const key = metric === "temp" ? "label_box_temp" : "label_box_humidity";
        return this._t(key, { box: Number(boxId) + 1 });
      }

      const slotMatch = s.name.match(/^box(\d+)_slot(\d+)_(filament|color|percent)$/);
      if (slotMatch) {
        const [, boxId, slotId, metric] = slotMatch;
        const keyMap = {
          filament: "label_slot_filament",
          color: "label_slot_color",
          percent: "label_slot_percent",
        };
        return this._t(keyMap[metric], { box: Number(boxId) + 1, slot: Number(slotId) + 1 });
      }

      return s.name;
    };
    // Assigned unconditionally: ha-form leaves computeHelper undefined until
    // someone sets it, so guarding on it meant this never ran. Harmless here
    // only because ha-form's own default is "no helper" either way.
    this._form.computeHelper = () => "";

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
      {
        name: "view_mode",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "full", label: this._t("view_mode_full") },
              { value: "compact", label: this._t("view_mode_compact") },
              { value: "box", label: this._t("view_mode_box") },
            ],
          },
        },
      },
      { name: "show_type_in_mini", selector: { boolean: {} } },
    ];
    themeForm.computeLabel = (s) => ({
      view_mode: this._t("schema_view_mode"),
      show_type_in_mini: this._t("schema_show_type_in_mini"),
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

defineOnce(EDITOR_TAG, KCFSCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "k-cfs-card",
  name: "Creality CFS Card",
  preview: true,
  description: "A card to control the Creality Filament System (CFS)"
});
