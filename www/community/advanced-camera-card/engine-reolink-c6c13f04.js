import{l as e,eb as t,ec as i,em as a,ea as n,eh as s,ed as r,el as o,ei as c,dW as l,d8 as u,en as h,ef as d,eg as g,ej as _,dg as p,di as m}from"./card-082b91a0.js";import{B as y,a as f,i as w,g as C}from"./within-dates-516ab2f3.js";import{C as b}from"./engine-86b0096c.js";import{g as k}from"./engine-generic-9048c20e.js";import{p as M}from"./parse-4859d476.js";import{e as D}from"./endOfDay-2e6ff39a.js";import"./media-c9012082.js";class z extends n{}class E extends y{constructor(){super(...arguments),this._channel=null,this._reolinkUniqueID=null,this._ptzEntities=null}async initialize(e){return await super.initialize(e),this._initializeChannel(),await this._initializeCapabilities(e.hass,e.entityRegistryManager),this}_initializeChannel(){const t=this._entity?.unique_id,i=t?String(t).match(/(?<uniqueid>.*)_(?<channel>\d+)/):null,a=i&&i.groups?.channel?Number(i.groups.channel):null,n=i?.groups?.uniqueid??null;if(null===a||null===n)throw new z(e("error.camera_initialization_reolink"),this.getConfig());this._channel=a,this._reolinkUniqueID=n}async _initializeCapabilities(e,i){const a=this.getConfig(),n=k(this.getConfig()),s=await this._getPTZEntities(e,i),r=s?this._entitiesToCapabilities(e,s):null,o=n||r?{...r,...n}:null;this._capabilities=new t({"favorite-events":!1,"favorite-recordings":!1,"remote-control-entity":!0,clips:!0,live:!0,menu:!0,recordings:!1,seek:!1,snapshots:!1,substream:!0,trigger:!0,...o&&{ptz:o}},{disable:a.capabilities?.disable,disableExcept:a.capabilities?.disable_except}),this._ptzEntities=s}_entitiesToCapabilities(e,t){const a={};for(const e of Object.keys(t))switch(e){case"left":case"right":case"up":case"down":a[e]=[i.Continuous];break;case"zoom_in":a.zoomIn=[i.Continuous];break;case"zoom_out":a.zoomOut=[i.Continuous]}const n=t?.presets?e.states[t.presets]:null;
/* istanbul ignore next: this path cannot be reached as ptzEntities will
        always have contents when this function is called  -- @preserve */
return Array.isArray(n?.attributes.options)&&(a.presets=n.attributes.options),Object.keys(a).length?a:null}async _getPTZEntities(e,t){
/* istanbul ignore next: this path cannot be reached as an exception is
           thrown in initialize() if this value is not found -- @preserve */
if(!this._reolinkUniqueID)return null;const i=`${this._reolinkUniqueID}_${this._channel}_`,a=await t.getMatchingEntities(e,(e=>e.config_entry_id===this._entity?.config_entry_id&&!!e.unique_id&&String(e.unique_id).startsWith(i)&&!e.disabled_by)),n=a.filter((e=>e.entity_id.startsWith("button."))),s=a.filter((e=>e.unique_id===`${i}ptz_preset`&&e.entity_id.startsWith("select."))),r=["stop","left","right","up","down","zoom_in","zoom_out"],o={};for(const e of n)for(const t of r)e.unique_id&&String(e.unique_id).endsWith(t)&&(o[t]=e.entity_id);return 1===s.length&&(o.presets=s[0].entity_id),Object.keys(o).length?o:null}getChannel(){return this._channel}getProxyConfig(){return{...super.getProxyConfig(),media:"auto"===this._config.proxy.media||this._config.proxy.media,ssl_verification:"auto"!==this._config.proxy.ssl_verification&&this._config.proxy.ssl_verification,ssl_ciphers:"auto"===this._config.proxy.ssl_ciphers?"intermediate":this._config.proxy.ssl_ciphers}}async executePTZAction(e,t,i){if(await super.executePTZAction(e,t,i))return!0;if(!this._ptzEntities)return!1;if("preset"===t){const t=this._ptzEntities.presets,n=i?.preset;return!(!n||!t)&&(await e.executeActions({actions:[a("select",t,n)]}),!0)}const n="start"===i?.phase?this._ptzEntities[t]:"stop"===i?.phase?this._ptzEntities.stop:null;return!!n&&(await e.executeActions({actions:[{action:"perform-action",perform_action:"button.press",target:{entity_id:n}}]}),!0)}}class x{static isReolinkEventQueryResults(e){return e.engine===r.Reolink&&e.type===g.Event}}class v extends f{constructor(){super(...arguments),this._cache=new s}getEngineType(){return r.Reolink}_reolinkFileMetadataGenerator(e,t,i){
/* istanbul ignore next: This situation cannot happen as the directory would
        be rejected by _reolinkDirectoryMetadataGenerator if there was no start date
        -- @preserve */
if(!i?._metadata?.startDate||t.media_class!==o)return null;const a=t.title.split(/ +/),n=M(a[0],"HH:mm:ss",i._metadata.startDate);if(!c(n))return null;const s=a.length>1?a[1].match(/(?<hours>\d+):(?<minutes>\d+):(?<seconds>\d+)/):null,r=s?.groups?{hours:Number(s.groups.hours),minutes:Number(s.groups.minutes),seconds:Number(s.groups.seconds)}:null,u=a.length>2?a.splice(2).map((e=>e.toLowerCase())).sort():null;return{cameraID:e,startDate:n,endDate:r?l(n,r):n,...u&&{what:u}}}_reolinkDirectoryMetadataGenerator(e,t){const i=M(t.title,"yyyy/M/d",new Date);return c(i)?{cameraID:e,startDate:u(i),endDate:D(i)}:null}_reolinkCameraMetadataGenerator(e){const t=e.media_content_id.match(/^media-source:\/\/reolink\/CAM\|(?<configEntryID>.+)\|(?<channel>\d+)$/);return t?.groups?{configEntryID:t.groups.configEntryID,channel:Number(t.groups.channel)}:null}async createCamera(e,t){const i=new E(t,this,{eventCallback:this._eventCallback});return await i.initialize({entityRegistryManager:this._entityRegistryManager,hass:e,stateWatcher:this._stateWatcher})}async _getMatchingDirectories(e,t,i,a){const n=t.getConfig(),s=t.getEntity(),r=s?.config_entry_id;if(null===t.getChannel()||!r)return null;const o=await this._browseMediaManager.walkBrowseMedias(e,[{targets:["media-source://reolink"],metadataGenerator:(e,t)=>this._reolinkCameraMetadataGenerator(e),matcher:e=>e._metadata?.channel===t.getChannel()&&e._metadata?.configEntryID===r}],{...!1!==a?.useCache&&{cache:this._cache}});return o?.length?await this._browseMediaManager.walkBrowseMedias(e,[{targets:[`media-source://reolink/RES|${r}|${t.getChannel()}|`+("low"===n.reolink?.media_resolution?"sub":"main")],metadataGenerator:(e,i)=>this._reolinkDirectoryMetadataGenerator(t.getID(),e),matcher:e=>e.can_expand&&w(e,i?.start,i?.end),sorter:e=>h(e)}],{...!1!==a?.useCache&&{cache:this._cache}}):null}async getEvents(e,t,i,a){if(i.favorite||i.tags?.size||i.what?.size||i.where?.size||i.hasSnapshot)return null;const n=new Map,s=async s=>{const o={...i,cameraIDs:new Set([s])},c=a?.useCache??1?this._requestCache.get(o):null;if(c)return void n.set(o,c);const l=t.getCamera(s),u=l&&l instanceof E?await this._getMatchingDirectories(e,l,o,a):null,d=o.limit??b;let _=[];u?.length&&(_=await this._browseMediaManager.walkBrowseMedias(e,[{targets:u,concurrency:1,metadataGenerator:(e,t)=>this._reolinkFileMetadataGenerator(s,e,t),earlyExit:e=>e.length>=d,matcher:e=>!e.can_expand&&w(e,o.start,o.end),sorter:e=>h(e)}],{...!1!==a?.useCache&&{cache:this._cache}}));const m=p(_,(e=>e._metadata?.startDate),"desc").slice(0,d),y={type:g.Event,engine:r.Reolink,browseMedia:m};(a?.useCache??1)&&this._requestCache.set(o,{...y,cached:!0},y.expiry),n.set(o,y)};return await d(i.cameraIDs,(e=>s(e))),n}generateMediaFromEvents(e,t,i,a){return x.isReolinkEventQueryResults(a)?C(a.browseMedia):null}async getMediaMetadata(e,t,i,a){const n=new Map,s=a?.useCache??1?this._requestCache.get(i):null;if(s)return n.set(i,s),n;const o=new Set,c=async i=>{const n=t.getCamera(i);if(!(n&&n instanceof E))return;const s=await this._getMatchingDirectories(e,n,null,a);for(const e of s??[])
/* istanbul ignore next: This situation cannot happen as the directory
                will not match without metadata -- @preserve */
e._metadata&&o.add(m(e._metadata?.startDate))};await d(i.cameraIDs,(e=>c(e)));const u={type:g.MediaMetadata,engine:r.Reolink,metadata:{...o.size&&{days:o}},expiry:l(new Date,{seconds:_}),cached:!1};return(a?.useCache??1)&&this._requestCache.set(i,{...u,cached:!0},u.expiry),n.set(i,u),n}getCameraMetadata(e,t){return{...super.getCameraMetadata(e,t),engineIcon:"reolink"}}getCameraEndpoints(e,t){const i=e.reolink?.url?{endpoint:e.reolink.url}:null;return{...super.getCameraEndpoints(e,t),...i&&{ui:i}}}}export{v as ReolinkCameraManagerEngine,x as ReolinkQueryResultsClassifier};
