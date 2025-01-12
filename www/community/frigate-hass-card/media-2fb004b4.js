import{dx as t,dy as i,dz as e,dA as n,cL as o,dB as a,_ as s,n as r,b as l,t as c,a as d,dC as h,x as p,e as u,dD as f,r as _,dE as g,dF as m,dG as v,dH as b,dI as y,l as z,dc as w}from"./card-7a934cb9.js";
/**
 * @license
 * Copyright 2018 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const C={},x=t(class extends i{constructor(){super(...arguments),this.ot=C}render(t,i){return i()}update(t,[i,n]){if(Array.isArray(i)){if(Array.isArray(this.ot)&&this.ot.length===i.length&&i.every(((t,i)=>t===this.ot[i])))return e}else if(this.ot===i)return e;return this.ot=Array.isArray(i)?Array.from(i):i,this.render(i,n)}});class I{constructor(){this._options=null,this._viewportIntersecting=null,this._microphoneMuteTimer=new n,this._root=null,this._eventListeners=new Map,this._children=[],this._target=null,this._mutationObserver=new MutationObserver(this._mutationHandler.bind(this)),this._intersectionObserver=new IntersectionObserver(this._intersectionHandler.bind(this)),this._mediaLoadedHandler=async t=>{this._target?.index===t&&(await this._unmuteTargetIfConfigured(this._target.selected?"selected":"visible"),await this._playTargetIfConfigured(this._target.selected?"selected":"visible"))},this._visibilityHandler=async()=>{await this._changeVisibility("visible"===document.visibilityState)},this._changeVisibility=async t=>{t?(await this._unmuteTargetIfConfigured("visible"),await this._playTargetIfConfigured("visible")):(await this._pauseAllIfConfigured("hidden"),await this._muteAllIfConfigured("hidden"))},this._microphoneChangeHandler=async t=>{"unmuted"===t?await this._unmuteTargetIfConfigured("microphone"):"muted"===t&&this._options?.autoMuteConditions?.includes("microphone")&&this._microphoneMuteTimer.start(this._options.microphoneMuteSeconds??60,(async()=>{await this._muteTargetIfConfigured("microphone")}))}}setOptions(t){this._options=t,this._options?.microphoneManager&&(this._options.microphoneManager.removeListener(this._microphoneChangeHandler),this._options.microphoneManager.addListener(this._microphoneChangeHandler))}hasRoot(){return!!this._root}destroy(){this._viewportIntersecting=null,this._microphoneMuteTimer.stop(),this._root=null,this._removeChildHandlers(),this._children=[],this._target=null,this._mutationObserver.disconnect(),this._intersectionObserver.disconnect(),this._options?.microphoneManager?.removeListener(this._microphoneChangeHandler),document.removeEventListener("visibilitychange",this._visibilityHandler)}async setTarget(t,i){this._target?.index===t&&this._target?.selected===i||(this._target?.selected&&(await this._pauseTargetIfConfigured("unselected"),await this._muteTargetIfConfigured("unselected"),this._microphoneMuteTimer.stop()),this._target={selected:i,index:t},i?(await this._unmuteTargetIfConfigured("selected"),await this._playTargetIfConfigured("selected")):(await this._unmuteTargetIfConfigured("visible"),await this._playTargetIfConfigured("visible")))}unsetTarget(){this._target=null}async _playTargetIfConfigured(t){null!==this._target&&this._options?.autoPlayConditions?.includes(t)&&await this._play(this._target.index)}async _play(t){await(this._children[t]?.play())}async _unmuteTargetIfConfigured(t){null!==this._target&&this._options?.autoUnmuteConditions?.includes(t)&&await this._unmute(this._target.index)}async _unmute(t){await(this._children[t]?.unmute())}async _pauseAllIfConfigured(t){if(this._options?.autoPauseConditions?.includes(t))for(const t of this._children.keys())await this._pause(t)}async _pauseTargetIfConfigured(t){null!==this._target&&this._options?.autoPauseConditions?.includes(t)&&await this._pause(this._target.index)}async _pause(t){await(this._children[t]?.pause())}async _muteAllIfConfigured(t){if(this._options?.autoMuteConditions?.includes(t))for(const t of this._children.keys())await this._mute(t)}async _muteTargetIfConfigured(t){null!==this._target&&this._options?.autoMuteConditions?.includes(t)&&await this._mute(this._target.index)}async _mute(t){await(this._children[t]?.mute())}_mutationHandler(t,i){this._initializeRoot()}_removeChildHandlers(){for(const[t,i]of this._eventListeners.entries())t.removeEventListener("frigate-card:media:loaded",i);this._eventListeners.clear()}initialize(t){this._root=t,this._initializeRoot(),document.addEventListener("visibilitychange",this._visibilityHandler),this._intersectionObserver.disconnect(),this._intersectionObserver.observe(t),this._mutationObserver.disconnect(),this._mutationObserver.observe(this._root,{childList:!0,subtree:!0})}_initializeRoot(){if(this._options&&this._root){this._removeChildHandlers(),this._children=[...this._root.querySelectorAll(this._options.playerSelector)];for(const[t,i]of this._children.entries()){const e=()=>this._mediaLoadedHandler(t);this._eventListeners.set(i,e),i.addEventListener("frigate-card:media:loaded",e)}}}async _intersectionHandler(t){const i=this._viewportIntersecting;this._viewportIntersecting=t.some((t=>t.isIntersecting)),null!==i&&i!==this._viewportIntersecting&&await this._changeVisibility(this._viewportIntersecting)}}const A={active:!0,breakpoints:{},lazyLoadCount:0};function L(t={}){let i,e,n;const o=new Set,a=["init","select"],s=["select"];function r(){"hidden"===document.visibilityState&&i.lazyUnloadConditions?.includes("hidden")?o.forEach((t=>{i.lazyUnloadCallback&&(i.lazyUnloadCallback(t,n[t]),o.delete(t))})):"visible"===document.visibilityState&&i.lazyLoadCallback&&c()}function l(t){return o.has(t)}function c(){const t=i.lazyLoadCount,a=e.selectedScrollSnap(),s=new Set;for(let i=1;i<=t&&a-i>=0;i++)s.add(a-i);s.add(a);for(let i=1;i<=t&&a+i<n.length;i++)s.add(a+i);s.forEach((t=>{!l(t)&&i.lazyLoadCallback&&(o.add(t),i.lazyLoadCallback(t,n[t]))}))}function d(){const t=e.previousScrollSnap();l(t)&&i.lazyUnloadCallback&&(i.lazyUnloadCallback(t,n[t]),o.delete(t))}return{name:"autoLazyLoad",options:t,init:function(o,l){const{mergeOptions:h,optionsAtMedia:p}=l,u=h(A,t);i=p(u),e=o,n=e.slideNodes(),i.lazyLoadCallback&&a.forEach((t=>e.on(t,c))),i.lazyUnloadCallback&&i.lazyUnloadConditions?.includes("unselected")&&s.forEach((t=>e.on(t,d))),document.addEventListener("visibilitychange",r)},destroy:function(){i.lazyLoadCallback&&a.forEach((t=>e.off(t,c))),i.lazyUnloadCallback&&s.forEach((t=>e.off(t,d))),document.removeEventListener("visibilitychange",r)}}}function S(){let t,i=[];const e=[];function n(n){const o=n.composedPath();for(const[a,s]of[...i.entries()].reverse())if(o.includes(s)){e[a]=n.detail,a!==t.selectedScrollSnap()&&n.stopPropagation();break}}function a(n){const o=n.composedPath();for(const[a,s]of i.entries())if(o.includes(s)){delete e[a],a!==t.selectedScrollSnap()&&n.stopPropagation();break}}function s(){const n=t.selectedScrollSnap(),a=e[n];a&&o(i[n],a)}return{name:"autoMediaLoadedInfo",options:{},init:function(e){t=e,i=t.slideNodes();for(const t of i)t.addEventListener("frigate-card:media:loaded",n),t.addEventListener("frigate-card:media:unloaded",a);t.on("init",s),t.containerNode().addEventListener("frigate-card:carousel:force-select",s)},destroy:function(){for(const t of i)t.removeEventListener("frigate-card:media:loaded",n),t.removeEventListener("frigate-card:media:unloaded",a);t.off("init",s),t.containerNode().removeEventListener("frigate-card:carousel:force-select",s)}}}class T{constructor(t){this._scrolling=!1,this._shouldReInitOnScrollStop=!1,this._scrollingStart=()=>{this._scrolling=!0},this._scrollingStop=()=>{this._scrolling=!1,this._shouldReInitOnScrollStop&&(this._shouldReInitOnScrollStop=!1,this._debouncedReInit())},this._debouncedReInit=a((()=>{this._scrolling=!1,this._shouldReInitOnScrollStop=!1,this._emblaApi?.reInit()}),500,{trailing:!0}),this._emblaApi=t,this._emblaApi.on("scroll",this._scrollingStart),this._emblaApi.on("settle",this._scrollingStop),this._emblaApi.on("destroy",this.destroy)}destroy(){this._emblaApi.off("scroll",this._scrollingStart),this._emblaApi.off("settle",this._scrollingStop),this._emblaApi.off("destroy",this.destroy)}reinit(){this._scrolling?this._shouldReInitOnScrollStop=!0:this._debouncedReInit()}}function $(){let t,i=null,e=null;const n=new Map,o=new ResizeObserver((function(t){let i=!1;for(const e of t){const t={height:e.contentRect.height,width:e.contentRect.width},o=n.get(e.target);t.width&&t.height&&(o?.height!==t.height||o?.width!==t.width)&&(n.set(e.target,t),i=!0)}i&&r()})),s=new IntersectionObserver((function(t){const n=t.some((t=>t.isIntersecting));if(n!==e){const t=n&&null!==e;e=n,t&&i?.reinit()}})),r=a((()=>function(){const{slideRegistry:e,options:{axis:n}}=t.internalEngine();if("y"===n)return;t.containerNode().style.removeProperty("max-height");const o=e[t.selectedScrollSnap()],a=t.slideNodes(),s=Math.max(...o.map((t=>a[t].getBoundingClientRect().height)));!isNaN(s)&&s>0&&(t.containerNode().style.maxHeight=`${s}px`);i?.reinit()}()),200,{trailing:!0});return{name:"autoSize",options:{},init:function(e){t=e,i=new T(t),s.observe(t.containerNode()),o.observe(t.containerNode());for(const i of t.slideNodes())o.observe(i);t.containerNode().addEventListener("frigate-card:media:loaded",r),t.on("settle",r)},destroy:function(){s.disconnect(),o.disconnect(),i?.destroy(),t.containerNode().removeEventListener("frigate-card:media:loaded",r),t.off("settle",r)}}}let P=class extends d{constructor(){super(...arguments),this.disabled=!1,this.label="",this._thumbnailError=!1,this._embedThumbnailTask=h(this,(()=>this.hass),(()=>this.thumbnail))}set controlConfig(t){t?.size&&this.style.setProperty("--frigate-card-next-prev-size",`${t.size}px`),this._controlConfig=t}render(){if(this.disabled||!this._controlConfig||"none"==this._controlConfig.style)return p``;const t=!this.thumbnail||["chevrons","icons"].includes(this._controlConfig.style)||this._thumbnailError,i={controls:!0,left:"left"===this.side,right:"right"===this.side,thumbnails:!t,icons:t};if(t){const t=this.icon&&!this._thumbnailError&&"chevrons"!==this._controlConfig.style?this.icon:"left"===this.side?{icon:"mdi:chevron-left"}:{icon:"mdi:chevron-right"};return p` <ha-icon-button class="${u(i)}" .label=${this.label}>
        <frigate-card-icon .hass=${this.hass} .icon=${t}></frigate-card-icon>
      </ha-icon-button>`}return f(this._embedThumbnailTask,(t=>t?p`<img
              src="${t}"
              class="${u(i)}"
              title="${this.label}"
              aria-label="${this.label}"
            />`:p``),{inProgressFunc:()=>p`<div class=${u(i)}></div>`,errorFunc:t=>{this._thumbnailError=!0}})}static get styles(){return _("ha-icon-button {\n  color: var(--frigate-card-button-color);\n  background-color: var(--frigate-card-button-background);\n  border-radius: 50%;\n  padding: 0px;\n  margin: 3px;\n  --ha-icon-display: block;\n  /* Buttons can always be clicked */\n  pointer-events: auto;\n}\n\n:host {\n  --frigate-card-next-prev-size: 48px;\n  --frigate-card-next-prev-size-hover: calc(var(--frigate-card-next-prev-size) * 2);\n  --frigate-card-left-position: 45px;\n  --frigate-card-right-position: 45px;\n  --mdc-icon-button-size: var(--frigate-card-next-prev-size);\n  --mdc-icon-size: calc(var(--mdc-icon-button-size) / 2);\n}\n\n.controls {\n  position: absolute;\n  z-index: 1;\n  overflow: hidden;\n}\n\n.controls.left {\n  left: var(--frigate-card-left-position);\n}\n\n.controls.right {\n  right: var(--frigate-card-right-position);\n}\n\n.controls.icons {\n  top: calc(50% - var(--frigate-card-next-prev-size) / 2);\n}\n\n.controls.thumbnails {\n  border-radius: 50%;\n  height: var(--frigate-card-next-prev-size);\n  top: calc(50% - var(--frigate-card-next-prev-size) / 2);\n  box-shadow: var(--frigate-card-css-box-shadow, 0px 0px 20px 5px black);\n  transition: all 0.2s ease-out;\n  opacity: 0.8;\n  aspect-ratio: 1/1;\n}\n\n.controls.thumbnails:hover {\n  opacity: 1 !important;\n  height: var(--frigate-card-next-prev-size-hover);\n  top: calc(50% - var(--frigate-card-next-prev-size-hover) / 2);\n}\n\n.controls.left.thumbnails:hover {\n  left: calc(var(--frigate-card-left-position) - (var(--frigate-card-next-prev-size-hover) - var(--frigate-card-next-prev-size)) / 2);\n}\n\n.controls.right.thumbnails:hover {\n  right: calc(var(--frigate-card-right-position) - (var(--frigate-card-next-prev-size-hover) - var(--frigate-card-next-prev-size)) / 2);\n}")}};s([r({attribute:!1})],P.prototype,"side",void 0),s([r({attribute:!1})],P.prototype,"hass",void 0),s([l()],P.prototype,"_controlConfig",void 0),s([r({attribute:!1})],P.prototype,"thumbnail",void 0),s([r({attribute:!1})],P.prototype,"icon",void 0),s([r({attribute:!0,type:Boolean})],P.prototype,"disabled",void 0),s([r()],P.prototype,"label",void 0),s([l()],P.prototype,"_thumbnailError",void 0),P=s([c("frigate-card-next-previous-control")],P);class E{constructor(t){this._config=null,this._hass=null,this._cameraManager=null,this._cameraID=null,this._host=t}setConfig(t){this._config=t??null,this._host.setAttribute("data-orientation",t?.orientation??"horizontal"),this._host.setAttribute("data-position",t?.position??"bottom-right"),this._host.setAttribute("style",Object.entries(t?.style??{}).map((([t,i])=>`${t}:${i}`)).join(";"))}getConfig(){return this._config}setCamera(t,i){this._cameraManager=t??null,this._cameraID=i??null}setForceVisibility(t){this._forceVisibility=t}handleAction(t,i){t.stopPropagation();const e=t.detail.action,n=g(e,i);n&&m(this._host,{action:n,...i&&{config:i}})}hasUsefulAction(){const t={pt:!0,z:!0,home:!0};if(!this._cameraID)return t;const i=this._cameraManager?.getCameraCapabilities(this._cameraID);if(!i||!i.hasPTZCapability())return t;const e=i.getPTZCapabilities();return{pt:!!(e?.up||e?.down||e?.left||e?.right),z:!!e?.zoomIn||!!e?.zoomOut,home:!!e?.presets?.length}}shouldDisplay(){return void 0!==this._forceVisibility?this._forceVisibility:"auto"===this._config?.mode?!!this._cameraID&&!!this._cameraManager?.getCameraCapabilities(this._cameraID)?.hasPTZCapability():"on"===this._config?.mode}getPTZActions(){const t=t=>({start_tap_action:v({ptzAction:t?.ptzAction,ptzPhase:"start",ptzPreset:t?.preset}),end_tap_action:v({ptzAction:t?.ptzAction,ptzPhase:"stop",ptzPreset:t?.preset})}),i={};return i.up=t({ptzAction:"up"}),i.down=t({ptzAction:"down"}),i.left=t({ptzAction:"left"}),i.right=t({ptzAction:"right"}),i.zoom_in=t({ptzAction:"zoom_in"}),i.zoom_out=t({ptzAction:"zoom_out"}),i.home={tap_action:v()},i}}let M=class extends d{constructor(){super(...arguments),this._controller=new E(this),this._actions=this._controller.getPTZActions(),this._actionPresence=null}willUpdate(t){t.has("config")&&this._controller.setConfig(this.config),(t.has("cameraManager")||t.has("cameraID"))&&this._controller.setCamera(this.cameraManager,this.cameraID),t.has("forceVisibility")&&this._controller.setForceVisibility(this.forceVisibility),(t.has("cameraID")||t.has("cameraManager"))&&(this._actionPresence=this._controller.hasUsefulAction())}render(){if(!this._controller.shouldDisplay())return;const t=(t,i,e)=>e?p`<frigate-card-icon
            class=${u({[t]:!0,disabled:!e})}
            .icon=${{icon:i}}
            .actionHandler=${b({hasHold:y(e?.hold_action),hasDoubleClick:y(e?.double_tap_action)})}
            .title=${z(`elements.ptz.${t}`)}
            @action=${t=>this._controller.handleAction(t,e)}
          ></frigate-card-icon>`:p``,i=this._controller.getConfig();return p` <div class="ptz">
      ${!i?.hide_pan_tilt&&this._actionPresence?.pt?p`<div class="ptz-move">
            ${t("right","mdi:arrow-right",this._actions.right)}
            ${t("left","mdi:arrow-left",this._actions.left)}
            ${t("up","mdi:arrow-up",this._actions.up)}
            ${t("down","mdi:arrow-down",this._actions.down)}
          </div>`:""}
      ${!i?.hide_zoom&&this._actionPresence?.z?p` <div class="ptz-zoom">
            ${t("zoom_in","mdi:plus",this._actions.zoom_in)}
            ${t("zoom_out","mdi:minus",this._actions.zoom_out)}
          </div>`:p``}
      ${!i?.hide_home&&this._actionPresence?.home?p`<div class="ptz-home">
            ${t("home","mdi:home",this._actions.home)}
          </div>`:p``}
    </div>`}static get styles(){return _(":host {\n  position: absolute;\n  width: fit-content;\n  height: fit-content;\n  --frigate-card-ptz-icon-size: 24px;\n}\n\n:host([data-position$=-left]) {\n  left: 5%;\n}\n\n:host([data-position$=-right]) {\n  right: 5%;\n}\n\n:host([data-position^=top-]) {\n  top: 5%;\n}\n\n:host([data-position^=bottom-]) {\n  bottom: 5%;\n}\n\n/*****************\n * Main Containers\n *****************/\n.ptz {\n  display: flex;\n  gap: 10px;\n  color: var(--light-primary-color);\n  opacity: 0.4;\n  transition: opacity 0.3s ease-in-out;\n}\n\n:host([data-orientation=vertical]) .ptz {\n  flex-direction: column;\n}\n\n:host([data-orientation=horizontal]) .ptz {\n  flex-direction: row;\n}\n\n.ptz:hover {\n  opacity: 1;\n}\n\n:host([data-orientation=vertical]) .ptz div {\n  width: calc(var(--frigate-card-ptz-icon-size) * 3);\n}\n\n:host([data-orientation=horizontal]) .ptz div {\n  height: calc(var(--frigate-card-ptz-icon-size) * 3);\n}\n\n.ptz-move,\n.ptz-zoom,\n.ptz-home {\n  position: relative;\n  background-color: rgba(0, 0, 0, 0.3);\n}\n\n.ptz-move {\n  height: calc(var(--frigate-card-ptz-icon-size) * 3);\n  width: calc(var(--frigate-card-ptz-icon-size) * 3);\n  border-radius: 50%;\n}\n\n:host([data-orientation=horizontal]) .ptz .ptz-zoom,\n:host([data-orientation=horizontal]) .ptz .ptz-home {\n  width: calc(var(--frigate-card-ptz-icon-size) * 1.5);\n}\n\n:host([data-orientation=vertical]) .ptz .ptz-zoom,\n:host([data-orientation=vertical]) .ptz .ptz-home {\n  height: calc(var(--frigate-card-ptz-icon-size) * 1.5);\n}\n\n.ptz-zoom,\n.ptz-home {\n  border-radius: var(--ha-card-border-radius, 4px);\n}\n\n/***********\n * PTZ Icons\n ***********/\nfrigate-card-icon {\n  position: absolute;\n  --mdc-icon-size: var(--frigate-card-ptz-icon-size);\n}\n\nfrigate-card-icon:not(.disabled) {\n  cursor: pointer;\n}\n\n.disabled {\n  color: var(--disabled-text-color);\n}\n\n.up {\n  top: 5px;\n  left: 50%;\n  transform: translateX(-50%);\n}\n\n.down {\n  bottom: 5px;\n  left: 50%;\n  transform: translateX(-50%);\n}\n\n.left {\n  left: 5px;\n  top: 50%;\n  transform: translateY(-50%);\n}\n\n.right {\n  right: 5px;\n  top: 50%;\n  transform: translateY(-50%);\n}\n\n:host([data-orientation=vertical]) .zoom_in {\n  right: 5px;\n  top: 50%;\n}\n\n:host([data-orientation=vertical]) .zoom_out {\n  left: 5px;\n  top: 50%;\n}\n\n:host([data-orientation=horizontal]) .zoom_in {\n  left: 50%;\n  top: 5px;\n}\n\n:host([data-orientation=horizontal]) .zoom_out {\n  left: 50%;\n  bottom: 5px;\n}\n\n:host([data-orientation=vertical]) .zoom_in,\n:host([data-orientation=vertical]) .zoom_out {\n  transform: translateY(-50%);\n}\n\n:host([data-orientation=horizontal]) .zoom_in,\n:host([data-orientation=horizontal]) .zoom_out {\n  transform: translateX(-50%);\n}\n\n.home {\n  top: 50%;\n  left: 50%;\n  transform: translateX(-50%) translateY(-50%);\n}")}};function k(t){w(t,"live:error")}s([r({attribute:!1})],M.prototype,"config",void 0),s([r({attribute:!1})],M.prototype,"cameraManager",void 0),s([r({attribute:!1})],M.prototype,"cameraID",void 0),s([r({attribute:!1})],M.prototype,"forceVisibility",void 0),M=s([c("frigate-card-ptz")],M);const H=(t,i)=>{void 0!==i?.fit?t.style.setProperty("--frigate-card-media-layout-fit",i.fit):t.style.removeProperty("--frigate-card-media-layout-fit");for(const e of["x","y"])void 0!==i?.position?.[e]?t.style.setProperty(`--frigate-card-media-layout-position-${e}`,`${i.position[e]}%`):t.style.removeProperty(`--frigate-card-media-layout-position-${e}`);for(const e of["top","bottom","left","right"])void 0!==i?.view_box?.[e]?t.style.setProperty(`--frigate-card-media-layout-view-box-${e}`,`${i.view_box[e]}%`):t.style.removeProperty(`--frigate-card-media-layout-view-box-${e}`)},O=2,R=(t,i)=>{t._controlsHideTimer&&(t._controlsHideTimer.stop(),delete t._controlsHideTimer,delete t._controlsOriginalValue),t.controls=i},N=(t,i=1)=>{const e=t._controlsOriginalValue??t.controls;R(t,!1),t._controlsHideTimer??=new n,t._controlsOriginalValue=e;const o=()=>{R(t,e),t.removeEventListener("loadstart",o)};t.addEventListener("loadstart",o),t._controlsHideTimer.start(i,(()=>{R(t,e)}))},D=async(t,i)=>{if(i?.play)try{await i.play()}catch(e){if("NotAllowedError"===e.name&&!t.isMuted()){await t.mute();try{await i.play()}catch(t){}}}};export{L as A,I as M,S as a,$ as b,O as c,k as d,N as h,x as i,D as p,R as s,H as u};
