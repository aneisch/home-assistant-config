/******************************************************************************
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
/* global Reflect, Promise, SuppressedError, Symbol, Iterator */


function __decorate(decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
}

typeof SuppressedError === "function" ? SuppressedError : function (error, suppressed, message) {
    var e = new Error(message);
    return e.name = "SuppressedError", e.error = error, e.suppressed = suppressed, e;
};

/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t$2=window,e$4=t$2.ShadowRoot&&(void 0===t$2.ShadyCSS||t$2.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s$3=Symbol(),n$5=new WeakMap;let o$3 = class o{constructor(t,e,n){if(this._$cssResult$=true,n!==s$3)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e;}get styleSheet(){let t=this.o;const s=this.t;if(e$4&&void 0===t){const e=void 0!==s&&1===s.length;e&&(t=n$5.get(s)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),e&&n$5.set(s,t));}return t}toString(){return this.cssText}};const r$2=t=>new o$3("string"==typeof t?t:t+"",void 0,s$3),i$2=(t,...e)=>{const n=1===t.length?t[0]:e.reduce(((e,s,n)=>e+(t=>{if(true===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[n+1]),t[0]);return new o$3(n,t,s$3)},S$1=(s,n)=>{e$4?s.adoptedStyleSheets=n.map((t=>t instanceof CSSStyleSheet?t:t.styleSheet)):n.forEach((e=>{const n=document.createElement("style"),o=t$2.litNonce;void 0!==o&&n.setAttribute("nonce",o),n.textContent=e.cssText,s.appendChild(n);}));},c$1=e$4?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return r$2(e)})(t):t;

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */var s$2;const e$3=window,r$1=e$3.trustedTypes,h$1=r$1?r$1.emptyScript:"",o$2=e$3.reactiveElementPolyfillSupport,n$4={toAttribute(t,i){switch(i){case Boolean:t=t?h$1:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t);}return t},fromAttribute(t,i){let s=t;switch(i){case Boolean:s=null!==t;break;case Number:s=null===t?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t);}catch(t){s=null;}}return s}},a$1=(t,i)=>i!==t&&(i==i||t==t),l$2={attribute:true,type:String,converter:n$4,reflect:false,hasChanged:a$1},d$1="finalized";let u$1 = class u extends HTMLElement{constructor(){super(),this._$Ei=new Map,this.isUpdatePending=false,this.hasUpdated=false,this._$El=null,this._$Eu();}static addInitializer(t){var i;this.finalize(),(null!==(i=this.h)&&void 0!==i?i:this.h=[]).push(t);}static get observedAttributes(){this.finalize();const t=[];return this.elementProperties.forEach(((i,s)=>{const e=this._$Ep(s,i);void 0!==e&&(this._$Ev.set(e,s),t.push(e));})),t}static createProperty(t,i=l$2){if(i.state&&(i.attribute=false),this.finalize(),this.elementProperties.set(t,i),!i.noAccessor&&!this.prototype.hasOwnProperty(t)){const s="symbol"==typeof t?Symbol():"__"+t,e=this.getPropertyDescriptor(t,s,i);void 0!==e&&Object.defineProperty(this.prototype,t,e);}}static getPropertyDescriptor(t,i,s){return {get(){return this[i]},set(e){const r=this[t];this[i]=e,this.requestUpdate(t,r,s);},configurable:true,enumerable:true}}static getPropertyOptions(t){return this.elementProperties.get(t)||l$2}static finalize(){if(this.hasOwnProperty(d$1))return  false;this[d$1]=true;const t=Object.getPrototypeOf(this);if(t.finalize(),void 0!==t.h&&(this.h=[...t.h]),this.elementProperties=new Map(t.elementProperties),this._$Ev=new Map,this.hasOwnProperty("properties")){const t=this.properties,i=[...Object.getOwnPropertyNames(t),...Object.getOwnPropertySymbols(t)];for(const s of i)this.createProperty(s,t[s]);}return this.elementStyles=this.finalizeStyles(this.styles),true}static finalizeStyles(i){const s=[];if(Array.isArray(i)){const e=new Set(i.flat(1/0).reverse());for(const i of e)s.unshift(c$1(i));}else void 0!==i&&s.push(c$1(i));return s}static _$Ep(t,i){const s=i.attribute;return  false===s?void 0:"string"==typeof s?s:"string"==typeof t?t.toLowerCase():void 0}_$Eu(){var t;this._$E_=new Promise((t=>this.enableUpdating=t)),this._$AL=new Map,this._$Eg(),this.requestUpdate(),null===(t=this.constructor.h)||void 0===t||t.forEach((t=>t(this)));}addController(t){var i,s;(null!==(i=this._$ES)&&void 0!==i?i:this._$ES=[]).push(t),void 0!==this.renderRoot&&this.isConnected&&(null===(s=t.hostConnected)||void 0===s||s.call(t));}removeController(t){var i;null===(i=this._$ES)||void 0===i||i.splice(this._$ES.indexOf(t)>>>0,1);}_$Eg(){this.constructor.elementProperties.forEach(((t,i)=>{this.hasOwnProperty(i)&&(this._$Ei.set(i,this[i]),delete this[i]);}));}createRenderRoot(){var t;const s=null!==(t=this.shadowRoot)&&void 0!==t?t:this.attachShadow(this.constructor.shadowRootOptions);return S$1(s,this.constructor.elementStyles),s}connectedCallback(){var t;void 0===this.renderRoot&&(this.renderRoot=this.createRenderRoot()),this.enableUpdating(true),null===(t=this._$ES)||void 0===t||t.forEach((t=>{var i;return null===(i=t.hostConnected)||void 0===i?void 0:i.call(t)}));}enableUpdating(t){}disconnectedCallback(){var t;null===(t=this._$ES)||void 0===t||t.forEach((t=>{var i;return null===(i=t.hostDisconnected)||void 0===i?void 0:i.call(t)}));}attributeChangedCallback(t,i,s){this._$AK(t,s);}_$EO(t,i,s=l$2){var e;const r=this.constructor._$Ep(t,s);if(void 0!==r&&true===s.reflect){const h=(void 0!==(null===(e=s.converter)||void 0===e?void 0:e.toAttribute)?s.converter:n$4).toAttribute(i,s.type);this._$El=t,null==h?this.removeAttribute(r):this.setAttribute(r,h),this._$El=null;}}_$AK(t,i){var s;const e=this.constructor,r=e._$Ev.get(t);if(void 0!==r&&this._$El!==r){const t=e.getPropertyOptions(r),h="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==(null===(s=t.converter)||void 0===s?void 0:s.fromAttribute)?t.converter:n$4;this._$El=r,this[r]=h.fromAttribute(i,t.type),this._$El=null;}}requestUpdate(t,i,s){let e=true;void 0!==t&&(((s=s||this.constructor.getPropertyOptions(t)).hasChanged||a$1)(this[t],i)?(this._$AL.has(t)||this._$AL.set(t,i),true===s.reflect&&this._$El!==t&&(void 0===this._$EC&&(this._$EC=new Map),this._$EC.set(t,s))):e=false),!this.isUpdatePending&&e&&(this._$E_=this._$Ej());}async _$Ej(){this.isUpdatePending=true;try{await this._$E_;}catch(t){Promise.reject(t);}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var t;if(!this.isUpdatePending)return;this.hasUpdated,this._$Ei&&(this._$Ei.forEach(((t,i)=>this[i]=t)),this._$Ei=void 0);let i=false;const s=this._$AL;try{i=this.shouldUpdate(s),i?(this.willUpdate(s),null===(t=this._$ES)||void 0===t||t.forEach((t=>{var i;return null===(i=t.hostUpdate)||void 0===i?void 0:i.call(t)})),this.update(s)):this._$Ek();}catch(t){throw i=false,this._$Ek(),t}i&&this._$AE(s);}willUpdate(t){}_$AE(t){var i;null===(i=this._$ES)||void 0===i||i.forEach((t=>{var i;return null===(i=t.hostUpdated)||void 0===i?void 0:i.call(t)})),this.hasUpdated||(this.hasUpdated=true,this.firstUpdated(t)),this.updated(t);}_$Ek(){this._$AL=new Map,this.isUpdatePending=false;}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$E_}shouldUpdate(t){return  true}update(t){ void 0!==this._$EC&&(this._$EC.forEach(((t,i)=>this._$EO(i,this[i],t))),this._$EC=void 0),this._$Ek();}updated(t){}firstUpdated(t){}};u$1[d$1]=true,u$1.elementProperties=new Map,u$1.elementStyles=[],u$1.shadowRootOptions={mode:"open"},null==o$2||o$2({ReactiveElement:u$1}),(null!==(s$2=e$3.reactiveElementVersions)&&void 0!==s$2?s$2:e$3.reactiveElementVersions=[]).push("1.6.3");

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var t$1;const i$1=window,s$1=i$1.trustedTypes,e$2=s$1?s$1.createPolicy("lit-html",{createHTML:t=>t}):void 0,o$1="$lit$",n$3=`lit$${(Math.random()+"").slice(9)}$`,l$1="?"+n$3,h=`<${l$1}>`,r=document,u=()=>r.createComment(""),d=t=>null===t||"object"!=typeof t&&"function"!=typeof t,c=Array.isArray,v=t=>c(t)||"function"==typeof(null==t?void 0:t[Symbol.iterator]),a="[ \t\n\f\r]",f=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,_=/-->/g,m=/>/g,p=RegExp(`>|${a}(?:([^\\s"'>=/]+)(${a}*=${a}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),g=/'/g,$=/"/g,y=/^(?:script|style|textarea|title)$/i,w=t=>(i,...s)=>({_$litType$:t,strings:i,values:s}),x=w(1),T=Symbol.for("lit-noChange"),A=Symbol.for("lit-nothing"),E=new WeakMap,C=r.createTreeWalker(r,129,null,false);function P(t,i){if(!Array.isArray(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==e$2?e$2.createHTML(i):i}const V=(t,i)=>{const s=t.length-1,e=[];let l,r=2===i?"<svg>":"",u=f;for(let i=0;i<s;i++){const s=t[i];let d,c,v=-1,a=0;for(;a<s.length&&(u.lastIndex=a,c=u.exec(s),null!==c);)a=u.lastIndex,u===f?"!--"===c[1]?u=_:void 0!==c[1]?u=m:void 0!==c[2]?(y.test(c[2])&&(l=RegExp("</"+c[2],"g")),u=p):void 0!==c[3]&&(u=p):u===p?">"===c[0]?(u=null!=l?l:f,v=-1):void 0===c[1]?v=-2:(v=u.lastIndex-c[2].length,d=c[1],u=void 0===c[3]?p:'"'===c[3]?$:g):u===$||u===g?u=p:u===_||u===m?u=f:(u=p,l=void 0);const w=u===p&&t[i+1].startsWith("/>")?" ":"";r+=u===f?s+h:v>=0?(e.push(d),s.slice(0,v)+o$1+s.slice(v)+n$3+w):s+n$3+(-2===v?(e.push(void 0),i):w);}return [P(t,r+(t[s]||"<?>")+(2===i?"</svg>":"")),e]};class N{constructor({strings:t,_$litType$:i},e){let h;this.parts=[];let r=0,d=0;const c=t.length-1,v=this.parts,[a,f]=V(t,i);if(this.el=N.createElement(a,e),C.currentNode=this.el.content,2===i){const t=this.el.content,i=t.firstChild;i.remove(),t.append(...i.childNodes);}for(;null!==(h=C.nextNode())&&v.length<c;){if(1===h.nodeType){if(h.hasAttributes()){const t=[];for(const i of h.getAttributeNames())if(i.endsWith(o$1)||i.startsWith(n$3)){const s=f[d++];if(t.push(i),void 0!==s){const t=h.getAttribute(s.toLowerCase()+o$1).split(n$3),i=/([.?@])?(.*)/.exec(s);v.push({type:1,index:r,name:i[2],strings:t,ctor:"."===i[1]?H:"?"===i[1]?L:"@"===i[1]?z:k});}else v.push({type:6,index:r});}for(const i of t)h.removeAttribute(i);}if(y.test(h.tagName)){const t=h.textContent.split(n$3),i=t.length-1;if(i>0){h.textContent=s$1?s$1.emptyScript:"";for(let s=0;s<i;s++)h.append(t[s],u()),C.nextNode(),v.push({type:2,index:++r});h.append(t[i],u());}}}else if(8===h.nodeType)if(h.data===l$1)v.push({type:2,index:r});else {let t=-1;for(;-1!==(t=h.data.indexOf(n$3,t+1));)v.push({type:7,index:r}),t+=n$3.length-1;}r++;}}static createElement(t,i){const s=r.createElement("template");return s.innerHTML=t,s}}function S(t,i,s=t,e){var o,n,l,h;if(i===T)return i;let r=void 0!==e?null===(o=s._$Co)||void 0===o?void 0:o[e]:s._$Cl;const u=d(i)?void 0:i._$litDirective$;return (null==r?void 0:r.constructor)!==u&&(null===(n=null==r?void 0:r._$AO)||void 0===n||n.call(r,false),void 0===u?r=void 0:(r=new u(t),r._$AT(t,s,e)),void 0!==e?(null!==(l=(h=s)._$Co)&&void 0!==l?l:h._$Co=[])[e]=r:s._$Cl=r),void 0!==r&&(i=S(t,r._$AS(t,i.values),r,e)),i}class M{constructor(t,i){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=i;}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){var i;const{el:{content:s},parts:e}=this._$AD,o=(null!==(i=null==t?void 0:t.creationScope)&&void 0!==i?i:r).importNode(s,true);C.currentNode=o;let n=C.nextNode(),l=0,h=0,u=e[0];for(;void 0!==u;){if(l===u.index){let i;2===u.type?i=new R(n,n.nextSibling,this,t):1===u.type?i=new u.ctor(n,u.name,u.strings,this,t):6===u.type&&(i=new Z(n,this,t)),this._$AV.push(i),u=e[++h];}l!==(null==u?void 0:u.index)&&(n=C.nextNode(),l++);}return C.currentNode=r,o}v(t){let i=0;for(const s of this._$AV) void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,i),i+=s.strings.length-2):s._$AI(t[i])),i++;}}class R{constructor(t,i,s,e){var o;this.type=2,this._$AH=A,this._$AN=void 0,this._$AA=t,this._$AB=i,this._$AM=s,this.options=e,this._$Cp=null===(o=null==e?void 0:e.isConnected)||void 0===o||o;}get _$AU(){var t,i;return null!==(i=null===(t=this._$AM)||void 0===t?void 0:t._$AU)&&void 0!==i?i:this._$Cp}get parentNode(){let t=this._$AA.parentNode;const i=this._$AM;return void 0!==i&&11===(null==t?void 0:t.nodeType)&&(t=i.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,i=this){t=S(this,t,i),d(t)?t===A||null==t||""===t?(this._$AH!==A&&this._$AR(),this._$AH=A):t!==this._$AH&&t!==T&&this._(t):void 0!==t._$litType$?this.g(t):void 0!==t.nodeType?this.$(t):v(t)?this.T(t):this._(t);}k(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}$(t){this._$AH!==t&&(this._$AR(),this._$AH=this.k(t));}_(t){this._$AH!==A&&d(this._$AH)?this._$AA.nextSibling.data=t:this.$(r.createTextNode(t)),this._$AH=t;}g(t){var i;const{values:s,_$litType$:e}=t,o="number"==typeof e?this._$AC(t):(void 0===e.el&&(e.el=N.createElement(P(e.h,e.h[0]),this.options)),e);if((null===(i=this._$AH)||void 0===i?void 0:i._$AD)===o)this._$AH.v(s);else {const t=new M(o,this),i=t.u(this.options);t.v(s),this.$(i),this._$AH=t;}}_$AC(t){let i=E.get(t.strings);return void 0===i&&E.set(t.strings,i=new N(t)),i}T(t){c(this._$AH)||(this._$AH=[],this._$AR());const i=this._$AH;let s,e=0;for(const o of t)e===i.length?i.push(s=new R(this.k(u()),this.k(u()),this,this.options)):s=i[e],s._$AI(o),e++;e<i.length&&(this._$AR(s&&s._$AB.nextSibling,e),i.length=e);}_$AR(t=this._$AA.nextSibling,i){var s;for(null===(s=this._$AP)||void 0===s||s.call(this,false,true,i);t&&t!==this._$AB;){const i=t.nextSibling;t.remove(),t=i;}}setConnected(t){var i;void 0===this._$AM&&(this._$Cp=t,null===(i=this._$AP)||void 0===i||i.call(this,t));}}class k{constructor(t,i,s,e,o){this.type=1,this._$AH=A,this._$AN=void 0,this.element=t,this.name=i,this._$AM=e,this.options=o,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=A;}get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}_$AI(t,i=this,s,e){const o=this.strings;let n=false;if(void 0===o)t=S(this,t,i,0),n=!d(t)||t!==this._$AH&&t!==T,n&&(this._$AH=t);else {const e=t;let l,h;for(t=o[0],l=0;l<o.length-1;l++)h=S(this,e[s+l],i,l),h===T&&(h=this._$AH[l]),n||(n=!d(h)||h!==this._$AH[l]),h===A?t=A:t!==A&&(t+=(null!=h?h:"")+o[l+1]),this._$AH[l]=h;}n&&!e&&this.j(t);}j(t){t===A?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,null!=t?t:"");}}class H extends k{constructor(){super(...arguments),this.type=3;}j(t){this.element[this.name]=t===A?void 0:t;}}const I=s$1?s$1.emptyScript:"";class L extends k{constructor(){super(...arguments),this.type=4;}j(t){t&&t!==A?this.element.setAttribute(this.name,I):this.element.removeAttribute(this.name);}}class z extends k{constructor(t,i,s,e,o){super(t,i,s,e,o),this.type=5;}_$AI(t,i=this){var s;if((t=null!==(s=S(this,t,i,0))&&void 0!==s?s:A)===T)return;const e=this._$AH,o=t===A&&e!==A||t.capture!==e.capture||t.once!==e.once||t.passive!==e.passive,n=t!==A&&(e===A||o);o&&this.element.removeEventListener(this.name,this,e),n&&this.element.addEventListener(this.name,this,t),this._$AH=t;}handleEvent(t){var i,s;"function"==typeof this._$AH?this._$AH.call(null!==(s=null===(i=this.options)||void 0===i?void 0:i.host)&&void 0!==s?s:this.element,t):this._$AH.handleEvent(t);}}class Z{constructor(t,i,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=i,this.options=s;}get _$AU(){return this._$AM._$AU}_$AI(t){S(this,t);}}const B=i$1.litHtmlPolyfillSupport;null==B||B(N,R),(null!==(t$1=i$1.litHtmlVersions)&&void 0!==t$1?t$1:i$1.litHtmlVersions=[]).push("2.8.0");const D=(t,i,s)=>{var e,o;const n=null!==(e=null==s?void 0:s.renderBefore)&&void 0!==e?e:i;let l=n._$litPart$;if(void 0===l){const t=null!==(o=null==s?void 0:s.renderBefore)&&void 0!==o?o:null;n._$litPart$=l=new R(i.insertBefore(u(),t),t,void 0,null!=s?s:{});}return l._$AI(t),l};

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */var l,o;class s extends u$1{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0;}createRenderRoot(){var t,e;const i=super.createRenderRoot();return null!==(t=(e=this.renderOptions).renderBefore)&&void 0!==t||(e.renderBefore=i.firstChild),i}update(t){const i=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=D(i,this.renderRoot,this.renderOptions);}connectedCallback(){var t;super.connectedCallback(),null===(t=this._$Do)||void 0===t||t.setConnected(true);}disconnectedCallback(){var t;super.disconnectedCallback(),null===(t=this._$Do)||void 0===t||t.setConnected(false);}render(){return T}}s.finalized=true,s._$litElement$=true,null===(l=globalThis.litElementHydrateSupport)||void 0===l||l.call(globalThis,{LitElement:s});const n$2=globalThis.litElementPolyfillSupport;null==n$2||n$2({LitElement:s});(null!==(o=globalThis.litElementVersions)&&void 0!==o?o:globalThis.litElementVersions=[]).push("3.3.3");

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const e$1=e=>n=>"function"==typeof n?((e,n)=>(customElements.define(e,n),n))(e,n):((e,n)=>{const{kind:t,elements:s}=n;return {kind:t,elements:s,finisher(n){customElements.define(e,n);}}})(e,n);

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const i=(i,e)=>"method"===e.kind&&e.descriptor&&!("value"in e.descriptor)?{...e,finisher(n){n.createProperty(e.key,i);}}:{kind:"field",key:Symbol(),placement:"own",descriptor:{},originalKey:e.key,initializer(){"function"==typeof e.initializer&&(this[e.key]=e.initializer.call(this));},finisher(n){n.createProperty(e.key,i);}},e=(i,e,n)=>{e.constructor.createProperty(n,i);};function n$1(n){return (t,o)=>void 0!==o?e(n,t,o):i(n,t)}

/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function t(t){return n$1({...t,state:true})}

/**
 * @license
 * Copyright 2021 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */var n;null!=(null===(n=window.HTMLSlotElement)||void 0===n?void 0:n.prototype.assignedElements)?(o,n)=>o.assignedElements(n):(o,n)=>o.assignedNodes(n).filter((o=>o.nodeType===Node.ELEMENT_NODE));

// Polymer legacy event helpers used courtesy of the Polymer project.
//
// Copyright (c) 2017 The Polymer Authors. All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are
// met:
//
//    * Redistributions of source code must retain the above copyright
// notice, this list of conditions and the following disclaimer.
//    * Redistributions in binary form must reproduce the above
// copyright notice, this list of conditions and the following disclaimer
// in the documentation and/or other materials provided with the
// distribution.
//    * Neither the name of Google Inc. nor the names of its
// contributors may be used to endorse or promote products derived from
// this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
// OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
// DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
// THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
/**
 * Dispatches a custom event with an optional detail value.
 *
 * @param {string} type Name of event type.
 * @param {*=} detail Detail value containing event-specific
 *   payload.
 * @param {{ bubbles: (boolean|undefined),
 *           cancelable: (boolean|undefined),
 *           composed: (boolean|undefined) }=}
 *  options Object specifying options.  These may include:
 *  `bubbles` (boolean, defaults to `true`),
 *  `cancelable` (boolean, defaults to false), and
 *  `node` on which to fire the event (HTMLElement, defaults to `this`).
 * @return {Event} The new event that was fired.
 */
const fireEvent = (node, type, detail, options) => {
    options = options || {};
    // @ts-ignore
    detail = detail === null || detail === undefined ? {} : detail;
    const event = new Event(type, {
        bubbles: options.bubbles === undefined ? true : options.bubbles,
        cancelable: Boolean(options.cancelable),
        composed: options.composed === undefined ? true : options.composed,
    });
    event.detail = detail;
    node.dispatchEvent(event);
    return event;
};

var common$9 = {
	version: "Weergawe",
	invalidConfiguration: "Ongeldige konfigurasie"
};
var editor$8 = {
	title: {
		name: "Titel (opsioneel)"
	},
	showControllers: {
		name: "Wys beheerders (CSV lys)"
	},
	alwaysShowZones: {
		name: "Wys altyd sones"
	},
	alwaysShowSequences: {
		name: "Wys altyd volgordes"
	},
	showTimelineScheduled: {
		name: "Wys geskeduleerde tydslyn"
	},
	showTimelineHistory: {
		name: "Wys tydslyn geskiedenis"
	}
};
var controller$8 = {
	zones: {
		name: "Sones",
		buttonHint: "Wys/verberg sones"
	},
	sequences: {
		name: "Volgordes",
		buttonHint: "Wys/versteek volgordes"
	}
};
var menu$8 = {
	enable: {
		name: "Aktiveer"
	},
	suspend: {
		name: "Opskort",
		hint: "Duur\n===============\nh:mm:ss\n<blank> = herstel"
	},
	manual: {
		name: "Handmatig",
		hint: "Duur"
	},
	pause: {
		name: "Wag"
	},
	resume: {
		name: "Hervat"
	},
	cancel: {
		name: "Kanselleer"
	},
	adjust: {
		name: "Aanpas",
		hint: "Aanpassingsopsies\n===============\nPersentasie: %n\nWerklike: =0:00:00\nToename: +0:00:00\nAfname: -0:00:00\nHerstel: <blank>"
	}
};
var af = {
	common: common$9,
	editor: editor$8,
	controller: controller$8,
	menu: menu$8
};

var af$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common$9,
    controller: controller$8,
    default: af,
    editor: editor$8,
    menu: menu$8
});

var common$8 = {
	version: "Version",
	invalidConfiguration: "Ungültige Konfiguration"
};
var editor$7 = {
	title: {
		name: "Title (optional)"
	},
	showControllers: {
		name: "Zeige Controller (CSV list)"
	},
	alwaysShowZones: {
		name: "Zeige Zonen immer an"
	},
	alwaysShowSequences: {
		name: "Zeige Sequenzen immer an"
	},
	showTimelineScheduled: {
		name: "Zeige geplante Ablaufpläne"
	},
	showTimelineHistory: {
		name: "Zeige vergangene Ablaufpläne"
	}
};
var controller$7 = {
	zones: {
		name: "Zonen",
		buttonHint: "Ein/Ausblenden der Zonen"
	},
	sequences: {
		name: "Sequenzen",
		buttonHint: "Ein/Ausblenden der Sequenzen"
	}
};
var menu$7 = {
	enable: {
		name: "Aktivieren"
	},
	suspend: {
		name: "Pausieren",
		hint: "Dauer\n===============\nh:mm:ss\n<blank> = reset"
	},
	manual: {
		name: "Manuell",
		hint: "Dauer"
	},
	pause: {
		name: "Pause"
	},
	resume: {
		name: "Fortsetzen"
	},
	cancel: {
		name: "Abbrechen"
	},
	adjust: {
		name: "Anpassen",
		hint: "Anpassungs Optionen\n===============\nProzent: %n\nAktuell: =0:00:00\nErhöhen: +0:00:00\nVerringern -0:00:00\nReset: <blank>"
	}
};
var de = {
	common: common$8,
	editor: editor$7,
	controller: controller$7,
	menu: menu$7
};

var de$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common$8,
    controller: controller$7,
    default: de,
    editor: editor$7,
    menu: menu$7
});

var common$7 = {
	version: "Version",
	invalidConfiguration: "Invalid configuration"
};
var editor$6 = {
	title: {
		name: "Title (optional)"
	},
	showControllers: {
		name: "Show controllers (CSV list)"
	},
	alwaysShowZones: {
		name: "Always show zones"
	},
	alwaysShowSequences: {
		name: "Always show sequences"
	},
	showTimelineScheduled: {
		name: "Show timeline scheduled"
	},
	showTimelineHistory: {
		name: "Show timeline history"
	}
};
var controller$6 = {
	zones: {
		name: "Zones",
		buttonHint: "Show/hide zones"
	},
	sequences: {
		name: "Sequences",
		buttonHint: "Show/hide sequences"
	}
};
var menu$6 = {
	enable: {
		name: "Enable"
	},
	suspend: {
		name: "Suspend",
		hint: "Duration\n===============\nh:mm:ss\n<blank> = reset"
	},
	manual: {
		name: "Manual",
		hint: "Duration"
	},
	pause: {
		name: "Pause"
	},
	resume: {
		name: "Resume"
	},
	cancel: {
		name: "Cancel"
	},
	adjust: {
		name: "Adjust",
		hint: "Adjustment options\n===============\nPercentage: %n\nActual: =0:00:00\nIncrease: +0:00:00\nDecrease: -0:00:00\nReset: <blank>"
	}
};
var en = {
	common: common$7,
	editor: editor$6,
	controller: controller$6,
	menu: menu$6
};

var en$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common$7,
    controller: controller$6,
    default: en,
    editor: editor$6,
    menu: menu$6
});

var common$6 = {
	version: "Versjon",
	invalid_configuration: "Ikke gyldig konfiguration"
};
var nb = {
	common: common$6
};

var nb$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common$6,
    default: nb
});

var common$5 = {
	version: "Verzia",
	invalidConfiguration: "Chybná konfigurácia"
};
var editor$5 = {
	title: {
		name: "Názov (voliteľné)"
	},
	showControllers: {
		name: "Ukázať ovládače (CSV zoznam)"
	},
	alwaysShowZones: {
		name: "Vždy zobraziť zóny"
	},
	alwaysShowSequences: {
		name: "Vždy zobrazovať sekvencie"
	},
	showTimelineScheduled: {
		name: "Zobraziť naplánovanú časovú os"
	},
	showTimelineHistory: {
		name: "Zobraziť históriu časovej osi"
	}
};
var controller$5 = {
	zones: {
		name: "Zóny",
		buttonHint: "Zobraziť/skryť zóny"
	},
	sequences: {
		name: "Sekvencie",
		buttonHint: "Zobraziť/skryť sekvencie"
	}
};
var menu$5 = {
	enable: {
		name: "Povoliť"
	},
	suspend: {
		name: "Pozastaviť",
		hint: "Trvanie\n===============\nh:mm:ss\n<blank> = reset"
	},
	manual: {
		name: "Manual",
		hint: "Trvanie"
	},
	pause: {
		name: "Pauza"
	},
	resume: {
		name: "Obnoviť"
	},
	cancel: {
		name: "Zrušiť"
	},
	adjust: {
		name: "Upraviť",
		hint: "Možnosti úprav\n===============\nPercento: %n\nAktuálne: =0:00:00\nZvýšiť: +0:00:00\nZnížiť: -0:00:00\nReset: <blank>"
	}
};
var sk = {
	common: common$5,
	editor: editor$5,
	controller: controller$5,
	menu: menu$5
};

var sk$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common$5,
    controller: controller$5,
    default: sk,
    editor: editor$5,
    menu: menu$5
});

var common$4 = {
	version: "Verzió",
	invalidConfiguration: "Hibás konfiguráció"
};
var editor$4 = {
	title: {
		name: "Név (opcionális)"
	},
	showControllers: {
		name: "Vezérlők megjelenítése (CSV lista)"
	},
	alwaysShowZones: {
		name: "Mindig mutassa a zónákat"
	},
	alwaysShowSequences: {
		name: "Mindig mutassa a szekvenciákat"
	},
	showTimelineScheduled: {
		name: "Jövőbeli idővonal megjelenítése"
	},
	showTimelineHistory: {
		name: "Múltbeli idővonal megjelenítése"
	}
};
var controller$4 = {
	zones: {
		name: "Zónák",
		buttonHint: "Zónák mutatása/elrejtése"
	},
	sequences: {
		name: "Szekvenciák",
		buttonHint: "Szekvenciák mutatása/elrejtése"
	}
};
var menu$4 = {
	enable: {
		name: "Engedélyez"
	},
	suspend: {
		name: "Felfüggesztés",
		hint: "Időtartam\n===============\nh:mm:ss\n<blank> = visszaállít"
	},
	manual: {
		name: "Kézi",
		hint: "Időtartam"
	},
	pause: {
		name: "Szünet"
	},
	resume: {
		name: "Folytatás"
	},
	cancel: {
		name: "Megszakítás"
	},
	adjust: {
		name: "Módosítás",
		hint: "Módosítási lehetőségek\n===============\nSzázalékos: %n\nJelenlegi: =0:00:00\nNövelés: +0:00:00\nCsökkentés: -0:00:00\nVisszaállít: <blank>"
	}
};
var hu = {
	common: common$4,
	editor: editor$4,
	controller: controller$4,
	menu: menu$4
};

var hu$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common$4,
    controller: controller$4,
    default: hu,
    editor: editor$4,
    menu: menu$4
});

var common$3 = {
	version: "Versiune",
	invalidConfiguration: "Configuraţie invalidă"
};
var editor$3 = {
	title: {
		name: "Titlu (optional)"
	},
	showControllers: {
		name: "Afișează controlere (Listă CSV)"
	},
	alwaysShowZones: {
		name: "Afișează întotdeauna zonele"
	},
	alwaysShowSequences: {
		name: "Afișează întotdeauna secvenţele"
	},
	showTimelineScheduled: {
		name: "Afișează cronologia programată"
	},
	showTimelineHistory: {
		name: "Afișează istoricul cronologiei"
	}
};
var controller$3 = {
	zones: {
		name: "Zone",
		buttonHint: "Afișează/ascunde zonele"
	},
	sequences: {
		name: "Secvenţe",
		buttonHint: "Afișează/ascunde secvenţele"
	}
};
var menu$3 = {
	enable: {
		name: "Activează"
	},
	suspend: {
		name: "Suspendă",
		hint: "Durată\n===============\nh:mm:ss\n<blank> = resetează"
	},
	manual: {
		name: "Manual",
		hint: "Durată"
	},
	pause: {
		name: "Pauză"
	},
	resume: {
		name: "Reia"
	},
	cancel: {
		name: "Renunţă"
	},
	adjust: {
		name: "Ajustează",
		hint: "Opțiuni de ajustare\n===============\nProcentaj: %n\nActual: =0:00:00\nCrește: +0:00:00\nScade: -0:00:00\nResetează: <blank>"
	}
};
var ro = {
	common: common$3,
	editor: editor$3,
	controller: controller$3,
	menu: menu$3
};

var ro$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common$3,
    controller: controller$3,
    default: ro,
    editor: editor$3,
    menu: menu$3
});

var common$2 = {
	version: "Versione",
	invalidConfiguration: "Configurazione non valida"
};
var editor$2 = {
	title: {
		name: "Titolo (Opzionale)"
	},
	showControllers: {
		name: "Mostra controller (lista CSV)"
	},
	alwaysShowZones: {
		name: "Mostra sempre le zone"
	},
	alwaysShowSequences: {
		name: "Mostra sempre le sequenze"
	},
	showTimelineScheduled: {
		name: "Mostra cronologia programmazione"
	},
	showTimelineHistory: {
		name: "Mostra cronologia"
	}
};
var controller$2 = {
	zones: {
		name: "Zone",
		buttonHint: "Mostra/nascondi zone"
	},
	sequences: {
		name: "Sequenze",
		buttonHint: "Mostra/nascondi zone"
	}
};
var menu$2 = {
	enable: {
		name: "Attiva"
	},
	suspend: {
		name: "Sospendi",
		hint: "Durata\n===============\nh:mm:ss\n<blank> = reset"
	},
	manual: {
		name: "Manuale",
		hint: "Durata"
	},
	pause: {
		name: "Pausa"
	},
	resume: {
		name: "Riprendi"
	},
	cancel: {
		name: "Cancella"
	},
	adjust: {
		name: "Regola",
		hint: "Opzioni di regolamento\n===============\nPercentuale: %n\nAttuale: =0:00:00\nAumenta: +0:00:00\nDiminuisci: -0:00:00\nReset: <blank>"
	}
};
var it = {
	common: common$2,
	editor: editor$2,
	controller: controller$2,
	menu: menu$2
};

var it$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common$2,
    controller: controller$2,
    default: it,
    editor: editor$2,
    menu: menu$2
});

var common$1 = {
	version: "Versión",
	invalidConfiguration: "Configuración invalida"
};
var editor$1 = {
	title: {
		name: "Título (opcional)"
	},
	showControllers: {
		name: "Mostrar controladores (lista CSV)"
	},
	alwaysShowZones: {
		name: "Siempre mostrar zonas"
	},
	alwaysShowSequences: {
		name: "Siempre mostrar secuencias"
	},
	showTimelineScheduled: {
		name: "Mostrar cronología programada"
	},
	showTimelineHistory: {
		name: "Mostrar el historial"
	}
};
var controller$1 = {
	zones: {
		name: "Zonas",
		buttonHint: "Mostrar/ocultar zonas"
	},
	sequences: {
		name: "Secuencias",
		buttonHint: "Mostrar/ocultar secuencias"
	}
};
var menu$1 = {
	enable: {
		name: "Activar"
	},
	suspend: {
		name: "Pausar",
		hint: "Duración\n===============\nh:mm:ss\n<blank> = reset"
	},
	manual: {
		name: "Manual",
		hint: "Duración"
	},
	pause: {
		name: "Pausar"
	},
	resume: {
		name: "Reanudar"
	},
	cancel: {
		name: "Cancelar"
	},
	adjust: {
		name: "Ajustar",
		hint: "Opciones de ajuste\n===============\nPorcentual: %n\nActual: =0:00:00\nAumentar: +0:00:00\nReducir: -0:00:00\nReset: <blank>"
	}
};
var es = {
	common: common$1,
	editor: editor$1,
	controller: controller$1,
	menu: menu$1
};

var es$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common$1,
    controller: controller$1,
    default: es,
    editor: editor$1,
    menu: menu$1
});

var common = {
	version: "Wersja",
	invalidConfiguration: "Nieprawidłowa konfiguracja"
};
var editor = {
	title: {
		name: "Tytuł (opcjonalnie)"
	},
	showControllers: {
		name: "Pokaż kontrolery (lista CSV)"
	},
	alwaysShowZones: {
		name: "Zawsze pokazuj strefy"
	},
	alwaysShowSequences: {
		name: "Zawsze pokazuj sekwencje"
	},
	showTimelineScheduled: {
		name: "Pokaż oś czasu planowania"
	},
	showTimelineHistory: {
		name: "Pokaż historię"
	}
};
var controller = {
	zones: {
		name: "Strefy",
		buttonHint: "Pokaż/ukryj strefy"
	},
	sequences: {
		name: "Sekwencje",
		buttonHint: "Pokaż/ukryj sekwencje"
	}
};
var menu = {
	enable: {
		name: "Aktywuj"
	},
	suspend: {
		name: "Zawieś",
		hint: "Czas trwania\n===============\nh:mm:ss\n<puste> = reset"
	},
	manual: {
		name: "Ręcznie",
		hint: "Czas trwania"
	},
	pause: {
		name: "Pauza"
	},
	resume: {
		name: "Wznów"
	},
	cancel: {
		name: "Anuluj"
	},
	adjust: {
		name: "Dostosuj",
		hint: "Opcje regulacji\n===============\nProcent: %n\nAktualne: =0:00:00\nZwiększ: +0:00:00\nZmniejsz: -0:00:00\nReset: <puste>"
	}
};
var pl = {
	common: common,
	editor: editor,
	controller: controller,
	menu: menu
};

var pl$1 = /*#__PURE__*/Object.freeze({
    __proto__: null,
    common: common,
    controller: controller,
    default: pl,
    editor: editor,
    menu: menu
});

const languages = {
    af: af$1,
    de: de$1,
    en: en$1,
    es: es$1,
    hu: hu$1,
    it: it$1,
    nb: nb$1,
    pl: pl$1,
    ro: ro$1,
    sk: sk$1,
};
class localise {
    constructor(preferred) {
        if (!(preferred in languages)) {
            preferred = preferred.substring(0, 2);
            if (!(preferred in languages)) {
                preferred = "en";
            }
        }
        this.lang = preferred;
    }
    find(language, keys) {
        let d = languages[language];
        for (const k of keys) {
            d = d[k];
            if (d === undefined)
                throw new Error();
        }
        return d;
    }
    t(key) {
        const keys = key.split(".");
        try {
            return this.find(this.lang, keys);
        }
        catch (e) {
            try {
                if (this.lang !== "en")
                    return this.find("en", keys);
                else
                    return "";
            }
            catch (e) {
                return "";
            }
        }
    }
}

const loc$1 = new localise(window.navigator.language);
let IrrigationUnlimitedCardEditor = class IrrigationUnlimitedCardEditor extends s {
    setConfig(config) {
        this._config = config;
    }
    get _name() {
        var _a;
        return ((_a = this._config) === null || _a === void 0 ? void 0 : _a.name) || "";
    }
    get _show_controllers() {
        var _a;
        return ((_a = this._config) === null || _a === void 0 ? void 0 : _a.show_controllers) || "";
    }
    get _always_show_zones() {
        var _a;
        return ((_a = this._config) === null || _a === void 0 ? void 0 : _a.always_show_zones) || false;
    }
    get _always_show_sequences() {
        var _a;
        return ((_a = this._config) === null || _a === void 0 ? void 0 : _a.always_show_sequences) || false;
    }
    get _show_timeline_scheduled() {
        var _a;
        return ((_a = this._config) === null || _a === void 0 ? void 0 : _a.show_timeline_scheduled) || false;
    }
    get _show_timeline_history() {
        var _a;
        return ((_a = this._config) === null || _a === void 0 ? void 0 : _a.show_timeline_history) || true;
    }
    render() {
        if (!this.hass) {
            return A;
        }
        return x `
      <div class="iu-editor-row">
        <ha-textfield
          label=${loc$1.t("editor.title.name")}
          .value=${this._name}
          .configValue=${"name"}
          @input="${this._valueChanged}"
        ></ha-textfield>
      </div>
      <div class="iu-editor-row">
        <ha-textfield
          label=${loc$1.t("editor.showControllers.name")}
          .value=${this._show_controllers}
          .configValue=${"show_controllers"}
          @input="${this._valueChanged}"
        ></ha-textfield>
      </div>
      <div class="iu-editor-row">
        <ha-switch
          id=${this._always_show_zones}
          .checked=${this._always_show_zones}
          .configValue=${"always_show_zones"}
          @change=${this._valueChanged}
        ></ha-switch>
        <label for=${this._always_show_zones}
          >${loc$1.t("editor.alwaysShowZones.name")}</label
        >
      </div>
      <div class="iu-editor-row">
        <ha-switch
          id=${this._always_show_sequences}
          .checked=${this._always_show_sequences}
          .configValue=${"always_show_sequences"}
          @change=${this._valueChanged}
        ></ha-switch>
        <label for=${this._always_show_sequences}
          >${loc$1.t("editor.alwaysShowSequences.name")}</label
        >
      </div>
      <div class="iu-editor-row">
        <ha-switch
          id=${this._show_timeline_scheduled}
          .checked=${this._show_timeline_scheduled}
          .configValue=${"show_timeline_scheduled"}
          @change=${this._valueChanged}
        ></ha-switch>
        <label for=${this._show_timeline_scheduled}
          >${loc$1.t("editor.showTimelineScheduled.name")}</label
        >
      </div>
      <div class="iu-editor-row">
        <ha-switch
          id=${this._show_timeline_history}
          .checked=${this._show_timeline_history}
          .configValue=${"show_timeline_history"}
          @change=${this._valueChanged}
        ></ha-switch>
        <label for=${this._show_timeline_history}
          >${loc$1.t("editor.showTimelineHistory.name")}</label
        >
      </div>
    `;
    }
    _valueChanged(ev) {
        if (!this._config || !this.hass) {
            return;
        }
        const target = ev.target;
        if (target.configValue) {
            if (target.value === "") {
                const tmpConfig = Object.assign({}, this._config);
                delete tmpConfig[target.configValue];
                this._config = tmpConfig;
            }
            else {
                this._config = Object.assign(Object.assign({}, this._config), { [target.configValue]: target.checked !== undefined ? target.checked : target.value });
            }
        }
        fireEvent(this, "config-changed", { config: this._config }, { bubbles: true, composed: true });
    }
};
IrrigationUnlimitedCardEditor.styles = i$2 `
    ha-switch {
      padding: 16px 6px;
    }
    ha-textfield {
      width: 100%;
    }
  `;
__decorate([
    n$1({ attribute: false })
], IrrigationUnlimitedCardEditor.prototype, "hass", void 0);
__decorate([
    t()
], IrrigationUnlimitedCardEditor.prototype, "_config", void 0);
IrrigationUnlimitedCardEditor = __decorate([
    e$1("irrigation-unlimited-card-editor")
], IrrigationUnlimitedCardEditor);

function hms_to_secs(value) {
    if (!value)
        return undefined;
    var hms = value.split(":");
    return +hms[0] * 60 * 60 + +hms[1] * 60 + (+hms[2] || 0);
}
function secs_to_hms(value) {
    if (!value)
        return undefined;
    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value - hours * 3600) / 60);
    const seconds = value % 60;
    return (String(hours) +
        ":" +
        String(minutes).padStart(2, "0") +
        ":" +
        String(seconds).padStart(2, "0"));
}
function date_to_str(value) {
    if (value !== null && !isNaN(value.getTime())) {
        return value.toLocaleTimeString(undefined, {
            weekday: "short",
            hour: "numeric",
            minute: "2-digit",
            hour12: false,
        });
    }
    return "";
}
function elapsed_secs(d1, d2) {
    return Math.round((d1.getTime() - d2.getTime()) / 1000);
}
function percent_completed(elapsed, total) {
    return Math.round((elapsed / total) * 100);
}
function humanise_adjustment(value) {
    if (value && value.length > 0 && value[0] === "%")
        return value.substring(1) + "%";
    return value;
}

class IUBase {
    constructor() {
        this.start = undefined;
        this.status = undefined;
        this._duration = undefined;
        this._remaining = undefined;
        this._percent_completed = undefined;
    }
    get duration() {
        return secs_to_hms(this._duration);
    }
    set duration(value) {
        this._duration = hms_to_secs(value);
        return;
    }
    get remaining() {
        return secs_to_hms(this._remaining);
    }
    set remaining(value) {
        this._remaining = hms_to_secs(value);
    }
    get percent_completed() {
        return this._percent_completed;
    }
    update_stats(now) {
        if (this.start && this._duration) {
            if (this.status === "on" || this.status === "delay") {
                const elapsed = elapsed_secs(now, this.start);
                this._remaining = this._duration - elapsed;
                this._percent_completed = percent_completed(elapsed, this._duration);
            }
        }
    }
    clear_stats() {
        this._remaining = this._percent_completed = undefined;
    }
}
class IUEntity extends IUBase {
    get id1() {
        return this.index + 1;
    }
    constructor(data) {
        super();
        this.last_updated = undefined;
        this.index = data.index;
        this.name = data.name;
        this.entity_id = data.entity_id;
    }
    update(hass) {
        let result = 0 /* IUUpdateStatus.None */;
        const entity = hass.states[this.entity_id];
        const date = new Date(entity.last_updated);
        if (this.last_updated === undefined || date > this.last_updated) {
            this.last_updated = date;
            result |= 1 /* IUUpdateStatus.EntityUpdated */;
            this.status = entity.attributes.status;
            if (this.status === "on" ||
                this.status === "delay" ||
                this.status === "paused") {
                this.start = new Date(entity.attributes.current_start);
                this.duration = entity.attributes.current_duration;
                this.remaining = entity.attributes.time_remaining;
            }
            else {
                this.start = undefined;
                this.clear_stats();
            }
        }
        if (this.status === "on" || this.status === "delay")
            result |= 2 /* IUUpdateStatus.TimerRequired */;
        return result;
    }
    timer(now) {
        if (this.status === "on" || this.status === "delay")
            this.update_stats(now);
    }
}
class IUSequenceZone extends IUBase {
    get id1() {
        return this.index + 1;
    }
    constructor(data) {
        super();
        this.enabled = true;
        this.suspended = null;
        this.index = data.index;
        this.zone_ids = data.zone_ids;
    }
    assign(szs) {
        this.icon = szs.icon;
        this.enabled = szs.enabled;
        this.suspended = szs.suspended ? new Date(szs.suspended) : null;
        this.adjustment = szs.adjustment;
        if (szs.start) {
            this.start = new Date(szs.start);
            this.duration = szs.duration;
        }
        else {
            this.start = undefined;
            this.duration = "0:00:00";
        }
        if (this.status === "off" && szs.status === "on") {
            this._remaining = this._duration;
        }
        else if (szs.status === "off")
            this._remaining = undefined;
        this.status = szs.status;
    }
}
class IUSequence extends IUEntity {
    constructor(data) {
        super(data);
        this.zones = [];
        for (const z of data.zones)
            this.zones.push(new IUSequenceZone(z));
    }
    update(hass) {
        let result = super.update(hass);
        if ((result & 1 /* IUUpdateStatus.EntityUpdated */) !== 0) {
            const entity = hass.states[this.entity_id];
            for (const szs of entity.attributes.zones)
                this.zones[szs.index].assign(szs);
        }
        return result;
    }
    timer(now) {
        super.timer(now);
        if (this.status === "on")
            for (const z of this.zones)
                if (z.status === "on")
                    z.update_stats(now);
    }
}
class IUZone extends IUEntity {
    constructor(data) {
        super(data);
        this.zone_id = data.zone_id;
    }
}
class IUController extends IUEntity {
    constructor(data) {
        super(data);
        this.zones = [];
        this.sequences = [];
        this.controller_id = data.controller_id;
        for (const z of data.zones)
            this.zones.push(new IUZone(z));
        for (const s of data.sequences)
            this.sequences.push(new IUSequence(s));
    }
    lookup_zone_name(zone_id) {
        for (const z of this.zones)
            if (z.zone_id === zone_id)
                return z.name;
        return undefined;
    }
    sequence_status(status) {
        for (const s of this.sequences) {
            if (s.status === status)
                return true;
        }
        return false;
    }
    pause_resume_status() {
        let result = 0;
        if (this.sequence_status("on"))
            result |= 1;
        if (this.sequence_status("paused"))
            result |= 2;
        return result;
    }
    update(hass) {
        let result = super.update(hass);
        for (const z of this.zones)
            result |= z.update(hass);
        for (const s of this.sequences)
            result |= s.update(hass);
        return result;
    }
}
class IUCoordinator {
    constructor(parent) {
        this.initialised = false;
        this.version = "";
        this.timer_id = undefined;
        this.parent = parent;
        this.controllers = [];
    }
    async _getInfo(hass) {
        try {
            const response = (await hass.callService("irrigation_unlimited", "get_info", {}, { entity_id: "irrigation_unlimited.coordinator" }, true, true)).response;
            return response;
        }
        catch (e) {
            console.log(e);
            throw e;
        }
    }
    validateEntities(hass) {
        for (var i = this.controllers.length - 1; i >= 0; i--) {
            const c = this.controllers[i];
            if (hass.states[c.entity_id]) {
                for (var j = c.zones.length - 1; j >= 0; j--) {
                    if (!hass.states[c.zones[j].entity_id]) {
                        console.error("Zone does not exist: ", c.zones[j].entity_id);
                        c.zones.pop();
                    }
                }
                for (var k = c.sequences.length - 1; k >= 0; k--) {
                    if (!hass.states[c.sequences[k].entity_id]) {
                        console.error("Sequence does not exist: ", c.sequences[k].entity_id);
                        c.sequences.pop();
                    }
                }
            }
            else {
                console.error("Controller does not exist: ", c.entity_id);
                this.controllers.pop();
            }
        }
    }
    init(hass) {
        if (!hass || this.initialised)
            return;
        this._getInfo(hass).then((response) => {
            this.version = response.version;
            for (const c of response.controllers)
                this.controllers.push(new IUController(c));
            this.validateEntities(hass);
            this.initialised = true;
            this.parent.requestUpdate();
        });
    }
    update(hass) {
        if (!this.initialised)
            return false;
        let result = 0 /* IUUpdateStatus.None */;
        for (const c of this.controllers)
            result |= c.update(hass);
        if (this.timer_id === undefined &&
            (result & 2 /* IUUpdateStatus.TimerRequired */) !== 0) {
            this.start_timer(hass);
        }
        else if (this.timer_id !== undefined &&
            (result & 2 /* IUUpdateStatus.TimerRequired */) === 0) {
            this.stop_timer();
        }
        return result !== 0;
    }
    start_timer(_hass) {
        if (this.timer_id)
            return;
        this.timer_id = setInterval((function (scope) {
            return function () {
                const now = new Date();
                for (const c of scope.controllers) {
                    c.timer(now);
                    for (const z of c.zones)
                        z.timer(now);
                    for (const s of c.sequences)
                        s.timer(now);
                }
                scope.parent.requestUpdate();
            };
        })(this), 1000);
    }
    stop_timer() {
        if (!this.timer_id)
            return;
        clearInterval(this.timer_id);
        this.timer_id = undefined;
    }
}

const styles = i$2 `
  .iu-controller.iu-hidden {
    display: none;
  }

  .iu-control-panel {
    display: flex;
    justify-content: flex-start;
    align-items: center;
  }

  .iu-control-panel-item {
    padding: 0.5em 0 0.5em 1em;
  }

  .iu-zones.iu-hidden.iu-content {
    display: none;
  }

  .iu-sequences.iu-hidden.iu-content {
    display: none;
  }

  .iu-hidden .iu-content {
    display: none;
  }

  .iu-hidden .iu-expander::before {
    content: "\u25B6";
    display: inline-block;
    rotate: none;
  }

  .iu-expander::before {
    content: "\u25B6";
    display: inline-block;
    rotate: 90deg;
  }

  .iu-controller-row.iu-td {
    display: flex;
    align-items: center;
    min-height: 3em;
  }

  .iu-zone-row.iu-td {
    display: flex;
    align-items: center;
    min-height: 3em;
    font-size: smaller;
  }

  .iu-timeline-row.iu-td {
    font-size: smaller;
  }

  .iu-timeline-row > .iu-td5.iu-dvf {
    height: 1em;
    line-height: 1em;
    overflow: hidden;
  }

  .iu-timeline-row > .iu-td5.iu-dvf > .iu-content {
    animation: slide-up 6s linear infinite;
  }

  @keyframes slide-up {
    0%,
    33% {
      transform: translateY(0);
    }
    42%,
    58% {
      transform: translateY(-33.3%);
    }
    67%,
    83% {
      transform: translateY(-66.7%);
    }
  }

  .iu-sequence-row.iu-td {
    display: flex;
    align-items: center;
    min-height: 3em;
    font-size: smaller;
  }

  .iu-sequence-zone-row.iu-td {
    display: flex;
    align-items: center;
    height: 2em;
    font-size: smaller;
  }

  .iu-td {
    display: flex;
    align-items: center;
  }

  .iu-td1 {
    flex: auto;
    width: 1.5em;
    text-align: center;
  }

  .iu-td2 {
    flex: 30px;
    text-align: center;
  }

  .iu-td3 {
    flex: 40%;
    text-align: left;
  }

  .iu-td4 {
    flex: 20%;
    text-align: center;
  }

  .iu-td5 {
    flex: 15%;
    text-align: center;
  }

  .iu-td6 {
    flex: 15%;
    text-align: center;
  }

  .iu-td7 {
    flex: 10%;
    text-align: center;
  }

  /* Cursors */
  .iu-collapsible > .iu-td > .iu-td1,
  .iu-collapsible > .iu-td > .iu-td2,
  .iu-collapsible > .iu-td > .iu-td3 {
    cursor: pointer;
  }

  .iu-controller-row .iu-td4,
  .iu-zone-row .iu-td4,
  .iu-sequence-row .iu-td4 {
    cursor: pointer;
  }

  .iu-controller-row > .iu-td3,
  .iu-timeline-row,
  .iu-sequence-zone-row,
  .iu-duration,
  .iu-adjustment {
    cursor: default;
  }

  /* Timeline colouring */
  .iu-timeline-scheduled,
  .iu-timeline-scheduled .iu-schedule,
  .iu-timeline-next,
  .iu-timeline-next .iu-schedule {
    color: var(--label-badge-blue, #039be5);
  }

  .iu-timeline-running,
  .iu-timeline-running .iu-schedule {
    color: var(--label-badge-green, #43a047);
  }

  .iu-timeline-history {
    color: var(--secondary-text-color, #727272);
  }

  /* Duration colouring */
  .iu-sequence.iu-on .iu-sequence-zone:not(.iu-on) .iu-duration,
  .iu-sequence.iu-paused .iu-sequence-zone:not(.iu-on) .iu-duration,
  .iu-sequence.iu-delay .iu-sequence-zone:not(.iu-on) .iu-duration {
    color: var(--label-badge-blue);
  }

  .iu-controller.iu-on .iu-controller-row .iu-duration,
  .iu-zone.iu-on .iu-zone-row .iu-duration,
  .iu-sequence.iu-on .iu-sequence-row .iu-duration,
  .iu-sequence.iu-delay .iu-sequence-row .iu-duration,
  .iu-sequence.iu-on .iu-sequence-zone-row .iu-duration {
    color: var(--state-on-color, #66a61e);
  }

  .iu-sequence.iu-paused .iu-sequence-row .iu-duration,
  .iu-sequence.iu-paused .iu-sequence-zone.iu-on .iu-duration {
    color: var(--state-on-color, #66a61e);
    animation: 1s step-end infinite duration-paused;
  }

  @keyframes duration-paused {
    50% {
      opacity: 0;
    }
  }

  /* Schedule colouring */
  .iu-schedule {
    color: var(--secondary-text-color, #727272);
  }

  .iu-controller.iu-manual .iu-schedule,
  .iu-zone.iu-manual .iu-zone-row .iu-schedule,
  .iu-sequence.iu-manual .iu-schedule {
    color: var(--label-badge-red, #df4c1e);
  }

  .iu-controller.iu-suspended .iu-start,
  .iu-zone.iu-suspended .iu-zone-row .iu-schedule,
  .iu-sequence.iu-suspended .iu-schedule {
    color: var(--label-badge-yellow, #ffff00);
    font-style: italic;
  }

  /* Name colouring */
  .iu-name {
    color: var(--secondary-text-color, #727272);
    font-weight: 500;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  /* Icon colouring */
  ha-icon {
    color: var(--state-icon-color, #44739e);
  }

  .iu-controller.iu-on .iu-controller-row .iu-td2 ha-icon,
  .iu-controller.iu-delay .iu-controller-row .iu-td2 ha-icon,
  .iu-zone.iu-on .iu-zone-row .iu-td2 ha-icon,
  .iu-sequence.iu-on .iu-sequence-row .iu-td2 ha-icon,
  .iu-sequence.iu-paused .iu-sequence-row .iu-td2 ha-icon,
  .iu-sequence.iu-delay .iu-sequence-row .iu-td2 ha-icon,
  .iu-sequence-zone.iu-on .iu-td2 ha-icon {
    color: var(--state-icon-active-color, #fdd835);
  }

  .iu-menu {
    position: relative;
    display: inline-block;
  }

  .iu-menu-button {
    background-color: transparent;
    text-align: center;
    display: block;
    font-size: 16px;
    border: none;
    cursor: pointer;
  }

  .iu-menu-content {
    display: flex;
    flex-direction: column;
    flex-wrap: nowrap;
    width: 200px;
    padding: 10px 0;
    position: absolute;
    background-color: var(--card-background-color, white);
    right: 0;
    box-shadow: 0px 0px 7px 0px rgba(50, 50, 50, 0.75);
    border-radius: 5px;
    z-index: 1;
  }

  .iu-menu-content.iu-hidden {
    display: none;
  }

  .iu-menu-content .iu-menu-item {
    display: flex;
    padding: 0px 5px;
    line-height: 48px;
  }

  .iu-menu .iu-menu-item:hover {
    color: var(--primary-color, #b3e5fc);
    background-color: var(--secondary-background-color, #e5e5e5);
  }

  .iu-menu-item.iu-hidden {
    display: none;
  }

  .iu-mc1 {
    flex: 30%;
    text-align: left;
  }

  .iu-mc2 {
    flex: 40%;
    text-align: right;
  }

  .iu-mc3 {
    flex: 30%;
    text-align: center;
  }

  .iu-mc3 ha-icon {
    display: flex;
  }

  .iu-adjust-input:invalid,
  .iu-time-input:invalid {
    color: var(--label-badge-red, #df4c1e);
  }
`;

const CARD_VERSION = "2026.1.0";

const loc = new localise(window.navigator.language);
/* eslint no-console: 0 */
console.info(`%c  IRRIGATION-UNLIMITED-CARD \n%c  ${loc.t("common.version")} ${CARD_VERSION}    `, "color: orange; font-weight: bold; background: black", "color: white; font-weight: bold; background: dimgray");
window.customCards = window.customCards || [];
window.customCards.push({
    type: "irrigation-unlimited-card",
    name: "Irrigation Unlimited Card",
    description: "A companion card for the Irrigation Unlimited integration",
});
let IrrigationUnlimitedCard = class IrrigationUnlimitedCard extends s {
    constructor() {
        super(...arguments);
        this.iu_coordinator = new IUCoordinator(this);
    }
    static async getConfigElement() {
        return document.createElement("irrigation-unlimited-card-editor");
    }
    setConfig(config) {
        if (!config) {
            throw new Error(loc.t("common.invalidConfiguration"));
        }
        this.config = config;
    }
    static getStubConfig() {
        return {};
    }
    getCardSize() {
        return 1;
    }
    firstUpdated(_changedProperties) {
        this.iu_coordinator.init(this.hass);
    }
    shouldUpdate(changedProps) {
        if (!this.hass) {
            return false;
        }
        if (changedProps.has("config"))
            return true;
        return this.iu_coordinator.update(this.hass);
    }
    render() {
        if (!this.hass)
            return A;
        return x `
      <ha-card
        .header=${this.config.name}
        tabindex="0"
        id="iu-card"
        @click="${this._clickNet}"
      >
        <div class="iu-header">
          <div class="iu-header-row iu-td">
            <div class="iu-td1"></div>
            <div class="iu-td2"></div>
            <div class="iu-td3"></div>
            <div class="iu-td4">
              <ha-icon icon="mdi:clock-outline"></ha-icon>
            </div>
            <div class="iu-td5"><ha-icon icon="mdi:timer-sand"></ha-icon></div>
            <div class="iu-td6"><ha-icon icon="mdi:delta"></ha-icon></div>
            <div class="iu-td7"><ha-icon icon="mdi:menu"></ha-icon></div>
          </div>
        </div>
        <div class="iu-controllers">
          ${this.iu_coordinator.controllers.map((controller) => this._renderController(controller))}
        </div>
        <div class="iu-footer"></div>
      </ha-card>
    `;
    }
    _renderController(controller) {
        var _a;
        const stateObj = this.hass.states[controller.entity_id];
        const status = stateObj.attributes.status;
        const isOn = stateObj.state === "on";
        const isDelay = status === "delay";
        const isEnabled = stateObj.attributes.enabled;
        const suspended = stateObj.attributes.suspended;
        const isHidden = !(!this.config.show_controllers ||
            (this.config.show_controllers &&
                ((_a = this.config.show_controllers) === null || _a === void 0 ? void 0 : _a.replace(/\s/g, "").split(",").includes(controller.controller_id))));
        const zonesHidden = !this.config.always_show_zones;
        const sequencesHidden = !this.config.always_show_sequences;
        let start;
        let duration;
        let schedule_name;
        if (isOn) {
            start = new Date(stateObj.attributes.current_start);
            duration = controller.remaining;
            schedule_name = stateObj.attributes.current_name;
        }
        else if (suspended) {
            start = new Date(suspended);
            duration = "";
            schedule_name = "";
        }
        else {
            start = new Date(stateObj.attributes.next_start);
            duration = stateObj.attributes.next_duration;
            schedule_name = stateObj.attributes.next_name;
        }
        const startStr = date_to_str(start);
        const classes = ["iu-controller", "iu-object"];
        if (isHidden)
            classes.push("iu-hidden");
        if (isOn)
            classes.push("iu-on");
        if (isEnabled)
            classes.push("iu-enabled");
        if (suspended)
            classes.push("iu-suspended");
        if (isDelay)
            classes.push("iu-delay");
        const zonesClasses = ["iu-zones iu-content"];
        if (zonesHidden)
            zonesClasses.push("iu-hidden");
        const sequencesClasses = ["iu-sequences iu-content"];
        if (sequencesHidden)
            sequencesClasses.push("iu-hidden");
        return x `
      <div class=${classes.join(" ")} iu-key="${controller.id1}.0.0.0">
        <hr />
        <div class="iu-controller-row iu-td">
          <div class="iu-td1"></div>
          <div class="iu-td2">
            <ha-icon .icon=${stateObj.attributes.icon}></ha-icon>
          </div>
          <div class="iu-td3">
            <span>${controller.id1}</span>
            <span class="iu-name">${controller.name}</span>
          </div>
          <div class="iu-td4" @click="${this._moreInfo}">
            <div ?hidden=${!isEnabled}>
              <span class="iu-schedule">${schedule_name}</span>
              <br ?hidden=${isOn || suspended} />
              <span class="iu-start" ?hidden=${isOn}>${startStr}</span>
            </div>
            <div ?hidden=${isEnabled}>&nbsp;</div>
          </div>
          <div class="iu-td5 iu-duration">
            <div ?hidden=${!isEnabled}>${duration}</div>
          </div>
          <div class="iu-td6"></div>
          <div class="iu-td7">
            ${this._renderMenu(isEnabled, false, true, true, controller.pause_resume_status(), null, suspended)}
          </div>
        </div>
        <div class="iu-control-panel">
          <div class="iu-control-panel-item iu-show-zones">
            <label>${loc.t("controller.zones.name")}&nbsp;</label>
            <ha-switch
              .checked="${!zonesHidden}"
              .disabled="${this.config.always_show_zones}"
              title=${loc.t("controller.zones.buttonHint")}
              @change="${this._toggleZones}"
            >
            </ha-switch>
          </div>
          <div class="iu-control-panel-item iu-show-sequences">
            <label>${loc.t("controller.sequences.name")}&nbsp;</label>
            <ha-switch
              .checked="${!sequencesHidden}"
              .disabled="${this.config.always_show_sequences}"
              title=${loc.t("controller.sequences.buttonHint")}
              @change="${this._toggleSequences}"
            >
            </ha-switch>
          </div>
        </div>
        <div class=${zonesClasses.join(" ")}>
          <hr />
          ${controller.zones.map((zone) => this._renderZone(controller, zone))}
        </div>
        <div class=${sequencesClasses.join(" ")}>
          <hr />
          ${controller.sequences.map((sequence) => this._renderSequence(controller, sequence))}
        </div>
      </div>
    `;
    }
    _renderZone(controller, zone) {
        const stateObj = this.hass.states[zone.entity_id];
        const status = stateObj.attributes.status;
        const isOn = stateObj.state === "on";
        const isEnabled = stateObj.attributes.enabled;
        const suspended = stateObj.attributes.suspended;
        const isBlocked = status === "blocked";
        let start;
        let duration;
        let schedule_index;
        let schedule_name;
        let adjustment;
        if (isOn) {
            start = new Date(stateObj.attributes.current_start);
            duration = zone.remaining;
            schedule_index = stateObj.attributes.current_schedule;
            schedule_name = stateObj.attributes.current_name;
            adjustment = stateObj.attributes.current_adjustment;
        }
        else if (suspended) {
            start = new Date(suspended);
            duration = "";
            schedule_index = -1;
            schedule_name = "";
            adjustment = "";
        }
        else {
            start = new Date(stateObj.attributes.next_start);
            duration = stateObj.attributes.next_duration;
            schedule_index = stateObj.attributes.next_schedule;
            schedule_name = stateObj.attributes.next_name;
            adjustment = stateObj.attributes.next_adjustment;
        }
        const isManual = schedule_index === 0;
        if (isManual)
            schedule_name = loc.t("menu.manual.name");
        const startStr = date_to_str(start);
        const classes = ["iu-zone", "iu-object"];
        if (isOn)
            classes.push("iu-on");
        if (isEnabled)
            classes.push("iu-enabled");
        if (suspended)
            classes.push("iu-suspended");
        if (isManual)
            classes.push("iu-manual");
        if (isBlocked)
            classes.push("iu-blocked");
        let timeline = stateObj.attributes.timeline;
        if (timeline !== undefined) {
            // Filter items
            timeline = timeline.filter((item) => {
                return ((item.start !== item.end &&
                    item.status === "history" &&
                    (this.config.show_timeline_history === undefined ||
                        this.config.show_timeline_history)) ||
                    (item.status === "scheduled" &&
                        this.config.show_timeline_scheduled) ||
                    (item.status === "next" && this.config.show_timeline_scheduled) ||
                    (item.status === "running" && this.config.show_timeline_scheduled));
            });
            // Sort items
            timeline.sort((a, b) => {
                const da = new Date(a.start).getTime();
                const db = new Date(b.start).getTime();
                if (a.status === "history" && a.status === "history")
                    return db - da;
                return da - db;
            });
            // Move first history item to head
            const idx = timeline.findIndex((item) => item.status === "history");
            if (idx >= 0)
                timeline.unshift(timeline.splice(idx, 1)[0]);
        }
        else
            timeline = [];
        return x `
      <div
        class=${classes.join(" ")}
        iu-key="${controller.id1}.${zone.id1}.0.0"
      >
        <div class="iu-collapsible iu-hidden">
          <div class="iu-zone-row iu-td">
            <div
              class="iu-td1 iu-expander"
              @click="${this._toggleCollapse}"
            ></div>
            <div class="iu-td2" @click="${this._toggleCollapse}">
              <ha-icon .icon=${stateObj.attributes.icon}></ha-icon>
            </div>
            <div class="iu-td3" @click="${this._toggleCollapse}">
              <span style="color: ${this._selectColour(zone.index)}"
                >${zone.id1}</span
              >
              <span class="iu-name">${stateObj.attributes.friendly_name}</span>
            </div>
            <div class="iu-td4" @click="${this._moreInfo}">
              <div ?hidden=${!isEnabled || isBlocked}>
                <span class="iu-schedule">${schedule_name}</span>
                <br ?hidden=${isOn || isManual || suspended} />
                <span class="iu-start" ?hidden=${isOn || isManual}
                  >${startStr}</span
                >
              </div>
              <div ?hidden=${!(!isEnabled || isBlocked)}>&nbsp;</div>
            </div>
            <div class="iu-td5 iu-duration">
              <div ?hidden=${!isEnabled || suspended || isBlocked}>
                ${duration}
              </div>
            </div>
            <div class="iu-td6 iu-adjustment">
              <div ?hidden=${!isEnabled || isBlocked || suspended || isManual}>
                ${humanise_adjustment(adjustment)}
              </div>
            </div>
            <div class="iu-td7">
              ${this._renderMenu(isEnabled, isBlocked, true, true, 0, adjustment, suspended)}
            </div>
          </div>
          <div class="iu-zone-timelines iu-content">
            ${timeline.map((item) => this._renderTimeline(item))}
          </div>
        </div>
      </div>
    `;
    }
    _renderTimeline(timeline) {
        const start = new Date(timeline.start);
        const duration = new Date(new Date(timeline.end).getTime() - start.getTime())
            .toISOString()
            .slice(12, 19);
        const startStr = start.toLocaleString(undefined, {
            weekday: "short",
            month: "numeric",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
            hour12: false,
        });
        const classes = ["iu-zone-timeline", "iu-object"];
        let icon = "";
        if (timeline.status === "history") {
            classes.push("iu-timeline-history");
            icon = "mdi:history";
        }
        else if (timeline.status === "scheduled") {
            classes.push("iu-timeline-scheduled");
            icon = "mdi:clock-outline";
        }
        else if (timeline.status === "next") {
            classes.push("iu-timeline-next");
            icon = "mdi:clock-star-four-points-outline";
        }
        else if (timeline.status === "running") {
            classes.push("iu-timeline-running");
            icon = "mdi:play";
        }
        let schedule_name;
        if (timeline.schedule !== 0)
            schedule_name = timeline.schedule_name;
        else
            schedule_name = loc.t("menu.manual.name");
        const dvf_present = timeline.volume != null || timeline.flow_rate != null ? "iu-dvf" : "";
        return x `
      <div class=${classes.join(" ")}>
        <div class="iu-timeline-row iu-td">
          <div class="iu-td1"></div>
          <div class="iu-td2">
            <ha-icon icon=${icon}></ha-icon>
          </div>
          <div class="iu-td3">${startStr}</div>
          <div class="iu-td4 iu-schedule">${schedule_name}</div>
          <div class="iu-td5 ${dvf_present}">
            <div class="iu-content">
              <span class="iu-duration">${duration}</span>
              <span class="iu-volume" ?hidden=${timeline.volume == null}
                ><br />${timeline.volume}</span
              >
              <span class="iu-flow-rate" ?hidden=${timeline.flow_rate == null}
                ><br />${timeline.flow_rate}</span
              >
            </div>
          </div>
          <div class="iu-td6 iu-adjustment">
            ${humanise_adjustment(timeline.adjustment)}
          </div>
          <div class="iu-td7"></div>
        </div>
      </div>
    `;
    }
    _renderSequence(controller, sequence) {
        const stateObj = this.hass.states[sequence.entity_id];
        const status = stateObj.attributes.status;
        const isOn = status === "on";
        const isPaused = status === "paused";
        const isDelay = status === "delay";
        const isBlocked = status === "blocked";
        const isEnabled = stateObj.attributes.enabled;
        const suspended = stateObj.attributes.suspended;
        let start;
        let duration;
        let schedule_index;
        let schedule_name;
        let adjustment;
        if (isOn || isPaused || isDelay) {
            start = new Date(stateObj.attributes.current_start);
            duration = sequence.remaining;
            schedule_index = stateObj.attributes.current_schedule;
            schedule_name = stateObj.attributes.current_name;
            adjustment = stateObj.attributes.adjustment;
        }
        else if (suspended) {
            start = new Date(suspended);
            duration = "";
            schedule_index = -1;
            schedule_name = "";
            adjustment = "";
        }
        else {
            start = new Date(stateObj.attributes.next_start);
            duration = stateObj.attributes.next_duration;
            schedule_index = stateObj.attributes.next_schedule;
            schedule_name = stateObj.attributes.next_name;
            adjustment = stateObj.attributes.adjustment;
        }
        const isManual = schedule_index === 0;
        if (isManual)
            schedule_name = loc.t("menu.manual.name");
        const isRunning = sequence.remaining !== undefined;
        const startStr = date_to_str(start);
        const classes = ["iu-sequence", "iu-object"];
        if (isOn)
            classes.push("iu-on");
        if (isPaused)
            classes.push("iu-paused");
        if (isDelay)
            classes.push("iu-delay");
        if (isEnabled)
            classes.push("iu-enabled");
        if (suspended)
            classes.push("iu-suspended");
        if (isManual)
            classes.push("iu-manual");
        if (isRunning)
            classes.push("iu-running");
        if (isBlocked)
            classes.push("iu-blocked");
        return x `
      <div
        class=${classes.join(" ")}
        iu-key="${controller.id1}.0.${sequence.id1}.0"
      >
        <div class="iu-collapsible iu-hidden">
          <div class="iu-sequence-row iu-td">
            <div
              class="iu-td1 iu-expander"
              @click="${this._toggleCollapse}"
            ></div>
            <div class="iu-td2" @click="${this._toggleCollapse}">
              <ha-icon
                .icon=${stateObj.attributes.icon}
                ?is-on=${isOn || isPaused}
              ></ha-icon>
            </div>
            <div class="iu-td3" @click="${this._toggleCollapse}">
              <span>${sequence.id1}</span>
              <span class="iu-name">${sequence.name}</span>
            </div>
            <div class="iu-td4" @click="${this._moreInfo}">
              <div ?hidden=${!isEnabled || isBlocked}>
                <span class="iu-schedule">${schedule_name}</span>
                <br ?hidden=${isOn || isPaused || isDelay || suspended} />
                <span class="iu-start" ?hidden=${isOn || isPaused || isDelay}
                  >${startStr}</span
                >
              </div>
              <div ?hidden=${!(!isEnabled || isBlocked)}>&nbsp;</div>
            </div>
            <div class="iu-td5 iu-duration">
              <div ?hidden=${!isEnabled || suspended || isBlocked}>
                ${duration}
              </div>
            </div>
            <div class="iu-td6 iu-adjustment">
              <div ?hidden=${isManual}>${humanise_adjustment(adjustment)}</div>
            </div>
            <div class="iu-td7">
              ${this._renderMenu(isEnabled, isBlocked, true, true, status === "on" || status === "delay"
            ? 1
            : status === "paused"
                ? 2
                : 0, adjustment, suspended)}
            </div>
          </div>
          <div class="iu-sequence-zones iu-content">
            ${sequence.zones.map((zone) => this._renderSequenceZone(controller, sequence, zone, isManual))}
          </div>
        </div>
      </div>
    `;
    }
    _renderSequenceZone(controller, sequence, sequenceZone, isManual) {
        var _a;
        const status = sequenceZone.status;
        const isOn = status === "on";
        const isEnabled = sequenceZone.enabled;
        const suspended = sequenceZone.suspended;
        const isBlocked = status === "blocked";
        const isRunning = sequenceZone.remaining !== undefined;
        let duration;
        let startStr = "";
        if (isOn)
            duration = sequenceZone.remaining;
        else if (suspended)
            duration = "";
        else
            duration = sequenceZone.duration;
        if (suspended !== null) {
            const start = new Date(suspended);
            startStr = date_to_str(start);
        }
        const classes = ["iu-sequence-zone", "iu-object"];
        if (isOn)
            classes.push("iu-on");
        if (isEnabled)
            classes.push("iu-enabled");
        if (suspended)
            classes.push("iu-suspended");
        if (isManual)
            classes.push("iu-manual");
        if (isRunning)
            classes.push("iu-running");
        if (isBlocked)
            classes.push("iu-blocked");
        return x `
      <div
        class=${classes.join(" ")}
        iu-key="${controller.id1}.0.${sequence.id1}.${sequenceZone.id1}"
      >
        <div class="iu-sequence-zone-row iu-td">
          <div class="iu-td1"></div>
          <div class="iu-td2">
            <ha-icon .icon=${sequenceZone.icon} ?is-on=${isOn}></ha-icon>
          </div>
          <div class="iu-td3">
            <span
              >${sequenceZone.zone_ids.map((zoneRef, index, array) => this._renderSequenceZoneRef(controller, zoneRef, index === array.length - 1))}</span
            >
          </div>
          <div class="iu-td4">
            <div ?hidden=${!isEnabled || isBlocked}>
              <span class="iu-start">${startStr}</span>
            </div>
          </div>
          <div class="iu-td5 iu-duration">
            <div ?hidden=${!isEnabled || suspended !== null || isBlocked}>
              ${duration}
            </div>
          </div>
          <div class="iu-td6 iu-adjustment">
            <div ?hidden=${isManual}>
              ${humanise_adjustment((_a = sequenceZone.adjustment) !== null && _a !== void 0 ? _a : "")}
            </div>
          </div>
          <div class="iu-td7">
            ${this._renderMenu(isEnabled, isBlocked, false, false, 0, sequenceZone.adjustment, suspended)}
          </div>
        </div>
      </div>
    `;
    }
    _renderSequenceZoneRef(controller, zoneRef, last) {
        const name = controller.lookup_zone_name(zoneRef);
        if (name)
            return x `<span class="iu-name"
        >${name}${last === false ? ", " : ""}</span
      >`;
        return x `
      <span style="color: ${this._selectColour(parseInt(zoneRef) - 1)}"
        >${zoneRef}</span
      >
    `;
    }
    _renderMenu(isEnabled, isBlocked, allowManual, allowCancel, pauseResume, adjustment, suspended) {
        return x `
      <div class="iu-menu">
        <ha-icon
          class="iu-menu-button"
          icon="mdi:dots-vertical"
          @click="${this._toggleMenu}"
        ></ha-icon>
        <div class="iu-menu-content iu-hidden">
          <div class="iu-menu-item iu-enable">
            <div class="iu-mc1">${loc.t("menu.enable.name")}</div>
            <div class="iu-mc2"></div>
            <div class="iu-mc3">
              ${this._renderEnabled(isEnabled, isBlocked)}
            </div>
          </div>
          <div
            class="iu-menu-item iu-suspend ${suspended === undefined
            ? "iu-hidden"
            : ""}"
          >
            <div class="iu-mc1">${loc.t("menu.suspend.name")}</div>
            <div class="iu-mc2">
              <input
                type="text"
                class="iu-time-input"
                placeholder="h:mm:ss"
                title=${loc.t("menu.suspend.hint")}
                size="8"
                maxlength="8"
                required
                pattern="^[0-9]{1,2}:[0-9]{2}:[0-9]{2}$"
                @keydown="${this._serviceSuspend}"
              />
            </div>
            <div class="iu-mc3">
              <ha-icon-button
                icon="mdi:timer-outline"
                title=${loc.t("menu.suspend.buttonHint")}
                @click="${this._serviceSuspend}"
              >
                <ha-icon icon="mdi:timer-outline"></ha-icon>
              </ha-icon-button>
            </div>
          </div>
          <div
            class="iu-menu-item iu-manual ${!allowManual ? "iu-hidden" : ""}"
          >
            <div class="iu-mc1">${loc.t("menu.manual.name")}</div>
            <div class="iu-mc2">
              <input
                type="text"
                class="iu-time-input"
                placeholder="0:00:00"
                title=${loc.t("menu.manual.hint")}
                size="8"
                maxlength="8"
                required
                pattern="^[0-9]{1,2}:[0-9]{2}:[0-9]{2}$"
                @keydown="${this._serviceManualRun}"
              />
            </div>
            <div class="iu-mc3">
              <ha-icon-button
                icon="mdi:play"
                title=${loc.t("menu.manual.buttonHint")}
                @click="${this._serviceManualRun}"
              >
                <ha-icon icon="mdi:run"></ha-icon>
              </ha-icon-button>
            </div>
          </div>
          <div
            class="iu-menu-item iu-pause ${(~pauseResume & 1) > 0
            ? "iu-hidden"
            : ""}"
          >
            <div class="iu-mc1">${loc.t("menu.pause.name")}</div>
            <div class="iu-mc2"></div>
            <div class="iu-mc3">
              <ha-icon-button
                .disabled=${(~pauseResume & 1) > 0}
                title=${loc.t("menu.pause.buttonHint")}
                @click="${this._servicePause}"
              >
                <ha-icon icon="mdi:pause"></ha-icon>
              </ha-icon-button>
            </div>
          </div>
          <div
            class="iu-menu-item iu-resume ${(~pauseResume & 2) > 0
            ? "iu-hidden"
            : ""}"
          >
            <div class="iu-mc1">${loc.t("menu.resume.name")}</div>
            <div class="iu-mc2"></div>
            <div class="iu-mc3">
              <ha-icon-button
                .disabled=${(~pauseResume & 2) > 0}
                title=${loc.t("menu.resume.buttonHint")}
                @click="${this._serviceResume}"
              >
                <ha-icon icon="mdi:play"></ha-icon>
              </ha-icon-button>
            </div>
          </div>
          <div
            class="iu-menu-item iu-cancel ${!allowCancel ? "iu-hidden" : ""}"
          >
            <div class="iu-mc1">${loc.t("menu.cancel.name")}</div>
            <div class="iu-mc2"></div>
            <div class="iu-mc3">
              <ha-icon-button
                .disabled=${!allowCancel}
                title=${loc.t("menu.cancel.buttonHint")}
                @click="${this._serviceCancel}"
              >
                <ha-icon icon="mdi:cancel"></ha-icon>
              </ha-icon-button>
            </div>
          </div>
          <div
            class="iu-menu-item iu-adjust ${adjustment === undefined
            ? "iu-hidden"
            : ""}"
          >
            <div class="iu-mc1">${loc.t("menu.adjust.name")}</div>
            <div class="iu-mc2">
              <input
                type="text"
                class="iu-adjust-input"
                value=${adjustment !== null && adjustment !== void 0 ? adjustment : ""}
                title=${loc.t("menu.adjust.hint")}
                size="9"
                maxlength="9"
                pattern="^$|^[=+-][0-9]{1,2}:[0-9]{2}:[0-9]{2}$|^%[0-9]*.?[0-9]+$"
                @keydown="${this._serviceAdjust}"
              />
            </div>
            <div class="iu-mc3">
              <ha-icon-button
                title=${loc.t("menu.adjust.buttonHint")}
                @click="${this._serviceAdjust}"
              >
                <ha-icon icon="mdi:adjust"></ha-icon>
              </ha-icon-button>
            </div>
          </div>
        </div>
      </div>
    `;
    }
    _renderEnabled(isEnabled, isBlocked) {
        return x `
      <ha-switch
        .checked=${isEnabled}
        .disabled=${isBlocked}
        title=${loc.t("menu.enable.buttonHint")}
        @change="${this._serviceEnable}"
      ></ha-switch>
    `;
    }
    _selectColour(index) {
        const palette = [
            "#3498db",
            "#e74c3c",
            "#9b59b6",
            "#f1c40f",
            "#2ecc71",
            "#1abc9c",
            "#34495e",
            "#e67e22",
            "#7f8c8d",
            "#27ae60",
            "#2980b9",
            "#8e44ad",
        ];
        return palette[index % palette.length];
    }
    _clickNet(e) {
        if (e.target.closest(".iu-menu"))
            return;
        this._closeAllMenus(e);
    }
    _toggleCollapse(e) {
        const target = e.target.closest(".iu-collapsible");
        target === null || target === void 0 ? void 0 : target.classList.toggle("iu-hidden");
    }
    _toggleZones(e) {
        var _a, _b;
        (_b = (_a = e.target
            .closest(".iu-controller")) === null || _a === void 0 ? void 0 : _a.querySelector(".iu-zones")) === null || _b === void 0 ? void 0 : _b.classList.toggle("iu-hidden");
    }
    _toggleSequences(e) {
        var _a, _b;
        (_b = (_a = e.target
            .closest(".iu-controller")) === null || _a === void 0 ? void 0 : _a.querySelector(".iu-sequences")) === null || _b === void 0 ? void 0 : _b.classList.toggle("iu-hidden");
    }
    _closeAllMenus(e) {
        var _a;
        const menus = (_a = e.target
            .closest("#iu-card")) === null || _a === void 0 ? void 0 : _a.querySelectorAll(".iu-menu-content:not(.iu-hidden)");
        menus === null || menus === void 0 ? void 0 : menus.forEach((p) => p.classList.add("iu-hidden"));
    }
    _toggleMenu(e) {
        var _a;
        const menu = (_a = e.target
            .closest(".iu-menu")) === null || _a === void 0 ? void 0 : _a.querySelector(".iu-menu-content");
        if (menu === null || menu === void 0 ? void 0 : menu.classList.contains("iu-hidden"))
            this._closeAllMenus(e);
        menu === null || menu === void 0 ? void 0 : menu.classList.toggle("iu-hidden");
    }
    _isNotEnterKey(e) {
        return e instanceof KeyboardEvent && e.key !== "Enter";
    }
    _get_iu_key(e) {
        var _a, _b;
        return (_b = (_a = e.target
            .closest(".iu-object")) === null || _a === void 0 ? void 0 : _a.getAttribute("iu-key")) === null || _b === void 0 ? void 0 : _b.split(".", 4);
    }
    _build_entity_id(keys) {
        const controller = this.iu_coordinator.controllers[+keys[0] - 1];
        let entity_id;
        if (keys[1] === "0" && keys[2] === "0") {
            entity_id = controller.entity_id;
        }
        else if (keys[1] !== "0") {
            entity_id = controller.zones[+keys[1] - 1].entity_id;
        }
        else {
            entity_id = controller.sequences[+keys[2] - 1].entity_id;
        }
        return entity_id;
    }
    _build_data(e) {
        const keys = this._get_iu_key(e);
        if (!keys)
            return;
        const entity_id = this._build_entity_id(keys);
        const data = {
            entity_id: entity_id,
        };
        if (keys[3] !== "0") {
            data["zones"] = Number(keys[3]);
        }
        return data;
    }
    _moreInfo(e) {
        const keys = this._get_iu_key(e);
        if (!keys)
            return;
        const entity_id = this._build_entity_id(keys);
        fireEvent(this, "hass-more-info", { entityId: entity_id, view: "history" });
    }
    _serviceEnable(e) {
        const data = this._build_data(e);
        if (!data)
            return;
        this.hass.callService("irrigation_unlimited", "toggle", data);
        return;
    }
    _serviceSuspend(e) {
        var _a;
        if (this._isNotEnterKey(e))
            return;
        const data = this._build_data(e);
        if (!data)
            return;
        const timeElement = (_a = e.target
            .closest(".iu-menu-item")) === null || _a === void 0 ? void 0 : _a.querySelector(".iu-time-input");
        if (timeElement.value)
            data["for"] = timeElement.value;
        else
            data["reset"] = null;
        this.hass.callService("irrigation_unlimited", "suspend", data);
    }
    _serviceManualRun(e) {
        var _a;
        if (this._isNotEnterKey(e))
            return;
        const data = this._build_data(e);
        if (!data)
            return;
        const timeElement = (_a = e.target
            .closest(".iu-menu-item")) === null || _a === void 0 ? void 0 : _a.querySelector(".iu-time-input");
        if (timeElement.value)
            data["time"] = timeElement.value;
        this.hass.callService("irrigation_unlimited", "manual_run", data);
        this._toggleMenu(e);
        return;
    }
    _serviceCancel(e) {
        const data = this._build_data(e);
        if (!data)
            return;
        this.hass.callService("irrigation_unlimited", "cancel", data);
        this._toggleMenu(e);
    }
    _servicePause(e) {
        const data = this._build_data(e);
        if (!data)
            return;
        data["sequence_id"] = "0";
        this.hass.callService("irrigation_unlimited", "pause", data);
        this._toggleMenu(e);
    }
    _serviceResume(e) {
        const data = this._build_data(e);
        if (!data)
            return;
        data["sequence_id"] = "0";
        this.hass.callService("irrigation_unlimited", "resume", data);
        this._toggleMenu(e);
    }
    _serviceAdjust(e) {
        var _a;
        if (this._isNotEnterKey(e))
            return;
        const data = this._build_data(e);
        if (!data)
            return;
        const adjustElement = (_a = e.target
            .closest(".iu-menu-item")) === null || _a === void 0 ? void 0 : _a.querySelector(".iu-adjust-input");
        const value = adjustElement.value;
        switch (value.slice(0, 1)) {
            case "%": {
                data["percentage"] = value.slice(1);
                break;
            }
            case "=": {
                data["actual"] = value.slice(1);
                break;
            }
            case "+": {
                data["increase"] = value.slice(1);
                break;
            }
            case "-": {
                data["decrease"] = value.slice(1);
                break;
            }
            case "": {
                data["reset"] = null;
                break;
            }
            default:
                return;
        }
        const keys = this._get_iu_key(e);
        if ("reset" in data && keys && keys[1] === "0" && keys[2] === "0") {
            this.hass.callService("irrigation_unlimited", "adjust_time", data);
            data["sequence_id"] = 0;
            this.hass.callService("irrigation_unlimited", "adjust_time", data);
            data["zones"] = 0;
            this.hass.callService("irrigation_unlimited", "adjust_time", data);
        }
        else
            this.hass.callService("irrigation_unlimited", "adjust_time", data);
        this._toggleMenu(e);
    }
};
IrrigationUnlimitedCard.styles = styles;
__decorate([
    n$1({ attribute: false })
], IrrigationUnlimitedCard.prototype, "hass", void 0);
__decorate([
    t()
], IrrigationUnlimitedCard.prototype, "config", void 0);
IrrigationUnlimitedCard = __decorate([
    e$1("irrigation-unlimited-card")
], IrrigationUnlimitedCard);

export { IrrigationUnlimitedCard };
