import{a,cV as e,x as t,cZ as r,r as i,d4 as s,_ as n,n as o,t as c}from"./card-fdaaae6b.js";import"./image-updating-player-bedf67d8.js";let d=class extends a{constructor(){super(...arguments),this._refImage=e()}async getMediaPlayerController(){return await this.updateComplete,await(this._refImage.value?.getMediaPlayerController())??null}render(){if(this.hass&&this.cameraConfig)return t`
      <advanced-camera-card-image-updating-player
        ${r(this._refImage)}
        .hass=${this.hass}
        .imageConfig=${this.cameraConfig.image}
        .cameraConfig=${this.cameraConfig}
      >
      </advanced-camera-card-image-updating-player>
    `}static get styles(){return i(s)}};n([o({attribute:!1})],d.prototype,"hass",void 0),n([o({attribute:!1})],d.prototype,"cameraConfig",void 0),d=n([c("advanced-camera-card-live-image")],d);export{d as AdvancedCameraCardLiveImage};
