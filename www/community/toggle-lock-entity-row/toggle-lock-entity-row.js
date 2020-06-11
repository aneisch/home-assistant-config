class ToggleLockEntityRow extends Polymer.Element {
  static get template() {
    return Polymer.html`
    <style>
      hui-generic-entity-row {
        margin: var(--ha-themed-slider-margin, initial);
      }
      .flex {
        display: flex;
        align-items: center;
      }
      #overlay {
        position: absolute;
        left: 0;
        right: 0;
        top: 0;
        bottom: 0;
        text-align: right;
        z-index: 1;
        width: 70px;
        height: 50px;
        margin-left: -13px;
        margin-top: -4px;
      }
      #lock {
        margin-top: 13px;
        opacity: 1;
        margin-right: 22px;
        -webkit-animation-duration: 5s;animation-duration 5s;
        -webkit-animation-fill-mode: both;animation-full-mode: both;
      }
      .wrapper {
        position: relative;
      }
      @keyframes fadeOut{
        0% {opacity: 1;}
        20% {opacity: 0;}
        80% {opacity: 0;}
        100% {opacity: 1;}
      }
      .fadeOut {
        -webkit-animation-name: fadeOut;animation-name: fadeOut;
      }
      .waitColor{
        color: #00FF00;
	  }
    </style>
    <hui-generic-entity-row
      config="[[_config]]"
      hass="[[_hass]]"
      >
      <div class="wrapper">
        <div class="flex">
          <ha-entity-toggle
            state-obj="[[stateObj]]"
            hass="[[_hass]]"
          ></ha-entity-toggle>
        </div>
        <div id="overlay" on-click='clickHandler'>
          <iron-icon id="lock" icon="mdi:lock-outline"></iron-icon>
        </div>
      </div>
    </hui-generic-entity-row>
    `
  }

  setConfig(config)
  {
    this._config = config;
    this.users = null;
    this.unlockdelay = 0;
    this.relockdelay = 5;
    this.unlockcolor = '#000000';

    if(config.users) {
      this.users = config.users;
    }
    if(config.unlockdelay) {
      this.unlockdelay = config.unlockdelay;
    }
    if(config.relockdelay) {
      this.relockdelay = config.relockdelay;
    }
    this.unlockdelay *= 1000;
    this.relockdelay *= 1000;
  }

  set hass(hass) {
    this._hass = hass;
    this.stateObj = this._config.entity in hass.states ? hass.states[this._config.entity] : null;
  }

  clickHandler(e) {
    e.stopPropagation();
    if(this.users) {
      if(! document.querySelector("home-assistant").hass.user) return;
      let user = document.querySelector("home-assistant").hass.user.name;
      if(this.users.indexOf(user) < 0) return;
    }

    const lock = this.$.lock;
    if(lock) {
      lock.classList.add('waitColor');
      document.getElementsByClassName('waitColor').color = this.waitColor;
      window.setTimeout(() => {
        this.$.overlay.style.pointerEvents = 'none';
        lock.icon = 'mdi:lock-open-outline';
        lock.classList.add('fadeOut');
        lock.classList.remove('waitColor');
      }, this.unlockdelay);
    }
	
    window.setTimeout(() => {
      this.$.overlay.style.pointerEvents = '';
      if(lock) {
        lock.classList.remove('fadeOut');
        lock.icon = 'mdi:lock-outline';
      }
    }, (this.unlockdelay+this.relockdelay));
  }
}

customElements.define('toggle-lock-entity-row', ToggleLockEntityRow);
