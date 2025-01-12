import{_ as i,n as t,t as e,a,x as r,r as o,c_ as s}from"./card-7a934cb9.js";import"./timeline-core-20820726.js";import"./startOfHour-46d4ddf6.js";import"./endOfDay-a09c2e03.js";import"./date-picker-d443e5be.js";let n=class extends a{render(){return this.timelineConfig?r`
      <frigate-card-timeline-core
        .hass=${this.hass}
        .viewManagerEpoch=${this.viewManagerEpoch}
        .timelineConfig=${this.timelineConfig}
        .thumbnailConfig=${this.timelineConfig.controls.thumbnails}
        .cameraManager=${this.cameraManager}
        .cameraIDs=${this.cameraManager?.getStore().getCameraIDsWithCapability({anyCapabilities:["clips","snapshots","recordings"]})}
        .cardWideConfig=${this.cardWideConfig}
        .itemClickAction=${"none"===this.timelineConfig.controls.thumbnails.mode?"play":"select"}
      >
      </frigate-card-timeline-core>
    `:r``}static get styles(){return o(s)}};i([t({attribute:!1})],n.prototype,"hass",void 0),i([t({attribute:!1})],n.prototype,"viewManagerEpoch",void 0),i([t({attribute:!1})],n.prototype,"timelineConfig",void 0),i([t({attribute:!1})],n.prototype,"cameraManager",void 0),i([t({attribute:!1})],n.prototype,"cardWideConfig",void 0),n=i([e("frigate-card-timeline")],n);export{n as FrigateCardTimeline};
