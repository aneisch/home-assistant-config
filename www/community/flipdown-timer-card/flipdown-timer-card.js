/*! *****************************************************************************
Copyright (c) Microsoft Corporation.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
***************************************************************************** */
function t(t,e,o,i){var r,n=arguments.length,s=n<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,o):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)s=Reflect.decorate(t,e,o,i);else for(var a=t.length-1;a>=0;a--)(r=t[a])&&(s=(n<3?r(s):n>3?r(e,o,s):r(e,o))||s);return n>3&&s&&Object.defineProperty(e,o,s),s
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */}const e=window.ShadowRoot&&(void 0===window.ShadyCSS||window.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,o=Symbol(),i=new Map;class r{constructor(t,e){if(this._$cssResult$=!0,e!==o)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t}get styleSheet(){let t=i.get(this.cssText);return e&&void 0===t&&(i.set(this.cssText,t=new CSSStyleSheet),t.replaceSync(this.cssText)),t}toString(){return this.cssText}}const n=t=>new r("string"==typeof t?t:t+"",o),s=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,o,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+t[i+1],t[0]);return new r(i,o)},a=(t,o)=>{e?t.adoptedStyleSheets=o.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet):o.forEach(e=>{const o=document.createElement("style"),i=window.litNonce;void 0!==i&&o.setAttribute("nonce",i),o.textContent=e.cssText,t.appendChild(o)})},l=e?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const o of t.cssRules)e+=o.cssText;return n(e)})(t):t
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */;var h;const d=window.trustedTypes,c=d?d.emptyScript:"",u=window.reactiveElementPolyfillSupport,p={toAttribute(t,e){switch(e){case Boolean:t=t?c:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let o=t;switch(e){case Boolean:o=null!==t;break;case Number:o=null===t?null:Number(t);break;case Object:case Array:try{o=JSON.parse(t)}catch(t){o=null}}return o}},f=(t,e)=>e!==t&&(e==e||t==t),g={attribute:!0,type:String,converter:p,reflect:!1,hasChanged:f};class m extends HTMLElement{constructor(){super(),this._$Et=new Map,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Ei=null,this.o()}static addInitializer(t){var e;null!==(e=this.l)&&void 0!==e||(this.l=[]),this.l.push(t)}static get observedAttributes(){this.finalize();const t=[];return this.elementProperties.forEach((e,o)=>{const i=this._$Eh(o,e);void 0!==i&&(this._$Eu.set(i,o),t.push(i))}),t}static createProperty(t,e=g){if(e.state&&(e.attribute=!1),this.finalize(),this.elementProperties.set(t,e),!e.noAccessor&&!this.prototype.hasOwnProperty(t)){const o="symbol"==typeof t?Symbol():"__"+t,i=this.getPropertyDescriptor(t,o,e);void 0!==i&&Object.defineProperty(this.prototype,t,i)}}static getPropertyDescriptor(t,e,o){return{get(){return this[e]},set(i){const r=this[t];this[e]=i,this.requestUpdate(t,r,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)||g}static finalize(){if(this.hasOwnProperty("finalized"))return!1;this.finalized=!0;const t=Object.getPrototypeOf(this);if(t.finalize(),this.elementProperties=new Map(t.elementProperties),this._$Eu=new Map,this.hasOwnProperty("properties")){const t=this.properties,e=[...Object.getOwnPropertyNames(t),...Object.getOwnPropertySymbols(t)];for(const o of e)this.createProperty(o,t[o])}return this.elementStyles=this.finalizeStyles(this.styles),!0}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const o=new Set(t.flat(1/0).reverse());for(const t of o)e.unshift(l(t))}else void 0!==t&&e.push(l(t));return e}static _$Eh(t,e){const o=e.attribute;return!1===o?void 0:"string"==typeof o?o:"string"==typeof t?t.toLowerCase():void 0}o(){var t;this._$Ep=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$Em(),this.requestUpdate(),null===(t=this.constructor.l)||void 0===t||t.forEach(t=>t(this))}addController(t){var e,o;(null!==(e=this._$Eg)&&void 0!==e?e:this._$Eg=[]).push(t),void 0!==this.renderRoot&&this.isConnected&&(null===(o=t.hostConnected)||void 0===o||o.call(t))}removeController(t){var e;null===(e=this._$Eg)||void 0===e||e.splice(this._$Eg.indexOf(t)>>>0,1)}_$Em(){this.constructor.elementProperties.forEach((t,e)=>{this.hasOwnProperty(e)&&(this._$Et.set(e,this[e]),delete this[e])})}createRenderRoot(){var t;const e=null!==(t=this.shadowRoot)&&void 0!==t?t:this.attachShadow(this.constructor.shadowRootOptions);return a(e,this.constructor.elementStyles),e}connectedCallback(){var t;void 0===this.renderRoot&&(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),null===(t=this._$Eg)||void 0===t||t.forEach(t=>{var e;return null===(e=t.hostConnected)||void 0===e?void 0:e.call(t)})}enableUpdating(t){}disconnectedCallback(){var t;null===(t=this._$Eg)||void 0===t||t.forEach(t=>{var e;return null===(e=t.hostDisconnected)||void 0===e?void 0:e.call(t)})}attributeChangedCallback(t,e,o){this._$AK(t,o)}_$ES(t,e,o=g){var i,r;const n=this.constructor._$Eh(t,o);if(void 0!==n&&!0===o.reflect){const s=(null!==(r=null===(i=o.converter)||void 0===i?void 0:i.toAttribute)&&void 0!==r?r:p.toAttribute)(e,o.type);this._$Ei=t,null==s?this.removeAttribute(n):this.setAttribute(n,s),this._$Ei=null}}_$AK(t,e){var o,i,r;const n=this.constructor,s=n._$Eu.get(t);if(void 0!==s&&this._$Ei!==s){const t=n.getPropertyOptions(s),a=t.converter,l=null!==(r=null!==(i=null===(o=a)||void 0===o?void 0:o.fromAttribute)&&void 0!==i?i:"function"==typeof a?a:null)&&void 0!==r?r:p.fromAttribute;this._$Ei=s,this[s]=l(e,t.type),this._$Ei=null}}requestUpdate(t,e,o){let i=!0;void 0!==t&&(((o=o||this.constructor.getPropertyOptions(t)).hasChanged||f)(this[t],e)?(this._$AL.has(t)||this._$AL.set(t,e),!0===o.reflect&&this._$Ei!==t&&(void 0===this._$E_&&(this._$E_=new Map),this._$E_.set(t,o))):i=!1),!this.isUpdatePending&&i&&(this._$Ep=this._$EC())}async _$EC(){this.isUpdatePending=!0;try{await this._$Ep}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var t;if(!this.isUpdatePending)return;this.hasUpdated,this._$Et&&(this._$Et.forEach((t,e)=>this[e]=t),this._$Et=void 0);let e=!1;const o=this._$AL;try{e=this.shouldUpdate(o),e?(this.willUpdate(o),null===(t=this._$Eg)||void 0===t||t.forEach(t=>{var e;return null===(e=t.hostUpdate)||void 0===e?void 0:e.call(t)}),this.update(o)):this._$EU()}catch(t){throw e=!1,this._$EU(),t}e&&this._$AE(o)}willUpdate(t){}_$AE(t){var e;null===(e=this._$Eg)||void 0===e||e.forEach(t=>{var e;return null===(e=t.hostUpdated)||void 0===e?void 0:e.call(t)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EU(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$Ep}shouldUpdate(t){return!0}update(t){void 0!==this._$E_&&(this._$E_.forEach((t,e)=>this._$ES(e,this[e],t)),this._$E_=void 0),this._$EU()}updated(t){}firstUpdated(t){}}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var _;m.finalized=!0,m.elementProperties=new Map,m.elementStyles=[],m.shadowRootOptions={mode:"open"},null==u||u({ReactiveElement:m}),(null!==(h=globalThis.reactiveElementVersions)&&void 0!==h?h:globalThis.reactiveElementVersions=[]).push("1.0.2");const v=globalThis.trustedTypes,w=v?v.createPolicy("lit-html",{createHTML:t=>t}):void 0,b=`lit$${(Math.random()+"").slice(9)}$`,y="?"+b,$=`<${y}>`,x=document,S=(t="")=>x.createComment(t),A=t=>null===t||"object"!=typeof t&&"function"!=typeof t,k=Array.isArray,E=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,C=/-->/g,M=/>/g,N=/>|[ 	\n\r](?:([^\s"'>=/]+)([ 	\n\r]*=[ 	\n\r]*(?:[^ 	\n\r"'`<>=]|("|')|))|$)/g,T=/'/g,H=/"/g,R=/^(?:script|style|textarea)$/i,D=(t=>(e,...o)=>({_$litType$:t,strings:e,values:o}))(1),O=Symbol.for("lit-noChange"),P=Symbol.for("lit-nothing"),L=new WeakMap,U=x.createTreeWalker(x,129,null,!1),B=(t,e)=>{const o=t.length-1,i=[];let r,n=2===e?"<svg>":"",s=E;for(let e=0;e<o;e++){const o=t[e];let a,l,h=-1,d=0;for(;d<o.length&&(s.lastIndex=d,l=s.exec(o),null!==l);)d=s.lastIndex,s===E?"!--"===l[1]?s=C:void 0!==l[1]?s=M:void 0!==l[2]?(R.test(l[2])&&(r=RegExp("</"+l[2],"g")),s=N):void 0!==l[3]&&(s=N):s===N?">"===l[0]?(s=null!=r?r:E,h=-1):void 0===l[1]?h=-2:(h=s.lastIndex-l[2].length,a=l[1],s=void 0===l[3]?N:'"'===l[3]?H:T):s===H||s===T?s=N:s===C||s===M?s=E:(s=N,r=void 0);const c=s===N&&t[e+1].startsWith("/>")?" ":"";n+=s===E?o+$:h>=0?(i.push(a),o.slice(0,h)+"$lit$"+o.slice(h)+b+c):o+b+(-2===h?(i.push(void 0),e):c)}const a=n+(t[o]||"<?>")+(2===e?"</svg>":"");return[void 0!==w?w.createHTML(a):a,i]};class V{constructor({strings:t,_$litType$:e},o){let i;this.parts=[];let r=0,n=0;const s=t.length-1,a=this.parts,[l,h]=B(t,e);if(this.el=V.createElement(l,o),U.currentNode=this.el.content,2===e){const t=this.el.content,e=t.firstChild;e.remove(),t.append(...e.childNodes)}for(;null!==(i=U.nextNode())&&a.length<s;){if(1===i.nodeType){if(i.hasAttributes()){const t=[];for(const e of i.getAttributeNames())if(e.endsWith("$lit$")||e.startsWith(b)){const o=h[n++];if(t.push(e),void 0!==o){const t=i.getAttribute(o.toLowerCase()+"$lit$").split(b),e=/([.?@])?(.*)/.exec(o);a.push({type:1,index:r,name:e[2],strings:t,ctor:"."===e[1]?j:"?"===e[1]?W:"@"===e[1]?Z:I})}else a.push({type:6,index:r})}for(const e of t)i.removeAttribute(e)}if(R.test(i.tagName)){const t=i.textContent.split(b),e=t.length-1;if(e>0){i.textContent=v?v.emptyScript:"";for(let o=0;o<e;o++)i.append(t[o],S()),U.nextNode(),a.push({type:2,index:++r});i.append(t[e],S())}}}else if(8===i.nodeType)if(i.data===y)a.push({type:2,index:r});else{let t=-1;for(;-1!==(t=i.data.indexOf(b,t+1));)a.push({type:7,index:r}),t+=b.length-1}r++}}static createElement(t,e){const o=x.createElement("template");return o.innerHTML=t,o}}function z(t,e,o=t,i){var r,n,s,a;if(e===O)return e;let l=void 0!==i?null===(r=o._$Cl)||void 0===r?void 0:r[i]:o._$Cu;const h=A(e)?void 0:e._$litDirective$;return(null==l?void 0:l.constructor)!==h&&(null===(n=null==l?void 0:l._$AO)||void 0===n||n.call(l,!1),void 0===h?l=void 0:(l=new h(t),l._$AT(t,o,i)),void 0!==i?(null!==(s=(a=o)._$Cl)&&void 0!==s?s:a._$Cl=[])[i]=l:o._$Cu=l),void 0!==l&&(e=z(t,l._$AS(t,e.values),l,i)),e}class Y{constructor(t,e){this.v=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}p(t){var e;const{el:{content:o},parts:i}=this._$AD,r=(null!==(e=null==t?void 0:t.creationScope)&&void 0!==e?e:x).importNode(o,!0);U.currentNode=r;let n=U.nextNode(),s=0,a=0,l=i[0];for(;void 0!==l;){if(s===l.index){let e;2===l.type?e=new q(n,n.nextSibling,this,t):1===l.type?e=new l.ctor(n,l.name,l.strings,this,t):6===l.type&&(e=new G(n,this,t)),this.v.push(e),l=i[++a]}s!==(null==l?void 0:l.index)&&(n=U.nextNode(),s++)}return r}m(t){let e=0;for(const o of this.v)void 0!==o&&(void 0!==o.strings?(o._$AI(t,o,e),e+=o.strings.length-2):o._$AI(t[e])),e++}}class q{constructor(t,e,o,i){var r;this.type=2,this._$AH=P,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=o,this.options=i,this._$Cg=null===(r=null==i?void 0:i.isConnected)||void 0===r||r}get _$AU(){var t,e;return null!==(e=null===(t=this._$AM)||void 0===t?void 0:t._$AU)&&void 0!==e?e:this._$Cg}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=z(this,t,e),A(t)?t===P||null==t||""===t?(this._$AH!==P&&this._$AR(),this._$AH=P):t!==this._$AH&&t!==O&&this.$(t):void 0!==t._$litType$?this.T(t):void 0!==t.nodeType?this.S(t):(t=>{var e;return k(t)||"function"==typeof(null===(e=t)||void 0===e?void 0:e[Symbol.iterator])})(t)?this.M(t):this.$(t)}A(t,e=this._$AB){return this._$AA.parentNode.insertBefore(t,e)}S(t){this._$AH!==t&&(this._$AR(),this._$AH=this.A(t))}$(t){this._$AH!==P&&A(this._$AH)?this._$AA.nextSibling.data=t:this.S(x.createTextNode(t)),this._$AH=t}T(t){var e;const{values:o,_$litType$:i}=t,r="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=V.createElement(i.h,this.options)),i);if((null===(e=this._$AH)||void 0===e?void 0:e._$AD)===r)this._$AH.m(o);else{const t=new Y(r,this),e=t.p(this.options);t.m(o),this.S(e),this._$AH=t}}_$AC(t){let e=L.get(t.strings);return void 0===e&&L.set(t.strings,e=new V(t)),e}M(t){k(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let o,i=0;for(const r of t)i===e.length?e.push(o=new q(this.A(S()),this.A(S()),this,this.options)):o=e[i],o._$AI(r),i++;i<e.length&&(this._$AR(o&&o._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){var o;for(null===(o=this._$AP)||void 0===o||o.call(this,!1,!0,e);t&&t!==this._$AB;){const e=t.nextSibling;t.remove(),t=e}}setConnected(t){var e;void 0===this._$AM&&(this._$Cg=t,null===(e=this._$AP)||void 0===e||e.call(this,t))}}class I{constructor(t,e,o,i,r){this.type=1,this._$AH=P,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=r,o.length>2||""!==o[0]||""!==o[1]?(this._$AH=Array(o.length-1).fill(new String),this.strings=o):this._$AH=P}get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}_$AI(t,e=this,o,i){const r=this.strings;let n=!1;if(void 0===r)t=z(this,t,e,0),n=!A(t)||t!==this._$AH&&t!==O,n&&(this._$AH=t);else{const i=t;let s,a;for(t=r[0],s=0;s<r.length-1;s++)a=z(this,i[o+s],e,s),a===O&&(a=this._$AH[s]),n||(n=!A(a)||a!==this._$AH[s]),a===P?t=P:t!==P&&(t+=(null!=a?a:"")+r[s+1]),this._$AH[s]=a}n&&!i&&this.k(t)}k(t){t===P?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,null!=t?t:"")}}class j extends I{constructor(){super(...arguments),this.type=3}k(t){this.element[this.name]=t===P?void 0:t}}const F=v?v.emptyScript:"";class W extends I{constructor(){super(...arguments),this.type=4}k(t){t&&t!==P?this.element.setAttribute(this.name,F):this.element.removeAttribute(this.name)}}class Z extends I{constructor(t,e,o,i,r){super(t,e,o,i,r),this.type=5}_$AI(t,e=this){var o;if((t=null!==(o=z(this,t,e,0))&&void 0!==o?o:P)===O)return;const i=this._$AH,r=t===P&&i!==P||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,n=t!==P&&(i===P||r);r&&this.element.removeEventListener(this.name,this,i),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){var e,o;"function"==typeof this._$AH?this._$AH.call(null!==(o=null===(e=this.options)||void 0===e?void 0:e.host)&&void 0!==o?o:this.element,t):this._$AH.handleEvent(t)}}class G{constructor(t,e,o){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(t){z(this,t)}}const J=window.litHtmlPolyfillSupport;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var X,K;null==J||J(V,q),(null!==(_=globalThis.litHtmlVersions)&&void 0!==_?_:globalThis.litHtmlVersions=[]).push("2.0.2");class Q extends m{constructor(){super(...arguments),this.renderOptions={host:this},this._$Dt=void 0}createRenderRoot(){var t,e;const o=super.createRenderRoot();return null!==(t=(e=this.renderOptions).renderBefore)&&void 0!==t||(e.renderBefore=o.firstChild),o}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Dt=((t,e,o)=>{var i,r;const n=null!==(i=null==o?void 0:o.renderBefore)&&void 0!==i?i:e;let s=n._$litPart$;if(void 0===s){const t=null!==(r=null==o?void 0:o.renderBefore)&&void 0!==r?r:null;n._$litPart$=s=new q(e.insertBefore(S(),t),t,void 0,null!=o?o:{})}return s._$AI(t),s})(e,this.renderRoot,this.renderOptions)}connectedCallback(){var t;super.connectedCallback(),null===(t=this._$Dt)||void 0===t||t.setConnected(!0)}disconnectedCallback(){var t;super.disconnectedCallback(),null===(t=this._$Dt)||void 0===t||t.setConnected(!1)}render(){return O}}Q.finalized=!0,Q._$litElement$=!0,null===(X=globalThis.litElementHydrateSupport)||void 0===X||X.call(globalThis,{LitElement:Q});const tt=globalThis.litElementPolyfillSupport;null==tt||tt({LitElement:Q}),(null!==(K=globalThis.litElementVersions)&&void 0!==K?K:globalThis.litElementVersions=[]).push("3.0.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const et=t=>e=>"function"==typeof e?((t,e)=>(window.customElements.define(t,e),e))(t,e):((t,e)=>{const{kind:o,elements:i}=e;return{kind:o,elements:i,finisher(e){window.customElements.define(t,e)}}})(t,e)
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */,ot=(t,e)=>"method"===e.kind&&e.descriptor&&!("value"in e.descriptor)?{...e,finisher(o){o.createProperty(e.key,t)}}:{kind:"field",key:Symbol(),placement:"own",descriptor:{},originalKey:e.key,initializer(){"function"==typeof e.initializer&&(this[e.key]=e.initializer.call(this))},finisher(o){o.createProperty(e.key,t)}};function it(t){return(e,o)=>void 0!==o?((t,e,o)=>{e.constructor.createProperty(o,t)})(t,e,o):ot(t,e)
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */}function rt(t){return it({...t,state:!0})}var nt=/d{1,4}|M{1,4}|YY(?:YY)?|S{1,3}|Do|ZZ|Z|([HhMsDm])\1?|[aA]|"[^"]*"|'[^']*'/g,st="[^\\s]+",at=/\[([^]*?)\]/gm;function lt(t,e){for(var o=[],i=0,r=t.length;i<r;i++)o.push(t[i].substr(0,e));return o}var ht=function(t){return function(e,o){var i=o[t].map((function(t){return t.toLowerCase()})).indexOf(e.toLowerCase());return i>-1?i:null}};function dt(t){for(var e=[],o=1;o<arguments.length;o++)e[o-1]=arguments[o];for(var i=0,r=e;i<r.length;i++){var n=r[i];for(var s in n)t[s]=n[s]}return t}var ct=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],ut=["January","February","March","April","May","June","July","August","September","October","November","December"],pt=lt(ut,3),ft={dayNamesShort:lt(ct,3),dayNames:ct,monthNamesShort:pt,monthNames:ut,amPm:["am","pm"],DoFn:function(t){return t+["th","st","nd","rd"][t%10>3?0:(t-t%10!=10?1:0)*t%10]}},gt=dt({},ft),mt=function(t,e){for(void 0===e&&(e=2),t=String(t);t.length<e;)t="0"+t;return t},_t={D:function(t){return String(t.getDate())},DD:function(t){return mt(t.getDate())},Do:function(t,e){return e.DoFn(t.getDate())},d:function(t){return String(t.getDay())},dd:function(t){return mt(t.getDay())},ddd:function(t,e){return e.dayNamesShort[t.getDay()]},dddd:function(t,e){return e.dayNames[t.getDay()]},M:function(t){return String(t.getMonth()+1)},MM:function(t){return mt(t.getMonth()+1)},MMM:function(t,e){return e.monthNamesShort[t.getMonth()]},MMMM:function(t,e){return e.monthNames[t.getMonth()]},YY:function(t){return mt(String(t.getFullYear()),4).substr(2)},YYYY:function(t){return mt(t.getFullYear(),4)},h:function(t){return String(t.getHours()%12||12)},hh:function(t){return mt(t.getHours()%12||12)},H:function(t){return String(t.getHours())},HH:function(t){return mt(t.getHours())},m:function(t){return String(t.getMinutes())},mm:function(t){return mt(t.getMinutes())},s:function(t){return String(t.getSeconds())},ss:function(t){return mt(t.getSeconds())},S:function(t){return String(Math.round(t.getMilliseconds()/100))},SS:function(t){return mt(Math.round(t.getMilliseconds()/10),2)},SSS:function(t){return mt(t.getMilliseconds(),3)},a:function(t,e){return t.getHours()<12?e.amPm[0]:e.amPm[1]},A:function(t,e){return t.getHours()<12?e.amPm[0].toUpperCase():e.amPm[1].toUpperCase()},ZZ:function(t){var e=t.getTimezoneOffset();return(e>0?"-":"+")+mt(100*Math.floor(Math.abs(e)/60)+Math.abs(e)%60,4)},Z:function(t){var e=t.getTimezoneOffset();return(e>0?"-":"+")+mt(Math.floor(Math.abs(e)/60),2)+":"+mt(Math.abs(e)%60,2)}},vt=function(t){return+t-1},wt=[null,"[1-9]\\d?"],bt=[null,st],yt=["isPm",st,function(t,e){var o=t.toLowerCase();return o===e.amPm[0]?0:o===e.amPm[1]?1:null}],$t=["timezoneOffset","[^\\s]*?[\\+\\-]\\d\\d:?\\d\\d|[^\\s]*?Z?",function(t){var e=(t+"").match(/([+-]|\d\d)/gi);if(e){var o=60*+e[1]+parseInt(e[2],10);return"+"===e[0]?o:-o}return 0}],xt=(ht("monthNamesShort"),ht("monthNames"),{default:"ddd MMM DD YYYY HH:mm:ss",shortDate:"M/D/YY",mediumDate:"MMM D, YYYY",longDate:"MMMM D, YYYY",fullDate:"dddd, MMMM D, YYYY",isoDate:"YYYY-MM-DD",isoDateTime:"YYYY-MM-DDTHH:mm:ssZ",shortTime:"HH:mm",mediumTime:"HH:mm:ss",longTime:"HH:mm:ss.SSS"});var St,At,kt=function(t,e,o){if(void 0===e&&(e=xt.default),void 0===o&&(o={}),"number"==typeof t&&(t=new Date(t)),"[object Date]"!==Object.prototype.toString.call(t)||isNaN(t.getTime()))throw new Error("Invalid Date pass to format");var i=[];e=(e=xt[e]||e).replace(at,(function(t,e){return i.push(e),"@@@"}));var r=dt(dt({},gt),o);return(e=e.replace(nt,(function(e){return _t[e](t,r)}))).replace(/@@@/g,(function(){return i.shift()}))};(function(){try{(new Date).toLocaleDateString("i")}catch(t){return"RangeError"===t.name}})(),function(){try{(new Date).toLocaleString("i")}catch(t){return"RangeError"===t.name}}(),function(){try{(new Date).toLocaleTimeString("i")}catch(t){return"RangeError"===t.name}}();!function(t){t.language="language",t.system="system",t.comma_decimal="comma_decimal",t.decimal_comma="decimal_comma",t.space_comma="space_comma",t.none="none"}(St||(St={})),function(t){t.language="language",t.system="system",t.am_pm="12",t.twenty_four="24"}(At||(At={}));const Et={required:{icon:"tune",name:"Required",secondary:"Required options for this card to function",show:!0},actions:{icon:"gesture-tap-hold",name:"Actions",secondary:"Perform actions based on tapping/clicking",show:!1,options:{tap:{icon:"gesture-tap",name:"Tap",secondary:"Set the action to perform on tap",show:!1},hold:{icon:"gesture-tap-hold",name:"Hold",secondary:"Set the action to perform on hold",show:!1},double_tap:{icon:"gesture-double-tap",name:"Double Tap",secondary:"Set the action to perform on double tap",show:!1}}},appearance:{icon:"palette",name:"Appearance",secondary:"Customize the name, icon, etc",show:!1}};let Ct=class extends Q{constructor(){super(...arguments),this._initialized=!1}setConfig(t){this._config=t,this.loadCardHelpers()}shouldUpdate(){return this._initialized||this._initialize(),!0}get _name(){var t;return(null===(t=this._config)||void 0===t?void 0:t.name)||""}get _entity(){var t;return(null===(t=this._config)||void 0===t?void 0:t.entity)||""}get _show_title(){var t;return(null===(t=this._config)||void 0===t?void 0:t.show_title)||!1}get _show_error(){var t;return(null===(t=this._config)||void 0===t?void 0:t.show_error)||!1}get _tap_action(){var t;return(null===(t=this._config)||void 0===t?void 0:t.tap_action)||{action:"more-info"}}get _hold_action(){var t;return(null===(t=this._config)||void 0===t?void 0:t.hold_action)||{action:"none"}}get _double_tap_action(){var t;return(null===(t=this._config)||void 0===t?void 0:t.double_tap_action)||{action:"none"}}render(){if(!this.hass||!this._helpers)return D``;this._helpers.importMoreInfoControl("climate");const t=Object.keys(this.hass.states).filter(t=>"timer"===t.substr(0,t.indexOf(".")));return D`
      <div class="card-config">
        <div class="option" @click=${this._toggleOption} .option=${"required"}>
          <div class="row">
            <ha-icon .icon=${"mdi:"+Et.required.icon}></ha-icon>
            <div class="title">${Et.required.name}</div>
          </div>
          <div class="secondary">${Et.required.secondary}</div>
        </div>
        ${Et.required.show?D`
              <div class="values">
                <paper-dropdown-menu
                  label="Entity (Required)"
                  @value-changed=${this._valueChanged}
                  .configValue=${"entity"}
                >
                  <paper-listbox slot="dropdown-content" .selected=${t.indexOf(this._entity)}>
                    ${t.map(t=>D`
                        <paper-item>${t}</paper-item>
                      `)}
                  </paper-listbox>
                </paper-dropdown-menu>
              </div>
            `:""}

        <div class="option" @click=${this._toggleOption} .option=${"appearance"}>
          <div class="row">
            <ha-icon .icon=${"mdi:"+Et.appearance.icon}></ha-icon>
            <div class="title">${Et.appearance.name}</div>
          </div>
          <div class="secondary">${Et.appearance.secondary}</div>
        </div>
        ${Et.appearance.show?D`
              <div class="values">
                <paper-input
                  label="Name (Optional)"
                  .value=${this._name}
                  .configValue=${"name"}
                  @value-changed=${this._valueChanged}
                ></paper-input>
                <br />
                <ha-formfield .label=${"Toggle title "+(this._show_title?"off":"on")}>
                  <ha-switch
                    .checked=${!1!==this._show_title}
                    .configValue=${"show_title"}
                    @change=${this._valueChanged}
                  ></ha-switch>
                </ha-formfield>
                <ha-formfield .label=${"Toggle error "+(this._show_error?"off":"on")}>
                  <ha-switch
                    .checked=${!1!==this._show_error}
                    .configValue=${"show_error"}
                    @change=${this._valueChanged}
                  ></ha-switch>
                </ha-formfield>
              </div>
            `:""}
      </div>
    `}_initialize(){void 0!==this.hass&&void 0!==this._config&&void 0!==this._helpers&&(this._initialized=!0)}async loadCardHelpers(){this._helpers=await window.loadCardHelpers()}_toggleAction(t){this._toggleThing(t,Et.actions.options)}_toggleOption(t){this._toggleThing(t,Et)}_toggleThing(t,e){const o=!e[t.target.option].show;for(const[t]of Object.entries(e))e[t].show=!1;e[t.target.option].show=o,this._toggle=!this._toggle}_valueChanged(t){if(!this._config||!this.hass)return;const e=t.target;if(this["_"+e.configValue]!==e.value){if(e.configValue)if(""===e.value){const t=Object.assign({},this._config);delete t[e.configValue],this._config=t}else this._config=Object.assign(Object.assign({},this._config),{[e.configValue]:void 0!==e.checked?e.checked:e.value});!function(t,e,o,i){i=i||{},o=null==o?{}:o;var r=new Event(e,{bubbles:void 0===i.bubbles||i.bubbles,cancelable:Boolean(i.cancelable),composed:void 0===i.composed||i.composed});r.detail=o,t.dispatchEvent(r)}(this,"config-changed",{config:this._config})}}static get styles(){return s`
      .option {
        padding: 4px 0px;
        cursor: pointer;
      }
      .row {
        display: flex;
        margin-bottom: -14px;
        pointer-events: none;
      }
      .title {
        padding-left: 16px;
        margin-top: -6px;
        pointer-events: none;
      }
      .secondary {
        padding-left: 40px;
        color: var(--secondary-text-color);
        pointer-events: none;
      }
      .values {
        padding-left: 16px;
        background: var(--secondary-background-color);
        display: grid;
      }
      ha-formfield {
        padding-bottom: 8px;
      }
    `}};t([it({attribute:!1})],Ct.prototype,"hass",void 0),t([rt()],Ct.prototype,"_config",void 0),t([rt()],Ct.prototype,"_toggle",void 0),t([rt()],Ct.prototype,"_helpers",void 0),Ct=t([et("flipdown-timer-card-editor")],Ct);var Mt={version:"Version",invalid_configuration:"Invalid configuration",show_warning:"Show Warning",show_error:"Show Error"},Nt={common:Mt},Tt={version:"Versjon",invalid_configuration:"Ikke gyldig konfiguration",show_warning:"Vis advarsel"},Ht={common:Tt};const Rt={en:Object.freeze({__proto__:null,common:Mt,default:Nt}),nb:Object.freeze({__proto__:null,common:Tt,default:Ht})};function Dt(t,e="",o=""){const i=(localStorage.getItem("selectedLanguage")||"en").replace(/['"]+/g,"").replace("-","_");let r;try{r=t.split(".").reduce((t,e)=>t[e],Rt[i])}catch(e){r=t.split(".").reduce((t,e)=>t[e],Rt.en)}return void 0===r&&(r=t.split(".").reduce((t,e)=>t[e],Rt.en)),""!==e&&""!==o&&(r=r.replace(e,o)),r}function Ot(t,e){return(t=t.toString()).length<e?Ot("0"+t,e):t}function Pt(t,e){e.forEach(e=>{t.appendChild(e)})}class Lt{constructor(t,e,o={}){if("number"!=typeof t)throw new Error(`FlipDown: Constructor expected unix timestamp, got ${typeof t} instead.`);this.rt=null,this.button1=null,this.button2=null,this.version="0.3.2",this.initialised=!1,this.active=!1,this.state="",this.headerShift=!1,this.delimeterBlink=null,this.delimeterIsBlinking=!1,this.now=this._getTime(),this.epoch=t,this.countdownEnded=!1,this.hasEndedCallback=null,this.element=e,this.rotorGroups=[],this.rotors=[],this.rotorLeafFront=[],this.rotorLeafRear=[],this.rotorTops=[],this.rotorBottoms=[],this.countdown=null,this.daysRemaining=0,this.clockValues={},this.clockStrings={},this.clockValuesAsString=[],this.prevClockValuesAsString=[],this.opts=this._parseOptions(o),this._setOptions()}start(){return this.initialised||this._init(),this.rt=null,this.active=!0,this._tick(),this}_startInterval(){clearInterval(this.countdown),this.active&&(this.countdown=window.setInterval(this._tick.bind(this),1e3))}stop(){clearInterval(this.countdown),this.countdown=null,this.active=!1}ifEnded(t){return this.hasEndedCallback=function(){t(),this.hasEndedCallback=null},this}_getTime(){return(new Date).getTime()/1e3}_hasCountdownEnded(){return this.epoch-this.now<0?(this.countdownEnded=!0,null!=this.hasEndedCallback&&(this.hasEndedCallback(),this.hasEndedCallback=null),!0):(this.countdownEnded=!1,!1)}_parseOptions(t){let e=["Days","Hours","Minutes","Seconds"];return t.headings&&4===t.headings.length&&(e=t.headings),{theme:t.hasOwnProperty("theme")&&t.theme?t.theme:"hass",showHeader:!(!t.hasOwnProperty("show_header")||!t.show_header)&&t.show_header,showHour:!(!t.hasOwnProperty("show_hour")||!t.show_hour)&&t.show_hour,btLocation:t.bt_location,headings:e}}_setOptions(){this.element.classList.add("flipdown__theme-"+this.opts.theme)}_init(t){this.state=t,this.initialised=!0,this._hasCountdownEnded()?this.daysremaining=0:this.daysremaining=Math.floor((this.epoch-this.now)/86400).toString().length;for(let t=0;t<6;t++)this.rotors.push(this._createRotor(0));let e=0;for(let t=0;t<3;t++){const o=[];for(let t=0;t<2;t++)this.rotors[e].setAttribute("id","d"+(1-t)),o.push(this.rotors[e]),e++;const i=this._createRotorGroup(o,t+1);this.rotorGroups.push(i),this.element.appendChild(i)}return this.element.appendChild(this._createButton()),this.rotorLeafFront=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-leaf-front")),this.rotorLeafRear=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-leaf-rear")),this.rotorTop=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-top")),this.rotorBottom=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-bottom")),this._tick(),this._updateClockValues(!0),this}_createRotorGroup(t,e){const o=document.createElement("div");o.className="rotor-group",this.opts.showHour&&"auto"!=this.opts.showHour||1!=e||(o.className+=" hide"),"auto"==this.opts.showHour&&"idle"==this.state&&(o.className+=" autohour",this.headerShift=!0),o.setAttribute("id",this.opts.headings[e]);const i=document.createElement("div");if(i.className="rotor-group-heading",this.opts.showHeader?(i.setAttribute("data-before",this.opts.headings[e]),i.setAttribute("data-after",this.opts.headings[e-1])):(i.setAttribute("data-before"," "),i.setAttribute("data-after"," "),i.className+=" no-height"),o.appendChild(i),Pt(o,t),e<3){const t=document.createElement("div");t.className="delimeter";const i=document.createElement("span");i.className="delimeter-span-top";const r=document.createElement("span");r.className="delimeter-span-bottom",Pt(t,[i,r]),o.appendChild(t),2==e&&(this.delimeterBlink=t)}return o}_createButton(){const t=document.createElement("div");t.className="button-group","bottom"==this.opts.btLocation?t.className+=" button-bottom":"hide"==this.opts.btLocation?t.className+=" hide":t.className+=" button-right";const e=document.createElement("div");e.className="button-group-heading",e.setAttribute("data-before","");const o=document.createElement("div");return o.className="btn",this.button1=document.createElement("button"),this.button2=document.createElement("button"),this.button1.className="btn-top",this.button2.className="btn-bottom",this.opts.showHeader?Pt(t,[e,o]):Pt(t,[o]),Pt(o,[this.button1,this.button2]),t}_createRotor(t=0){const e=document.createElement("div"),o=document.createElement("div"),i=document.createElement("div"),r=document.createElement("div"),n=document.createElement("figure"),s=document.createElement("figure"),a=document.createElement("div"),l=document.createElement("div");return e.className="rotor",r.className="rotor-leaf",n.className="rotor-leaf-rear",s.className="rotor-leaf-front",o.className="rotor-trans-top",i.className="rotor-trans-bottom",a.className="rotor-top",l.className="rotor-bottom",s.textContent=t,n.textContent=t,a.textContent=t,l.textContent=t,Pt(e,[o,i,r,a,l]),Pt(r,[n,s]),e}_updator(t){this.epoch=t}_tick(t=!1){this.now=this._getTime();let e=Math.floor(this.epoch-this.now<=0?0:this.epoch-this.now);null!=this.rt&&(e=this.rt),this.clockValues.d=Math.floor(e/86400),e-=86400*this.clockValues.d,this.clockValues.h=Math.floor(e/3600),e-=3600*this.clockValues.h,this.clockValues.m=Math.floor(e/60),e-=60*this.clockValues.m,this.clockValues.s=Math.floor(e),this._updateClockValues(!1,t)}_updateClockValues(t=!1,e=!1){function o(){this.rotorTop.forEach((t,e)=>{t.textContent!=this.clockValuesAsString[e]&&(t.textContent=this.clockValuesAsString[e])})}function i(){this.rotorLeafRear.forEach((t,e)=>{if(t.textContent!=this.clockValuesAsString[e]){t.textContent=this.clockValuesAsString[e],t.parentElement.classList.add("flipped");const o=setInterval(function(){t.parentElement.classList.remove("flipped"),clearInterval(o)}.bind(this),500)}})}this.clockStrings.d=Ot(this.clockValues.d,2),this.clockStrings.h=Ot(this.clockValues.h,2),this.clockStrings.m=Ot(this.clockValues.m,2),this.clockStrings.s=Ot(this.clockValues.s,2),"auto"==this.opts.showHour&&(this.clockValues.h>0||"idle"==this.state)?(this.headerShift||(this.rotorGroups.forEach(t=>t.classList.add("autohour")),this.headerShift=!0),"active"!=this.state||this.delimeterIsBlinking?"active"!=this.state&&this.delimeterIsBlinking&&(this.delimeterBlink.classList.remove("blink"),this.delimeterIsBlinking=!1):(this.delimeterBlink.classList.add("blink"),this.delimeterIsBlinking=!0),this.clockValuesAsString=("00"+this.clockStrings.h+this.clockStrings.m).split("")):(this.headerShift&&(this.rotorGroups.forEach(t=>t.classList.remove("autohour")),this.headerShift=!1),this.delimeterIsBlinking&&(this.delimeterBlink.classList.remove("blink"),this.delimeterIsBlinking=!1),this.clockValuesAsString=(this.clockStrings.h+this.clockStrings.m+this.clockStrings.s).split("")),o.call(this),i.call(this),t?(o.call(this),i.call(this)):(setTimeout(function(){this.rotorLeafFront.forEach((t,e)=>{t.textContent=this.prevClockValuesAsString[e]})}.bind(this),500),setTimeout(function(){this.rotorBottom.forEach((t,e)=>{t.textContent=this.prevClockValuesAsString[e]})}.bind(this),500)),this.prevClockValuesAsString=this.clockValuesAsString}}const Ut=s`
  /* THEMES */
  /********** Theme: hass **********/
  /* Font styles */
  .flipdown.flipdown__theme-hass {
    font-family: sans-serif;
    font-weight: bold;
  }
  /* Rotor group headings */
  .flipdown.flipdown__theme-hass .rotor-group-heading:before {
    color: var(--primary-color);
  }
  /* Delimeters */
  /* Rotor tops */
  .flipdown.flipdown__theme-hass .rotor,
  .flipdown.flipdown__theme-hass .rotor-top,
  .flipdown.flipdown__theme-hass .rotor-leaf-front {
    color: var(--text-primary-color);
    background-color: var(--primary-color);
  }
  /* Rotor bottoms */
  .flipdown.flipdown__theme-hass .rotor-bottom,
  .flipdown.flipdown__theme-hass .rotor-leaf-rear {
    color: var(--text-primary-color);
    background-color: var(--primary-color);
  }
  /* Hinge */
  .flipdown.flipdown__theme-hass .rotor:after {
    border-top: solid 1px var(--dark-primary-color);
  }
  .flipdown.flipdown__theme-hass .delimeter span {
    background-color: var(--primary-color);
  }
  .flipdown.flipdown__theme-hass .btn-top,
  .flipdown.flipdown__theme-hass .btn-bottom {
    background-color: var(--dark-primary-color);
    color: var(--text-primary-color);
  }
  /********** Theme: dark **********/
  /* Font styles */
  .flipdown.flipdown__theme-dark {
    font-family: sans-serif;
    font-weight: bold;
  }
  /* Rotor group headings */
  .flipdown.flipdown__theme-dark .rotor-group-heading:before {
    color: #000000;
  }
  /* Delimeters */
  /* Rotor tops */
  .flipdown.flipdown__theme-dark .rotor,
  .flipdown.flipdown__theme-dark .rotor-top,
  .flipdown.flipdown__theme-dark .rotor-leaf-front {
    color: #ffffff;
    background-color: #151515;
  }
  /* Rotor bottoms */
  .flipdown.flipdown__theme-dark .rotor-bottom,
  .flipdown.flipdown__theme-dark .rotor-leaf-rear {
    color: #efefef;
    background-color: #202020;
  }
  /* Hinge */
  .flipdown.flipdown__theme-dark .rotor:after {
    border-top: solid 1px #151515;
  }
  .flipdown.flipdown__theme-dark .delimeter span {
    background-color: #151515;
  }
  .flipdown.flipdown__theme-dark .btn-top,
  .flipdown.flipdown__theme-dark .btn-bottom {
    background-color: #202020;
    color: #ffffff;
  }
  /********** Theme: light **********/
  /* Font styles */
  .flipdown.flipdown__theme-light {
    font-family: sans-serif;
    font-weight: bold;
  }
  /* Rotor group headings */
  .flipdown.flipdown__theme-light .rotor-group-heading:before {
    color: #eeeeee;
  }
  /* Delimeters */
  .flipdown.flipdown__theme-light .rotor-group:nth-child(n + 1):nth-child(-n + 2):before,
  .flipdown.flipdown__theme-light .rotor-group:nth-child(n + 1):nth-child(-n + 2):after {
    background-color: #dddddd;
  }
  /* Rotor tops */
  .flipdown.flipdown__theme-light .rotor,
  .flipdown.flipdown__theme-light .rotor-top,
  .flipdown.flipdown__theme-light .rotor-leaf-front {
    color: #222222;
    background-color: #dddddd;
  }
  /* Rotor bottoms */
  .flipdown.flipdown__theme-light .rotor-bottom,
  .flipdown.flipdown__theme-light .rotor-leaf-rear {
    color: #333333;
    background-color: #eeeeee;
  }
  /* Hinge */
  .flipdown.flipdown__theme-light .rotor:after {
    border-top: solid 1px #222222;
  }
  .flipdown.flipdown__theme-light .delimeter span {
    background-color: #eeeeee;
  }
  .flipdown.flipdown__theme-light .btn-top,
  .flipdown.flipdown__theme-light .btn-bottom {
    background-color: #dddddd;
    color: #222222;
  }
  /* END OF THEMES */
  .flipdown_shell {
    width: 100%;
    text-align: center;
    align-content: center;
    display: block;
  }

  .flipdown {
    overflow: visible;
    display: inline-block;
  }

  .flipdown .rotor-group {
    position: relative;
    display: inline-block;
  }

  .flipdown .delimeter {
    width: var(--rotor-space, 20px);
    height: var(--rotor-height, 80px);
    position: relative;
    float: left;
  }

  .flipdown .delimeter.blink {
    animation: blinker 1s linear infinite;
  }

  @keyframes blinker {
    50% {
      opacity: 0;
    }
  }

  .flipdown .rotor-group-heading {
    width: calc(var(--rotor-width, 50px) * 2 + 5px);
    height: 30px;
  }

  .flipdown .rotor-group-heading:before {
    display: block;
    line-height: 30px;
    text-align: center;
  }

  .flipdown .hide {
    display: none;
  }

  .flipdown .no-height {
    height: 0px;
  }

  .flipdown .rotor-group .rotor-group-heading:before {
    content: attr(data-before);
  }
  .flipdown .rotor-group.autohour .rotor-group-heading:before {
    content: attr(data-after);
  }

  .flipdown .rotor:after {
    content: '';
    z-index: 2;
    position: absolute;
    bottom: 0px;
    left: 0px;
    width: var(--rotor-width, 50px);
    height: calc(var(--rotor-height, 80px) / 2);
    border-radius: 0px 0px 4px 4px;
  }

  .flipdown .delimeter span {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    position: absolute;
    left: calc(50% - 5px);
  }
  .flipdown .delimeter-span-top {
    top: calc(var(--rotor-height, 80px) / 2 - 20px);
  }
  .flipdown .delimeter-span-bottom {
    bottom: calc(var(--rotor-height, 80px) / 2 - 20px);
  }

  .flipdown .rotor {
    position: relative;
    float: left;
    width: var(--rotor-width, 50px);
    height: var(--rotor-height, 80px);
    margin: 0px 5px 0px 0px;
    border-radius: 4px;
    font-size: 4rem;
    text-align: center;
    perspective: 200px;
  }

  .flipdown #d0 {
    margin: 0;
  }

  .flipdown .button-group {
    position: relative;
  }

  .flipdown .button-group.button-right {
    float: right;
    padding-left: var(--rotor-space, 20px);
  }

  .flipdown .button-group.button-right .button-group-heading {
    height: 30px;
    line-height: 30px;
    text-align: center;
  }

  .flipdown .button-group.button-right .btn {
    position: relative;
    float: left;
    width: var(--button-width, 50px);
    height: var(--rotor-height, 80px);
    margin: 0px 0px 0px 0px;
    border-radius: 4px;
    font-size: 4rem;
    text-align: center;
  }

  .flipdown .button-group.button-right .btn-top,
  .flipdown .button-group.button-right .btn-bottom {
    overflow: hidden;
    position: absolute;
    left: 0px;
    width: var(--button-width, 50px);
    margin: 0px;
    height: calc(var(--rotor-height, 80px) / 2 - 2px);
    padding: 0px;
    border-radius: 4px;
    border: 0px;
    font-family: sans-serif;
  }

  .flipdown .button-group.button-right .btn-bottom {
    bottom: 0;
  }

  .flipdown .button-group.button-bottom {
    position: relative;
    margin-top: 5px;
  }

  .flipdown .button-group.button-bottom .button-group-heading {
    display: none;
  }

  .flipdown .button-group.button-bottom .btn-top,
  .flipdown .button-group.button-bottom .btn-bottom {
    overflow: hidden;
    width: var(--button-width, calc(var(--rotor-width, 50px) * 2 + 5px));
    margin: 0px;
    height: 20px;
    padding: 0px;
    border-radius: 4px;
    border: 0px;
    font-family: sans-serif;
  }
  .flipdown .button-group.button-bottom .btn-bottom {
    margin-left: var(--rotor-space, 20px);
  }

  .flipdown .rotor:last-child {
    margin-right: 0;
  }

  .flipdown .rotor-top,
  .flipdown .rotor-bottom {
    overflow: hidden;
    position: absolute;
    width: var(--rotor-width, 50px);
    height: calc(var(--rotor-height, 80px) / 2);
  }


  .flipdown .rotor-trans-top,
  .flipdown .rotor-trans-bottom {
    position: absolute;
    width: var(--rotor-width, 50px);
    height: calc(var(--rotor-height, 80px) / 2);
    z-index: 1000;
  }

  .flipdown .rotor-trans-bottom {
    bottom: 0px;
  }

  .flipdown .rotor-leaf {
    z-index: 1;
    position: absolute;
    width: var(--rotor-width, 50px);
    height: var(--rotor-height, 80px);
    transform-style: preserve-3d;
    transition: transform 0s;
  }

  .flipdown .rotor-leaf.flipped {
    transform: rotateX(-180deg);
    transition: all 0.5s ease-in-out;
  }

  .flipdown .rotor-leaf.flippedf {
    transform: rotateX(-180deg);
    transition: all 0.2s ease-in-out;
  }

  .flipdown .rotor-leaf.flippedfr {
    transform: rotateX(180deg);
    transition: all 0.2s ease-in-out;
  }

  .flipdown .rotor-leaf-front,
  .flipdown .rotor-leaf-rear {
    overflow: hidden;
    position: absolute;
    width: var(--rotor-width, 50px);
    height: calc(var(--rotor-height, 80px) / 2);
    margin: 0;
    transform: rotateX(0deg);
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
  }

  .flipdown .rotor-leaf-front {
    line-height: var(--rotor-height, 80px);
    border-radius: 4px;
  }

  .flipdown .rotor-leaf-rear {
    line-height: 0px;
    border-radius: 4px;
    transform: rotateX(-180deg);
  }

  .flipdown .front-bottom {
    bottom: 0px;
    line-height: 0px;
  }

  .flipdown .rear-bottom {
    bottom: 0px;
    line-height: var(--rotor-height, 80px);
  }

  .flipdown .rotor-top {
    line-height: var(--rotor-height, 80px);
    border-radius: 4px 4px 0px 0px;
  }

  .flipdown .rotor-bottom {
    bottom: 0;
    line-height: 0px;
    border-radius: 0px 0px 4px 4px;
  }
