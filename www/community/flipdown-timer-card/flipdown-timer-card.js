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
function t(t,e,o,i){var n,r=arguments.length,s=r<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,o):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)s=Reflect.decorate(t,e,o,i);else for(var a=t.length-1;a>=0;a--)(n=t[a])&&(s=(r<3?n(s):r>3?n(e,o,s):n(e,o))||s);return r>3&&s&&Object.defineProperty(e,o,s),s
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */}const e=window.ShadowRoot&&(void 0===window.ShadyCSS||window.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,o=Symbol(),i=new Map;class n{constructor(t,e){if(this._$cssResult$=!0,e!==o)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t}get styleSheet(){let t=i.get(this.cssText);return e&&void 0===t&&(i.set(this.cssText,t=new CSSStyleSheet),t.replaceSync(this.cssText)),t}toString(){return this.cssText}}const r=t=>new n("string"==typeof t?t:t+"",o),s=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,o,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+t[i+1],t[0]);return new n(i,o)},a=(t,o)=>{e?t.adoptedStyleSheets=o.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet):o.forEach(e=>{const o=document.createElement("style");o.textContent=e.cssText,t.appendChild(o)})},l=e?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const o of t.cssRules)e+=o.cssText;return r(e)})(t):t
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */;var h,d,c,u;const p={toAttribute(t,e){switch(e){case Boolean:t=t?"":null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let o=t;switch(e){case Boolean:o=null!==t;break;case Number:o=null===t?null:Number(t);break;case Object:case Array:try{o=JSON.parse(t)}catch(t){o=null}}return o}},f=(t,e)=>e!==t&&(e==e||t==t),g={attribute:!0,type:String,converter:p,reflect:!1,hasChanged:f};class m extends HTMLElement{constructor(){super(),this._$Et=new Map,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Ei=null,this.o()}static addInitializer(t){var e;null!==(e=this.l)&&void 0!==e||(this.l=[]),this.l.push(t)}static get observedAttributes(){this.finalize();const t=[];return this.elementProperties.forEach((e,o)=>{const i=this._$Eh(o,e);void 0!==i&&(this._$Eu.set(i,o),t.push(i))}),t}static createProperty(t,e=g){if(e.state&&(e.attribute=!1),this.finalize(),this.elementProperties.set(t,e),!e.noAccessor&&!this.prototype.hasOwnProperty(t)){const o="symbol"==typeof t?Symbol():"__"+t,i=this.getPropertyDescriptor(t,o,e);void 0!==i&&Object.defineProperty(this.prototype,t,i)}}static getPropertyDescriptor(t,e,o){return{get(){return this[e]},set(i){const n=this[t];this[e]=i,this.requestUpdate(t,n,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)||g}static finalize(){if(this.hasOwnProperty("finalized"))return!1;this.finalized=!0;const t=Object.getPrototypeOf(this);if(t.finalize(),this.elementProperties=new Map(t.elementProperties),this._$Eu=new Map,this.hasOwnProperty("properties")){const t=this.properties,e=[...Object.getOwnPropertyNames(t),...Object.getOwnPropertySymbols(t)];for(const o of e)this.createProperty(o,t[o])}return this.elementStyles=this.finalizeStyles(this.styles),!0}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const o=new Set(t.flat(1/0).reverse());for(const t of o)e.unshift(l(t))}else void 0!==t&&e.push(l(t));return e}static _$Eh(t,e){const o=e.attribute;return!1===o?void 0:"string"==typeof o?o:"string"==typeof t?t.toLowerCase():void 0}o(){var t;this._$Ev=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$Ep(),this.requestUpdate(),null===(t=this.constructor.l)||void 0===t||t.forEach(t=>t(this))}addController(t){var e,o;(null!==(e=this._$Em)&&void 0!==e?e:this._$Em=[]).push(t),void 0!==this.renderRoot&&this.isConnected&&(null===(o=t.hostConnected)||void 0===o||o.call(t))}removeController(t){var e;null===(e=this._$Em)||void 0===e||e.splice(this._$Em.indexOf(t)>>>0,1)}_$Ep(){this.constructor.elementProperties.forEach((t,e)=>{this.hasOwnProperty(e)&&(this._$Et.set(e,this[e]),delete this[e])})}createRenderRoot(){var t;const e=null!==(t=this.shadowRoot)&&void 0!==t?t:this.attachShadow(this.constructor.shadowRootOptions);return a(e,this.constructor.elementStyles),e}connectedCallback(){var t;void 0===this.renderRoot&&(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),null===(t=this._$Em)||void 0===t||t.forEach(t=>{var e;return null===(e=t.hostConnected)||void 0===e?void 0:e.call(t)})}enableUpdating(t){}disconnectedCallback(){var t;null===(t=this._$Em)||void 0===t||t.forEach(t=>{var e;return null===(e=t.hostDisconnected)||void 0===e?void 0:e.call(t)})}attributeChangedCallback(t,e,o){this._$AK(t,o)}_$Eg(t,e,o=g){var i,n;const r=this.constructor._$Eh(t,o);if(void 0!==r&&!0===o.reflect){const s=(null!==(n=null===(i=o.converter)||void 0===i?void 0:i.toAttribute)&&void 0!==n?n:p.toAttribute)(e,o.type);this._$Ei=t,null==s?this.removeAttribute(r):this.setAttribute(r,s),this._$Ei=null}}_$AK(t,e){var o,i,n;const r=this.constructor,s=r._$Eu.get(t);if(void 0!==s&&this._$Ei!==s){const t=r.getPropertyOptions(s),a=t.converter,l=null!==(n=null!==(i=null===(o=a)||void 0===o?void 0:o.fromAttribute)&&void 0!==i?i:"function"==typeof a?a:null)&&void 0!==n?n:p.fromAttribute;this._$Ei=s,this[s]=l(e,t.type),this._$Ei=null}}requestUpdate(t,e,o){let i=!0;void 0!==t&&(((o=o||this.constructor.getPropertyOptions(t)).hasChanged||f)(this[t],e)?(this._$AL.has(t)||this._$AL.set(t,e),!0===o.reflect&&this._$Ei!==t&&(void 0===this._$ES&&(this._$ES=new Map),this._$ES.set(t,o))):i=!1),!this.isUpdatePending&&i&&(this._$Ev=this._$EC())}async _$EC(){this.isUpdatePending=!0;try{await this._$Ev}catch(t){Promise.reject(t)}const t=this.performUpdate();return null!=t&&await t,!this.isUpdatePending}performUpdate(){var t;if(!this.isUpdatePending)return;this.hasUpdated,this._$Et&&(this._$Et.forEach((t,e)=>this[e]=t),this._$Et=void 0);let e=!1;const o=this._$AL;try{e=this.shouldUpdate(o),e?(this.willUpdate(o),null===(t=this._$Em)||void 0===t||t.forEach(t=>{var e;return null===(e=t.hostUpdate)||void 0===e?void 0:e.call(t)}),this.update(o)):this._$E_()}catch(t){throw e=!1,this._$E_(),t}e&&this._$AE(o)}willUpdate(t){}_$AE(t){var e;null===(e=this._$Em)||void 0===e||e.forEach(t=>{var e;return null===(e=t.hostUpdated)||void 0===e?void 0:e.call(t)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$E_(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$Ev}shouldUpdate(t){return!0}update(t){void 0!==this._$ES&&(this._$ES.forEach((t,e)=>this._$Eg(e,this[e],t)),this._$ES=void 0),this._$E_()}updated(t){}firstUpdated(t){}}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var _,v,w,b;m.finalized=!0,m.elementProperties=new Map,m.elementStyles=[],m.shadowRootOptions={mode:"open"},null===(d=(h=globalThis).reactiveElementPlatformSupport)||void 0===d||d.call(h,{ReactiveElement:m}),(null!==(c=(u=globalThis).reactiveElementVersions)&&void 0!==c?c:u.reactiveElementVersions=[]).push("1.0.0-rc.3");const y=globalThis.trustedTypes,$=y?y.createPolicy("lit-html",{createHTML:t=>t}):void 0,x=`lit$${(Math.random()+"").slice(9)}$`,A="?"+x,S=`<${A}>`,E=document,C=(t="")=>E.createComment(t),k=t=>null===t||"object"!=typeof t&&"function"!=typeof t,M=Array.isArray,T=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,N=/-->/g,H=/>/g,R=/>|[ 	\n\r](?:([^\s"'>=/]+)([ 	\n\r]*=[ 	\n\r]*(?:[^ 	\n\r"'`<>=]|("|')|))|$)/g,D=/'/g,P=/"/g,O=/^(?:script|style|textarea)$/i,V=(t=>(e,...o)=>({_$litType$:t,strings:e,values:o}))(1),U=Symbol.for("lit-noChange"),L=Symbol.for("lit-nothing"),Y=new WeakMap,z=E.createTreeWalker(E,129,null,!1);class B{constructor({strings:t,_$litType$:e},o){let i;this.parts=[];let n=0,r=0;const s=t.length-1,a=this.parts,[l,h]=((t,e)=>{const o=t.length-1,i=[];let n,r=2===e?"<svg>":"",s=T;for(let e=0;e<o;e++){const o=t[e];let a,l,h=-1,d=0;for(;d<o.length&&(s.lastIndex=d,l=s.exec(o),null!==l);)d=s.lastIndex,s===T?"!--"===l[1]?s=N:void 0!==l[1]?s=H:void 0!==l[2]?(O.test(l[2])&&(n=RegExp("</"+l[2],"g")),s=R):void 0!==l[3]&&(s=R):s===R?">"===l[0]?(s=null!=n?n:T,h=-1):void 0===l[1]?h=-2:(h=s.lastIndex-l[2].length,a=l[1],s=void 0===l[3]?R:'"'===l[3]?P:D):s===P||s===D?s=R:s===N||s===H?s=T:(s=R,n=void 0);const c=s===R&&t[e+1].startsWith("/>")?" ":"";r+=s===T?o+S:h>=0?(i.push(a),o.slice(0,h)+"$lit$"+o.slice(h)+x+c):o+x+(-2===h?(i.push(void 0),e):c)}const a=r+(t[o]||"<?>")+(2===e?"</svg>":"");return[void 0!==$?$.createHTML(a):a,i]})(t,e);if(this.el=B.createElement(l,o),z.currentNode=this.el.content,2===e){const t=this.el.content,e=t.firstChild;e.remove(),t.append(...e.childNodes)}for(;null!==(i=z.nextNode())&&a.length<s;){if(1===i.nodeType){if(i.hasAttributes()){const t=[];for(const e of i.getAttributeNames())if(e.endsWith("$lit$")||e.startsWith(x)){const o=h[r++];if(t.push(e),void 0!==o){const t=i.getAttribute(o.toLowerCase()+"$lit$").split(x),e=/([.?@])?(.*)/.exec(o);a.push({type:1,index:n,name:e[2],strings:t,ctor:"."===e[1]?W:"?"===e[1]?Z:"@"===e[1]?J:F})}else a.push({type:6,index:n})}for(const e of t)i.removeAttribute(e)}if(O.test(i.tagName)){const t=i.textContent.split(x),e=t.length-1;if(e>0){i.textContent=y?y.emptyScript:"";for(let o=0;o<e;o++)i.append(t[o],C()),z.nextNode(),a.push({type:2,index:++n});i.append(t[e],C())}}}else if(8===i.nodeType)if(i.data===A)a.push({type:2,index:n});else{let t=-1;for(;-1!==(t=i.data.indexOf(x,t+1));)a.push({type:7,index:n}),t+=x.length-1}n++}}static createElement(t,e){const o=E.createElement("template");return o.innerHTML=t,o}}function I(t,e,o=t,i){var n,r,s,a;if(e===U)return e;let l=void 0!==i?null===(n=o._$Cl)||void 0===n?void 0:n[i]:o._$Cu;const h=k(e)?void 0:e._$litDirective$;return(null==l?void 0:l.constructor)!==h&&(null===(r=null==l?void 0:l._$AO)||void 0===r||r.call(l,!1),void 0===h?l=void 0:(l=new h(t),l._$AT(t,o,i)),void 0!==i?(null!==(s=(a=o)._$Cl)&&void 0!==s?s:a._$Cl=[])[i]=l:o._$Cu=l),void 0!==l&&(e=I(t,l._$AS(t,e.values),l,i)),e}class q{constructor(t,e){this.v=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get _$AU(){return this._$AM._$AU}p(t){var e;const{el:{content:o},parts:i}=this._$AD,n=(null!==(e=null==t?void 0:t.creationScope)&&void 0!==e?e:E).importNode(o,!0);z.currentNode=n;let r=z.nextNode(),s=0,a=0,l=i[0];for(;void 0!==l;){if(s===l.index){let e;2===l.type?e=new j(r,r.nextSibling,this,t):1===l.type?e=new l.ctor(r,l.name,l.strings,this,t):6===l.type&&(e=new X(r,this,t)),this.v.push(e),l=i[++a]}s!==(null==l?void 0:l.index)&&(r=z.nextNode(),s++)}return n}m(t){let e=0;for(const o of this.v)void 0!==o&&(void 0!==o.strings?(o._$AI(t,o,e),e+=o.strings.length-2):o._$AI(t[e])),e++}}class j{constructor(t,e,o,i){this.type=2,this._$C_=!0,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=o,this.options=i}get _$AU(){var t,e;return null!==(e=null===(t=this._$AM)||void 0===t?void 0:t._$AU)&&void 0!==e?e:this._$C_}get parentNode(){return this._$AA.parentNode}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=I(this,t,e),k(t)?t===L||null==t||""===t?(this._$AH!==L&&this._$AR(),this._$AH=L):t!==this._$AH&&t!==U&&this.$(t):void 0!==t._$litType$?this.T(t):void 0!==t.nodeType?this.A(t):(t=>{var e;return M(t)||"function"==typeof(null===(e=t)||void 0===e?void 0:e[Symbol.iterator])})(t)?this.M(t):this.$(t)}C(t,e=this._$AB){return this._$AA.parentNode.insertBefore(t,e)}A(t){this._$AH!==t&&(this._$AR(),this._$AH=this.C(t))}$(t){const e=this._$AA.nextSibling;null!==e&&3===e.nodeType&&(null===this._$AB?null===e.nextSibling:e===this._$AB.previousSibling)?e.data=t:this.A(E.createTextNode(t)),this._$AH=t}T(t){var e;const{values:o,_$litType$:i}=t,n="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=B.createElement(i.h,this.options)),i);if((null===(e=this._$AH)||void 0===e?void 0:e._$AD)===n)this._$AH.m(o);else{const t=new q(n,this),e=t.p(this.options);t.m(o),this.A(e),this._$AH=t}}_$AC(t){let e=Y.get(t.strings);return void 0===e&&Y.set(t.strings,e=new B(t)),e}M(t){M(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let o,i=0;for(const n of t)i===e.length?e.push(o=new j(this.C(C()),this.C(C()),this,this.options)):o=e[i],o._$AI(n),i++;i<e.length&&(this._$AR(o&&o._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){var o;for(null===(o=this._$AP)||void 0===o||o.call(this,!1,!0,e);t&&t!==this._$AB;){const e=t.nextSibling;t.remove(),t=e}}setConnected(t){var e;void 0===this._$AM&&(this._$C_=t,null===(e=this._$AP)||void 0===e||e.call(this,t))}}class F{constructor(t,e,o,i,n){this.type=1,this._$AH=L,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=n,o.length>2||""!==o[0]||""!==o[1]?(this._$AH=Array(o.length-1).fill(L),this.strings=o):this._$AH=L}get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}_$AI(t,e=this,o,i){const n=this.strings;let r=!1;if(void 0===n)t=I(this,t,e,0),r=!k(t)||t!==this._$AH&&t!==U,r&&(this._$AH=t);else{const i=t;let s,a;for(t=n[0],s=0;s<n.length-1;s++)a=I(this,i[o+s],e,s),a===U&&(a=this._$AH[s]),r||(r=!k(a)||a!==this._$AH[s]),a===L?t=L:t!==L&&(t+=(null!=a?a:"")+n[s+1]),this._$AH[s]=a}r&&!i&&this.P(t)}P(t){t===L?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,null!=t?t:"")}}class W extends F{constructor(){super(...arguments),this.type=3}P(t){this.element[this.name]=t===L?void 0:t}}class Z extends F{constructor(){super(...arguments),this.type=4}P(t){t&&t!==L?this.element.setAttribute(this.name,""):this.element.removeAttribute(this.name)}}class J extends F{constructor(){super(...arguments),this.type=5}_$AI(t,e=this){var o;if((t=null!==(o=I(this,t,e,0))&&void 0!==o?o:L)===U)return;const i=this._$AH,n=t===L&&i!==L||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,r=t!==L&&(i===L||n);n&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){var e,o;"function"==typeof this._$AH?this._$AH.call(null!==(o=null===(e=this.options)||void 0===e?void 0:e.host)&&void 0!==o?o:this.element,t):this._$AH.handleEvent(t)}}class X{constructor(t,e,o){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(t){I(this,t)}}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var K,G,Q,tt,et,ot;null===(v=(_=globalThis).litHtmlPlatformSupport)||void 0===v||v.call(_,B,j),(null!==(w=(b=globalThis).litHtmlVersions)&&void 0!==w?w:b.litHtmlVersions=[]).push("2.0.0-rc.4");class it extends m{constructor(){super(...arguments),this.renderOptions={host:this},this._$Dt=void 0}createRenderRoot(){var t,e;const o=super.createRenderRoot();return null!==(t=(e=this.renderOptions).renderBefore)&&void 0!==t||(e.renderBefore=o.firstChild),o}update(t){const e=this.render();super.update(t),this._$Dt=((t,e,o)=>{var i,n;const r=null!==(i=null==o?void 0:o.renderBefore)&&void 0!==i?i:e;let s=r._$litPart$;if(void 0===s){const t=null!==(n=null==o?void 0:o.renderBefore)&&void 0!==n?n:null;r._$litPart$=s=new j(e.insertBefore(C(),t),t,void 0,null!=o?o:{})}return s._$AI(t),s})(e,this.renderRoot,this.renderOptions)}connectedCallback(){var t;super.connectedCallback(),null===(t=this._$Dt)||void 0===t||t.setConnected(!0)}disconnectedCallback(){var t;super.disconnectedCallback(),null===(t=this._$Dt)||void 0===t||t.setConnected(!1)}render(){return U}}it.finalized=!0,it._$litElement$=!0,null===(G=(K=globalThis).litElementHydrateSupport)||void 0===G||G.call(K,{LitElement:it}),null===(tt=(Q=globalThis).litElementPlatformSupport)||void 0===tt||tt.call(Q,{LitElement:it}),(null!==(et=(ot=globalThis).litElementVersions)&&void 0!==et?et:ot.litElementVersions=[]).push("3.0.0-rc.3");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const nt=t=>e=>"function"==typeof e?((t,e)=>(window.customElements.define(t,e),e))(t,e):((t,e)=>{const{kind:o,elements:i}=e;return{kind:o,elements:i,finisher(e){window.customElements.define(t,e)}}})(t,e)
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */,rt=(t,e)=>"method"===e.kind&&e.descriptor&&!("value"in e.descriptor)?{...e,finisher(o){o.createProperty(e.key,t)}}:{kind:"field",key:Symbol(),placement:"own",descriptor:{},originalKey:e.key,initializer(){"function"==typeof e.initializer&&(this[e.key]=e.initializer.call(this))},finisher(o){o.createProperty(e.key,t)}};function st(t){return(e,o)=>void 0!==o?((t,e,o)=>{e.constructor.createProperty(o,t)})(t,e,o):rt(t,e)
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */}function at(t){return st({...t,state:!0})}var lt=/d{1,4}|M{1,4}|YY(?:YY)?|S{1,3}|Do|ZZ|Z|([HhMsDm])\1?|[aA]|"[^"]*"|'[^']*'/g,ht="[^\\s]+",dt=/\[([^]*?)\]/gm;function ct(t,e){for(var o=[],i=0,n=t.length;i<n;i++)o.push(t[i].substr(0,e));return o}var ut=function(t){return function(e,o){var i=o[t].map((function(t){return t.toLowerCase()})).indexOf(e.toLowerCase());return i>-1?i:null}};function pt(t){for(var e=[],o=1;o<arguments.length;o++)e[o-1]=arguments[o];for(var i=0,n=e;i<n.length;i++){var r=n[i];for(var s in r)t[s]=r[s]}return t}var ft=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],gt=["January","February","March","April","May","June","July","August","September","October","November","December"],mt=ct(gt,3),_t={dayNamesShort:ct(ft,3),dayNames:ft,monthNamesShort:mt,monthNames:gt,amPm:["am","pm"],DoFn:function(t){return t+["th","st","nd","rd"][t%10>3?0:(t-t%10!=10?1:0)*t%10]}},vt=pt({},_t),wt=function(t,e){for(void 0===e&&(e=2),t=String(t);t.length<e;)t="0"+t;return t},bt={D:function(t){return String(t.getDate())},DD:function(t){return wt(t.getDate())},Do:function(t,e){return e.DoFn(t.getDate())},d:function(t){return String(t.getDay())},dd:function(t){return wt(t.getDay())},ddd:function(t,e){return e.dayNamesShort[t.getDay()]},dddd:function(t,e){return e.dayNames[t.getDay()]},M:function(t){return String(t.getMonth()+1)},MM:function(t){return wt(t.getMonth()+1)},MMM:function(t,e){return e.monthNamesShort[t.getMonth()]},MMMM:function(t,e){return e.monthNames[t.getMonth()]},YY:function(t){return wt(String(t.getFullYear()),4).substr(2)},YYYY:function(t){return wt(t.getFullYear(),4)},h:function(t){return String(t.getHours()%12||12)},hh:function(t){return wt(t.getHours()%12||12)},H:function(t){return String(t.getHours())},HH:function(t){return wt(t.getHours())},m:function(t){return String(t.getMinutes())},mm:function(t){return wt(t.getMinutes())},s:function(t){return String(t.getSeconds())},ss:function(t){return wt(t.getSeconds())},S:function(t){return String(Math.round(t.getMilliseconds()/100))},SS:function(t){return wt(Math.round(t.getMilliseconds()/10),2)},SSS:function(t){return wt(t.getMilliseconds(),3)},a:function(t,e){return t.getHours()<12?e.amPm[0]:e.amPm[1]},A:function(t,e){return t.getHours()<12?e.amPm[0].toUpperCase():e.amPm[1].toUpperCase()},ZZ:function(t){var e=t.getTimezoneOffset();return(e>0?"-":"+")+wt(100*Math.floor(Math.abs(e)/60)+Math.abs(e)%60,4)},Z:function(t){var e=t.getTimezoneOffset();return(e>0?"-":"+")+wt(Math.floor(Math.abs(e)/60),2)+":"+wt(Math.abs(e)%60,2)}},yt=function(t){return+t-1},$t=[null,"[1-9]\\d?"],xt=[null,ht],At=["isPm",ht,function(t,e){var o=t.toLowerCase();return o===e.amPm[0]?0:o===e.amPm[1]?1:null}],St=["timezoneOffset","[^\\s]*?[\\+\\-]\\d\\d:?\\d\\d|[^\\s]*?Z?",function(t){var e=(t+"").match(/([+-]|\d\d)/gi);if(e){var o=60*+e[1]+parseInt(e[2],10);return"+"===e[0]?o:-o}return 0}],Et=(ut("monthNamesShort"),ut("monthNames"),{default:"ddd MMM DD YYYY HH:mm:ss",shortDate:"M/D/YY",mediumDate:"MMM D, YYYY",longDate:"MMMM D, YYYY",fullDate:"dddd, MMMM D, YYYY",isoDate:"YYYY-MM-DD",isoDateTime:"YYYY-MM-DDTHH:mm:ssZ",shortTime:"HH:mm",mediumTime:"HH:mm:ss",longTime:"HH:mm:ss.SSS"});var Ct,kt=function(t,e,o){if(void 0===e&&(e=Et.default),void 0===o&&(o={}),"number"==typeof t&&(t=new Date(t)),"[object Date]"!==Object.prototype.toString.call(t)||isNaN(t.getTime()))throw new Error("Invalid Date pass to format");var i=[];e=(e=Et[e]||e).replace(dt,(function(t,e){return i.push(e),"@@@"}));var n=pt(pt({},vt),o);return(e=e.replace(lt,(function(e){return bt[e](t,n)}))).replace(/@@@/g,(function(){return i.shift()}))};(function(){try{(new Date).toLocaleDateString("i")}catch(t){return"RangeError"===t.name}})(),function(){try{(new Date).toLocaleString("i")}catch(t){return"RangeError"===t.name}}(),function(){try{(new Date).toLocaleTimeString("i")}catch(t){return"RangeError"===t.name}}();!function(t){t.language="language",t.system="system",t.comma_decimal="comma_decimal",t.decimal_comma="decimal_comma",t.space_comma="space_comma",t.none="none"}(Ct||(Ct={}));const Mt={required:{icon:"tune",name:"Required",secondary:"Required options for this card to function",show:!0},actions:{icon:"gesture-tap-hold",name:"Actions",secondary:"Perform actions based on tapping/clicking",show:!1,options:{tap:{icon:"gesture-tap",name:"Tap",secondary:"Set the action to perform on tap",show:!1},hold:{icon:"gesture-tap-hold",name:"Hold",secondary:"Set the action to perform on hold",show:!1},double_tap:{icon:"gesture-double-tap",name:"Double Tap",secondary:"Set the action to perform on double tap",show:!1}}},appearance:{icon:"palette",name:"Appearance",secondary:"Customize the name, icon, etc",show:!1}};let Tt=class extends it{constructor(){super(...arguments),this._initialized=!1}setConfig(t){this._config=t,this.loadCardHelpers()}shouldUpdate(){return this._initialized||this._initialize(),!0}get _name(){var t;return(null===(t=this._config)||void 0===t?void 0:t.name)||""}get _entity(){var t;return(null===(t=this._config)||void 0===t?void 0:t.entity)||""}get _show_title(){var t;return(null===(t=this._config)||void 0===t?void 0:t.show_title)||!1}get _show_error(){var t;return(null===(t=this._config)||void 0===t?void 0:t.show_error)||!1}get _tap_action(){var t;return(null===(t=this._config)||void 0===t?void 0:t.tap_action)||{action:"more-info"}}get _hold_action(){var t;return(null===(t=this._config)||void 0===t?void 0:t.hold_action)||{action:"none"}}get _double_tap_action(){var t;return(null===(t=this._config)||void 0===t?void 0:t.double_tap_action)||{action:"none"}}render(){if(!this.hass||!this._helpers)return V``;this._helpers.importMoreInfoControl("climate");const t=Object.keys(this.hass.states).filter(t=>"timer"===t.substr(0,t.indexOf(".")));return V`
      <div class="card-config">
        <div class="option" @click=${this._toggleOption} .option=${"required"}>
          <div class="row">
            <ha-icon .icon=${"mdi:"+Mt.required.icon}></ha-icon>
            <div class="title">${Mt.required.name}</div>
          </div>
          <div class="secondary">${Mt.required.secondary}</div>
        </div>
        ${Mt.required.show?V`
              <div class="values">
                <paper-dropdown-menu
                  label="Entity (Required)"
                  @value-changed=${this._valueChanged}
                  .configValue=${"entity"}
                >
                  <paper-listbox slot="dropdown-content" .selected=${t.indexOf(this._entity)}>
                    ${t.map(t=>V`
                        <paper-item>${t}</paper-item>
                      `)}
                  </paper-listbox>
                </paper-dropdown-menu>
              </div>
            `:""}

        <div class="option" @click=${this._toggleOption} .option=${"appearance"}>
          <div class="row">
            <ha-icon .icon=${"mdi:"+Mt.appearance.icon}></ha-icon>
            <div class="title">${Mt.appearance.name}</div>
          </div>
          <div class="secondary">${Mt.appearance.secondary}</div>
        </div>
        ${Mt.appearance.show?V`
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
    `}_initialize(){void 0!==this.hass&&void 0!==this._config&&void 0!==this._helpers&&(this._initialized=!0)}async loadCardHelpers(){this._helpers=await window.loadCardHelpers()}_toggleAction(t){this._toggleThing(t,Mt.actions.options)}_toggleOption(t){this._toggleThing(t,Mt)}_toggleThing(t,e){const o=!e[t.target.option].show;for(const[t]of Object.entries(e))e[t].show=!1;e[t.target.option].show=o,this._toggle=!this._toggle}_valueChanged(t){if(!this._config||!this.hass)return;const e=t.target;if(this["_"+e.configValue]!==e.value){if(e.configValue)if(""===e.value){const t=Object.assign({},this._config);delete t[e.configValue],this._config=t}else this._config=Object.assign(Object.assign({},this._config),{[e.configValue]:void 0!==e.checked?e.checked:e.value});!function(t,e,o,i){i=i||{},o=null==o?{}:o;var n=new Event(e,{bubbles:void 0===i.bubbles||i.bubbles,cancelable:Boolean(i.cancelable),composed:void 0===i.composed||i.composed});n.detail=o,t.dispatchEvent(n)}(this,"config-changed",{config:this._config})}}static get styles(){return s`
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
    `}};t([st({attribute:!1})],Tt.prototype,"hass",void 0),t([at()],Tt.prototype,"_config",void 0),t([at()],Tt.prototype,"_toggle",void 0),t([at()],Tt.prototype,"_helpers",void 0),Tt=t([nt("flipdown-timer-card-editor")],Tt);var Nt={version:"Version",invalid_configuration:"Invalid configuration",show_warning:"Show Warning",show_error:"Show Error"},Ht={common:Nt},Rt={version:"Versjon",invalid_configuration:"Ikke gyldig konfiguration",show_warning:"Vis advarsel"},Dt={common:Rt};const Pt={en:Object.freeze({__proto__:null,common:Nt,default:Ht}),nb:Object.freeze({__proto__:null,common:Rt,default:Dt})};function Ot(t,e="",o=""){const i=(localStorage.getItem("selectedLanguage")||"en").replace(/['"]+/g,"").replace("-","_");let n;try{n=t.split(".").reduce((t,e)=>t[e],Pt[i])}catch(e){n=t.split(".").reduce((t,e)=>t[e],Pt.en)}return void 0===n&&(n=t.split(".").reduce((t,e)=>t[e],Pt.en)),""!==e&&""!==o&&(n=n.replace(e,o)),n}function Vt(t,e){return(t=t.toString()).length<e?Vt("0"+t,e):t}function Ut(t,e){e.forEach(e=>{t.appendChild(e)})}class Lt{constructor(t,e,o={}){if("number"!=typeof t)throw new Error(`FlipDown: Constructor expected unix timestamp, got ${typeof t} instead.`);this.rt=null,this.button1=null,this.button2=null,this.version="0.3.2",this.initialised=!1,this.active=!1,this.now=this._getTime(),this.epoch=t,this.countdownEnded=!1,this.hasEndedCallback=null,this.element=e,this.rotors=[],this.rotorLeafFront=[],this.rotorLeafRear=[],this.rotorTops=[],this.rotorBottoms=[],this.countdown=null,this.daysRemaining=0,this.clockValues={},this.clockStrings={},this.clockValuesAsString=[],this.prevClockValuesAsString=[],this.opts=this._parseOptions(o),this._setOptions()}start(){return this.initialised||this._init(),this.rt=null,this.active=!0,this._tick(),this}_startInterval(){clearInterval(this.countdown),this.active&&(this.countdown=window.setInterval(this._tick.bind(this),1e3))}stop(){clearInterval(this.countdown),this.countdown=null,this.active=!1}ifEnded(t){return this.hasEndedCallback=function(){t(),this.hasEndedCallback=null},this}_getTime(){return(new Date).getTime()/1e3}_hasCountdownEnded(){return this.epoch-this.now<0?(this.countdownEnded=!0,null!=this.hasEndedCallback&&(this.hasEndedCallback(),this.hasEndedCallback=null),!0):(this.countdownEnded=!1,!1)}_parseOptions(t){let e=["Days","Hours","Minutes","Seconds"];return t.headings&&4===t.headings.length&&(e=t.headings),{theme:t.hasOwnProperty("theme")&&t.theme?t.theme:"hass",showHeader:!(!t.hasOwnProperty("show_header")||!t.show_header)&&t.show_header,showHour:!(!t.hasOwnProperty("show_hour")||!t.show_hour)&&t.show_hour,btLocation:t.bt_location,headings:e}}_setOptions(){this.element.classList.add("flipdown__theme-"+this.opts.theme)}_init(){this.initialised=!0,this._hasCountdownEnded()?this.daysremaining=0:this.daysremaining=Math.floor((this.epoch-this.now)/86400).toString().length;for(let t=0;t<6;t++)this.rotors.push(this._createRotor(0));let t=0;for(let e=0;e<3;e++){const o=[];for(let e=0;e<2;e++)this.rotors[t].setAttribute("id","d"+(1-e)),o.push(this.rotors[t]),t++;this.element.appendChild(this._createRotorGroup(o,e+1))}return this.element.appendChild(this._createButton()),this.rotorLeafFront=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-leaf-front")),this.rotorLeafRear=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-leaf-rear")),this.rotorTop=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-top")),this.rotorBottom=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-bottom")),this._tick(),this._updateClockValues(!0),this}_createRotorGroup(t,e){const o=document.createElement("div");o.className="rotor-group",this.opts.showHour||1!=e||(o.className+=" hide"),o.setAttribute("id",this.opts.headings[e]);const i=document.createElement("div");if(i.className="rotor-group-heading",i.setAttribute("data-before",this.opts.headings[e]),this.opts.showHeader&&o.appendChild(i),Ut(o,t),e<3){const t=document.createElement("div");t.className="delimeter";const e=document.createElement("span");e.className="delimeter-span-top";const i=document.createElement("span");i.className="delimeter-span-bottom",Ut(t,[e,i]),o.appendChild(t)}return o}_createButton(){const t=document.createElement("div");t.className="button-group","bottom"==this.opts.btLocation?t.className+=" button-bottom":"hide"==this.opts.btLocation?t.className+=" hide":t.className+=" button-right";const e=document.createElement("div");e.className="button-group-heading",e.setAttribute("data-before","");const o=document.createElement("div");return o.className="btn",this.button1=document.createElement("button"),this.button2=document.createElement("button"),this.button1.className="btn-top",this.button2.className="btn-bottom",this.opts.showHeader?Ut(t,[e,o]):Ut(t,[o]),Ut(o,[this.button1,this.button2]),t}_createRotor(t=0){const e=document.createElement("div"),o=document.createElement("div"),i=document.createElement("figure"),n=document.createElement("figure"),r=document.createElement("div"),s=document.createElement("div");return e.className="rotor",o.className="rotor-leaf",i.className="rotor-leaf-rear",n.className="rotor-leaf-front",r.className="rotor-top",s.className="rotor-bottom",n.textContent=t,i.textContent=t,r.textContent=t,s.textContent=t,Ut(e,[o,r,s]),Ut(o,[i,n]),e}_updator(t){this.epoch=t}_tick(t=!1){this.now=this._getTime();let e=Math.floor(this.epoch-this.now<=0?0:this.epoch-this.now);null!=this.rt&&(e=this.rt),this.clockValues.d=Math.floor(e/86400),e-=86400*this.clockValues.d,this.clockValues.h=Math.floor(e/3600),e-=3600*this.clockValues.h,this.clockValues.m=Math.floor(e/60),e-=60*this.clockValues.m,this.clockValues.s=Math.floor(e),this._updateClockValues(!1,t)}_updateClockValues(t=!1,e=!1){function o(){this.rotorTop.forEach((t,e)=>{t.textContent!=this.clockValuesAsString[e]&&(t.textContent=this.clockValuesAsString[e])})}function i(){this.rotorLeafRear.forEach((t,e)=>{if(t.textContent!=this.clockValuesAsString[e]){t.textContent=this.clockValuesAsString[e],t.parentElement.classList.add("flipped");const o=setInterval(function(){t.parentElement.classList.remove("flipped"),clearInterval(o)}.bind(this),500)}})}this.clockStrings.d=Vt(this.clockValues.d,2),this.clockStrings.h=Vt(this.clockValues.h,2),this.clockStrings.m=Vt(this.clockValues.m,2),this.clockStrings.s=Vt(this.clockValues.s,2),this.clockValuesAsString=(this.clockStrings.h+this.clockStrings.m+this.clockStrings.s).split(""),o.call(this),i.call(this),t?(o.call(this),i.call(this)):(setTimeout(function(){this.rotorLeafFront.forEach((t,e)=>{t.textContent=this.prevClockValuesAsString[e]})}.bind(this),500),setTimeout(function(){this.rotorBottom.forEach((t,e)=>{t.textContent=this.prevClockValuesAsString[e]})}.bind(this),500)),this.prevClockValuesAsString=this.clockValuesAsString}}const Yt=s`
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

  .flipdown .rotor-group-heading {
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

  .flipdown .rotor-group:nth-child(1) .rotor-group-heading:before {
    content: attr(data-before);
  }

  .flipdown .rotor-group:nth-child(2) .rotor-group-heading:before {
    content: attr(data-before);
  }

  .flipdown .rotor-group:nth-child(3) .rotor-group-heading:before {
    content: attr(data-before);
  }

  .flipdown .rotor-group:nth-child(4) .rotor-group-heading:before {
    content: attr(data-before);
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
    border-radius: 4px 4px 0px 0px;
  }

  .flipdown .rotor-leaf-rear {
    line-height: 0px;
    border-radius: 0px 0px 4px 4px;
    transform: rotateX(-180deg);
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
`;function zt(t){const e=t.split(":").map(Number);return 3600*e[0]+60*e[1]+e[2]}console.info(`%c  FLIPDOWN-TIMER-CARD \n%c  ${Ot("common.version")} 1.0.0    `,"color: orange; font-weight: bold; background: black","color: white; font-weight: bold; background: dimgray"),window.customCards=window.customCards||[],window.customCards.push({type:"flipdown-timer-card",name:"Flipdown Timer Card",description:"A template custom card for you to create something awesome"});let Bt=[];let It=class extends it{constructor(){super(...arguments),this.fd=null}static async getConfigElement(){return document.createElement("flipdown-timer-card-editor")}static getStubConfig(){return{}}setConfig(t){if(!t)throw new Error(Ot("common.invalid_configuration"));t.test_gui&&function(){var t=document.querySelector("home-assistant");if(t=(t=(t=(t=(t=(t=(t=(t=t&&t.shadowRoot)&&t.querySelector("home-assistant-main"))&&t.shadowRoot)&&t.querySelector("app-drawer-layout partial-panel-resolver"))&&t.shadowRoot||t)&&t.querySelector("ha-panel-lovelace"))&&t.shadowRoot)&&t.querySelector("hui-root")){var e=t.lovelace;return e.current_view=t.___curView,e}return null}().setEditMode(!0),this.config=Object.assign({},t),this.config.styles||(this.config.styles={rotor:!1,button:!1})}shouldUpdate(t){return!!this.config&&function(t,e,o){if(e.has("config")||o)return!0;if(t.config.entity){var i=e.get("hass");return!i||i.states[t.config.entity]!==t.hass.states[t.config.entity]}return!1}(this,t,!1)}disconnectedCallback(){super.disconnectedCallback(),this.fd&&this.fd.stop()}connectedCallback(){var t;if(super.connectedCallback(),this.config&&this.config.entity){(null===(t=this.hass)||void 0===t?void 0:t.states[this.config.entity])&&this._start()}}_start(){var t;const e=this.hass.states[this.config.entity],o=null===(t=this.shadowRoot)||void 0===t?void 0:t.getElementById("flipdown");if(!o)return!1;if(o&&!this.fd&&this._init(),"active"===e.state){this.fd.button1.textContent="stop",this.fd.button2.textContent="cancel";let t=zt(e.attributes.remaining);const o=new Date(e.last_changed).getTime();t=Math.max(t+o/1e3,0),this.fd._updator(t),this.fd.start(),Bt.push(this),Bt=Bt.filter(t=>null!=t.offsetParent),Bt.forEach(t=>{t.fd._startInterval()})}else if("idle"===e.state)this.fd.stop(),this.fd.button1.textContent="start",this.fd.button2.textContent="reset",this._reset();else if("paused"===e.state){this.fd.stop(),this.fd.button1.textContent="resume",this.fd.button2.textContent="cancel";const t=zt(e.attributes.remaining);this.fd.rt=t,this.fd._tick(!0)}return!0}_clear(){this.fd=null}_reset(){const t=this.hass.states[this.config.entity],e=zt(this.config.duration?this.config.duration:t.attributes.duration);this.fd.rt=e,this.fd._tick(!0)}updated(t){if(super.updated(t),t.has("hass")){const e=this.hass.states[this.config.entity],o=t.get("hass");(o?o.states[this.config.entity]:void 0)!==e?this._start():e||this._clear()}}render(){return this.config.show_warning?this._showWarning(Ot("common.show_warning")):this.config.show_error?this._showError(Ot("common.show_error")):V`
      <ha-card>
        <div class="card-content">
          ${this.config.show_title?V`<hui-generic-entity-row .hass=${this.hass} .config=${this.config}></hui-generic-entity-row>`:V``}
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
    `}_init(){var t;const e=null===(t=this.shadowRoot)||void 0===t?void 0:t.getElementById("flipdown"),o=(new Date).getTime()/1e3;this.fd||(this.fd=new Lt(o,e,{show_header:!1,show_hour:this.config.show_hour,bt_location:this.config.styles.button&&this.config.styles.button.hasOwnProperty("location")?this.config.styles.button.location:"right",theme:this.config.theme})._init()),this.config.entity&&(null==e||e.querySelectorAll(".rotor").forEach((t,e)=>{t.addEventListener("click",()=>{this._handleRotorClick(t,e)})}),this.fd.button1.addEventListener("click",()=>this._handleBtnClick(1)),this.fd.button2.addEventListener("click",()=>this._handleBtnClick(2)))}firstUpdated(){this._init()}_handleRotorClick(t,e){if("idle"!==this.hass.states[this.config.entity].state)return!1;const o=Number(t.querySelector(".rotor-leaf-rear").textContent),i=o<[5,9,5,9,5,9][e]?o+1:0;return t.querySelector(".rotor-leaf-rear").textContent=i,t.querySelector(".rotor-top").textContent=i,t.querySelector(".rotor-leaf").classList.add("flippedf"),setTimeout(()=>{t.querySelector(".rotor-leaf-front").textContent=i,t.querySelector(".rotor-bottom").textContent=i,t.querySelector(".rotor-leaf").classList.remove("flippedf")},200),!0}_handleBtnClick(t){const e=this.hass.states[this.config.entity].state;switch(t){case 1:const t=this._getRotorTime();"idle"===e&&"00:00:00"!=t?this.hass.callService("timer","start",{entity_id:this.config.entity,duration:t}):"active"===e?this.hass.callService("timer","pause",{entity_id:this.config.entity}):"paused"===e&&this.hass.callService("timer","start",{entity_id:this.config.entity});break;case 2:"idle"===e?this._reset():this.hass.callService("timer","cancel",{entity_id:this.config.entity})}}_getRotorTime(){let t="";return this.fd.rotorTop.forEach((e,o)=>{t+=e.textContent,1!=o&&3!=o||(t+=":")}),t}_showWarning(t){return V`
      <hui-warning>${t}</hui-warning>
    `}_showError(t){const e=document.createElement("hui-error-card");return e.setConfig({type:"error",error:t,origConfig:this.config}),V`
      ${e}
    `}static get styles(){return r(Yt)}};t([st({attribute:!1})],It.prototype,"hass",void 0),t([st({attribute:!1})],It.prototype,"fd",void 0),t([at()],It.prototype,"config",void 0),It=t([nt("flipdown-timer-card")],It);export{It as FlipdownTimer,zt as durationToSeconds};
