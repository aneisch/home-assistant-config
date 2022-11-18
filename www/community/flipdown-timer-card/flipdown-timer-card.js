function t(t,e,o,i){var s,r=arguments.length,n=r<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,o):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(t,e,o,i);else for(var l=t.length-1;l>=0;l--)(s=t[l])&&(n=(r<3?s(n):r>3?s(e,o,n):s(e,o))||n);return r>3&&n&&Object.defineProperty(e,o,n),n
/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */}const e=window,o=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),s=new WeakMap;class r{constructor(t,e,o){if(this._$cssResult$=!0,o!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(o&&void 0===t){const o=void 0!==e&&1===e.length;o&&(t=s.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),o&&s.set(e,t))}return t}toString(){return this.cssText}}const n=t=>new r("string"==typeof t?t:t+"",void 0,i),l=(t,...e)=>{const o=1===t.length?t[0]:e.reduce(((e,o,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+t[i+1]),t[0]);return new r(o,t,i)},a=o?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const o of t.cssRules)e+=o.cssText;return n(e)})(t):t
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */;var h;const d=window,c=d.trustedTypes,p=c?c.emptyScript:"",u=d.reactiveElementPolyfillSupport,f={toAttribute(t,e){switch(e){case Boolean:t=t?p:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let o=t;switch(e){case Boolean:o=null!==t;break;case Number:o=null===t?null:Number(t);break;case Object:case Array:try{o=JSON.parse(t)}catch(t){o=null}}return o}},g=(t,e)=>e!==t&&(e==e||t==t),m={attribute:!0,type:String,converter:f,reflect:!1,hasChanged:g};class _ extends HTMLElement{constructor(){super(),this._$Ei=new Map,this.isUpdatePending=!1,this.hasUpdated=!1,this._$El=null,this.u()}static addInitializer(t){var e;this.finalize(),(null!==(e=this.h)&&void 0!==e?e:this.h=[]).push(t)}static get observedAttributes(){this.finalize();const t=[];return this.elementProperties.forEach(((e,o)=>{const i=this._$Ep(o,e);void 0!==i&&(this._$Ev.set(i,o),t.push(i))})),t}static createProperty(t,e=m){if(e.state&&(e.attribute=!1),this.finalize(),this.elementProperties.set(t,e),!e.noAccessor&&!this.prototype.hasOwnProperty(t)){const o="symbol"==typeof t?Symbol():"__"+t,i=this.getPropertyDescriptor(t,o,e);void 0!==i&&Object.defineProperty(this.prototype,t,i)}}static getPropertyDescriptor(t,e,o){return{get(){return this[e]},set(i){const s=this[t];this[e]=i,this.requestUpdate(t,s,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)||m}static finalize(){if(this.hasOwnProperty("finalized"))return!1;this.finalized=!0;const t=Object.getPrototypeOf(this);if(t.finalize(),void 0!==t.h&&(this.h=[...t.h]),this.elementProperties=new Map(t.elementProperties),this._$Ev=new Map,this.hasOwnProperty("properties")){const t=this.properties,e=[...Object.getOwnPropertyNames(t),...Object.getOwnPropertySymbols(t)];for(const o of e)this.createProperty(o,t[o])}return this.elementStyles=this.finalizeStyles(this.styles),!0}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const o=new Set(t.flat(1/0).reverse());for(const t of o)e.unshift(a(t))}else void 0!==t&&e.push(a(t));return e}static _$Ep(t,e){const o=e.attribute;return!1===o?void 0:"string"==typeof o?o:"string"==typeof t?t.toLowerCase():void 0}u(){var t;this._$E_=new Promise((t=>this.enableUpdating=t)),this._$AL=new Map,this._$Eg(),this.requestUpdate(),null===(t=this.constructor.h)||void 0===t||t.forEach((t=>t(this)))}addController(t){var e,o;(null!==(e=this._$ES)&&void 0!==e?e:this._$ES=[]).push(t),void 0!==this.renderRoot&&this.isConnected&&(null===(o=t.hostConnected)||void 0===o||o.call(t))}removeController(t){var e;null===(e=this._$ES)||void 0===e||e.splice(this._$ES.indexOf(t)>>>0,1)}_$Eg(){this.constructor.elementProperties.forEach(((t,e)=>{this.hasOwnProperty(e)&&(this._$Ei.set(e,this[e]),delete this[e])}))}createRenderRoot(){var t;const i=null!==(t=this.shadowRoot)&&void 0!==t?t:this.attachShadow(this.constructor.shadowRootOptions);return((t,i)=>{o?t.adoptedStyleSheets=i.map((t=>t instanceof CSSStyleSheet?t:t.styleSheet)):i.forEach((o=>{const i=document.createElement("style"),s=e.litNonce;void 0!==s&&i.setAttribute("nonce",s),i.textContent=o.cssText,t.appendChild(i)}))})(i,this.constructor.elementStyles),i}connectedCallback(){var t;void 0===this.renderRoot&&(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),null===(t=this._$ES)||void 0===t||t.forEach((t=>{var e;return null===(e=t.hostConnected)||void 0===e?void 0:e.call(t)}))}enableUpdating(t){}disconnectedCallback(){var t;null===(t=this._$ES)||void 0===t||t.forEach((t=>{var e;return null===(e=t.hostDisconnected)||void 0===e?void 0:e.call(t)}))}attributeChangedCallback(t,e,o){this._$AK(t,o)}_$EO(t,e,o=m){var i;const s=this.constructor._$Ep(t,o);if(void 0!==s&&!0===o.reflect){const r=(void 0!==(null===(i=o.converter)||void 0===i?void 0:i.toAttribute)?o.converter:f).toAttribute(e,o.type);this._$El=t,null==r?this.removeAttribute(s):this.setAttribute(s,r),this._$El=null}}_$AK(t,e){var o;const i=this.constructor,s=i._$Ev.get(t);if(void 0!==s&&this._$El!==s){const t=i.getPropertyOptions(s),r="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==(null===(o=t.converter)||void 0===o?void 0:o.fromAttribute)?t.converter:f;this._$El=s,this[s]=r.fromAttribute(e,t.type),this._$El=null}}requestUpdate(t,e,o){let i=!0;void 0!==t&&(((o=o||this.constructor.getPropertyOptions(t)).hasChanged||g)(this[t],e)?(this._$AL.has(t)||this._$AL.set(t,e),!0===o.reflect&&this._$El!==t&&(void 0===this._$EC&&(this._$EC=new Map),this._$EC.set(t,o))):i=!1),!this.isUpdatePending&&i&&(this._$E_=this._$Ej())}async _$Ej(){this.isUpdatePending=!0;try{await this._$E_}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var t;if(!this.isUpdatePending)return;this.hasUpdated,this._$Ei&&(this._$Ei.forEach(((t,e)=>this[e]=t)),this._$Ei=void 0);let e=!1;const o=this._$AL;try{e=this.shouldUpdate(o),e?(this.willUpdate(o),null===(t=this._$ES)||void 0===t||t.forEach((t=>{var e;return null===(e=t.hostUpdate)||void 0===e?void 0:e.call(t)})),this.update(o)):this._$Ek()}catch(t){throw e=!1,this._$Ek(),t}e&&this._$AE(o)}willUpdate(t){}_$AE(t){var e;null===(e=this._$ES)||void 0===e||e.forEach((t=>{var e;return null===(e=t.hostUpdated)||void 0===e?void 0:e.call(t)})),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$Ek(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$E_}shouldUpdate(t){return!0}update(t){void 0!==this._$EC&&(this._$EC.forEach(((t,e)=>this._$EO(e,this[e],t))),this._$EC=void 0),this._$Ek()}updated(t){}firstUpdated(t){}}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var v;_.finalized=!0,_.elementProperties=new Map,_.elementStyles=[],_.shadowRootOptions={mode:"open"},null==u||u({ReactiveElement:_}),(null!==(h=d.reactiveElementVersions)&&void 0!==h?h:d.reactiveElementVersions=[]).push("1.4.2");const b=window,w=b.trustedTypes,y=w?w.createPolicy("lit-html",{createHTML:t=>t}):void 0,$=`lit$${(Math.random()+"").slice(9)}$`,x="?"+$,k=`<${x}>`,E=document,A=(t="")=>E.createComment(t),S=t=>null===t||"object"!=typeof t&&"function"!=typeof t,C=Array.isArray,N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,R=/-->/g,T=/>/g,O=RegExp(">|[ \t\n\f\r](?:([^\\s\"'>=/]+)([ \t\n\f\r]*=[ \t\n\f\r]*(?:[^ \t\n\f\r\"'`<>=]|(\"|')|))|$)","g"),H=/'/g,L=/"/g,P=/^(?:script|style|textarea|title)$/i,z=(t=>(e,...o)=>({_$litType$:t,strings:e,values:o}))(1),B=Symbol.for("lit-noChange"),V=Symbol.for("lit-nothing"),U=new WeakMap,M=E.createTreeWalker(E,129,null,!1),q=(t,e)=>{const o=t.length-1,i=[];let s,r=2===e?"<svg>":"",n=N;for(let e=0;e<o;e++){const o=t[e];let l,a,h=-1,d=0;for(;d<o.length&&(n.lastIndex=d,a=n.exec(o),null!==a);)d=n.lastIndex,n===N?"!--"===a[1]?n=R:void 0!==a[1]?n=T:void 0!==a[2]?(P.test(a[2])&&(s=RegExp("</"+a[2],"g")),n=O):void 0!==a[3]&&(n=O):n===O?">"===a[0]?(n=null!=s?s:N,h=-1):void 0===a[1]?h=-2:(h=n.lastIndex-a[2].length,l=a[1],n=void 0===a[3]?O:'"'===a[3]?L:H):n===L||n===H?n=O:n===R||n===T?n=N:(n=O,s=void 0);const c=n===O&&t[e+1].startsWith("/>")?" ":"";r+=n===N?o+k:h>=0?(i.push(l),o.slice(0,h)+"$lit$"+o.slice(h)+$+c):o+$+(-2===h?(i.push(void 0),e):c)}const l=r+(t[o]||"<?>")+(2===e?"</svg>":"");if(!Array.isArray(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return[void 0!==y?y.createHTML(l):l,i]};class I{constructor({strings:t,_$litType$:e},o){let i;this.parts=[];let s=0,r=0;const n=t.length-1,l=this.parts,[a,h]=q(t,e);if(this.el=I.createElement(a,o),M.currentNode=this.el.content,2===e){const t=this.el.content,e=t.firstChild;e.remove(),t.append(...e.childNodes)}for(;null!==(i=M.nextNode())&&l.length<n;){if(1===i.nodeType){if(i.hasAttributes()){const t=[];for(const e of i.getAttributeNames())if(e.endsWith("$lit$")||e.startsWith($)){const o=h[r++];if(t.push(e),void 0!==o){const t=i.getAttribute(o.toLowerCase()+"$lit$").split($),e=/([.?@])?(.*)/.exec(o);l.push({type:1,index:s,name:e[2],strings:t,ctor:"."===e[1]?X:"?"===e[1]?K:"@"===e[1]?J:W})}else l.push({type:6,index:s})}for(const e of t)i.removeAttribute(e)}if(P.test(i.tagName)){const t=i.textContent.split($),e=t.length-1;if(e>0){i.textContent=w?w.emptyScript:"";for(let o=0;o<e;o++)i.append(t[o],A()),M.nextNode(),l.push({type:2,index:++s});i.append(t[e],A())}}}else if(8===i.nodeType)if(i.data===x)l.push({type:2,index:s});else{let t=-1;for(;-1!==(t=i.data.indexOf($,t+1));)l.push({type:7,index:s}),t+=$.length-1}s++}}static createElement(t,e){const o=E.createElement("template");return o.innerHTML=t,o}}function D(t,e,o=t,i){var s,r,n,l;if(e===B)return e;let a=void 0!==i?null===(s=o._$Co)||void 0===s?void 0:s[i]:o._$Cl;const h=S(e)?void 0:e._$litDirective$;return(null==a?void 0:a.constructor)!==h&&(null===(r=null==a?void 0:a._$AO)||void 0===r||r.call(a,!1),void 0===h?a=void 0:(a=new h(t),a._$AT(t,o,i)),void 0!==i?(null!==(n=(l=o)._$Co)&&void 0!==n?n:l._$Co=[])[i]=a:o._$Cl=a),void 0!==a&&(e=D(t,a._$AS(t,e.values),a,i)),e}class j{constructor(t,e){this.u=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}v(t){var e;const{el:{content:o},parts:i}=this._$AD,s=(null!==(e=null==t?void 0:t.creationScope)&&void 0!==e?e:E).importNode(o,!0);M.currentNode=s;let r=M.nextNode(),n=0,l=0,a=i[0];for(;void 0!==a;){if(n===a.index){let e;2===a.type?e=new F(r,r.nextSibling,this,t):1===a.type?e=new a.ctor(r,a.name,a.strings,this,t):6===a.type&&(e=new Z(r,this,t)),this.u.push(e),a=i[++l]}n!==(null==a?void 0:a.index)&&(r=M.nextNode(),n++)}return s}p(t){let e=0;for(const o of this.u)void 0!==o&&(void 0!==o.strings?(o._$AI(t,o,e),e+=o.strings.length-2):o._$AI(t[e])),e++}}class F{constructor(t,e,o,i){var s;this.type=2,this._$AH=V,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=o,this.options=i,this._$Cm=null===(s=null==i?void 0:i.isConnected)||void 0===s||s}get _$AU(){var t,e;return null!==(e=null===(t=this._$AM)||void 0===t?void 0:t._$AU)&&void 0!==e?e:this._$Cm}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=D(this,t,e),S(t)?t===V||null==t||""===t?(this._$AH!==V&&this._$AR(),this._$AH=V):t!==this._$AH&&t!==B&&this.g(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>C(t)||"function"==typeof(null==t?void 0:t[Symbol.iterator]))(t)?this.k(t):this.g(t)}O(t,e=this._$AB){return this._$AA.parentNode.insertBefore(t,e)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}g(t){this._$AH!==V&&S(this._$AH)?this._$AA.nextSibling.data=t:this.T(E.createTextNode(t)),this._$AH=t}$(t){var e;const{values:o,_$litType$:i}=t,s="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=I.createElement(i.h,this.options)),i);if((null===(e=this._$AH)||void 0===e?void 0:e._$AD)===s)this._$AH.p(o);else{const t=new j(s,this),e=t.v(this.options);t.p(o),this.T(e),this._$AH=t}}_$AC(t){let e=U.get(t.strings);return void 0===e&&U.set(t.strings,e=new I(t)),e}k(t){C(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let o,i=0;for(const s of t)i===e.length?e.push(o=new F(this.O(A()),this.O(A()),this,this.options)):o=e[i],o._$AI(s),i++;i<e.length&&(this._$AR(o&&o._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){var o;for(null===(o=this._$AP)||void 0===o||o.call(this,!1,!0,e);t&&t!==this._$AB;){const e=t.nextSibling;t.remove(),t=e}}setConnected(t){var e;void 0===this._$AM&&(this._$Cm=t,null===(e=this._$AP)||void 0===e||e.call(this,t))}}class W{constructor(t,e,o,i,s){this.type=1,this._$AH=V,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=s,o.length>2||""!==o[0]||""!==o[1]?(this._$AH=Array(o.length-1).fill(new String),this.strings=o):this._$AH=V}get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}_$AI(t,e=this,o,i){const s=this.strings;let r=!1;if(void 0===s)t=D(this,t,e,0),r=!S(t)||t!==this._$AH&&t!==B,r&&(this._$AH=t);else{const i=t;let n,l;for(t=s[0],n=0;n<s.length-1;n++)l=D(this,i[o+n],e,n),l===B&&(l=this._$AH[n]),r||(r=!S(l)||l!==this._$AH[n]),l===V?t=V:t!==V&&(t+=(null!=l?l:"")+s[n+1]),this._$AH[n]=l}r&&!i&&this.j(t)}j(t){t===V?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,null!=t?t:"")}}class X extends W{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===V?void 0:t}}const G=w?w.emptyScript:"";class K extends W{constructor(){super(...arguments),this.type=4}j(t){t&&t!==V?this.element.setAttribute(this.name,G):this.element.removeAttribute(this.name)}}class J extends W{constructor(t,e,o,i,s){super(t,e,o,i,s),this.type=5}_$AI(t,e=this){var o;if((t=null!==(o=D(this,t,e,0))&&void 0!==o?o:V)===B)return;const i=this._$AH,s=t===V&&i!==V||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,r=t!==V&&(i===V||s);s&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){var e,o;"function"==typeof this._$AH?this._$AH.call(null!==(o=null===(e=this.options)||void 0===e?void 0:e.host)&&void 0!==o?o:this.element,t):this._$AH.handleEvent(t)}}class Z{constructor(t,e,o){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(t){D(this,t)}}const Q=b.litHtmlPolyfillSupport;null==Q||Q(I,F),(null!==(v=b.litHtmlVersions)&&void 0!==v?v:b.litHtmlVersions=[]).push("2.4.0");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var Y,tt;class et extends _{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var t,e;const o=super.createRenderRoot();return null!==(t=(e=this.renderOptions).renderBefore)&&void 0!==t||(e.renderBefore=o.firstChild),o}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,o)=>{var i,s;const r=null!==(i=null==o?void 0:o.renderBefore)&&void 0!==i?i:e;let n=r._$litPart$;if(void 0===n){const t=null!==(s=null==o?void 0:o.renderBefore)&&void 0!==s?s:null;r._$litPart$=n=new F(e.insertBefore(A(),t),t,void 0,null!=o?o:{})}return n._$AI(t),n})(e,this.renderRoot,this.renderOptions)}connectedCallback(){var t;super.connectedCallback(),null===(t=this._$Do)||void 0===t||t.setConnected(!0)}disconnectedCallback(){var t;super.disconnectedCallback(),null===(t=this._$Do)||void 0===t||t.setConnected(!1)}render(){return B}}et.finalized=!0,et._$litElement$=!0,null===(Y=globalThis.litElementHydrateSupport)||void 0===Y||Y.call(globalThis,{LitElement:et});const ot=globalThis.litElementPolyfillSupport;null==ot||ot({LitElement:et}),(null!==(tt=globalThis.litElementVersions)&&void 0!==tt?tt:globalThis.litElementVersions=[]).push("3.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const it=t=>e=>"function"==typeof e?((t,e)=>(customElements.define(t,e),e))(t,e):((t,e)=>{const{kind:o,elements:i}=e;return{kind:o,elements:i,finisher(e){customElements.define(t,e)}}})(t,e)
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */,st=(t,e)=>"method"===e.kind&&e.descriptor&&!("value"in e.descriptor)?{...e,finisher(o){o.createProperty(e.key,t)}}:{kind:"field",key:Symbol(),placement:"own",descriptor:{},originalKey:e.key,initializer(){"function"==typeof e.initializer&&(this[e.key]=e.initializer.call(this))},finisher(o){o.createProperty(e.key,t)}};function rt(t){return(e,o)=>void 0!==o?((t,e,o)=>{e.constructor.createProperty(o,t)})(t,e,o):st(t,e)}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function nt(t){return rt({...t,state:!0})}
/**
 * @license
 * Copyright 2021 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */var lt,at,ht;null===(lt=window.HTMLSlotElement)||void 0===lt||lt.prototype.assignedElements,function(t){t.language="language",t.system="system",t.comma_decimal="comma_decimal",t.decimal_comma="decimal_comma",t.space_comma="space_comma",t.none="none"}(at||(at={})),function(t){t.language="language",t.system="system",t.am_pm="12",t.twenty_four="24"}(ht||(ht={}));const dt={required:{icon:"tune",name:"Required",secondary:"Required options for this card to function",show:!0},actions:{icon:"gesture-tap-hold",name:"Actions",secondary:"Perform actions based on tapping/clicking",show:!1,options:{tap:{icon:"gesture-tap",name:"Tap",secondary:"Set the action to perform on tap",show:!1},hold:{icon:"gesture-tap-hold",name:"Hold",secondary:"Set the action to perform on hold",show:!1},double_tap:{icon:"gesture-double-tap",name:"Double Tap",secondary:"Set the action to perform on double tap",show:!1}}},appearance:{icon:"palette",name:"Appearance",secondary:"Customize the name, icon, etc",show:!1}};let ct=class extends et{constructor(){super(...arguments),this._initialized=!1}setConfig(t){this._config=t,this.loadCardHelpers()}shouldUpdate(){return this._initialized||this._initialize(),!0}get _name(){var t;return(null===(t=this._config)||void 0===t?void 0:t.name)||""}get _entity(){var t;return(null===(t=this._config)||void 0===t?void 0:t.entity)||""}get _show_title(){var t;return(null===(t=this._config)||void 0===t?void 0:t.show_title)||!1}get _show_error(){var t;return(null===(t=this._config)||void 0===t?void 0:t.show_error)||!1}get _tap_action(){var t;return(null===(t=this._config)||void 0===t?void 0:t.tap_action)||{action:"more-info"}}get _hold_action(){var t;return(null===(t=this._config)||void 0===t?void 0:t.hold_action)||{action:"none"}}get _double_tap_action(){var t;return(null===(t=this._config)||void 0===t?void 0:t.double_tap_action)||{action:"none"}}render(){if(!this.hass||!this._helpers)return z``;this._helpers.importMoreInfoControl("climate");let t=Object.keys(this.hass.states).filter((t=>"timer"===t.substr(0,t.indexOf("."))||"input_datetime"===t.substr(0,t.indexOf("."))||"sensor"===t.substr(0,t.indexOf("."))));return z`
      <div class="card-config">
        <div class="option" @click=${this._toggleOption} .option=${"required"}>
          <div class="row">
            <ha-icon .icon=${`mdi:${dt.required.icon}`}></ha-icon>
            <div class="title">${dt.required.name}</div>
          </div>
          <div class="secondary">${dt.required.secondary}</div>
        </div>
        ${dt.required.show?z`
              <div class="values">
                <paper-dropdown-menu
                  label="Entity (Required)"
                  @value-changed=${this._valueChanged}
                  .configValue=${"entity"}
                >
                  <paper-listbox slot="dropdown-content" .selected=${t.indexOf(this._entity)}>
                    ${t.map((t=>z`
                        <paper-item>${t}</paper-item>
                      `))}
                  </paper-listbox>
                </paper-dropdown-menu>
              </div>
            `:""}

        <div class="option" @click=${this._toggleOption} .option=${"appearance"}>
          <div class="row">
            <ha-icon .icon=${`mdi:${dt.appearance.icon}`}></ha-icon>
            <div class="title">${dt.appearance.name}</div>
          </div>
          <div class="secondary">${dt.appearance.secondary}</div>
        </div>
        ${dt.appearance.show?z`
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
    `}_initialize(){void 0!==this.hass&&void 0!==this._config&&void 0!==this._helpers&&(this._initialized=!0)}async loadCardHelpers(){this._helpers=await window.loadCardHelpers()}_toggleAction(t){this._toggleThing(t,dt.actions.options)}_toggleOption(t){this._toggleThing(t,dt)}_toggleThing(t,e){const o=!e[t.target.option].show;for(const[t]of Object.entries(e))e[t].show=!1;e[t.target.option].show=o,this._toggle=!this._toggle}_valueChanged(t){if(!this._config||!this.hass)return;const e=t.target;if(this[`_${e.configValue}`]!==e.value){if(e.configValue)if(""===e.value){const t=Object.assign({},this._config);delete t[e.configValue],this._config=t}else this._config=Object.assign(Object.assign({},this._config),{[e.configValue]:void 0!==e.checked?e.checked:e.value});!function(t,e,o,i){i=i||{},o=null==o?{}:o;var s=new Event(e,{bubbles:void 0===i.bubbles||i.bubbles,cancelable:Boolean(i.cancelable),composed:void 0===i.composed||i.composed});s.detail=o,t.dispatchEvent(s)}(this,"config-changed",{config:this._config})}}static get styles(){return l`
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
    `}};t([rt({attribute:!1})],ct.prototype,"hass",void 0),t([nt()],ct.prototype,"_config",void 0),t([nt()],ct.prototype,"_toggle",void 0),t([nt()],ct.prototype,"_helpers",void 0),ct=t([it("flipdown-timer-card-editor")],ct);var pt={version:"Version",invalid_configuration:"Invalid configuration",show_warning:"Show Warning",show_error:"Show Error"},ut={common:pt},ft={version:"Versjon",invalid_configuration:"Ikke gyldig konfiguration",show_warning:"Vis advarsel"},gt={common:ft};const mt={en:Object.freeze({__proto__:null,common:pt,default:ut}),nb:Object.freeze({__proto__:null,common:ft,default:gt})};function _t(t,e="",o=""){const i=(localStorage.getItem("selectedLanguage")||"en").replace(/['"]+/g,"").replace("-","_");let s;try{s=t.split(".").reduce(((t,e)=>t[e]),mt[i])}catch(e){s=t.split(".").reduce(((t,e)=>t[e]),mt.en)}return void 0===s&&(s=t.split(".").reduce(((t,e)=>t[e]),mt.en)),""!==e&&""!==o&&(s=s.replace(e,o)),s}function vt(t,e){return(t=t.toString()).length<e?vt("0"+t,e):t}function bt(t,e){e.forEach((e=>{t.appendChild(e)}))}class wt{constructor(t,e,o={}){if("number"!=typeof t)throw new Error(`FlipDown: Constructor expected unix timestamp, got ${typeof t} instead.`);this.rt=null,this.button1=null,this.button2=null,this.version="0.3.2",this._sign=!0,this.initialised=!1,this.active=!1,this.state="",this.headerShift=!1,this.delimeterBlink=null,this.delimeterIsBlinking=!1,this.now=this._getTime(),this.epoch=t,this.countdownEnded=!1,this.hasEndedCallback=null,this.element=e,this.rotorGroups=[],this.rotors=[],this.rotorLeafFront=[],this.rotorLeafRear=[],this.rotorTops=[],this.rotorBottoms=[],this.countdown=null,this.daysRemaining=0,this.clockValues={},this.clockStrings={},this.clockValuesAsString=[],this.prevClockValuesAsString=[],this.opts=this._parseOptions(o),this._setOptions()}start(){return this.initialised||this._init(),this.rt=null,this.active=!0,this._tick(),this}_startInterval(){clearInterval(this.countdown),this.active&&(this.countdown=window.setInterval(this._tick.bind(this),1e3))}stop(){clearInterval(this.countdown),this.countdown=null,this.active=!1}ifEnded(t){return this.hasEndedCallback=function(){t(),this.hasEndedCallback=null},this}_getTime(){return(new Date).getTime()/1e3}_hasCountdownEnded(){return this.epoch-this.now<0?(this.countdownEnded=!0,null!=this.hasEndedCallback&&(this.hasEndedCallback(),this.hasEndedCallback=null),!0):(this.countdownEnded=!1,!1)}_parseOptions(t){let e=["Days","Hours","Minutes","Seconds"];return t.headings&&4===t.headings.length&&(e=t.headings),{theme:t.hasOwnProperty("theme")&&t.theme?t.theme:"hass",showHeader:!(!t.hasOwnProperty("show_header")||!t.show_header)&&t.show_header,showHour:!(!t.hasOwnProperty("show_hour")||!t.show_hour)&&t.show_hour,btLocation:t.bt_location,headings:e}}_setOptions(){this.element.classList.add(`flipdown__theme-${this.opts.theme}`)}_init(t){this.state=t,this.initialised=!0,this._hasCountdownEnded()?this.daysremaining=0:this.daysremaining=Math.floor((this.epoch-this.now)/86400).toString().length;for(let t=0;t<6;t++)this.rotors.push(this._createRotor(0));let e=0;for(let t=0;t<3;t++){const o=[];for(let t=0;t<2;t++)this.rotors[e].setAttribute("id","d"+(1-t)),o.push(this.rotors[e]),e++;const i=this._createRotorGroup(o,t+1);this.rotorGroups.push(i),this.element.appendChild(i)}return this.element.appendChild(this._createButton()),this.rotorLeafFront=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-leaf-front")),this.rotorLeafRear=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-leaf-rear")),this.rotorTop=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-top")),this.rotorBottom=Array.prototype.slice.call(this.element.getElementsByClassName("rotor-bottom")),this._tick(),this._updateClockValues(!0),this}_createRotorGroup(t,e){const o=document.createElement("div");o.className="rotor-group",this.opts.showHour&&"auto"!=this.opts.showHour||1!=e||(o.className+=" hide"),"auto"==this.opts.showHour&&"idle"==this.state&&(o.className+=" autohour",this.headerShift=!0),o.setAttribute("id",this.opts.headings[e]);const i=document.createElement("div");if(i.className="rotor-group-heading",this.opts.showHeader?(i.setAttribute("data-before",this.opts.headings[e]),i.setAttribute("data-after",this.opts.headings[e-1])):(i.setAttribute("data-before"," "),i.setAttribute("data-after"," "),i.className+=" no-height"),o.appendChild(i),bt(o,t),e<3){const t=document.createElement("div");t.className="delimeter";const i=document.createElement("span");i.className="delimeter-span-top";const s=document.createElement("span");s.className="delimeter-span-bottom",bt(t,[i,s]),o.appendChild(t),2==e&&(this.delimeterBlink=t)}return o}_createButton(){const t=document.createElement("div");t.className="button-group","bottom"==this.opts.btLocation?t.className+=" button-bottom":"hide"==this.opts.btLocation?t.className+=" hide":t.className+=" button-right";const e=document.createElement("div");e.className="button-group-heading",e.setAttribute("data-before","");const o=document.createElement("div");return o.className="btn",this.button1=document.createElement("button"),this.button2=document.createElement("button"),this.button1.className="btn-top",this.button2.className="btn-bottom",this.opts.showHeader?bt(t,[e,o]):bt(t,[o]),bt(o,[this.button1,this.button2]),t}_createRotor(t=0){const e=document.createElement("div"),o=document.createElement("div"),i=document.createElement("div"),s=document.createElement("div"),r=document.createElement("figure"),n=document.createElement("figure"),l=document.createElement("div"),a=document.createElement("div");return e.className="rotor",s.className="rotor-leaf",r.className="rotor-leaf-rear",n.className="rotor-leaf-front",o.className="rotor-trans-top",i.className="rotor-trans-bottom",l.className="rotor-top",a.className="rotor-bottom",n.textContent=t,r.textContent=t,l.textContent=t,a.textContent=t,bt(e,[o,i,s,l,a]),bt(s,[r,n]),e}_updator(t){this.epoch=t}_tick(t=!1){let e;this.now=this._getTime(),this.epoch-this.now>=0?(e=Math.floor(this.epoch-this.now),this._sign=!0):(e=0,this._sign=!0),null!=this.rt&&(e=this.rt),this.clockValues.d=0,this.clockValues.h=Math.floor(e/3600),e-=3600*this.clockValues.h,this.clockValues.m=Math.floor(e/60),e-=60*this.clockValues.m,this.clockValues.s=Math.floor(e),this._updateClockValues(!1,t)}_updateClockValues(t=!1,e=!1){function o(){this.rotorBottom.forEach(((t,e)=>{t.textContent=this.clockValuesAsString[e]}))}function i(){this.rotorTop.forEach(((t,e)=>{t.textContent!=this.clockValuesAsString[e]&&(t.textContent=this.clockValuesAsString[e])}))}function s(){this.rotorLeafRear.forEach(((t,e)=>{if(t.textContent!=this.clockValuesAsString[e]){t.textContent=this.clockValuesAsString[e];let o=this._sign?"flipped":"flippedr";t.parentElement.classList.add(o);const i=setInterval(function(){t.parentElement.classList.remove(o),r.call(this),clearInterval(i)}.bind(this),500)}}))}function r(){this.rotorLeafFront.forEach(((t,e)=>{t.classList.remove("front-bottom")})),this.rotorLeafRear.forEach(((t,e)=>{t.classList.remove("rear-bottom")}))}this.clockStrings.d=vt(this.clockValues.d,2),this.clockStrings.h=vt(this.clockValues.h,2),this.clockStrings.m=vt(this.clockValues.m,2),this.clockStrings.s=vt(this.clockValues.s,2),"auto"==this.opts.showHour&&(this.clockValues.h>0||"idle"==this.state)?(this.headerShift||(this.rotorGroups.forEach((t=>t.classList.add("autohour"))),this.headerShift=!0),"active"!=this.state||this.delimeterIsBlinking?"active"!=this.state&&this.delimeterIsBlinking&&(this.delimeterBlink.classList.remove("blink"),this.delimeterIsBlinking=!1):(this.delimeterBlink.classList.add("blink"),this.delimeterIsBlinking=!0),this.clockValuesAsString=("00"+this.clockStrings.h+this.clockStrings.m).split("")):(this.headerShift&&(this.rotorGroups.forEach((t=>t.classList.remove("autohour"))),this.headerShift=!1),this.delimeterIsBlinking&&(this.delimeterBlink.classList.remove("blink"),this.delimeterIsBlinking=!1),this.clockValuesAsString=(this.clockStrings.h+this.clockStrings.m+this.clockStrings.s).split("")),this._sign?i.call(this):function(){this.rotorLeafFront.forEach(((t,e)=>{t.classList.add("front-bottom")})),this.rotorLeafRear.forEach(((t,e)=>{t.classList.add("rear-bottom")})),o.call(this)}.call(this),s.call(this),t?(i.call(this),s.call(this)):(setTimeout(function(){this.rotorLeafFront.forEach(((t,e)=>{t.textContent=this.prevClockValuesAsString[e]}))}.bind(this),500),this._sign?setTimeout(o.bind(this),500):setTimeout(function(){this.rotorTop.forEach(((t,e)=>{t.textContent=this.prevClockValuesAsString[e]}))}.bind(this),500)),this.prevClockValuesAsString=this.clockValuesAsString}}const yt=l`
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
    font-size: var(--rotor-fontsize);
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
    font-size: var(--button-fontsize);
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
    height: var(--button-height, 20px);
    padding: 0px;
    border-radius: 4px;
    border: 0px;
    font-family: sans-serif;
    font-size: var(--button-fontsize);
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

  .flipdown .rotor-leaf.flippedr {
    transform: rotateX(180deg);
    transition: all 0.5s ease-in-out;
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
`;function $t(t){const e=t.split(":").map(Number);return 3600*e[0]+60*e[1]+e[2]}console.info(`%c  FLIPDOWN-TIMER-CARD \n%c  ${_t("common.version")} 1.0.0    `,"color: orange; font-weight: bold; background: black","color: white; font-weight: bold; background: dimgray"),window.customCards=window.customCards||[],window.customCards.push({type:"flipdown-timer-card",name:"Flipdown Timer Card",description:"A template custom card for you to create something awesome"});let xt=[];function kt(){xt=xt.filter((t=>null!=t.offsetParent)),xt.forEach((t=>{t.fd._startInterval()}))}let Et=class extends et{constructor(){super(...arguments),this.fd=null}static async getConfigElement(){return document.createElement("flipdown-timer-card-editor")}static getStubConfig(){return{}}setConfig(t){if(!t)throw new Error(_t("common.invalid_configuration"));t.test_gui&&function(){var t=document.querySelector("home-assistant");if(t=(t=(t=(t=(t=(t=(t=(t=t&&t.shadowRoot)&&t.querySelector("home-assistant-main"))&&t.shadowRoot)&&t.querySelector("app-drawer-layout partial-panel-resolver"))&&t.shadowRoot||t)&&t.querySelector("ha-panel-lovelace"))&&t.shadowRoot)&&t.querySelector("hui-root")){var e=t.lovelace;return e.current_view=t.___curView,e}return null}().setEditMode(!0),this.config=Object.assign({},t);let e=["start","stop","cancel","resume","reset"],o=["Hours","Minutes","Seconds"];if(t.hasOwnProperty("localize")){if(t.localize.button){const o=t.localize.button.replace(/\s/g,"").split(",");5===o.length&&(e=o)}if(t.localize.header){const e=t.localize.header.replace(/\s/g,"").split(",");3===e.length&&(o=e)}}o.unshift("Days"),this.config.localizeBtn=e,this.config.localizeHeader=o,this.config.styles||(this.config.styles={rotor:!1,button:!1})}shouldUpdate(t){return!!this.config&&function(t,e,o){if(e.has("config")||o)return!0;if(t.config.entity){var i=e.get("hass");return!i||i.states[t.config.entity]!==t.hass.states[t.config.entity]}return!1}(this,t,!1)}disconnectedCallback(){super.disconnectedCallback(),this.fd&&this.fd.stop()}connectedCallback(){var t;if(super.connectedCallback(),this.config&&this.config.entity){(null===(t=this.hass)||void 0===t?void 0:t.states[this.config.entity])&&this._start()}}_start(){var t;const e=this.hass.states[this.config.entity],o=null===(t=this.shadowRoot)||void 0===t?void 0:t.getElementById("flipdown");if(!o)return!1;if(o&&!this.fd&&this._init(),this.fd.state=e.state,"active"===e.state){this.fd.button1.textContent=this.config.localizeBtn[1],this.fd.button2.textContent=this.config.localizeBtn[2];let t=$t(e.attributes.remaining);const o=new Date(e.last_changed).getTime();t=Math.max(t+o/1e3,0),this.fd._updator(t),this.fd.start(),xt.push(this),kt()}else if("idle"===e.state)this.fd.stop(),this.fd.button1.textContent=this.config.localizeBtn[0],this.fd.button2.textContent=this.config.localizeBtn[4],this._reset();else if("paused"===e.state){this.fd.stop(),this.fd.button1.textContent=this.config.localizeBtn[3],this.fd.button2.textContent=this.config.localizeBtn[2];const t=$t(e.attributes.remaining);this.fd.rt=t,this.fd._tick(!0)}else{this.fd.button1.textContent="X",this.fd.button2.textContent="X";const t=new Date(e.state).getTime()/1e3;isNaN(t)||t<1?(this.fd.rt=0,this.fd.stop(),this.fd._tick(!0)):(this.fd._updator(t),this.fd.start(),xt.push(this),kt())}return!0}_clear(){this.fd=null}_reset(){const t=this.hass.states[this.config.entity],e=$t(this.config.duration?this.config.duration:t.attributes.duration);this.fd.rt=e,this.fd._tick(!0)}updated(t){if(super.updated(t),t.has("hass")){const e=this.hass.states[this.config.entity],o=t.get("hass");(o?o.states[this.config.entity]:void 0)!==e?this._start():e||this._clear()}}render(){return this.config.show_warning?this._showWarning(_t("common.show_warning")):this.config.show_error?this._showError(_t("common.show_error")):z`
      <ha-card>
        <div class="card-content">
          ${this.config.show_title?z`<hui-generic-entity-row .hass=${this.hass} .config=${this.config}></hui-generic-entity-row>`:z``}
          <div class="flipdown_shell" style="
            --rotor-width:  ${this.config.styles.rotor&&this.config.styles.rotor.width||"50px"};
            --rotor-height: ${this.config.styles.rotor&&this.config.styles.rotor.height||"80px"};
            --rotor-space:  ${this.config.styles.rotor&&this.config.styles.rotor.space||"20px"};
            --rotor-fontsize:  ${this.config.styles.rotor&&this.config.styles.rotor.fontsize||"4rem"};
            --button-fontsize:  ${this.config.styles.button&&this.config.styles.button.fontsize||"1em"};
            ${this.config.styles.button&&this.config.styles.button.width&&"--button-width: "+this.config.styles.button.width+";"}
            ${this.config.styles.button&&this.config.styles.button.height&&"--button-height: "+this.config.styles.button.height+";"}
          ">
            <div id="flipdown" class="flipdown"></div>
          </div>
        </div>
      </ha-card>
    `}_init(){var t;const e=null===(t=this.shadowRoot)||void 0===t?void 0:t.getElementById("flipdown"),o=(new Date).getTime()/1e3,i=this.config.entity.substring(0,this.config.entity.indexOf(".")),s=this.hass.states[this.config.entity].state;let r;r="timer"==i?this.config.styles.button&&this.config.styles.button.hasOwnProperty("location")?this.config.styles.button.location:"right":"hide",this.fd||(this.fd=new wt(o,e,{show_header:this.config.show_header,show_hour:this.config.show_hour,bt_location:r,theme:this.config.theme,headings:this.config.localizeHeader})._init(s)),this.config.entity&&(null==e||e.querySelectorAll(".rotor-trans-top").forEach(((t,e)=>{t.addEventListener("click",(()=>{this._handleRotorClick(t,e,!0)}))})),null==e||e.querySelectorAll(".rotor-trans-bottom").forEach(((t,e)=>{t.addEventListener("click",(()=>{this._handleRotorClick(t,e,!1)}))})),this.fd.button1.addEventListener("click",(()=>this._handleBtnClick(1))),this.fd.button2.addEventListener("click",(()=>this._handleBtnClick(2))))}firstUpdated(){this._init()}_handleRotorClick(t,e,o){if("idle"!==this.hass.states[this.config.entity].state)return!1;const i=[9,9,5,9,5,9],s=t.offsetParent;if(o){const t=Number(s.querySelector(".rotor-leaf-rear").textContent),o=t<i[e]?t+1:0;s.querySelector(".rotor-leaf-front").classList.add("front-bottom"),s.querySelector(".rotor-leaf-rear").classList.add("rear-bottom"),s.querySelector(".rotor-leaf-rear").textContent=o,s.querySelector(".rotor-bottom").textContent=o,s.querySelector(".rotor-leaf").classList.add("flippedfr"),setTimeout((()=>{s.querySelector(".rotor-leaf-front").textContent=o,s.querySelector(".rotor-top").textContent=o,s.querySelector(".rotor-leaf").classList.remove("flippedfr"),s.querySelector(".rotor-leaf-front").classList.remove("front-bottom"),s.querySelector(".rotor-leaf-rear").classList.remove("rear-bottom")}),200)}else{const t=Number(s.querySelector(".rotor-leaf-rear").textContent),o=t>0?t-1:i[e];s.querySelector(".rotor-leaf-rear").textContent=o,s.querySelector(".rotor-top").textContent=o,s.querySelector(".rotor-leaf").classList.add("flippedf"),setTimeout((()=>{s.querySelector(".rotor-leaf-front").textContent=o,s.querySelector(".rotor-bottom").textContent=o,s.querySelector(".rotor-leaf").classList.remove("flippedf")}),200)}return!0}_handleBtnClick(t){const e=this.hass.states[this.config.entity].state;switch(t){case 1:let t=this._getRotorTime();"idle"===e&&"00:00:00"!=t?("auto"==this.config.show_hour&&(t=t.substr(3,5)+":00"),this.hass.callService("timer","start",{entity_id:this.config.entity,duration:t})):"active"===e?this.hass.callService("timer","pause",{entity_id:this.config.entity}):"paused"===e&&this.hass.callService("timer","start",{entity_id:this.config.entity});break;case 2:"idle"===e?this._reset():this.hass.callService("timer","cancel",{entity_id:this.config.entity})}}_getRotorTime(){let t="";return this.fd.rotorTop.forEach(((e,o)=>{t+=e.textContent,1!=o&&3!=o||(t+=":")})),t}_showWarning(t){return z`
      <hui-warning>${t}</hui-warning>
    `}_showError(t){const e=document.createElement("hui-error-card");return e.setConfig({type:"error",error:t,origConfig:this.config}),z`
      ${e}
    `}static get styles(){return n(yt)}};t([rt({attribute:!1})],Et.prototype,"hass",void 0),t([rt({attribute:!1})],Et.prototype,"fd",void 0),t([nt()],Et.prototype,"config",void 0),Et=t([it("flipdown-timer-card")],Et);export{Et as FlipdownTimer,$t as durationToSeconds};