`;function Bt(t){const e=t.split(":").map(Number);return 3600*e[0]+60*e[1]+e[2]}console.info(`%c  FLIPDOWN-TIMER-CARD \n%c  ${Dt("common.version")} 1.0.0    `,"color: orange; font-weight: bold; background: black","color: white; font-weight: bold; background: dimgray"),window.customCards=window.customCards||[],window.customCards.push({type:"flipdown-timer-card",name:"Flipdown Timer Card",description:"A template custom card for you to create something awesome"});let Vt=[];let zt=class extends Q{constructor(){super(...arguments),this.fd=null}static async getConfigElement(){return document.createElement("flipdown-timer-card-editor")}static getStubConfig(){return{}}setConfig(t){if(!t||!t.entity)throw new Error(Dt("common.invalid_configuration"));t.test_gui&&function(){var t=document.querySelector("home-assistant");if(t=(t=(t=(t=(t=(t=(t=(t=t&&t.shadowRoot)&&t.querySelector("home-assistant-main"))&&t.shadowRoot)&&t.querySelector("app-drawer-layout partial-panel-resolver"))&&t.shadowRoot||t)&&t.querySelector("ha-panel-lovelace"))&&t.shadowRoot)&&t.querySelector("hui-root")){var e=t.lovelace;return e.current_view=t.___curView,e}return null}().setEditMode(!0),this.config=Object.assign({},t);let e=["start","stop","cancel","resume","reset"],o=["Hours","Minutes","Seconds"];if(t.hasOwnProperty("localize")){if(t.localize.button){const o=t.localize.button.replace(/\s/g,"").split(",");5===o.length&&(e=o)}if(t.localize.header){const e=t.localize.header.replace(/\s/g,"").split(",");3===e.length&&(o=e)}}o.unshift("Days"),this.config.localizeBtn=e,this.config.localizeHeader=o,this.config.styles||(this.config.styles={rotor:!1,button:!1})}shouldUpdate(t){return!!this.config&&function(t,e,o){if(e.has("config")||o)return!0;if(t.config.entity){var i=e.get("hass");return!i||i.states[t.config.entity]!==t.hass.states[t.config.entity]}return!1}(this,t,!1)}disconnectedCallback(){super.disconnectedCallback(),this.fd&&this.fd.stop()}connectedCallback(){var t;if(super.connectedCallback(),this.config&&this.config.entity){(null===(t=this.hass)||void 0===t?void 0:t.states[this.config.entity])&&this._start()}}_start(){var t;const e=this.hass.states[this.config.entity],o=null===(t=this.shadowRoot)||void 0===t?void 0:t.getElementById("flipdown");if(!o)return!1;if(o&&!this.fd&&this._init(),this.fd.state=e.state,"active"===e.state){this.fd.button1.textContent=this.config.localizeBtn[1],this.fd.button2.textContent=this.config.localizeBtn[2];let t=Bt(e.attributes.remaining);const o=new Date(e.last_changed).getTime();t=Math.max(t+o/1e3,0),this.fd._updator(t),this.fd.start(),Vt.push(this),Vt=Vt.filter(t=>null!=t.offsetParent),Vt.forEach(t=>{t.fd._startInterval()})}else if("idle"===e.state)this.fd.stop(),this.fd.button1.textContent=this.config.localizeBtn[0],this.fd.button2.textContent=this.config.localizeBtn[4],this._reset();else if("paused"===e.state){this.fd.stop(),this.fd.button1.textContent=this.config.localizeBtn[3],this.fd.button2.textContent=this.config.localizeBtn[2];const t=Bt(e.attributes.remaining);this.fd.rt=t,this.fd._tick(!0)}return!0}_clear(){this.fd=null}_reset(){const t=this.hass.states[this.config.entity],e=Bt(this.config.duration?this.config.duration:t.attributes.duration);this.fd.rt=e,this.fd._tick(!0)}updated(t){if(super.updated(t),t.has("hass")){const e=this.hass.states[this.config.entity],o=t.get("hass");(o?o.states[this.config.entity]:void 0)!==e?this._start():e||this._clear()}}render(){return this.config.show_warning?this._showWarning(Dt("common.show_warning")):this.config.show_error?this._showError(Dt("common.show_error")):D`
      <ha-card>
        <div class="card-content">
          ${this.config.show_title?D`<hui-generic-entity-row .hass=${this.hass} .config=${this.config}></hui-generic-entity-row>`:D``}
          <div class="flipdown_shell" style="
            --rotor-width:  ${this.config.styles.rotor&&this.config.styles.rotor.width||"50px"};
            --rotor-height: ${this.config.styles.rotor&&this.config.styles.rotor.height||"80px"};
            --rotor-space:  ${this.config.styles.rotor&&this.config.styles.rotor.space||"20px"};
            ${this.config.styles.button&&this.config.styles.button.width&&"--button-width: "+this.config.styles.button.width}
          ">
            <div id="flipdown" class="flipdown"></div>
          </div>
        </div>
      </ha-card>
    `}_init(){var t;const e=null===(t=this.shadowRoot)||void 0===t?void 0:t.getElementById("flipdown"),o=(new Date).getTime()/1e3,i=this.hass.states[this.config.entity].state;this.fd||(this.fd=new Lt(o,e,{show_header:this.config.show_header,show_hour:this.config.show_hour,bt_location:this.config.styles.button&&this.config.styles.button.hasOwnProperty("location")?this.config.styles.button.location:"right",theme:this.config.theme,headings:this.config.localizeHeader})._init(i)),this.config.entity&&(null==e||e.querySelectorAll(".rotor-trans-top").forEach((t,e)=>{t.addEventListener("click",()=>{this._handleRotorClick(t,e,!0)})}),null==e||e.querySelectorAll(".rotor-trans-bottom").forEach((t,e)=>{t.addEventListener("click",()=>{this._handleRotorClick(t,e,!1)})}),this.fd.button1.addEventListener("click",()=>this._handleBtnClick(1)),this.fd.button2.addEventListener("click",()=>this._handleBtnClick(2)))}firstUpdated(){this._init()}_handleRotorClick(t,e,o){if("idle"!==this.hass.states[this.config.entity].state)return!1;const i=[5,9,5,9,5,9],r=t.offsetParent;if(o){const t=Number(r.querySelector(".rotor-leaf-rear").textContent),o=t<i[e]?t+1:0;r.querySelector(".rotor-leaf-front").classList.add("front-bottom"),r.querySelector(".rotor-leaf-rear").classList.add("rear-bottom"),r.querySelector(".rotor-leaf-rear").textContent=o,r.querySelector(".rotor-bottom").textContent=o,r.querySelector(".rotor-leaf").classList.add("flippedfr"),setTimeout(()=>{r.querySelector(".rotor-leaf-front").textContent=o,r.querySelector(".rotor-top").textContent=o,r.querySelector(".rotor-leaf").classList.remove("flippedfr"),r.querySelector(".rotor-leaf-front").classList.remove("front-bottom"),r.querySelector(".rotor-leaf-rear").classList.remove("rear-bottom")},200)}else{const t=Number(r.querySelector(".rotor-leaf-rear").textContent),o=t>0?t-1:i[e];r.querySelector(".rotor-leaf-rear").textContent=o,r.querySelector(".rotor-top").textContent=o,r.querySelector(".rotor-leaf").classList.add("flippedf"),setTimeout(()=>{r.querySelector(".rotor-leaf-front").textContent=o,r.querySelector(".rotor-bottom").textContent=o,r.querySelector(".rotor-leaf").classList.remove("flippedf")},200)}return!0}_handleBtnClick(t){const e=this.hass.states[this.config.entity].state;switch(t){case 1:let t=this._getRotorTime();"idle"===e&&"00:00:00"!=t?("auto"==this.config.show_hour&&(t=t.substr(3,5)+":00"),this.hass.callService("timer","start",{entity_id:this.config.entity,duration:t})):"active"===e?this.hass.callService("timer","pause",{entity_id:this.config.entity}):"paused"===e&&this.hass.callService("timer","start",{entity_id:this.config.entity});break;case 2:"idle"===e?this._reset():this.hass.callService("timer","cancel",{entity_id:this.config.entity})}}_getRotorTime(){let t="";return this.fd.rotorTop.forEach((e,o)=>{t+=e.textContent,1!=o&&3!=o||(t+=":")}),t}_showWarning(t){return D`
      <hui-warning>${t}</hui-warning>
    `}_showError(t){const e=document.createElement("hui-error-card");return e.setConfig({type:"error",error:t,origConfig:this.config}),D`
      ${e}
    `}static get styles(){return n(Ut)}};t([it({attribute:!1})],zt.prototype,"hass",void 0),t([it({attribute:!1})],zt.prototype,"fd",void 0),t([rt()],zt.prototype,"config",void 0),zt=t([et("flipdown-timer-card")],zt);export{zt as FlipdownTimer,Bt as durationToSeconds};
