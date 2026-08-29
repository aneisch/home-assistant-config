import{Do as e,Eo as t,Mo as n,To as r,U as i,ko as a,lt as o}from"./shared-DSCWESL1.js";import"./timeline-core-mL6OwmdN.js";var s=class extends e{render(){return this.timelineConfig?a`
      <advanced-camera-card-timeline-core
        .hass=${this.hass}
        .viewManagerEpoch=${this.viewManagerEpoch}
        .timelineConfig=${this.timelineConfig}
        .thumbnailConfig=${this.timelineConfig.controls.thumbnails}
        .cameraManager=${this.cameraManager}
        .foldersManager=${this.foldersManager}
        .conditionStateManager=${this.conditionStateManager}
        .viewItemManager=${this.viewItemManager}
        .cardWideConfig=${this.cardWideConfig}
        .itemClickAction=${this.timelineConfig.controls.thumbnails.mode===`none`?`play`:`select`}
      >
      </advanced-camera-card-timeline-core>
    `:a``}static get styles(){return n(i)}};o([r({attribute:!1})],s.prototype,`hass`,void 0),o([r({attribute:!1})],s.prototype,`viewManagerEpoch`,void 0),o([r({attribute:!1})],s.prototype,`timelineConfig`,void 0),o([r({attribute:!1})],s.prototype,`cameraManager`,void 0),o([r({attribute:!1})],s.prototype,`foldersManager`,void 0),o([r({attribute:!1})],s.prototype,`conditionStateManager`,void 0),o([r({attribute:!1})],s.prototype,`viewItemManager`,void 0),o([r({attribute:!1})],s.prototype,`cardWideConfig`,void 0),s=o([t(`advanced-camera-card-timeline`)],s);export{s as AdvancedCameraCardTimeline};