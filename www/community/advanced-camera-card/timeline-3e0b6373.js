import{_ as e,n as t,t as i,a,x as r,r as o,d6 as n}from"./card-937acef1.js";import"./timeline-core-100e22c4.js";import"./startOfHour-c2fa3fdc.js";import"./endOfDay-a2066737.js";import"./date-picker-3510b095.js";let s=class extends a{render(){return this.timelineConfig?r`
      <advanced-camera-card-timeline-core
        .hass=${this.hass}
        .viewManagerEpoch=${this.viewManagerEpoch}
        .timelineConfig=${this.timelineConfig}
        .thumbnailConfig=${this.timelineConfig.controls.thumbnails}
        .cameraManager=${this.cameraManager}
        .cameraIDs=${this.cameraManager?.getStore().getCameraIDsWithCapability({anyCapabilities:["clips","snapshots","recordings"]})}
        .cardWideConfig=${this.cardWideConfig}
        .itemClickAction=${"none"===this.timelineConfig.controls.thumbnails.mode?"play":"select"}
      >
      </advanced-camera-card-timeline-core>
    `:r``}static get styles(){return o(n)}};e([t({attribute:!1})],s.prototype,"hass",void 0),e([t({attribute:!1})],s.prototype,"viewManagerEpoch",void 0),e([t({attribute:!1})],s.prototype,"timelineConfig",void 0),e([t({attribute:!1})],s.prototype,"cameraManager",void 0),e([t({attribute:!1})],s.prototype,"cardWideConfig",void 0),s=e([i("advanced-camera-card-timeline")],s);export{s as AdvancedCameraCardTimeline};
