import{ds as e,dt as t,du as s,dv as i,a as o,l as n,c_ as a,x as c,r,_ as d,n as h,b as l,t as p}from"./card-082b91a0.js";import{d as m}from"./dispatch-live-error-a3b02041.js";import{s as u,h as v,M as y,m as g,V as b}from"./audio-d4b540aa.js";import{c as f}from"./endpoint-baa446bc.js";import{g as w}from"./get-technology-for-video-rtc-778a0c05.js";class C extends HTMLElement{constructor(){super(),this.DISCONNECT_TIMEOUT=5e3,this.RECONNECT_TIMEOUT=15e3,this.CODECS=["avc1.640029","avc1.64002A","avc1.640033","hvc1.1.6.L153.B0","mp4a.40.2","mp4a.40.5","flac","opus"],this.mode="webrtc,mse,hls,mjpeg",this.media="video,audio",this.background=!1,this.visibilityThreshold=0,this.visibilityCheck=!0,this.pcConfig={bundlePolicy:"max-bundle",iceServers:[{urls:"stun:stun.l.google.com:19302"}],sdpSemantics:"unified-plan"},this.wsState=WebSocket.CLOSED,this.pcState=WebSocket.CLOSED,this.video=null,this.ws=null,this.wsURL="",this.pc=null,this.connectTS=0,this.mseCodecs="",this.disconnectTID=0,this.reconnectTID=0,this.ondata=null,this.onmessage=null,this.microphoneStream=null,this.mediaPlayerController=null,this.controls=!0}reconnect(){this.wsState!==WebSocket.CLOSED?(this.ws?.addEventListener("close",(()=>this.onconnect())),this.ondisconnect()):(this.ondisconnect(),this.onconnect())}setControls(e){this.controls=e,this.video&&u(this.video,e)}set src(e){"string"!=typeof e&&(e=e.toString()),e.startsWith("http")?e="ws"+e.substring(4):e.startsWith("/")&&(e="ws"+location.origin.substring(4)+e),this.wsURL=e,this.onconnect()}play(){}send(e){this.ws&&this.ws.send(JSON.stringify(e))}codecs(e){return this.CODECS.filter((e=>this.media.indexOf(e.indexOf("vc1")>0?"video":"audio")>=0)).filter((t=>e(`video/mp4; codecs="${t}"`))).join()}connectedCallback(){if(this.disconnectTID&&(clearTimeout(this.disconnectTID),this.disconnectTID=0),this.video){const e=this.video.seekable;e.length>0&&(this.video.currentTime=e.end(e.length-1)),this.play()}else this.oninit();this.onconnect()}disconnectedCallback(){this.background||this.disconnectTID||this.wsState===WebSocket.CLOSED&&this.pcState===WebSocket.CLOSED||(this.disconnectTID=setTimeout((()=>{this.reconnectTID&&(clearTimeout(this.reconnectTID),this.reconnectTID=0),this.disconnectTID=0,this.ondisconnect()}),this.DISCONNECT_TIMEOUT))}oninit(){this.video=document.createElement("video"),u(this.video,this.controls),this.video.playsInline=!0,this.video.preload="auto",this.video.style.display="block",this.video.style.width="100%",this.video.style.height="100%",this.appendChild(this.video),this.video.addEventListener("error",(e=>{this.ws&&this.wsState===WebSocket.OPEN&&this.ws.close()}));const o=window.navigator.userAgent.match(/Version\/(\d+).+Safari/);if(o){const e=o[1]<"13"?"mp4a.40.2":o[1]<"14"?"flac":"opus";this.CODECS.splice(this.CODECS.indexOf(e))}if(!this.background){if("hidden"in document&&this.visibilityCheck&&document.addEventListener("visibilitychange",(()=>{document.hidden?this.disconnectedCallback():this.isConnected&&this.connectedCallback()})),"IntersectionObserver"in window&&this.visibilityThreshold){new IntersectionObserver((e=>{e.forEach((e=>{e.isIntersecting?this.isConnected&&this.connectedCallback():this.disconnectedCallback()}))}),{threshold:this.visibilityThreshold}).observe(this)}this.video.onloadeddata=()=>{this.controls&&v(this.video,y),e(this,this.video,{...this.mediaPlayerController&&{mediaPlayerController:this.mediaPlayerController},capabilities:{supports2WayAudio:!!this.pc,supportsPause:!0,hasAudio:g(this.video)},technology:w(this)})},this.video.onvolumechange=()=>t(this),this.video.onplay=()=>s(this),this.video.onpause=()=>i(this),this.video.muted=!0}}onconnect(){return!(!this.isConnected||!this.wsURL||this.ws||this.pc)&&(this.wsState=WebSocket.CONNECTING,this.connectTS=Date.now(),this.ws=new WebSocket(this.wsURL),this.ws.binaryType="arraybuffer",this.ws.addEventListener("open",(e=>this.onopen(e))),this.ws.addEventListener("close",(e=>this.onclose(e))),!0)}ondisconnect(){this.wsState=WebSocket.CLOSED,this.ws&&(this.ws.close(),this.ws=null),this.pcState=WebSocket.CLOSED,this.pc&&(this.pc.close(),this.pc=null),this.video.src="",this.video.srcObject=null}onopen(){this.wsState=WebSocket.OPEN,this.ws.addEventListener("message",(e=>{if("string"==typeof e.data){const t=JSON.parse(e.data);for(const e in this.onmessage)this.onmessage[e](t)}else this.ondata(e.data)})),this.ondata=null,this.onmessage={};const e=[];return this.mode.indexOf("mse")>=0&&("MediaSource"in window||"ManagedMediaSource"in window)?(e.push("mse"),this.onmse()):this.mode.indexOf("hls")>=0&&this.video.canPlayType("application/vnd.apple.mpegurl")?(e.push("hls"),this.onhls()):this.mode.indexOf("mp4")>=0&&(e.push("mp4"),this.onmp4()),this.mode.indexOf("webrtc")>=0&&"RTCPeerConnection"in window&&(e.push("webrtc"),this.onwebrtc()),this.mode.indexOf("mjpeg")>=0&&(e.length?this.onmessage.mjpeg=t=>{"error"===t.type&&0===t.value.indexOf(e[0])&&this.onmjpeg()}:(e.push("mjpeg"),this.onmjpeg())),e}onclose(){if(this.wsState===WebSocket.CLOSED)return!1;this.wsState=WebSocket.CONNECTING,this.ws=null;const e=Math.max(this.RECONNECT_TIMEOUT-(Date.now()-this.connectTS),0);return this.reconnectTID=setTimeout((()=>{this.reconnectTID=0,this.onconnect()}),e),!0}onmse(){let e;if("ManagedMediaSource"in window){const t=window.ManagedMediaSource;e=new t,e.addEventListener("sourceopen",(()=>{this.send({type:"mse",value:this.codecs(t.isTypeSupported)})}),{once:!0}),this.video.disableRemotePlayback=!0,this.video.srcObject=e}else e=new MediaSource,e.addEventListener("sourceopen",(()=>{URL.revokeObjectURL(this.video.src),this.send({type:"mse",value:this.codecs(MediaSource.isTypeSupported)})}),{once:!0}),this.video.src=URL.createObjectURL(e),this.video.srcObject=null;this.play(),this.mseCodecs="",this.onmessage.mse=t=>{if("mse"!==t.type)return;this.mseCodecs=t.value;const s=e.addSourceBuffer(t.value);s.mode="segments",s.addEventListener("updateend",(()=>{if(!s.updating)try{if(o>0){const e=i.slice(0,o);o=0,s.appendBuffer(e)}else if(s.buffered&&s.buffered.length){const t=s.buffered.end(s.buffered.length-1)-15,i=s.buffered.start(0);t>i&&(s.remove(i,t),e.setLiveSeekableRange(t,t+15))}}catch(e){}}));const i=new Uint8Array(2097152);let o=0;this.ondata=e=>{if(s.updating||o>0){const t=new Uint8Array(e);i.set(t,o),o+=t.byteLength}else try{s.appendBuffer(e)}catch(e){}}}}onwebrtc(){const e=new RTCPeerConnection(this.pcConfig);e.addEventListener("icecandidate",(e=>{if(e.candidate&&this.mode.indexOf("webrtc/tcp")>=0&&"udp"===e.candidate.protocol)return;const t=e.candidate?e.candidate.toJSON().candidate:"";this.send({type:"webrtc/candidate",value:t})})),e.addEventListener("connectionstatechange",(()=>{if("connected"===e.connectionState){const t=e.getTransceivers().filter((e=>"recvonly"===e.currentDirection)).map((e=>e.receiver.track)),s=document.createElement("video");s.addEventListener("loadeddata",(()=>this.onpcvideo(s)),{once:!0}),s.srcObject=new MediaStream(t)}else"failed"!==e.connectionState&&"disconnected"!==e.connectionState||(e.close(),this.pcState=WebSocket.CLOSED,this.pc=null,this.onconnect())})),this.onmessage.webrtc=t=>{switch(t.type){case"webrtc/candidate":if(this.mode.indexOf("webrtc/tcp")>=0&&t.value.indexOf(" udp ")>0)return;e.addIceCandidate({candidate:t.value,sdpMid:"0"}).catch((e=>{console.warn(e)}));break;case"webrtc/answer":e.setRemoteDescription({type:"answer",sdp:t.value}).catch((e=>{console.warn(e)}));break;case"error":if(t.value.indexOf("webrtc/offer")<0)return;e.close()}},this.createOffer(e).then((e=>{this.send({type:"webrtc/offer",value:e.sdp})})),this.pcState=WebSocket.CONNECTING,this.pc=e}async createOffer(e){this.microphoneStream?.getTracks().forEach((t=>{e.addTransceiver(t,{direction:"sendonly"})}));try{if(this.media.indexOf("microphone")>=0){(await navigator.mediaDevices.getUserMedia({audio:!0})).getTracks().forEach((t=>{e.addTransceiver(t,{direction:"sendonly"})}))}}catch(e){console.warn(e)}for(const t of["video","audio"])this.media.indexOf(t)>=0&&e.addTransceiver(t,{direction:"recvonly"});const t=await e.createOffer();return await e.setLocalDescription(t),t}onpcvideo(e){if(this.pc){let t=0,s=0;const i=e.srcObject;i.getVideoTracks().length>0&&(t+=544),i.getAudioTracks().length>0&&(t+=258),this.mseCodecs.indexOf("hvc1.")>=0&&(s+=560),this.mseCodecs.indexOf("avc1.")>=0&&(s+=528),this.mseCodecs.indexOf("mp4a.")>=0&&(s+=257),t>=s?(this.video.srcObject=i,this.play(),this.pcState=WebSocket.OPEN,this.wsState=WebSocket.CLOSED,this.ws&&(this.ws.close(),this.ws=null)):(this.pcState=WebSocket.CLOSED,this.pc&&(this.pc.close(),this.pc=null))}e.srcObject=null}onmjpeg(){let t=!1;this.ondata=s=>{u(this.video,!1),this.video.poster="data:image/jpeg;base64,"+C.btoa(s),t||(t=!0,e(this,this.video,{...this.mediaPlayerController&&{mediaPlayerController:this.mediaPlayerController},technology:["mjpeg"]}))},this.send({type:"mjpeg"})}onhls(){this.onmessage.hls=e=>{if("hls"!==e.type)return;const t="http"+this.wsURL.substring(2,this.wsURL.indexOf("/ws"))+"/hls/",s=e.value.replace("hls/",t);this.video.src="data:application/vnd.apple.mpegurl;base64,"+btoa(s),this.play()},this.send({type:"hls",value:this.codecs((e=>this.video.canPlayType(e)))})}onmp4(){const t=document.createElement("canvas");let s;const i=document.createElement("video");i.autoplay=!0,i.playsInline=!0,i.muted=!0,i.addEventListener("loadeddata",(o=>{s||(t.width=i.videoWidth,t.height=i.videoHeight,s=t.getContext("2d"),e(this,i,{...this.mediaPlayerController&&{mediaPlayerController:this.mediaPlayerController},technology:["mp4"]})),s.drawImage(i,0,0,t.width,t.height),u(this.video,!1),this.video.poster=t.toDataURL("image/jpeg")})),this.ondata=e=>{i.src="data:video/mp4;base64,"+C.btoa(e)},this.send({type:"mp4",value:this.codecs(this.video.canPlayType)})}static btoa(e){const t=new Uint8Array(e),s=t.byteLength;let i="";for(let e=0;e<s;e++)i+=String.fromCharCode(t[e]);return window.btoa(i)}}customElements.define("advanced-camera-card-live-go2rtc-player",C);let S=class extends o{constructor(){super(...arguments),this.controls=!1,this._message=null,this._mediaPlayerController=new b(this,(()=>this._player?.video??null),(()=>this.controls))}async getMediaPlayerController(){return this._mediaPlayerController}disconnectedCallback(){this._player=void 0,this._message=null}connectedCallback(){super.connectedCallback(),this.requestUpdate()}async _createPlayer(){if(!this.hass)return;const e=this.cameraEndpoints?.go2rtc;if(!e)return this._message={type:"error",message:n("error.live_camera_no_endpoint"),context:this.cameraConfig},void m(this);const t=await f(this.hass,e,86400);if(!t)return this._message={type:"error",message:n("error.failed_sign"),context:this.cameraConfig},void m(this);this._player=new C,this._player.mediaPlayerController=this._mediaPlayerController,this._player.microphoneStream=this.microphoneState?.stream??null,this._player.src=t,this._player.visibilityCheck=!1,this._player.setControls(this.controls),this.cameraConfig?.go2rtc?.modes&&this.cameraConfig.go2rtc.modes.length&&(this._player.mode=this.cameraConfig.go2rtc.modes.join(",")),this.requestUpdate()}willUpdate(e){e.has("cameraEndpoints")&&(this._message=null),this._message||this._player&&!e.has("cameraEndpoints")||this._createPlayer(),e.has("controls")&&this._player&&this._player.setControls(this.controls),this._player&&e.has("microphoneState")&&this._player.microphoneStream!==(this.microphoneState?.stream??null)&&(this._player.microphoneStream=this.microphoneState?.stream??null,this._player.reconnect())}render(){return this._message?a(this._message):c`${this._player}`}static get styles(){return r(":host {\n  width: 100%;\n  height: 100%;\n  display: block;\n}\n\nvideo {\n  object-fit: var(--advanced-camera-card-media-layout-fit, contain);\n  object-position: var(--advanced-camera-card-media-layout-position-x, 50%) var(--advanced-camera-card-media-layout-position-y, 50%);\n  object-view-box: inset(var(--advanced-camera-card-media-layout-view-box-top, 0%) var(--advanced-camera-card-media-layout-view-box-right, 0%) var(--advanced-camera-card-media-layout-view-box-bottom, 0%) var(--advanced-camera-card-media-layout-view-box-left, 0%));\n  width: 100%;\n  height: 100%;\n  display: block;\n}")}};d([h({attribute:!1})],S.prototype,"cameraConfig",void 0),d([h({attribute:!1})],S.prototype,"cameraEndpoints",void 0),d([h({attribute:!1})],S.prototype,"microphoneState",void 0),d([h({attribute:!1})],S.prototype,"microphoneConfig",void 0),d([h({attribute:!0,type:Boolean})],S.prototype,"controls",void 0),d([l()],S.prototype,"_message",void 0),S=d([p("advanced-camera-card-live-go2rtc")],S);export{S as AdvancedCameraCardGo2RTC};
