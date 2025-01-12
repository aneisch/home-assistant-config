import{dx as A,dy as e,eL as t,eM as i,dz as a,eI as r,eN as g,dA as s,_ as o,n as c,cR as l,b as C,t as h,a as I,cM as n,eO as E,du as u,dv as M,cP as w,x as m,cQ as B,eJ as Q,i as d,cL as L,l as b,r as D}from"./card-a5cfa285.js";
/**
 * @license
 * Copyright 2020 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const p=A(class extends e{constructor(A){if(super(A),A.type!==t.PROPERTY&&A.type!==t.ATTRIBUTE&&A.type!==t.BOOLEAN_ATTRIBUTE)throw Error("The `live` directive is not allowed on child or event bindings");if(!i(A))throw Error("`live` bindings can only contain a single expression")}render(A){return A}update(A,[e]){if(e===a||e===r)return e;const i=A.element,s=A.name;if(A.type===t.PROPERTY){if(e===i[s])return a}else if(A.type===t.BOOLEAN_ATTRIBUTE){if(!!e===i.hasAttribute(s))return a}else if(A.type===t.ATTRIBUTE&&i.getAttribute(s)===e+"")return a;return g(A),e}});class k{constructor(A,e,t,i,a){this._timer=new s,this._timerSeconds=e,this._callback=t,this._timerStartCallback=i,this._timerStopCallback=a,(this._host=A).addController(this)}removeController(){this.stopTimer(),this._host.removeController(this)}get value(){return this._value}updateValue(){this._value=this._callback()}clearValue(){this._value=void 0}stopTimer(){this._timer.isRunning()&&(this._timer.stop(),this._timerStopCallback?.())}startTimer(){this.stopTimer(),this._timerStartCallback?.(),this._timer.startRepeated(this._timerSeconds,(()=>{this.updateValue(),this._host.requestUpdate()}))}hasTimer(){return this._timer.isRunning()}hostConnected(){this.updateValue(),this.startTimer(),this._host.requestUpdate()}hostDisconnected(){this.clearValue(),this.stopTimer()}}var j="data:image/jpeg;base64,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";let y=class extends I{constructor(){super(...arguments),this._message=null,this._refImage=n(),this._boundVisibilityHandler=this._visibilityHandler.bind(this),this._mediaLoadedInfo=null}async play(){this._cachedValueController?.startTimer()}async pause(){this._cachedValueController?.stopTimer()}async mute(){}async unmute(){}isMuted(){return!0}async seek(A){}async setControls(A){}isPaused(){return!this._cachedValueController?.hasTimer()}async getScreenshotURL(){return this._cachedValueController?.value??null}_getCameraEntity(){return(this.cameraConfig?.camera_entity||this.cameraConfig?.webrtc_card?.entity)??null}shouldUpdate(A){if(!this.hass||"visible"!==document.visibilityState)return!1;const e=this._getRelevantEntityForMode(this._resolveMode(this.imageConfig?.mode));return!A.has("hass")||1!=A.size||!e||(E(this.hass,A.get("hass"),[e])?(this._cachedValueController?.clearValue(),!0):!this.hasUpdated)}willUpdate(A){A.has("imageConfig")&&(this._cachedValueController&&this._cachedValueController.removeController(),this.imageConfig&&(this._cachedValueController=new k(this,this.imageConfig.refresh_seconds,this._getImageSource.bind(this),(()=>u(this)),(()=>M(this)))));const e=this._getRelevantEntityForMode(this._resolveMode(this.imageConfig?.mode));(A.has("cameraConfig")||A.has("view")||e&&!this._getAcceptableState(e))&&this._cachedValueController?.clearValue(),this._cachedValueController?.value||this._cachedValueController?.updateValue(),["imageConfig","view"].some((e=>A.has(e)))&&(this._message=null)}_getAcceptableState(A){const e=(A?this.hass?.states[A]:null)??null;return this.hass&&this.hass.connected&&e&&Date.now()-Date.parse(e.last_updated)<3e5?e:null}connectedCallback(){super.connectedCallback(),document.addEventListener("visibilitychange",this._boundVisibilityHandler),this._cachedValueController?.startTimer()}disconnectedCallback(){this._cachedValueController?.stopTimer(),this._message=null,document.removeEventListener("visibilitychange",this._boundVisibilityHandler),super.disconnectedCallback()}_visibilityHandler(){this._refImage.value&&("hidden"===document.visibilityState?(this._cachedValueController?.stopTimer(),this._cachedValueController?.clearValue(),this._forceSafeImage()):(this._cachedValueController?.startTimer(),this.requestUpdate()))}_buildImageURL(A){return A.searchParams.append("_t",String(Date.now())),A.toString()}_addQueryParametersToURL(A,e){if(e){const t=new URLSearchParams(e);for(const[e,i]of t.entries())A.searchParams.append(e,i)}return A}_getRelevantEntityForMode(A){return"camera"===A?this._getCameraEntity():"entity"===A?this.imageConfig?.entity??null:null}_resolveMode(A){if(!A)return"screensaver";if("auto"!==A)return A;const e=this._getCameraEntity();return this.imageConfig?.entity?"entity":this.imageConfig?.url?"url":e?"camera":"screensaver"}_getImageSource(){const A=this._resolveMode(this.imageConfig?.mode);if(this.hass&&"camera"===A){const A=this._getAcceptableState(this._getCameraEntity());if(A?.attributes.entity_picture){const e=new URL(A.attributes.entity_picture,document.baseURI);return this._addQueryParametersToURL(e,this.imageConfig?.entity_parameters),this._buildImageURL(e)}}if(this.hass&&"entity"===A&&this.imageConfig?.entity){const A=this._getAcceptableState(this.imageConfig?.entity);if(A?.attributes.entity_picture){const e=new URL(A.attributes.entity_picture,document.baseURI);return this._addQueryParametersToURL(e,this.imageConfig?.entity_parameters),this._buildImageURL(e)}}return"url"===A&&this.imageConfig?.url?this._buildImageURL(new URL(this.imageConfig.url,document.baseURI)):j}_forceSafeImage(A){this._refImage.value&&(this._refImage.value.src=!A&&this.imageConfig?.url?this.imageConfig.url:j)}render(){if(this._message)return w(this._message);const A=this._cachedValueController?.value;return A?m`
          <img
            ${B(this._refImage)}
            src=${p(A)}
            @load=${A=>{const e=Q(A,{player:this,capabilities:{supportsPause:!!this.imageConfig?.refresh_seconds}});e&&!d(this._mediaLoadedInfo,e)&&(this._mediaLoadedInfo=e,L(this,e))}}
            @error=${()=>{const A=this._resolveMode(this.imageConfig?.mode);"camera"===A||"entity"===A?this._forceSafeImage(!0):"url"===A&&(this._message={type:"error",message:b("error.image_load_error"),context:this.imageConfig})}}
          />
        `:m``}static get styles(){return D(':host {\n  background-color: var(--primary-background-color);\n  background-position: center;\n  background-repeat: no-repeat;\n  background-image: url("data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIj8+CjxzdmcKICAgaW5rc2NhcGU6dmVyc2lvbj0iMS4yLjIgKGIwYTg0ODY1NDEsIDIwMjItMTItMDEpIgogICBzb2RpcG9kaTpkb2NuYW1lPSJpcmlzLW91dGxpbmUuc3ZnIgogICBpZD0ic3ZnNCIKICAgdmVyc2lvbj0iMS4xIgogICB2aWV3Qm94PSIwIDAgMjQgMjQiCiAgIHhtbG5zOmlua3NjYXBlPSJodHRwOi8vd3d3Lmlua3NjYXBlLm9yZy9uYW1lc3BhY2VzL2lua3NjYXBlIgogICB4bWxuczpzb2RpcG9kaT0iaHR0cDovL3NvZGlwb2RpLnNvdXJjZWZvcmdlLm5ldC9EVEQvc29kaXBvZGktMC5kdGQiCiAgIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICAgeG1sbnM6c3ZnPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CiAgPGRlZnMKICAgICBpZD0iZGVmczgiIC8+CiAgPHNvZGlwb2RpOm5hbWVkdmlldwogICAgIGlkPSJuYW1lZHZpZXc2IgogICAgIHBhZ2Vjb2xvcj0iI2I5M2UzZSIKICAgICBib3JkZXJjb2xvcj0iIzAwMDAwMCIKICAgICBib3JkZXJvcGFjaXR5PSIwLjI1IgogICAgIGlua3NjYXBlOnNob3dwYWdlc2hhZG93PSIyIgogICAgIGlua3NjYXBlOnBhZ2VvcGFjaXR5PSIwLjYwNzg0MzE0IgogICAgIGlua3NjYXBlOnBhZ2VjaGVja2VyYm9hcmQ9ImZhbHNlIgogICAgIGlua3NjYXBlOmRlc2tjb2xvcj0iI2QxZDFkMSIKICAgICBzaG93Z3JpZD0iZmFsc2UiCiAgICAgaW5rc2NhcGU6em9vbT0iMTkuMzc4NTc4IgogICAgIGlua3NjYXBlOmN4PSI4LjI4MjM0MTUiCiAgICAgaW5rc2NhcGU6Y3k9IjEyLjM1OTAwOCIKICAgICBpbmtzY2FwZTp3aW5kb3ctd2lkdGg9IjM4NDAiCiAgICAgaW5rc2NhcGU6d2luZG93LWhlaWdodD0iMTUyNyIKICAgICBpbmtzY2FwZTp3aW5kb3cteD0iMTA4MCIKICAgICBpbmtzY2FwZTp3aW5kb3cteT0iMjI3IgogICAgIGlua3NjYXBlOndpbmRvdy1tYXhpbWl6ZWQ9IjEiCiAgICAgaW5rc2NhcGU6Y3VycmVudC1sYXllcj0ic3ZnNCIgLz4KICA8ZwogICAgIGlkPSJnMTExOSIKICAgICBzdHlsZT0iZmlsbC1vcGFjaXR5OjAuMDU7ZmlsbDojZmZmZmZmIj4KICAgIDxjaXJjbGUKICAgICAgIHN0eWxlPSJkaXNwbGF5OmlubGluZTtmaWxsOiMwMDAwMDA7ZmlsbC1vcGFjaXR5OjAuNDk3ODI4MjU7c3Ryb2tlLXdpZHRoOjEuMzk3Mjk7b3BhY2l0eTowLjUiCiAgICAgICBpZD0icGF0aDE3MCIKICAgICAgIGN4PSIxMiIKICAgICAgIGN5PSIxMiIKICAgICAgIGlua3NjYXBlOmxhYmVsPSJCYWNrZ3JvdW5kIgogICAgICAgcj0iMTEuMjUiIC8+CiAgICA8cGF0aAogICAgICAgZD0iTSAxMy43MzAwMDEsMTUgOS44MzAwMDAzLDIxLjc2IEMgMTAuNTMsMjEuOTEgMTEuMjUsMjIgMTIsMjIgYyAyLjQwMDAwMSwwIDQuNiwtMC44NSA2LjMyLC0yLjI1IEwgMTQuNjYwMDAxLDEzLjQgTSAyLjQ2MDAwMDMsMTUgYyAwLjkyLDIuOTIgMy4xNSw1LjI2IDUuOTksNi4zNCBMIDEyLjEyLDE1IG0gLTMuNTc5OTk5NywtMyAtMy45LC02Ljc0OTk5OTYgYyAtMS42NCwxLjc0OTk5OSAtMi42NCw0LjEzOTk5OTMgLTIuNjQsNi43NDk5OTk2IDAsMC42OCAwLjA3LDEuMzUgMC4yLDIgaCA3LjQ5IE0gMjEuOCw5Ljk5OTk5OTcgSCAxNC4zMTAwMDEgTCAxNC42MDAwMDEsMTAuNSAxOS4zNiwxOC43NSBDIDIxLDE2Ljk3IDIyLDE0LjYgMjIsMTIgMjIsMTEuMzEgMjEuOTMsMTAuNjQgMjEuOCw5Ljk5OTk5OTcgbSAtMC4yNiwtMSBDIDIwLjYyLDYuMDcwMDAwNSAxOC4zOSwzLjc0MDAwMDIgMTUuNTUwMDAxLDIuNjYwMDAwMiBMIDExLjg4LDguOTk5OTk5NyBNIDkuNDAwMDAwMywxMC41IDE0LjE3MDAwMSwyLjI0MDAwMDIgYyAtMC43LC0wLjE1IC0xLjQyMDAwMSwtMC4yNCAtMi4xNzAwMDEsLTAuMjQgLTIuMzk5OTk5NywwIC00LjU5OTk5OTcsMC44NCAtNi4zMTk5OTk3LDIuMjUwMDAwMyBsIDMuNjYsNi4zNDk5OTk1IHoiCiAgICAgICBpZD0icGF0aDIiCiAgICAgICBpbmtzY2FwZTpsYWJlbD0iSXJpcyIKICAgICAgIHN0eWxlPSJmaWxsLW9wYWNpdHk6MC41MDIyMTAwMjtmaWxsOiNmZmZmZmY7b3BhY2l0eTowLjc1IiAvPgogIDwvZz4KPC9zdmc+Cg==");\n  background-size: 10%;\n  background-position: center;\n}\n\nimg {\n  width: 100%;\n  height: 100%;\n  display: block;\n  object-fit: var(--frigate-card-media-layout-fit, contain);\n  object-position: var(--frigate-card-media-layout-position-x, 50%) var(--frigate-card-media-layout-position-y, 50%);\n  object-view-box: inset(var(--frigate-card-media-layout-view-box-top, 0%) var(--frigate-card-media-layout-view-box-right, 0%) var(--frigate-card-media-layout-view-box-bottom, 0%) var(--frigate-card-media-layout-view-box-left, 0%));\n}')}};o([c({attribute:!1})],y.prototype,"hass",void 0),o([c({attribute:!1})],y.prototype,"view",void 0),o([c({attribute:!1})],y.prototype,"cameraConfig",void 0),o([c({attribute:!1})],y.prototype,"cameraManager",void 0),o([c({attribute:!1,hasChanged:l})],y.prototype,"imageConfig",void 0),o([C()],y.prototype,"_message",void 0),y=o([h("frigate-card-image")],y);export{y as FrigateCardImage};
