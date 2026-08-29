import{Do as e,Eo as t,Mo as n,To as r,U as i,bo as a,c as o,ko as s,lt as c,xo as l}from"./shared-DSCWESL1.js";import"./image-updating-player-Oj8s4mV9.js";var u=class extends e{constructor(...e){super(...e),this._refImage=a()}async getMediaPlayerController(){return await this.updateComplete,await this._refImage.value?.getMediaPlayerController()??null}render(){let e=this.camera?.getConfig();if(!(!this.hass||!e))return s`
      <advanced-camera-card-image-updating-player
        ${l(this._refImage)}
        .hass=${this.hass}
        .imageConfig=${e.image}
        .cameraConfig=${e}
        .targetID=${this.targetID}
        .cameraTitle=${this.cameraTitle}
        .proxyConfig=${this.camera?.getLiveProxyConfig()}
        @advanced-camera-card:image-updating-player:error=${e=>o(this,{reason:e.detail})}
      >
      </advanced-camera-card-image-updating-player>
    `}static get styles(){return n(i)}};c([r({attribute:!1})],u.prototype,`hass`,void 0),c([r({attribute:!1})],u.prototype,`camera`,void 0),c([r({attribute:!1})],u.prototype,`targetID`,void 0),c([r({attribute:!1})],u.prototype,`cameraTitle`,void 0),u=c([t(`advanced-camera-card-live-image`)],u);export{u as AdvancedCameraCardLiveImage};