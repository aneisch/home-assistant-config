class BigNumberCard extends HTMLElement {
  _DEFAULT_STYLE = 'var(--label-badge-blue)';
  _DEFAULT_COLOR = 'var(--primary-text-color)';
  
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }
  setConfig(config) {
    if (!config.entity) {
      throw new Error('Please define an entity');
    }

    const root = this.shadowRoot;
    if (root.lastChild) root.removeChild(root.lastChild);
    const cardConfig = Object.assign({}, config);
    if (!cardConfig.scale) cardConfig.scale = "50px";
    if (!cardConfig.from) cardConfig.from = "left";
    if (!cardConfig.noneString) cardConfig.nonestring = null;
    if (!cardConfig.noneCardClass) cardConfig.noneCardClass = null;
    if (!cardConfig.noneValueClass) cardConfig.noneValueClass = null;
    this.isNoneConfig = Boolean(cardConfig.noneString || cardConfig.noneCardClass || cardConfig.noneValueClass)

    const card = document.createElement('ha-card');
    const content = document.createElement('div');
    content.id = "value"
    const title = document.createElement('div');
    title.id = "title"
    title.textContent = cardConfig.title;
    const style = document.createElement('style');
    style.textContent = `
      ha-card {
        text-align: center;
        --bignumber-color: ${this._getColor(null, cardConfig)};
        --bignumber-fill-color: ${this._getStyle(null, cardConfig)};
        --bignumber-percent: 100%;
        --bignumber-direction: ${cardConfig.from};
        --base-unit: ${cardConfig.scale};
        padding: calc(var(--base-unit)*0.6) calc(var(--base-unit)*0.3);
        background: linear-gradient(to var(--bignumber-direction), var(--card-background-color) var(--bignumber-percent), var(--bignumber-fill-color) var(--bignumber-percent));
      }
      #value {
        font-size: calc(var(--base-unit) * 1.3);
        line-height: calc(var(--base-unit) * 1.3);
        color: var(--bignumber-color);
      }
      #value small{opacity: 0.5}
      #title {
        font-size: calc(var(--base-unit) * 0.5);
        line-height: calc(var(--base-unit) * 0.5);
        color: var(--bignumber-color);
      }
    `;
    card.appendChild(content);
    card.appendChild(title);
    card.appendChild(style);
    card.addEventListener('click', event => {
      this._fire('hass-more-info', { entityId: cardConfig.entity });
    });
    root.appendChild(card);
    this._config = cardConfig;
  }

  _fire(type, detail, options) {
    const node = this.shadowRoot;
    options = options || {};
    detail = (detail === null || detail === undefined) ? {} : detail;
    const event = new Event(type, {
      bubbles: options.bubbles === undefined ? true : options.bubbles,
      cancelable: Boolean(options.cancelable),
      composed: options.composed === undefined ? true : options.composed
    });
    event.detail = detail;
    node.dispatchEvent(event);
    return event;
  }

  _computeSeverity(stateValue, sections) {
    if (stateValue === undefined || stateValue === null) return;
    const numberValue = Number(stateValue);
    for (const section of sections) {
      if (numberValue <= section.value) return section;
    }
  }

  _getColor(entityState, config) {
    if (config.severity) {
      const severity = this._computeSeverity(entityState, config.severity);
      if (severity && severity.color) return severity.color;
    }
    if (config.color) return config.color;
    return this._DEFAULT_COLOR;
  }

  _getStyle(entityState, config) {
    if (config.severity) {
      const severity = this._computeSeverity(entityState, config.severity);
      if (severity && severity.bnStyle) return severity.bnStyle;
    }
    if (config.bnStyle) return config.bnStyle;
    return this._DEFAULT_STYLE;
  }

  _translatePercent(value, min, max) {
    return 100-100 * (value - min) / (max - min);
  }

  set hass(hass) {
    const config = this._config;
    const root = this.shadowRoot;
    const entityState = config.attribute 
      ? hass.states[config.entity].attributes[config.attribute] 
      : hass.states[config.entity].state;
    const measurement = hass.states[config.entity].attributes.unit_of_measurement || "";

    if (entityState !== this._entityState) {
      if (config.min !== undefined && config.max !== undefined) {
        root.querySelector("ha-card").style.setProperty('--bignumber-percent', `${this._translatePercent(entityState, config.min, config.max)}%`);
      }
      root.querySelector("ha-card").style.setProperty('--bignumber-fill-color', `${this._getStyle(entityState, config)}`);
      root.querySelector("ha-card").style.setProperty('--bignumber-color', `${this._getColor(entityState, config)}`);
      this._entityState = entityState
      let value = (config.round == null ? entityState : parseFloat(entityState).toFixed(config.round)) 
      if (config.hideunit==true) 
        { root.getElementById("value").textContent = `${value}`; }
      else 
        { root.getElementById("value").innerHTML = `${value}<small>${measurement}</small>`; }
      if (this.isNoneConfig){
        if (isNaN(value)) {
          if (config.noneString) {
            root.getElementById("value").textContent = config.noneString;
          }
          if (config.noneCardClass) {
            root.querySelector("ha-card").classList.add(config.noneCardClass)
          }
          if (config.noneValueClass) {
            root.getElementById("value").classList.add(config.noneValueClass)
          }
        } else {
          root.querySelector("ha-card").classList.remove(config.noneCardClass)
          root.getElementById("value").classList.remove(config.noneValueClass)
        }
      }  
    }
    root.lastChild.hass = hass;
  }

  getCardSize() {
    return 1;
  }
}

customElements.define('bignumber-card', BigNumberCard);

// Configure the preview in the Lovelace card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'bignumber-card',
  name: 'Big number card',
  preview: false,
  description: 'A simple card to display big numbers for sensors. It also supports severity levels as background.'
});
