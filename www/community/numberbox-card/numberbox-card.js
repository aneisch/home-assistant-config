((LitElement) => {

console.info('NUMBERBOX_CARD 4.8');
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;
class NumberBox extends LitElement {

constructor() {
	super();
	this.bounce = false;
	this.pending = false;
	this.rolling = false;
	this.state = 0;
	this.old = {state: undefined, t:{}, h:''};
}

render() {
	if(!this.stateObj){return html`<ha-card>Missing:'${this.config.entity}'</ha-card>`;}
	
	const k={name:'friendly_name',icon:'icon',picture:'entity_picture',unit:'unit_of_measurement'};
	for(const n of Object.keys(k)) {
		if( this.config[n] === undefined && this.stateObj.attributes[k[n]] ){
			this.config[n]=this.stateObj.attributes[k[n]];
		}
	}

	const d={min:0,max:9e9,step:1,toggle:null};
	for(const j of Object.keys(d)) {
		const b=j+'_entity';
		if(b in this.config && this.config[b] in this._hass.states ) {
			const c=this._hass.states[this.config[b]]; this.old.t[this.config[b]]=c.last_updated
			if( d[j]!==null && !isNaN(parseFloat(c.state)) ){this.config[j]=c.state;}
			if(j=='toggle'){this.config[j]=c;}
		}
		if(d[j]!==null){
			if(this.config[j] === undefined){ this.config[j]=this.stateObj.attributes[j];}
			if(isNaN(parseFloat(this.config[j]))){this.config[j]=d[j];}
		}
	}

	return html`
	<ha-card class="${(!this.config.border)?'noborder':''}">
		${(this.config.icon || this.config.picture || this.config.name) ? html`<div class="${this.config.toggle?'gridt':'grid'}">
		<div class="grid-content grid-left" @click="${() => this.moreInfo()}">
			${this.config.picture ? html`
				<state-badge
				.overrideImage="${this.config.picture}"
				></state-badge>` : this.config.icon ? html`
				<state-badge
				.overrideIcon="${this.config.icon}"
				.stateObj=${this.stateObj}
				></state-badge>` : null }
			<div class="info">
				${this.config.name?this.config.name:''}
				${this.secondaryInfo()}
			</div>
		</div><div class="grid-content grid-right">${this.renderNum()}</div>
		${this.config.toggle ? html`<div class="grid-content grid-right"><ha-entity-toggle .stateObj="${this.config.toggle}"
		.hass="${this._hass}"></ha-entity-toggle></div>` : null }
		</div>` : this.renderNum() }
	</ha-card>
`;
}

updated(x) {
	if(this.old.h !=''){
		const a=this.renderRoot.querySelector('.secondary');
		if(a){a.innerHTML=this.old.h;}
	}
}


secondaryInfo(){
	const s=this.config.secondary_info;
	if(!s){return;}
	let r=s;
	let h=s;
	if(s.indexOf('%')> -1){
		const j=s.split(' ');
		for (let i in j) {
			if(j[i][0]=='%'){
				j[i]=j[i].substring(1).split(':');
				let b=this._hass.states;
				for (let d=0; d<j[i].length; d++){
					if(b.hasOwnProperty(j[i][d])){
						b=b[ j[i][d] ];
						if(!d){
							this.old.t[ j[i][d] ]=b.last_updated;
						}
					}
				}
				if( b !== Object(b) ){ j[i]=b;}
			}
		}
		r = j.join(' ');
		
	}else{
		const v=s.replace('-','_');
		if(this.stateObj[v]){
			h='';
			r=html`<ha-relative-time .datetime=${new Date(this.stateObj[v])}
						.hass=${this._hass} ></ha-relative-time>`;
		}
	}
	if(h){h=r; r='';}
	this.old.h=h;
	return html`<div class="secondary">${r}</div>`;
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
		<div class="cur-num-box" @click="${() => this.moreInfo()}" >
			<h3 class="cur-num ${(this.pending===false)? '':'upd'}"> ${this.niceNum()} </h3>
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

timeNum(x,s,m){
	x=x+'';
	if(x.indexOf(':')>0){
		x = x.split(':');s = 0; m = 1;
		while (x.length > 0) {
			s += m * parseInt(x.pop(), 10);
			m *= 60;
		}
		x=s;
	}
	return Number(x);
}

numTime(x,f,t,u){
	if(t=="timehm"){u=1;f=1;}
	x=Math.round(x);
	t = (x>=3600 || f)? Math.floor(x/3600).toString().padStart(2,'0') + ':' : '';
	t += (Math.floor(x/60)-Math.floor(x/3600)*60).toString().padStart(2,'0');
	if( !u ){
		t += ':' + Math.round(x%60).toString().padStart(2,'0');
	}
	return t;
}

setNumb(c){
	let v=this.pending;
	if( v===false ){ v=this.timeNum(this.state); v=isNaN(v)?this.config.min:v;}
	let adval=c?(v + Number(this.config.step)):(v - Number(this.config.step));
	adval=Math.round(adval*1e9)/1e9;
	if(adval==this.state){
		clearTimeout(this.bounce);this.pending=false;
	}else{
		if(adval <= Number(this.config.max) && adval >= Number(this.config.min)){
			this.pending = adval;
			if(this.config.delay){
				clearTimeout(this.bounce);
				this.bounce = setTimeout(this.publishNum, this.config.delay, this);
			}else{
				this.publishNum(this);
			}
		}
	}
}

publishNum(dhis){
	if(dhis.pending===false){return;}
	const s=dhis.config.service.split('.');
	if(s[0]=='input_datetime'){dhis.pending=dhis.numTime(dhis.pending,1);}
	const v={entity_id: dhis.config.entity, [dhis.config.param]: dhis.pending};
	dhis.pending=false;
	dhis.old.state=dhis.state;
	dhis._hass.callService(s[0], s[1], v);
}

niceNum(){
	let fix=0; let v=this.pending;
	if( v === false ){
		v=this.state;
		if(v=='unavailable' || ( v=='unknown' && this.config.initial === undefined ) ){return '?';}
		v=this.timeNum(v);
		if(isNaN(v) && this.config.initial !== undefined){
			v=Number(this.config.initial);
			if(isNaN(v)){return this.config.initial;}
		}
	}	
	let stp=Number(this.config.step) || 1;
	if( Math.round(stp) != stp ){
		fix=stp.toString().split(".")[1].length || 1; stp=fix;
	}else{ stp=fix; }
	fix = v.toFixed(fix);
	const u=this.config.unit;
	if( u=="time" || u=="timehm"){
		let t = this.numTime(fix,0,u);
		return html`${t}`;
	}
	if(isNaN(Number(fix))){return fix;}
	const lang={language:this._hass.language, comma_decimal:['en-US','en'], decimal_comma:['de','es','it'], space_comma:['fr','sv','cs'], system:undefined};
	let g=this._hass.locale.number_format || 'language';
	if(g!='none'){
		g=lang.hasOwnProperty(g)? lang[g] : lang.language;
		fix = new Intl.NumberFormat(g, {maximumFractionDigits: stp, minimumFractionDigits: stp}).format(Number(fix));
	}
	return u===false ? fix: html`${fix}<span class="cur-unit">${u}</span>`;
}



moreInfo() {
	if(!this.config.moreinfo){return;}
	const e = new Event('hass-more-info', {bubbles: true, cancelable: true, composed: true});
	e.detail = {entityId: this.config.moreinfo};
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
		old: {},
	};
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
	.gridt {
		display: grid;
		grid-template-columns: repeat(3, auto);
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
	const c=config.entity.split('.')[0];
	if (!(config.service || c == 'input_number' || c == 'number')){
		throw new Error('Please define a number entity.');
	}
	this.config = {
		icon_plus: "mdi:plus",
		icon_minus: "mdi:minus",
		service: c + ".set_value",
		param: "value",
		delay: 1000,
		speed: 0,
		refresh: 0,
		initial: undefined,
		moreinfo: config.entity,
		...config
	};
	if(this.config.service.split('.').length < 2){
		this.config.service=c +'.'+this.config.service;
	}
}

set hass(hass) {
	if (hass && this.config) {
		this.stateObj = this.config.entity in hass.states ? hass.states[this.config.entity] : null;
	}
	this._hass = hass;
	if(this.stateObj){
		this.state=this.stateObj.state;
		if(this.config.state){this.state=this.stateObj.attributes[this.config.state];}
	}
}

shouldUpdate(changedProps) {
	const o = this.old.t;
	for(const p in o){if(p in this._hass.states && this._hass.states[p].last_updated != o[p]){ return true; }}
	if( changedProps.has('config') || changedProps.has('stateObj') || changedProps.has('pending') ){
		if(this.old.state != this.state || this.config.refresh){ return true; }
	}
}

static getConfigElement() {
	return document.createElement("numberbox-card-editor");
}

static getStubConfig() {
	return {border: true};
}

} customElements.define('numberbox-card', NumberBox);

//Editor
const fireEvent = (node, type, detail = {}, options = {}) => {
	const event = new Event(type, {
		bubbles: options.bubbles === undefined ? true : options.bubbles,
		cancelable: Boolean(options.cancelable),
		composed: options.composed === undefined ? true : options.composed,
	});
	event.detail = detail;
	node.dispatchEvent(event);
	return event;
};

class NumberBoxEditor extends LitElement {

async Pick(){
	const c="ha-entity-picker";
	if(!customElements.get(c)){
		const r = "partial-panel-resolver";
		await customElements.whenDefined(r);
		const p = document.createElement(r);
		p.hass = {panels: [{url_path: "tmp", component_name: "config"}]};
		p._updateRoutes();
		await p.routerOptions.routes.tmp.load();
		const d=document.createElement("ha-panel-config");
		await d.routerOptions.routes.automation.load();
	}
	const a=document.createElement(c);
	this.render();
}
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
	this.Pick();
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
		.includeDomains=${['input_number','number']}
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
	<ha-textfield
		label="Name (Optional, false to hide)"
		.value="${(this.config.name!==undefined)?this.config.name:''}"
		.configValue="${'name'}"
		@input="${this.updVal}"
	></ha-textfield>
	<ha-icon-picker
		label="Icon (Optional, false to hide)"
		.value="${(this.config.icon!==undefined)?this.config.icon:''}"
		.configValue="${'icon'}"
		@value-changed="${this.updVal}"
	></ha-icon-picker>
</div>
<div class="side">
	<ha-textfield
		label="Secondary Info (Optional)"
		.value="${(this.config.secondary_info!==undefined)?this.config.secondary_info:''}"
		.configValue="${'secondary_info'}"
		@input="${this.updVal}"
	></ha-textfield>
</div>
<div class="side">
	<ha-textfield
		label="Picture url(Optional, false to hide)"
		.value="${(this.config.picture!==undefined)?this.config.picture:''}"
		.configValue="${'picture'}"
		@input="${this.updVal}"
	></ha-textfield>
</div><div class="side">
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
	<ha-textfield
		label="Initial [?]"
		.value="${(this.config.initial!==undefined)?this.config.initial:''}"
		.configValue=${'initial'}
		@input=${this.updVal}
		type="number"
		step="any"
	></ha-textfield>
	<ha-textfield
		label="Unit (false to hide)"
		.value="${(this.config.unit!==undefined)?this.config.unit:''}"
		.configValue=${'unit'}
		@input=${this.updVal}
	></ha-textfield>
</div>
<div class="side">
	<ha-textfield
		label="Update Delay [1000] ms"
		.value="${(this.config.delay!==undefined)?this.config.delay:''}"
		.configValue=${'delay'}
		@input=${this.updVal}
		type="number"
	></ha-textfield>
	<ha-textfield
		label="Long press Speed [0] ms"
		.value="${(this.config.speed!==undefined)?this.config.speed:''}"
		.configValue=${'speed'}
		@input=${this.updVal}
		type="number"
	></ha-textfield>
</div>
<div><b>Advanced Config</b> <a target="_blank" href="https://github.com/htmltiger/numberbox-card#configuration">more info</a></div>
<div class="side">
	<ha-textfield
		label="min"
		.value="${(this.config.min!==undefined)?this.config.min:''}"
		.configValue="${'min'}"
		@input="${this.updVal}"
		type="number"
		step="any"
	></ha-textfield>
	<ha-textfield
		label="max"
		.value="${(this.config.max!==undefined)?this.config.max:''}"
		.configValue="${'max'}"
		@input="${this.updVal}"
		type="number"
		step="any"
	></ha-textfield>
	<ha-textfield
		label="step"
		.value="${(this.config.step!==undefined)?this.config.step:''}"
		.configValue="${'step'}"
		@input="${this.updVal}"
		type="number"
		step="any"
	></ha-textfield>
</div>
<div class="side">
	<ha-entity-picker
		label="min_entity"
		.hass=${this.hass}
		.value="${this.config.min_entity}"
		.configValue=${'min_entity'}
		@change="${this.updVal}"
		allow-custom-entity
	></ha-entity-picker>
	<ha-entity-picker
		label="max_entity"
		.hass=${this.hass}
		.value="${this.config.max_entity}"
		.configValue=${'max_entity'}
		@change="${this.updVal}"
		allow-custom-entity
	></ha-entity-picker>
</div>
<div class="side">
	<ha-entity-picker
		label="step_entity"
		.hass=${this.hass}
		.value="${this.config.step_entity}"
		.configValue=${'step_entity'}
		@change="${this.updVal}"
		allow-custom-entity
	></ha-entity-picker>
	<ha-entity-picker
		label="toggle_entity"
		.hass=${this.hass}
		.value="${this.config.toggle_entity}"
		.configValue=${'toggle_entity'}
		@change="${this.updVal}"
		allow-custom-entity
	></ha-entity-picker>
</div>
<div class="side">
	<ha-entity-picker
		label="moreinfo"
		.hass=${this.hass}
		.value="${this.config.moreinfo}"
		.configValue=${'moreinfo'}
		@change="${this.updVal}"
		allow-custom-entity
	></ha-entity-picker>
</div>
<div class="side">
	<ha-textfield
		label="service"
		.value="${(this.config.service!==undefined)?this.config.service:''}"
		.configValue="${'service'}"
		@input="${this.updVal}"
	></ha-textfield>
	<ha-textfield
		label="param"
		.value="${(this.config.param!==undefined)?this.config.param:''}"
		.configValue="${'param'}"
		@input="${this.updVal}"
	></ha-textfield>
	<ha-textfield
		label="state"
		.value="${(this.config.state!==undefined)?this.config.state:''}"
		.configValue="${'state'}"
		@input="${this.updVal}"
	></ha-textfield>
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
			const reg = new RegExp(/^-?\d*\.?\d+$/);
			if (target.value === 'false') {
				target.value = false;
			}else if(reg.test(target.value)){
				target.value=Number(target.value);
			}
			this.config = {
				...this.config,
				[target.configValue]: target.checked !== undefined ? target.checked : target.value,
			};
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
