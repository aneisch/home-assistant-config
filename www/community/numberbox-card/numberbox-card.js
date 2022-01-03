((LitElement) => {

console.info('NUMBERBOX_CARD 3.3');
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;
class NumberBox extends LitElement {

constructor() {
	super();
	this.bounce = false;
	this.pending = false;
	this.rolling = false;
	this.state = 0;
}

render() {
	if(!this.stateObj){return html`<ha-card>Missing:'${this.config.entity}'</ha-card>`;}
	if( this.config.name === undefined && this.stateObj.attributes.friendly_name ){
		this.config.name=this.stateObj.attributes.friendly_name;
	}
	if( this.config.icon === undefined && this.stateObj.attributes.icon ){
		this.config.icon=this.stateObj.attributes.icon;
	}
	if( this.config.unit === undefined && this.stateObj.attributes.unit_of_measurement ){
		this.config.unit=this.stateObj.attributes.unit_of_measurement;
	}
	if(!this.config.icon_plus){this.config.icon_plus='mdi:plus';}
	if(!this.config.icon_minus){this.config.icon_minus='mdi:minus';}
	if( this.config.delay === undefined ){ this.config.delay=1000;}
	this.state=this.stateObj.state;
	if(this.config.state){this.state=this.stateObj.attributes[this.config.state];}
	if(this.config.min === undefined){ this.config.min=this.stateObj.attributes.min;}
	if(this.config.max === undefined){ this.config.max=this.stateObj.attributes.max;}
	if(this.config.step === undefined){ this.config.step=this.stateObj.attributes.step;}
	if(!this.config.service){this.config.service="set_value";}
	if(!this.config.param){this.config.param="value";}
	if(!this.config.speed){ this.config.speed=0;}


	return html`
	<ha-card class="${(!this.config.border)?'noborder':''}">
		${(this.config.icon || this.config.name) ? html`<div class="grid">
		<div class="grid-content grid-left" @click="${() => this.moreInfo('hass-more-info')}">
			${this.config.icon ? html`
				<state-badge
				.overrideIcon="${this.config.icon}"
				.stateObj=${this.stateObj}
				></state-badge>` : null }
			<div class="info">
				${this.config.name?this.config.name:''}
				${this.secondaryInfo()}
			</div>
		</div><div class="grid-content grid-right">${this.renderNum()}</div></div>` : this.renderNum() }
	</ha-card>
`;
}

secondaryInfo(){
	const s=this.config.secondary_info;
	if(!s){return;}
	const v=s.replace('-','_');
	return html`<div class="secondary"> ${(this.stateObj[v])? 
	html`<ha-relative-time
		.datetime=${new Date(this.stateObj[v])}
		.hass=${this._hass}
	></ha-relative-time>`:s}</div>`;
}

renderNum(){
	return html`
	<section class="body">
	<div class="main">
		<div class="cur-box">
		<ha-icon class="padl" 
			icon="${this.config.icon_plus}" 
			@click="${() => this.setNumb(1)}" 
			@mousedown="${() => this.Press(1)}"
			@touchstart="${() => this.Press(1)}"
			@mouseup="${() => this.Press(2)}"
			@touchend="${() => this.Press(2)}"
		>
		</ha-icon>
		<div class="cur-num-box" @click="${() => this.moreInfo('hass-more-info')}" >
			<h3 class="cur-num ${(this.pending===false)? '':'upd'}" > ${this.niceNum()} </h3>
		</div>
		<ha-icon class="padr"
			icon="${this.config.icon_minus}"
			@click="${() => this.setNumb(0)}"
			@mousedown="${() => this.Press(0)}"
			@touchstart="${() => this.Press(0)}"
			@mouseup="${() => this.Press(2)}"
			@touchend="${() => this.Press(2)}"
		>
		</ha-icon>
		</div>
	</div>
	</section>`;
}

Press(v) {
	if( this.config.speed>0 ){
		clearInterval(this.rolling);
		if(v<2){this.rolling = setInterval(() => this.setNumb(v), this.config.speed, this);}
	}
}

setNumb(c){
	let v=this.pending;
	if( v===false ){ v=Number(this.state); v=isNaN(v)?this.config.min:v;}
	let adval=c?(v + Number(this.config.step)):(v - Number(this.config.step));
	adval=Math.round(adval*1000)/1000
	if( adval <=  Number(this.config.max) && adval >= Number(this.config.min)){
		this.pending=(adval);
		if(this.config.delay){
			clearTimeout(this.bounce);
			this.bounce = setTimeout(this.publishNum, this.config.delay, this);
		}else{
			this.publishNum(this);
		}
	}
}

publishNum(dhis){
	const v=dhis.pending;
	dhis.pending=false;
	let d={entity_id: dhis.stateObj.entity_id};
	d[dhis.config.param]=v;
	dhis._hass.callService(dhis.stateObj.entity_id.split('.')[0], dhis.config.service, d);
}

niceNum(){
	let fix=0; let v=this.pending;
	if( v === false ){
		v=this.state;
		if(v=='unavailable' || ( v=='unknown' && this.config.initial === undefined ) ){return '?';}
		v=Number(v);
		if(isNaN(v) && this.config.initial !== undefined){
			v=Number(this.config.initial);
		}
	}	
	const stp=Number(this.config.step) || 1;
	if( Math.round(stp) != stp ){ fix=stp.toString().split(".")[1].length || 1;}
	fix = v.toFixed(fix);
	const u=this.config.unit;
	if( u=="time" ){
		return html`${
			Math.floor(fix/3600).toString().padStart(2,'0')
			}:${
			(Math.floor(fix/60)-Math.floor(fix/3600)*60).toString().padStart(2,'0')
			}:${
			(fix%60).toString().padStart(2,'0')
			}`
	}
	return u===false ? fix: html`${fix}<span class="cur-unit" >${u}</span>`;
}



moreInfo(type, options = {}) {
	const e = new Event(type, {
		bubbles: options.bubbles || true,
		cancelable: options.cancelable || true,
		composed: options.composed || true,
	});
	e.detail = {entityId: this.stateObj.entity_id};
	this.dispatchEvent(e);
	return e;
}

static get properties() {
	return {
		_hass: {},
		config: {},
		stateObj: {},
		bounce: {},
		rolling: {},
		pending: {},
		state: {},
	}
}

static get styles() {
	return css`
	ha-card{
		-webkit-font-smoothing:var(--paper-font-body1_-_-webkit-font-smoothing);
		font-size:var(--paper-font-body1_-_font-size);
		font-weight:var(--paper-font-body1_-_font-weight);
		line-height:var(--paper-font-body1_-_line-height);
		padding:4px 0}
	state-badge{flex:0 0 40px;}
	ha-card.noborder{padding:0 !important;margin:0 !important;
		box-shadow:none !important;border:none !important}
	.body{
		display:grid;grid-auto-flow:column;grid-auto-columns:1fr;
		place-items:center}
	.main{display:flex;flex-direction:row;align-items:center;justify-content:center}
	.cur-box{display:flex;align-items:center;justify-content:center;flex-direction:row-reverse}
	.cur-num-box{display:flex;align-items:center}
	.cur-num{
		font-size:var(--paper-font-subhead_-_font-size);
		line-height:var(--paper-font-subhead_-_line-height);
		font-weight:normal;margin:0}
	.cur-unit{font-size:80%;opacity:0.5}
	.upd{color:#f00}
	.padr,.padl{padding:8px;cursor:pointer}
	.grid {
	  display: grid;
	  grid-template-columns: repeat(2, auto);
	}
	.grid-content {
	  display: grid; align-items: center;
	}
	.grid-left {
	  cursor: pointer;
	  flex-direction: row;
	  display: flex;
      overflow: hidden;
	}
	.info{
	  margin-left: 16px;
	  margin-right: 8px;
	  text-align: left;
	  font-size: var(--paper-font-body1_-_font-size);
	  flex: 1 0 30%;
	}
	.info, .info > * {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
	}
	.grid-right .body{margin-left:auto}
	.grid-right {
	  text-align: right
	}
	.secondary{
           color:var(--secondary-text-color);
           white-space: normal;}
	`;
}

getCardSize() {
	return 1;
}

setConfig(config) {
	if (!config.entity) throw new Error('Please define an entity.');
	let c=config.entity.split('.')[0];
	if (!(config.service || c == 'input_number' || c == 'number')){
		throw new Error('Please define a number entity.');
	}
	this.config = {
		name: config.name,
		entity: config.entity,
		icon: config.icon,
		border: config.border,
		unit: config.unit,
		icon_plus: config.icon_plus,
		icon_minus: config.icon_minus,
		delay: config.delay,
		speed: config.speed,
		initial: config.initial,
		secondary_info: config.secondary_info,
		state: config.state,
		min: config.min,
		max: config.max,
		step: config.step,
		service: config.service,
		param: config.param,
	};
}

set hass(hass) {
	if (hass && this.config) {
		this.stateObj = this.config.entity in hass.states ? hass.states[this.config.entity] : null;
	}
	this._hass = hass;
}

shouldUpdate(changedProps) {
	if( changedProps.has('config') || changedProps.has('stateObj') || changedProps.has('pending') ){return true;}
}

static getConfigElement() {
    return document.createElement("numberbox-card-editor");
}

static getStubConfig() {
	return {border: true};
}

} customElements.define('numberbox-card', NumberBox);

//Editor
const includeDomains = ['input_number','number'];
const fireEvent = (node, type, detail = {}, options = {}) => {
	const event = new Event(type, {
		bubbles: options.bubbles === undefined ? true : options.bubbles,
		cancelable: Boolean(options.cancelable),
		composed: options.composed === undefined ? true : options.composed,
	});
	event.detail = detail;
	node.dispatchEvent(event);
	return event;
}

class NumberBoxEditor extends LitElement {

static get properties() {
	return { hass: {}, config: {} };
}

static get styles() {
	return css`
.side {
	display:flex;
	align-items:center;
}
.side > * {
	flex:1;
	padding-right:4px;
}	
`;
}
get _border() {
	if (this.config.border) {
		return true;
	} else {
		return false;
	}
}
setConfig(config) {
	this.config = config;
}

render() {
	if (!this.hass){ return html``; }
	return html`
<div class="side">
	<ha-entity-picker
		label="Entity (required)"
		.hass=${this.hass}
		.value="${this.config.entity}"
		.configValue=${'entity'}
		.includeDomains=${includeDomains}
		@change="${this.updVal}"
		allow-custom-entity
	></ha-entity-picker>
	<ha-formfield label="Show border?">
		<ha-switch
			.checked=${this._border}
			.configValue="${'border'}"
			@change=${this.updVal}
		></ha-switch>
	</ha-formfield>
</div>
<div class="side">
	<paper-input
		label="Secondary Info (Optional)"
		.value="${this.config.secondary_info}"
		.configValue="${'secondary_info'}"
		@value-changed="${this.updVal}"
	></paper-input>
</div>
<div class="side">
	<paper-input
		label="Name (Optional, false to hide)"
		.value="${this.config.name}"
		.configValue="${'name'}"
		@value-changed="${this.updVal}"
	></paper-input>
	<ha-icon-picker
		label="Icon (Optional, false to hide)"
		.value="${this.config.icon}"
		.configValue="${'icon'}"
		@value-changed="${this.updVal}"
	></ha-icon-picker>
</div>
<div class="side">
	<ha-icon-picker
		label="Icon Plus [mdi:plus]"
		.value="${this.config.icon_plus}"
		.configValue=${'icon_plus'}
		@value-changed=${this.updVal}
	></ha-icon-picker>
	<ha-icon-picker
		label="Icon Minus [mdi:minus]"
		.value="${this.config.icon_minus}"
		.configValue=${'icon_minus'}
		@value-changed=${this.updVal}
	></ha-icon-picker>
</div>			
<div class="side">
	<paper-input
		label="Initial [?]"
		.value="${this.config.initial}"
		.configValue=${'initial'}
		@value-changed=${this.updVal}
	></paper-input>
	<paper-input
		label="Unit (false to hide)"
		.value="${this.config.unit}"
		.configValue=${'unit'}
		@value-changed=${this.updVal}
	></paper-input>
</div>
<div class="side">
	<paper-input
		label="Update Delay [1000] ms"
		.value="${this.config.delay}"
		.configValue=${'delay'}
		@value-changed=${this.updVal}
	></paper-input>
	<paper-input
		label="Long press Speed [0] ms"
		.value="${this.config.speed}"
		.configValue=${'speed'}
		@value-changed=${this.updVal}
	></paper-input>
</div>
`;
}


updVal(v) {
	if (!this.config || !this.hass) {return;}
	const { target } = v;
	if (this[`_${target.configValue}`] === target.value) {
		return;
	}
	if (target.configValue) {
		if (target.value === '') {
			try{delete this.config[target.configValue];}catch(e){}
		} else {
		if (target.value === 'false') {target.value = false;}
			this.config = {
				...this.config,
				[target.configValue]: target.checked !== undefined ? target.checked : target.value,
			}
		}
	}
	fireEvent(this, 'config-changed', { config: this.config });
}

}
customElements.define("numberbox-card-editor", NumberBoxEditor);

})(window.LitElement || Object.getPrototypeOf(customElements.get("hui-masonry-view") ));

window.customCards = window.customCards || [];
window.customCards.push({
	type: 'numberbox-card',
	name: 'Numberbox Card',
	preview: false,
	description: 'Replace number/input_number sliders with plus and minus buttons'
});

