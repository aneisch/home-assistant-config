/**
 * @module Lovelace class for accessing Arlo camera through the AArlo
 * module.
 *
 * Startup Notes:
 * - hass(); called at startup; set initial internal status and then updates
 *   image element data
 * - setConfig(); called at startup; we read out config data and store inside
 *   `?c` variables.
 * - render(); called at startup; we start initialView() and return the
 *   skeleton HTML for the card.
 * - initialView(); loops until HTML is in place then set up which individual
 *   elements are present (eg, motion sensor if asked for) and then displays
 *   the image card.
 *
 * Running Notes:
 * - hass(); called when state changes; update internal status and then updates
 *   image element data
 *
 * Controlling what's on screen:
 * - setup(Image|library|Video|Stream)View; one off, set visibility that doesn't
 *   change
 * - update(Image|Video|Stream)View; set up text, alt, state and visibility that
 *   do change
 * - show(Image|Video|Stream)View; show layers for this card
 * - hide(Image|Video|Stream)View; don't show layers for this card
 *
 * What's what:
 * - this._gc; global configuration
 * - this._cc; all cameras configurations
 * - this._cs; all camara states
 * - this._lc; all library configurations
 * - this._ls; all library states
 */


const LitElement = Object.getPrototypeOf(
        customElements.get("ha-panel-lovelace")
    );
const html = LitElement.prototype.html;


// noinspection JSUnresolvedVariable,CssUnknownTarget,CssUnresolvedCustomProperty,HtmlRequiredAltAttribute,RequiredAttributes,JSFileReferences
class AarloGlance extends LitElement {

    constructor() {
        super();

        // State and config.
        this._hass = null;
        this._config = null;
        this._ready = false

        // The current image URL.
        this._image = ''

        // Internationalisation.
        this._i = null
        this._lang = null

        // The current image URL has a timestamp suffix added, this is the URL without it.
        // This way we can check for token changes.
        this._image_base = ''

        this._hls = null;
        this._dash = null;
        this._video = null
        this._videoState = ''
        this._stream = null
        this._modalViewer = false

        this._gc = {}
        this._cc = {}
        this._cs = {}
        this._lc = {}
        this._ls = {}
        this._cameraIndex = 0
    }

    static get styleTemplate() {
        return html`
            <link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css">
            <style>
                ha-card {
                    position: relative;
                    min-height: 48px;
                    overflow: hidden;
                }
                .box {
                    white-space: var(--paper-font-common-nowrap_-_white-space); overflow: var(--paper-font-common-nowrap_-_overflow); text-overflow: var(--paper-font-common-nowrap_-_text-overflow);
                    position: absolute;
                    left: 0;
                    right: 0;
                    background-color: rgba(0, 0, 0, 0.4);
                    padding: 4px 8px;
                    font-size: 16px;
                    line-height: 36px;
                    color: white;
                    display: flex;
                    justify-content: space-between;
                }
                .box-top {
                    top: 0;
                }
                .box-bottom {
                    bottom: 0;
                }
                .box-bottom-small {
                    bottom: 0;
                    line-height: 30px;
                }
                .box-title {
                    font-weight: 500;
                    margin-left: 4px;
                }
                .box-status {
                    font-weight: 500;
                    margin-right: 4px;
                    text-transform: capitalize;
                }
                ha-icon {
                    cursor: pointer;
                    padding: 2px;
                    color: #a9a9a9;
                }
                div.aarlo-aspect-16x9 {
                    padding-top: 55%;
                }
                div.aarlo-aspect-1x1 {
                    padding-top: 100%;
                }
                div.aarlo-base {
                    margin: 0;
                    overflow: hidden;
                    position: relative;
                    width: 100%;
                }
                div.aarlo-modal-base {
                    margin: 0 auto;
                    position: relative;
                }
                .aarlo-image {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    width: 100%;
                    transform: translate(-50%, -50%);
                    cursor: pointer;
                }
                .aarlo-video {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    width: 100%;
                    height: auto;
                    transform: translate(-50%, -50%);
                }
                .aarlo-library {
                    width: 100%;
                    cursor: pointer;
                }
                .aarlo-modal-video-wrapper {
                    overflow: hidden;
                    position: absolute;
                    top: 0;
                    left: 0;
                }
                .aarlo-modal-video {
                    position: absolute;
                    top: -8px;
                    left: 0;
                }
                .aarlo-modal-video-background {
                    position: absolute;
                    top: 0;
                    left: 0;
                    background-color: darkgrey;
                }
                .aarlo-library-row {
                    display: flex;
                    margin: 6px 2px 6px 2px;
                }
                .aarlo-library-column {
                    flex: 32%;
                    padding: 2px;
                }
                .hidden {
                    display: none;
                }
                .aarlo-broken-image {
                    background: grey url("/static/images/image-broken.svg") center/36px
                    no-repeat;
                }
                .slidecontainer {
                    text-align: center;
                    width: 70%;
                }
                .slider {
                    -webkit-appearance: none;
                    background: #d3d3d3;
                    outline: none;
                    opacity: 0.7;
                    width: 100%;
                    height: 10px;
                    -webkit-transition: .2s;
                    transition: opacity .2s;
                }
                .slider:hover {
                    opacity: 1;
                }
                .slider::-webkit-slider-thumb {
                    -webkit-appearance: none;
                    appearance: none;
                    background: #4CAF50;
                    width: 10px;
                    height: 10px;
                    cursor: pointer;
                }
                .slider::-moz-range-thumb {
                    background: #4CAF50;
                    width: 10px;
                    height: 10px;
                    cursor: pointer;
                }
            </style>
        `;
    }

    render() {
        this.initialView()
        return html`
            ${AarloGlance.styleTemplate}
            <div class="w3-modal"
                 id="${this._id('modal-viewer')}"
                 style="display:none">
                <div class="w3-modal-content w3-animate-opacity aarlo-modal-base"
                     id="${this._id('modal-content')}">
                    <div class="aarlo-modal-video-wrapper"
                         id="${this._id('modal-video-wrapper')}">
                        <div class="aarlo-modal-video-background"
                             id="${this._id('modal-video-background')}">
                        </div>
                        <video class="aarlo-modal-video"
                               id="${this._id('modal-stream-player')}"
                               @ended="${() => { this.stopStream() }}"
                               @mouseover="${() => { this.mouseOverVideo(); }}"
                               @click="${() => { this.clickVideo(); }}">
                            Your browser does not support the video tag.
                        </video>
                        <video class="aarlo-modal-video"
                               id="${this._id('modal-video-player')}"
                               playsinline
                               @canplay="${() => { this.startVideo() }}"
                               @ended="${() => { this.stopVideo(); }}"
                               @mouseover="${() => { this.mouseOverVideo(); }}"
                               @click="${() => { this.clickVideo(); }}">
                            Your browser does not support the video tag.
                        </video>
                        <div class="box box-bottom"
                               id="${this._id('modal-video-controls')}">
                            <div>
                                <ha-icon id="${this._id('modal-video-door-lock')}"
                                         @click="${() => { this.toggleLock(this.cc.doorLockId); }}">
                                </ha-icon>
                                <ha-icon id="${this._id('modal-video-light-on')}"
                                         @click="${() => { this.toggleLight(this.cc.lightId); }}">
                                </ha-icon>
                                <ha-icon id="${this._id('modal-video-stop')}"
                                         @click="${() => { this.controlStopVideoOrStream(); }}">
                                </ha-icon>
                                <ha-icon id="${this._id('modal-video-play')}"
                                         @click="${() => { this.controlPlayVideo(); }}">
                                </ha-icon>
                                <ha-icon id="${this._id('modal-video-pause')}"
                                         @click="${() => { this.controlPauseVideo(); }}">
                                </ha-icon>
                            </div>
                            <div class='slidecontainer'>
                                <input class="slider"
                                       id="${this._id('modal-video-seek')}"
                                       type="range" value="0" min="1" max="100">
                            </div>
                            <div>
                                <ha-icon id="${this._id('modal-video-full-screen')}"
                                         @click="${() => { this.controlFullScreen(); }}">
                                </ha-icon>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <ha-card>
                <div class="aarlo-base aarlo-aspect-${this.gc.aspectRatio}"
                     id="${this._id('aarlo-wrapper')}">
                    <video class="aarlo-video"
                           id="${this._id('stream-player')}"
                           style="display:none"
                           poster="${this._streamPoster}"
                           @ended="${() => { this.stopStream() }}"
                           @mouseover="${() => { this.mouseOverVideo(); }}"
                           @click="${() => { this.clickVideo(); }}">
                        Your browser does not support the video tag.
                    </video>
                    <video class="aarlo-video"
                           id="${this._id('video-player')}"
                           style="display:none"
                           playsinline
                           @canplay="${() => { this.startVideo() }}"
                           @ended="${() => { this.stopVideo(); }}"
                           @mouseover="${() => { this.mouseOverVideo(); }}"
                           @click="${() => { this.clickVideo(); }}">
                        Your browser does not support the video tag.
                    </video>
                    <img class="aarlo-image"
                         id="${this._id('image-viewer')}"
                         style="display:none"
                         @click="${() => { this.clickImage(); }}">
                    <div class="aarlo-image"
                         id="${this._id('library-viewer')}"
                         style="display:none">
                    </div>
                    <div class="aarlo-image aarlo-broken-image" 
                         id="${this._id('broken-image')}"
                         style="height: 100px">
                    </div>
                </div>
                <div class="box box-top"
                     id="${this._id('top-bar')}"
                     style="display:none">
                    <div class="box-title"
                         id="${this._id('top-bar-title')}">
                    </div>
                    <div class="box-status"
                         id="${this._id('top-bar-date')}">
                    </div>
                    <div class="box-status"
                         id="${this._id('top-bar-status')}">
                    </div>
                </div>
                <div class="box box-bottom"
                     id="${this._id('bottom-bar')}"
                     style="display:none">
                    <div class="box-title"
                         id="${this._id('bottom-bar-title')}">
                    </div>
                    <div class=""
                         id="${this._id('bottom-bar-camera')}">
                        <ha-icon id="${this._id('camera-on-off')}"
                                 @click="${() => { this.toggleCamera() }}">
                        </ha-icon>
                        <ha-icon id="${this._id('camera-motion')}"
                                 @click="${() => { this.moreInfo(this.cc.motionId); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('camera-sound')}"
                                 @click="${() => { this.moreInfo(this.cc.soundId); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('camera-captured')}"
                                 @click="${() => { this.openLibrary(0) }}">
                        </ha-icon>
                        <ha-icon id="${this._id('camera-play')}"
                                 @click="${() => { this.showOrStopStream() }}">
                        </ha-icon>
                        <ha-icon id="${this._id('camera-snapshot')}"
                                 @click="${() => { this.wsUpdateSnapshot() }}">
                        </ha-icon>
                        <ha-icon id="${this._id('camera-battery')}"
                                 @click="${() => { this.moreInfo(this.cc.batteryId) }}">
                        </ha-icon>
                        <ha-icon id="${this._id('camera-wifi-signal')}"
                                 @click="${() => { this.moreInfo(this.cc.signalId) }}">
                        </ha-icon>
                        <ha-icon id="${this._id('camera-light-left')}"
                                 @click="${() => { this.toggleLight(this.cc.lightId) }}">
                        </ha-icon>
                    </div>
                    <div class="box-title"
                         id="${this._id('bottom-bar-date')}">
                    </div>
                    <div class="box-status"
                         id="${this._id('bottom-bar-externals')}">
                        <ha-icon id="${this._id('externals-door')}"
                                 @click="${() => { this.moreInfo(this.cc.doorId); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('externals-door-bell')}"
                                 @click="${() => { this.moreInfo(this.cc.doorBellId); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('externals-door-lock')}"
                                 @click="${() => { this.toggleLock(this.cc.doorLockId); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('externals-door-2')}"
                                 @click="${() => { this.moreInfo(this.cc.door2Id); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('externals-door-bell-2')}"
                                 @click="${() => { this.moreInfo(this.cc.door2BellId); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('externals-door-lock-2')}"
                                 @click="${() => { this.toggleLock(this.cc.door2LockId); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('externals-light')}"
                                 @click="${() => { this.toggleLight(this.cc.lightId); }}">
                         </ha-icon>
                    </div>
                    <div class="box-status"
                         id="${this._id('bottom-bar-status')}">
                    </div>
                </div>
                <div class="box box-bottom-small"
                     id="${this._id('library-controls')}"
                     style="display:none">
                    <div>
                        <ha-icon id="${this._id('library-control-first')}"
                                 @click="${() => { this.firstLibraryPage(); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('library-control-previous')}"
                                 @click="${() => { this.previousLibraryPage(); }}">
                        </ha-icon>
                    </div>
                    <div style="margin-left: auto; margin-right: auto">
                        <ha-icon id="${this._id('library-control-resize')}"
                                 @click="${() => { this.resizeLibrary() }}">
                        </ha-icon>
                        <ha-icon id="${this._id('library-control-close')}"
                                 @click="${() => { this.closeLibrary() }}">
                        </ha-icon>
                    </div>
                    <div>
                        <ha-icon id="${this._id('library-control-next')}"
                                 @click="${() => { this.nextLibraryPage() }}">
                        </ha-icon>
                        <ha-icon id="${this._id('library-control-last')}"
                                 @click="${() => { this.lastLibraryPage(); }}">
                        </ha-icon>
                    </div>
                </div>
                <div class="box box-bottom"
                     id="${this._id('video-controls')}"
                     style="display:none">
                    <div>
                        <ha-icon id="${this._id('video-door-lock')}"
                                 @click="${() => { this.toggleLock(this.cc.doorLockId); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('video-light-on')}"
                                 @click="${() => { this.toggleLight(this.cc.lightId); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('video-stop')}"
                                 @click="${() => { this.controlStopVideoOrStream(); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('video-play')}"
                                 @click="${() => { this.controlPlayVideo(); }}">
                        </ha-icon>
                        <ha-icon id="${this._id('video-pause')}"
                                 @click="${() => { this.controlPauseVideo(); }}">
                        </ha-icon>
                    </div>
                    <div class='slidecontainer'>
                        <input class="slider"
                               id="${this._id('video-seek')}"
                               type="range" value="0" min="1" max="100">
                    </div>
                    <div>
                        <ha-icon 
                                 id="${this._id('video-full-screen')}"
                                 @click="${() => { this.controlFullScreen(); }}">
                        </ha-icon>
                    </div>
                </div>
            </ha-card>`
    }

    static get properties() {
        return {
            // All handle internally
        }
    }

    updated(_changedProperties) {
        // All handle internally
    }

    set hass( hass ) {
        this._hass = hass;
        if ( this._ready ) {
            this.updateView()
        }
    }

    getCardSize() {
        return this.gc.cardSize
    }

    moreInfo( id ) {
        const event = new Event('hass-more-info', {
            bubbles: true,
            cancelable: false,
            composed: true,
        });
        event.detail = { entityId: id };
        this.shadowRoot.dispatchEvent(event);
        return event;
    }

    throwError( error ) {
        console.error( error );
        throw new Error( error )
    }

    _log( msg ) {
        if( this.gc.log ) {
            console.log( `${this.cc.id}: ${msg}` )
        }
    }

    _id( id ) {
        return `${id}-${this.gc.idSuffix}`
    }

    _mid( id ) {
        return (this._modalViewer ? "modal-" : "") + this._id(id)
    }

    /**
     * Look for card element in shadow dom.
     *
     * @param id The element or `null`
    */
    _element( id ) {
        return this.shadowRoot.getElementById( this._id(id) )
    }

    /**
     * Look for modal card element in shadow dom.
     *
     * Automatically chooses modal name if modal window open.
     *
     * @param id The element or `null`
    */
    _melement( id ) {
        return this.shadowRoot.getElementById( this._mid(id) )
    }

    __show( element, show ) {
        if ( element ) { element.style.display = show ? '' : 'none' }
    }
    _show( id, show = true ) {
        this.__show( this._element(id), show )
    }
    _mshow( id, show = true ) {
        this.__show( this._melement(id), show )
    }

    __hide( element ) {
        if ( element ) { element.style.display = 'none' }
    }
    _hide( id ) {
        this.__hide( this._element(id) )
    }
    _mhide( id ) {
        this.__hide( this._melement(id) )
    }

    __isHidden( element ) {
        return element && element.style.display === 'none'
    }
    _misHidden( id ) {
        return this.__isHidden( this._melement(id) )
    }

    __title( element, title ) {
        if ( element ) { element.title = title }
    }
    __text( element, text ) {
        if ( element ) { element.innerText = text }
    }
    __alt( element, alt ) {
        if ( element ) { element.alt = alt }
    }
    __src( element, src ) {
        if ( element ) { element.src = src }
    }
    __poster( element, poster ) {
        if ( element ) { element.poster = poster }
    }
    __icon( element, icon ) {
        if ( element ) { element.icon = icon }
    }
    __state( element, state ) {
        let color = ""
        switch( state ) {
            case "on":
            case "state-on":
                color = "white"
                break
            case "warn":
            case "state-warn":
                color = "orange"
                break
            case "error":
            case "state-error":
                color = "red"
                break
            case "update":
            case "state-update":
                color = "#cccccc"
                break
            case "off":
            case "state-off":
                color = "#505050"
                break
        }
        if ( element ) {
            element.style.color = color
        }
    }

    /**
     * Set a variety of element values.
     *
     * It gets called a lot.
     */
    __set( element, title, text, icon, state, src, alt, poster ) {
        if ( title !== undefined )  { this.__title( element, title ) }
        if ( text !== undefined )   { this.__text ( element, text ) }
        if ( icon !== undefined )   { this.__icon ( element, icon ) }
        if ( state !== undefined )  { this.__state( element, state ) }
        if ( src !== undefined )    { this.__src( element, src ) }
        if ( alt !== undefined )    { this.__alt( element, alt ) }
        if ( poster !== undefined ) { this.__poster( element, poster ) }
    }

    /**
     * Set a variety pieces of element data.
     *
     * @param id - ID of element to change
     * @param dictionary - Object containing changes. Not all entries need to
     *     be set.
     */
    _set( id, { title, text, icon, state, src, alt, poster } = {} ) {
        this.__set( this._element(id), title, text, icon, state, src, alt, poster )
    }
    /**
     * Set a variety pieces of element data.
     *
     * This uses the modal version when a modal window is open.
     *
     * @param id - ID of element to change
     * @param dictionary - Object containing changes. Not all entries need to
     *     be set.
     */
    _mset( id, { title, text, icon, state, src, alt, poster } = {} ) {
        this.__set( this._melement(id), title, text, icon, state, src, alt, poster )
    }

    _widthHeight(id, width, height, width_suffix = '' ) {
        let element = this._element(id)
        if ( element ) {
            if ( width !== null ) {
                element.style.setProperty("width",`${width}px`,width_suffix)
            }
            if ( height !== null ) {
                element.style.height = `${height}px`
            }
        }
    }

    _paddingTop( id, top ) {
        let element = this._element(id)
        if ( element ) {
            if ( top !== null ) {
                element.style.paddingTop=`${top}px`
            }
        }
    }

    /**
     * Replace all of `from` with `to` and return the new string.
     *
     * @param old_string string we are converting
     * @param from what to replace
     * @param to what to replace it with
     * @returns {*} the new string
     * @private
     */
    _replaceAll( old_string, from, to ) {
        while( true ) {
            const new_string = old_string.replace( from,to )
            if( new_string === old_string ) {
                return new_string
            }
            old_string = new_string
        }
    }

    _findEgressToken( url ) {
        let parser = document.createElement('a');
        parser.href = url;
        let queries = parser.search.replace(/^\?/, '').split('&');
        for( let i = 0; i < queries.length; i++ ) {
            const split = queries[i].split('=');
            if( split[0] === 'egressToken' ) {
                return split[1]
            }
        }
        return 'unknown'
    }

    get gc() {
        return this._gc
    }
    get gl() {
        return this._gl
    }
    get cc() {
        if( !(`${this._cameraIndex}` in this._cc) ) {
            this._cc[`${this._cameraIndex}`] = {}
        }
        return this._cc[`${this._cameraIndex}`]
    }
    get cs() {
        if( !(`${this._cameraIndex}` in this._cs) ) {
            this._cs[`${this._cameraIndex}`] = {}
        }
        return this._cs[this._cameraIndex]
    }
    get lc() {
        if( !(`${this._cameraIndex}` in this._lc) ) {
            this._lc[`${this._cameraIndex}`] = {}
        }
        return this._lc[this._cameraIndex]
    }
    get ls() {
        if( !(`${this._cameraIndex}` in this._ls) ) {
            this._ls[`${this._cameraIndex}`] = {}
        }
        return this._ls[this._cameraIndex]
    }

    _getState(_id, default_value = '') {
        return this._hass !== null && _id in this._hass.states ?
            this._hass.states[_id] : {
                state: default_value,
                attributes: {
                    friendly_name: 'unknown',
                    wired_only: false,
                    image_source: "unknown",
                    charging: false
                }
            };
    }

    updateStatuses() {

        // CAMERA
        const camera = this._getState(this.cc.id,'unknown');

        // Set the camera name now. We have to wait untik now to ensure `_hass`
        // is set and we can get to the camera state.
        if ( !this.cc.name ) {
            this.cc.name = this._config.name ? this._config.name : camera.attributes.friendly_name;
        }

        // Image changed? See if:
        //  - camera has changed state then do an update
        //  - camera has changed state and was taking a snapshot then queue up some updates
        //  - auth (base name) has changed then do an update
        //  - image source has changed then do an update
        if ( camera.state !== this.cs.state ) {
            this._log( `state-update: ${this.cs.state} --> ${camera.state}` )
            this.updateImageURL()
            if ( this.cs.state === 'taking snapshot' ) {
                this.cc.snapshotTimeouts.forEach( (seconds) => {
                    this.updateImageURLLater( seconds )
                })
            }
        }
        else if ( this._image_base !== camera.attributes.entity_picture ) {
            this._log( `auth-update: ${this._image_base} --> ${camera.attributes.entity_picture}` )
            this.updateImageURL()
        }
        else if ( this.cs.imageSource !== camera.attributes.image_source ) {
            this._log( `source-update: ${this.cs.imageSource} --> ${camera.attributes.image_source}` )
            this.updateImageURL()
        }

        // Save camera state.
        this.cs.state = camera.state
        this.cs.imageSource = camera.attributes.image_source
        this.cs.lastVideo = camera.attributes.last_video

        // FUNCTIONS
        if( this.cc.showPlay ) {
            this.cs.playState = 'state-on';
            if ( camera.state !== 'streaming' ) {
                this.cs.playText = this._i.image.start_stream
                this.cs.playIcon = 'mdi:play'
            } else {
                this.cs.playText = this._i.image.stop_stream
                this.cs.playIcon = 'mdi:stop'
            }
        }

        if( this.cc.showCameraOnOff ) {
            if ( this.cs.state === 'off' ) {
                this.cs.onOffState = 'state-on';
                this.cs.onOffText  = this._i.image.turn_camera_on
                this.cs.onOffIcon  = 'mdi:camera'
                this.cs.showCameraControls = false
            } else {
                this.cs.onOffState = '';
                this.cs.onOffText  = this._i.image.turn_camera_off
                this.cs.onOffIcon  = 'mdi:camera-off'
                this.cs.showCameraControls = true
            }
        } else {
            this.cs.showCameraControls = true
        }

        if( this.cc.showSnapshot ) {
            this.cs.snapshotState = '';
            this.cs.snapshotText  = this._i.image.take_a_snapshot
            this.cs.snapshotIcon  = 'mdi:camera'
        }

        // SENSORS
        if( this.cc.showBattery ) {
            if ( camera.attributes.wired_only ) {
                this.cs.batteryState = 'state-update';
                this.cs.batteryText  = this._i.status.plugged_in
                this.cs.batteryIcon  = 'power-plug';
            } else {
                const battery = this._getState(this.cc.batteryId, 0);
                const prefix = camera.attributes.charging ? 'battery-charging' : 'battery';
                this.cs.batteryState = battery.state < 25 ? 'state-warn' : ( battery.state < 15 ? 'state-error' : 'state-update' );
                this.cs.batteryText  = `${this._i.status.battery_strength}: ${battery.state}%`;
                this.cs.batteryIcon  = prefix + ( battery.state < 10 ? '-outline' :
                                                    ( battery.state > 90 ? '' : '-' + Math.round(battery.state/10) + '0' ) );
            }
        }

        if( this.cc.showSignal ) {
            const signal = this._getState(this.cc.signalId, 0);
            this.cs.signalText = `${this._i.status.signal_strength}: ${signal.state}`
            this.cs.signalIcon = signal.state === "0" ? 'mdi:wifi-outline' : 'mdi:wifi-strength-' + signal.state;
        }

        if( this.cc.showMotion ) {
            this.cs.motionState = this._getState(this.cc.motionId,'off').state === 'on' ? 'state-on' : '';
            this.cs.motionText  = `${this._i.status.motion}: ` +
                    ( this.cs.motionState !== '' ? this._i.status.detected : this._i.status.clear )
        }

        if( this.cc.showSound ) {
            this.cs.soundState = this._getState(this.cc.soundId,'off').state === 'on' ? 'state-on' : '';
            this.cs.soundText  = `${this._i.status.sound}: ` +
                    ( this.cs.soundState !== '' ? this._i.status.detected : this._i.status.clear )
        }

        // We always save this, used by library code to check for updates
        const captured = this._getState(this.cc.capturedTodayId, 0).state;
        const last = this._getState(this.cc.lastCaptureId, 0).state;
        this.cs.capturedText = `${this._i.status.captured}: ` + 
                ( captured === "0" ? this._i.status.captured_nothing : `${captured} ${this._i.status.captured_something} ${last}` );
        this.cs.capturedIcon  = 'mdi:file-video'
        this.cs.capturedState = captured !== "0" ? 'state-update' : ''

        // OPTIONAL DOORS
        if( this.cc.showDoor ) {
            const doorState = this._getState(this.cc.doorId, 'off');
            this.cs.doorState = doorState.state === 'on' ? 'state-on' : '';
            this.cs.doorText  = doorState.attributes.friendly_name + ': ' +
                    ( this.cs.doorState === '' ? this._i.status.door_closed : this._i.status.door_open )
            this.cs.doorIcon  = this.cs.doorState === '' ? 'mdi:door' : 'mdi:door-open';
        }
        if( this.cc.showDoor2 ) {
            const door2State = this._getState(this.cc.door2Id, 'off');
            this.cs.door2State = door2State.state === 'on' ? 'state-on' : '';
            this.cs.door2Text  = door2State.attributes.friendly_name + ': ' +
                    ( this.cs.door2State === '' ? this._i.status.door_closed : this._i.status.door_open )
            this.cs.door2Icon  = this.cs.door2State === '' ? 'mdi:door' : 'mdi:door-open';
        }

        if( this.cc.showDoorLock ) {
            const doorLockState = this._getState(this.cc.doorLockId, 'locked');
            this.cs.doorLockState = doorLockState.state === 'locked' ? 'state-on' : 'state-warn';
            this.cs.doorLockText  = doorLockState.attributes.friendly_name + ': ' +
                    ( this.cs.doorLockState === 'state-on' ? this._i.status.lock_locked : this._i.status.lock_unlocked )
            this.cs.doorLockIcon  = this.cs.doorLockState === 'state-on' ? 'mdi:lock' : 'mdi:lock-open';
        }
        if( this.cc.showDoor2Lock ) {
            const door2LockState = this._getState(this.cc.door2LockId, 'locked');
            this.cs.door2LockState = door2LockState.state === 'locked' ? 'state-on' : 'state-warn';
            this.cs.door2LockText  = door2LockState.attributes.friendly_name + ': ' + 
                    ( this.cs.door2LockState === 'state-on' ? this._i.status.lock_locked : this._i.status.lock_unlocked )
            this.cs.door2LockIcon  = this.cs.door2LockState === 'state-on' ? 'mdi:lock' : 'mdi:lock-open';
        }

        if( this.cc.showDoorBell ) {
            const doorBellState = this._getState(this.cc.doorBellId, 'off');
            this.cs.doorBellState = doorBellState.state === 'on' ? 'state-on' : '';
            this.cs.doorBellText  = doorBellState.attributes.friendly_name + ': ' +
                    ( this.cs.doorBellState === 'state-on' ?  this._i.status.doorbell_pressed : this._i.status.doorbell_idle )
            this.cs.doorBellIcon  = 'mdi:doorbell-video';
        }
        if( this.cc.showDoor2Bell ) {
            const door2BellState = this._getState(this.cc.door2BellId, 'off');
            this.cs.door2BellState = door2BellState.state === 'on' ? 'state-on' : '';
            this.cs.door2BellText  = door2BellState.attributes.friendly_name + ': ' +
                    ( this.cs.door2BellState === 'state-on' ?  this._i.status.doorbell_pressed : this._i.status.doorbell_idle )
            this.cs.door2BellIcon  = 'mdi:doorbell-video';
        }

        if( this.cc.showLight ) {
            const lightState = this._getState(this.cc.lightId, 'off');
            this.cs.lightState = lightState.state === 'on' ? 'state-on' : '';
            this.cs.lightText  = lightState.attributes.friendly_name + ': ' +
                    ( this.cs.lightState === 'state-on' ?   this._i.status.light_on : this._i.status.light_off )
            this.cs.lightIcon  = 'mdi:lightbulb';
        }
    }

    checkConfig() {

        if ( this._hass === null ) {
            return;
        }

        if ( !(this.cc.id in this._hass.states) ) {
            this.throwError( 'unknown camera' );
        }
        if ( this.cc.doorId && !(this.cc.doorId in this._hass.states) ) {
            this.throwError( 'unknown door' )
        }
        if ( this.cc.doorBellId && !(this.cc.doorBellId in this._hass.states) ) {
            this.throwError( 'unknown door bell' )
        }
        if ( this.cc.doorLockId && !(this.cc.doorLockId in this._hass.states) ) {
            this.throwError( 'unknown door lock' )
        }
        if ( this.cc.door2Id && !(this.cc.door2Id in this._hass.states) ) {
            this.throwError( 'unknown door (#2)' )
        }
        if ( this.cc.door2BellId && !(this.cc.door2BellId in this._hass.states) ) {
            this.throwError( 'unknown door bell (#2)' )
        }
        if ( this.cc.door2LockId && !(this.cc.door2LockId in this._hass.states) ) {
            this.throwError( 'unknown door lock (#2)' )
        }
    }

    getGlobalCameraConfig( config ) {
    }

    getGlobalLibraryConfig( config ) {
    }

    getCameraConfig( config ) {
    }

    getLibraryConfig( config ) {
    }

    setConfig(config) {

        // find camera
        let camera = ""
        if( config.entity ) {
            camera = config.entity.replace( 'camera.','' );
        }
        if( config.camera ) {
            camera = config.camera
        }
        if( camera === "" ) {
            this.throwError( 'missing a camera definition' )
            return
        }
        if( !config.show ) {
            this.throwError( 'missing show components' );
            return
        }

        // see if aarlo prefix, remove from custom names if not present
        let prefix = "";
        if ( camera.startsWith( 'aarlo_' ) ) {
            camera = camera.replace( 'aarlo_','' )
            prefix = "aarlo_"
        }
        if( config.prefix ) {
            prefix = config.prefix;
        }

        // save then check new config
        this._config = config
        this.checkConfig()

        // GLOBAL config
        // Language override?
        this.gc.lang = config.lang

        // aspect ratio
        this.gc.aspectRatio = config.aspect_ratio === 'square' ? '1x1' : '16x9';
        this.gc.aspectRatioMultiplier = config.aspect_ratio === 'square' ? 1 : 0.5625

        // logging?
        this.gc.log = config.logging ? config.logging : false

        // lovelace card size
        this.gc.cardSize = config.card_size ? parseInt(config.card_size) : 3

        // swipe threshold
        this.gc.swipeThreshold = config.swipe_threshold ? parseInt(config.swipe_threshold) : 150

        // TODO use proxy for defaults... read defaults as though a camera... or just keep simple
        // and copy the defaults and add camera specifics

        // PER-CAMERA config
        this._cameraIndex = 0

        // library config
        this.lc.onClick = config.library_click ? config.library_click : ''
        this.lc.sizes = config.library_sizes ? config.library_sizes : [ 3 ]
        this.lc.recordings = config.max_recordings ? parseInt(config.max_recordings) : 99
        this.lc.regions = config.library_regions ? config.library_regions : this.lc.sizes
        this.lc.colors = {
            "Animal"  : config.library_animal ? config.library_animal : 'orangered',
            "Vehicle" : config.library_vehicle ? config.library_vehicle : 'yellow',
            "Person"  : config.library_person ? config.library_person : 'lime'
        }
        this.ls.sizeIndex = 0
        this.ls.size = -1
        this.ls.gridCount = -1

        // on click
        this.cc.imageClick = config.image_click ? config.image_click : '';

        // snapshot updates
        this.cc.snapshotTimeouts = config.snapshot_retry ? config.snapshot_retry : [ 2, 5 ]

        // modal window multiplier
        this.cc.modalMultiplier = config.modal_multiplier ? parseFloat(config.modal_multiplier) : 0.8;

        // stream directly from Arlo
        this.cc.playDirectFromArlo = config.play_direct ? config.play_direct : false;

        // auto play
        this.cc.autoPlay = config.auto_play ? config.auto_play : false
        this.cs.autoPlay = this.cc.autoPlay
        this.cs.autoPlayTimer = null

        // camera and sensors
        this.cc.id              = config.camera_id ? config.camera_id : 'camera.' + prefix + camera;
        this.cc.motionId        = config.motion_id ? config.motion_id : 'binary_sensor.' + prefix + 'motion_' + camera;
        this.cc.soundId         = config.sound_id ? config.sound_id : 'binary_sensor.' + prefix + 'sound_' + camera;
        this.cc.batteryId       = config.battery_id ? config.battery_id : 'sensor.' + prefix + 'battery_level_' + camera;
        this.cc.signalId        = config.signal_id ? config.signal_id : 'sensor.' + prefix + 'signal_strength_' + camera;
        this.cc.capturedTodayId = config.capture_id ? config.capture_id : 'sensor.' + prefix + 'captured_today_' + camera;
        this.cc.lastCaptureId   = config.last_id ? config.last_id : 'sensor.' + prefix + 'last_' + camera;

        // door definition
        this.cc.doorId     = config.door ? config.door: null;
        this.cc.doorBellId = config.door_bell ? config.door_bell : null;
        this.cc.doorLockId = config.door_lock ? config.door_lock : null;

        // door2 definition
        this.cc.door2Id     = config.door2 ? config.door2: null;
        this.cc.door2BellId = config.door2_bell ? config.door2_bell : null;
        this.cc.door2LockId = config.door2_lock ? config.door2_lock : null;

        // light definition
        this.cc.lightId     = config.light ? config.light: null;

        // what are we hiding?
        const hide = this._config.hide || [];
        const show_title  = !hide.includes('title')
        const show_date   = !hide.includes('date')
        const show_status = !hide.includes('status')

        // ui configuration
        this.cc.showTopTitle     = config.top_title ? show_title : false
        this.cc.showTopDate      = config.top_date ? show_date : false
        this.cc.showTopStatus    = config.top_status ? show_status : false
        this.cc.showBottomTitle  = config.top_title ? false : show_title
        this.cc.showBottomDate   = config.top_date ? false : show_date
        this.cc.showBottomStatus = config.top_status ? false : show_status

        // what are we showing?
        const show = this._config.show || [];
        
        this.cc.showPlay        = show.includes('play')
        this.cc.showSnapshot    = show.includes('snapshot')
        this.cc.showCameraOnOff = show.includes('on_off')

        this.cc.showBattery    = show.includes('battery') || show.includes('battery_level')
        this.cc.showSignal     = show.includes('signal_strength')
        this.cc.showMotion     = show.includes('motion')
        this.cc.showSound      = show.includes('sound')
        this.cc.showCaptured   = show.includes('captured') || show.includes('captured_today')
        this.cc.showImageDate  = show.includes('image_date')

        this.cc.showDoor      = !!this.cc.doorId
        this.cc.showDoorLock  = !!this.cc.doorLockId
        this.cc.showDoorBell  = !!this.cc.doorBellId
        this.cc.showDoor2     = !!this.cc.door2Id
        this.cc.showDoor2Lock = !!this.cc.door2LockId
        this.cc.showDoor2Bell = !!this.cc.door2BellId

        this.cc.showLight      = !!this.cc.lightId
        this.cc.showLightLeft  =   config.light_left ? !!config.light_left : false;
        this.cc.showLightRight =  !this.cc.showLightLeft

        this.cc.showOthers = ( this.cc.showDoor || this.cc.showDoorLock || this.cc.showDoorBell ||
                                this.cc.showDoor2 || this.cc.showDoor2Lock || this.cc.showDoor2Bell ||
                                    this.cc.showLight )

        // web item id suffix
        //this.gc.idSuffix = this.cc.id.replaceAll('.','-').replaceAll('_','-')
        this.gc.idSuffix = this._replaceAll( this.cc.id,'.','-' )
        this.gc.idSuffix = this._replaceAll( this.gc.idSuffix,'_','-' )
    }

    getModalDimensions() {
        let width  = window.innerWidth * this.cc.modalMultiplier
        let height = window.innerHeight * this.cc.modalMultiplier
        const ratio = this.gc.aspectRatioMultiplier
        if( height / width > ratio ) {
            height = width * ratio
        } else if( height / width < ratio ) {
            width = height * (1/ratio)
        }
        this.cs.modalWidth = Math.round(width)
        this.cs.modalHeight = Math.round(height)

        let topOffset = window.pageYOffset
        if( topOffset !== 0 ) {
            this.cs.modalTop = Math.round( topOffset + ( (window.innerHeight - height) / 2 ) )
        } else {
            this.cs.modalTop = null
        }
    }

    repositionModal() {
        this.getModalDimensions()
        this._paddingTop( "modal-viewer", this.cs.modalTop )
    }

    setModalElementData() {
        this.getModalDimensions()
        this._paddingTop( "modal-viewer", this.cs.modalTop )
        this._widthHeight("modal-content", this.cs.modalWidth - 16, null, "important")
        this._widthHeight("modal-video-wrapper", this.cs.modalWidth, this.cs.modalHeight - 16)
        this._widthHeight("modal-video-background", this.cs.modalWidth, this.cs.modalHeight)
        this._widthHeight("modal-video-player", this.cs.modalWidth, this.cs.modalHeight)
        this._widthHeight("modal-stream-player", this.cs.modalWidth, this.cs.modalHeight)
 
        // window.onscroll = () => {
            // this.positionModal()
        // }
        // window.ontouchend = () => {
            // this.showVideoControls(2)
        // }
    }

    showModal( show = true ) {
        if( this._modalViewer ) {
            this.setModalElementData()
            this._element('modal-viewer').style.display =  show ? 'block' : 'none'
        }
    }

    hideModal() {
        if( this._modalViewer ) {
            this._element('modal-viewer').style.display = 'none'
        }
    }


    setupImageView() {
        this._show('top-bar-title', this.cc.showTopTitle )
        this._show('top-bar-date', this.cc.showTopDate && this.cc.showImageDate )
        this._show('top-bar-status', this.cc.showTopStatus )
        this._show('bottom-bar-title', this.cc.showBottomTitle )
        this._show('bottom-bar-camera', this.cs.showCameraControls )
        this._show('bottom-bar-date', this.cc.showBottomDate && this.cc.showImageDate )
        this._show('bottom-bar-externals', this.cc.showOthers )
        this._show('bottom-bar-status', this.cc.showBottomStatus )

        this._show('camera-on-off', this.cc.showCameraOnOff )
        this._show('camera-captured', this.cc.showCaptured )
        this._show('camera-light-left', this.cc.showLightLeft )

        this._show("externals-door", this.cc.showDoor )
        this._show("externals-door-lock", this.cc.showDoorLock )
        this._show("externals-door-bell", this.cc.showDoorBell )
        this._show("externals-door-2", this.cc.showDoor2 )
        this._show("externals-door-lock-2", this.cc.showDoor2Lock )
        this._show("externals-door-bell-2", this.cc.showDoor2Bell )
        this._show("externals-light", this.cc.showLightRight )

        this._set("top-bar-title", {text: this.cc.name})
        this._set("bottom-bar-title", {text: this.cc.name})
    }

    updateImageView() {

        // Nothing there yet...
        if( !this.isViewReady() ) {
            return
        }

        if( this._image !== '' ) {
            this.cs.imageDate     = '';
            this.cs.imageFullDate = this.cs.imageSource ? this.cs.imageSource : ''
            if( this.cs.imageFullDate.startsWith('capture/') ) { 
                this.cs.imageDate     = this.cs.imageFullDate.substr(8);
                this.cs.imageFullDate = `${this._i.image.automatic_capture} ${this.cs.imageDate}`
            } else if( this.cs.imageFullDate.startsWith('snapshot/') ) { 
                this.cs.imageDate     = this.cs.imageFullDate.substr(9);
                this.cs.imageFullDate = `${this._i.image.snapshot_capture} ${this.cs.imageDate}`
            }
        } else {
            this.cs.imageFullDate = ''
            this.cs.imageDate = ''
        }

        this._set("image-viewer", {title: this.cs.imageFullDate, alt: this.cs.imageFullDate, src: this._image})

        this._set("top-bar-date", {title: this.cs.imageFullDate, text: this.cs.imageDate})
        this._set("top-bar-status", {text: this.cs.state })
        this._set("bottom-bar-date", {title: this.cs.imageFullDate, text: this.cs.imageDate})
        this._set("bottom-bar-date", {text: this.cs.imageDate})
        this._set("bottom-bar-status", {text: this.cs.state})

        this._set ("camera-on-off", {title: this.cs.onOffText, icon: this.cs.onOffIcon, state: this.cs.onOffState})
        this._set ("camera-motion", {title: this.cs.motionText, icon: "mdi:run-fast", state: this.cs.motionState})
        this._show('camera-motion', this.cc.showMotion && this.cs.showCameraControls )
        this._set ("camera-sound", {title: this.cs.soundText, icon: "mdi:ear-hearing", state: this.cs.soundState})
        this._show('camera-sound', this.cc.showSound && this.cs.showCameraControls )
        this._set ("camera-captured", {title: this.cs.capturedText, icon: this.cs.capturedIcon, state: this.cs.capturedState})
        this._set ("camera-play", {title: this.cs.playText, icon: this.cs.playIcon, state: this.cs.playState})
        this._show('camera-play', this.cc.showPlay && this.cs.showCameraControls )
        this._set ("camera-snapshot", {title: this.cs.snapshotText, icon: this.cs.snapshotIcon, state: this.cs.snapshotState})
        this._show('camera-snapshot', this.cc.showSnapshot && this.cs.showCameraControls )
        this._set ("camera-battery", {title: this.cs.batteryText, icon: `mdi:${this.cs.batteryIcon}`, state: this.cs.batteryState})
        this._show('camera-battery', this.cc.showBattery && this.cs.showCameraControls )
        this._set ("camera-wifi-signal", {title: this.cs.signalText, icon: this.cs.signalIcon, state: 'state-update'})
        this._show('camera-wifi-signal', this.cc.showSignal && this.cs.showCameraControls )
        this._set ("camera-light-left", {title: this.cs.lightText, icon: this.cs.lightIcon, state: this.cs.lightState})

        this._set("externals-door", {title: this.cs.doorText, icon: this.cs.doorIcon, state: this.cs.doorState})
        this._set("externals-door-bell", {title: this.cs.doorBellText, icon: this.cs.doorBellIcon, state: this.cs.doorBellState})
        this._set("externals-door-lock", {title: this.cs.doorLockText, icon: this.cs.doorLockIcon, state: this.cs.doorLockState})
        this._set("externals-door-2", {title: this.cs.door2Text, icon: this.cs.door2Icon, state: this.cs.door2State})
        this._set("externals-door-bell-2", {title: this.cs.door2BellText, icon: this.cs.door2BellIcon, state: this.cs.door2BellState})
        this._set("externals-door-lock-2", {title: this.cs.door2LockText, icon: this.cs.door2LockIcon, state: this.cs.door2LockState})
        this._set("externals-light", {title: this.cs.lightText, icon: this.cs.lightIcon, state: this.cs.lightState})
    }

    /**
     * Generate a new image URL.
     *
     * This is done when Arlo changes the image or Home Assistance changes
     * the authentication token. We always add the current time to the end to
     * force the browser to reload.
     *
     * It makes no attempt to reload the image.
     */
    updateImageURL() {
        const camera = this._getState(this.cc.id,'unknown');
        this._image_base = camera.attributes.entity_picture
        this._image = camera.attributes.entity_picture + "&t=" + new Date().getTime()
    }

    updateImageURLLater(seconds = 2) {
        setTimeout(() => {
            this.updateImageURL()
            this.updateImageView()
        }, seconds * 1000);
    }

    showImageView() {
        if( this._image !== '' ) {
            this._show("image-viewer")
            this._hide("broken-image")
        } else {
            this._show("broken-image")
            this._hide("image-viewer")
        }
        this._show('top-bar', this.cc.showTopTitle || this.cc.showTopDate || this.cc.showTopStatus )
        this._show('bottom-bar')
        this.hideVideoView()
        this.hideStreamView()
        this.hideLibraryView()
        this.hideModal()
    }

    hideImageView() {
        this._hide("image-viewer")
        this._hide("broken-image")
        this._hide('top-bar')
        this._hide('bottom-bar')
    }

    setupLibraryView() {
        this._show("library-control-first" )
        this._show("library-control-previous" )
        this._show("library-control-next" )
        this._show("library-control-last" )
        this._show('library-control-resize',this.lc.sizes.length > 1 )
        this._set("library-control-resize",{ state: "on"} )
        this._set("library-control-close",{ state: "on"} )

        // rudementary swipe support
        let viewer = this._element("library-viewer")
        viewer.addEventListener('touchstart', (e) => {
            this.ls.xDown = e.touches[0].clientX
            this.ls.xUp = null
        }, { passive: true })
        viewer.addEventListener('touchmove', (e) => {
            this.ls.xUp = e.touches[0].clientX
        }, { passive: true })
        viewer.addEventListener('touchend', () => {
            if( this.ls.xDown && this.ls.xUp ) {
                const xDiff = this.ls.xDown - this.ls.xUp;
                if( xDiff > this.gc.swipeThreshold ) {
                    this.nextLibraryPage()
                } else if( xDiff < (0 - this.gc.swipeThreshold) ) {
                    this.previousLibraryPage()
                }
            }
        }, { passive: true })

        // set state
        this.ls.offset = -1
    }

    _updateLibraryHTML() {

        // update library state to reflect the new layout
        this.ls.size = this.lc.sizes[this.ls.sizeIndex]
        this.ls.gridCount = this.ls.size * this.ls.size

        let grid = document.createElement("div")
        grid.style.display = "grid"
        grid.style['grid-template-columns'] = `repeat(${this.ls.size},1fr)`
        grid.style['grid-template-rows'] = `repeat(${this.ls.size},1fr)`
        grid.style['grid-gap'] = '1px'
        grid.style.padding= '2px'

        for( let i = 0; i < this.ls.size * this.ls.size; ++i ) {

            let img = document.createElement("img")
            img.id = this._id(`library-${i}`)
            img.style.width = "100%"
            img.style.height = "100%"
            img.style.objectFit = "cover"
            img.addEventListener("click", () => { this.playLibraryVideo(i) } )

            let box = document.createElement("div")
            box.id = this._id(`library-box-${i}`)
            box.style.width = "100%"
            box.style.height = "100%"
            box.style.position = "absolute"
            box.style.top = "0"
            img.addEventListener("click", () => { this.playLibraryVideo(i) } )

            const column = Math.floor((i % this.ls.size) + 1)
            const row = Math.floor((i / this.ls.size) + 1)
            let div = document.createElement("div")
            div.style.position= 'relative'
            div.style.gridColumn = `${column}`
            div.style.gridRow    = `${row}`
            div.appendChild(img)
            div.appendChild(box)
            grid.appendChild(div)
        }

        // replace.
        let container = this._element('library-viewer')
        container.innerHTML = ''
        container.appendChild(grid)
    }

    _updateLibraryView() {
   
        // Massage offset so it fits in library.
        if( this.ls.offset + this.ls.gridCount > this.ls.videos.length ) {
            this.ls.offset = Math.max(this.ls.videos.length - this.ls.gridCount, 0)
        } else if( this.ls.offset < 0 ) {
            this.ls.offset = 0
        }

        let i = 0;
        let j= this.ls.offset;
        const show_triggers = this.lc.regions.includes(this.ls.size)
        const last = Math.min(j + this.ls.gridCount, this.ls.videos.length)
        for( ; j < last; i++, j++ ) {
            const id = `library-${i}`
            const bid = `library-box-${i}`
            const video = this.ls.videos[j]
            let captured_text = `${this._i.library.captured}: ${video.created_at_pretty}`
            if ( video.trigger && video.trigger !== '' ) {
                captured_text += ` (${this._i.trigger[video.trigger.toLowerCase()]})`
            }
            this._set( id,{title: captured_text, alt: captured_text, src: video.thumbnail} )
            this._show( id )

            // highlight is on at this level and we have something?
            if( show_triggers && video.trigger !== null ) {
                const coords = video.trigger_region.split(",")

                let box = this._element( bid )
                box.style.left = `${parseFloat(coords[0]) * 100}%`
                box.style.top = `${parseFloat(coords[1]) * 100}%`
                box.style.width = `${(parseFloat(coords[2]) - parseFloat(coords[0])) * 100}%`
                box.style.height = `${(parseFloat(coords[3]) - parseFloat(coords[1])) * 100}%`
                box.style.borderStyle = "solid"
                box.style.borderWidth = "thin"
                box.style.borderColor = video.trigger in this.lc.colors ?
                                               this.lc.colors[video.trigger] : "cyan"
                this._set( bid,{title: captured_text, alt: captured_text } )
                this._show( bid )
            } else {
                this._hide( bid )
            }

        }
        for( ; i < this.ls.gridCount; i++ ) {
            this._hide(`library-${i}`)
        }

        this.ls.lastOffset = this.ls.offset

        const not_at_start = this.ls.offset !== 0
        this._set( "library-control-first",{
            title: not_at_start ? this._i.library.first_page : "",
            icon: 'mdi:page-first',
            state: not_at_start ? "on" : "off"
        })
        this._set( "library-control-previous",{
            title: not_at_start ? this._i.library.previous_page : "",
            icon: 'mdi:chevron-left',
            state: not_at_start ? "on" : "off"
        })

        this._set( "library-control-resize",{ title: this._i.library.next_size, icon: 'mdi:resize', state: "on" })
        this._set( "library-control-close",{ title: this._i.library.close, icon: 'mdi:close', state: "on" })

        const not_at_end = this.ls.offset + this.ls.gridCount < this.ls.videos.length
        this._set( "library-control-next",{
            title: not_at_end ? this._i.library.next_page : "",
            icon: 'mdi:chevron-right',
            state: not_at_end ? "on" : "off"
        })
        this._set( "library-control-last",{
            title: not_at_end ? this._i.library.last_page : "",
            icon: 'mdi:page-last',
            state: not_at_end ? "on" : "off"
        })
    }

    updateLibraryView() {

        // Nothing there yet...
        if( !this.isViewReady() ) {
            return
        }

        // Resized? Rebuild grid and force reload of images.
        if ( this.ls.size !== this.lc.sizes[this.ls.sizeIndex] ) {
            this._updateLibraryHTML()
            this.ls.lastOffset = -1
        }

        // If no library then load it.
        if ( !this.ls.videos ) {
            this._log( `library-load` )
            this.asyncLoadLibrary().then( () => {
                this._updateLibraryView()
            })
 
        // If last video changed then reload library.
        } else if ( this.ls.lastVideo !== this.cs.lastVideo ) {
            this._log( `library-video-update: ${this.ls.lastVideo} --> ${this.cs.lastVideo}` )
            this.ls.lastVideo = this.cs.lastVideo
            this.asyncLoadLibrary().then( () => {
                this._updateLibraryView()
            })

        // If offset has changed then reload images
        } else if ( this.ls.lastOffset !== this.ls.offset ) {
            this._log( `library-view-update` )
            this._updateLibraryView()
        }
    }

    showLibraryView() {
        this._show("library-viewer")
        this._show("library-controls")
        this.hideVideoView()
        this.hideStreamView()
        this.hideImageView()
        this.hideModal()
    }

    hideLibraryView() {
        this._hide("library-viewer")
        this._hide("library-controls")
    }

    setupVideoView() {
        this._show("video-stop")
        this._show("video-full-screen")
        this._show("video-door-lock", this.cc.showDoorLock )
        this._show("video-light-on", this.cc.showLight )
        this._show("modal-video-stop")
        this._show("modal-video-full-screen")
        this._show("modal-video-door-lock", this.cc.showDoorLock )
        this._show("modal-video-light-on", this.cc.showLight )

        this._set ("video-stop", {title: this._i.video.stop, icon: "mdi:stop"} )
        this._set ("video-play", {title: this._i.video.play, icon: "mdi:play"} )
        this._set ("video-pause", {title: this._i.video.pause, icon: "mdi:pause"} )
        this._set ("video-full-screen", {title: this._i.video.fullscreen, icon: "mdi:fullscreen"} )

        this._set ("modal-video-stop", {title: this._i.video.stop, icon: "mdi:stop"} )
        this._set ("modal-video-play", {title: this._i.video.play, icon: "mdi:play"} )
        this._set ("modal-video-pause", {title: this._i.video.pause, icon: "mdi:pause"} )
        this._set ("modal-video-full-screen", {title: this._i.video.fullscreen, icon: "mdi:fullscreen"} )
    }

    updateVideoView( state = '' ) {

        // Nothing there yet...
        if( !this.isViewReady() ) {
            return
        }

        if( state === 'starting' ) {
            this._mset( 'video-player',{src: this._video, poster: this._videoPoster} )
            this._mshow("video-seek")
            this._videoState = 'playing'
            this.setUpSeekBar();
            this.showVideoControls(4);
        } else if( state !== '' ) {
            this._videoState = state
        }

        this._mshow("video-play", this._videoState === 'paused')
        this._mshow("video-pause", this._videoState === 'playing')
    }

    showVideoView() {
        this.hideStreamView()
        this._mshow("video-player")
        this._mshow("video-controls")
        this.showModal()
        this.hideLibraryView()
        this.hideImageView()
    }

    hideVideoView() {
        this._mhide("video-player")
        this._mhide("video-controls")
        this.hideModal()
    }

    showVideo() {
        this.updateVideoView('starting')
        this.showVideoView()
    }
 
    setMPEGStreamElementData() {
        const video = this._melement('stream-player')
        const et = this._findEgressToken( this._stream );

        this._dash = dashjs.MediaPlayer().create();
        this._dash.extend("RequestModifier", () => {
            return {
                modifyRequestHeader: function (xhr) {
                    xhr.setRequestHeader('Egress-Token',et);
                    return xhr;
                }
            };
        }, true);
        this._dash.initialize( video, this._stream, true )
    }

    setHLSStreamElementData() {
        const video = this._melement('stream-player')
        if (Hls.isSupported()) {
            this._hls = new Hls();
            this._hls.attachMedia(video);
            this._hls.on(Hls.Events.MEDIA_ATTACHED, () => {
                this._hls.loadSource(this._stream);
                this._hls.on(Hls.Events.MANIFEST_PARSED, () => {
                    video.play();
                });
            })
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = this._stream;
            video.addEventListener('loadedmetadata', () => {
                video.play();
            });
        }
    }

    // Mostly handled in setupVideoView
    setupStreamView() {
    }

    updateStreamView( state = '' ) {

        // Autostart?
        if ( state === '' && this._stream === null ) {
            if( this.cs.autoPlay && this.cs.autoPlayTimer === null ) {
                this.cs.autoPlayTimer = setTimeout( () => {
                    this.playStream( false )
                },5 * 1000 )
            }
            return
        }

        // Nothing there yet...
        if( !this.isViewReady() ) {
            return
        }

        if ( state === 'starting' ) {
            if ( this.cc.playDirectFromArlo ) {
                this.setMPEGStreamElementData()
            } else {
                this.setHLSStreamElementData()
            }
            this._mhide("video-play")
            this._mhide("video-pause")
            this._mhide("video-seek")
            this.showVideoControls(4);
        }

        this._mset( "video-door-lock", {title: this.cs.doorLockText, icon: this.cs.doorLockIcon, state: this.cs.doorLockState} )
        this._mset( "video-light-on", {title: this.cs.lightText, icon: this.cs.lightIcon, state: this.cs.lightState} )
    }

    showStreamView() {
        this.hideVideoView()
        this._mshow("stream-player")
        this._mshow("video-controls")
        this.showModal()
        this.hideLibraryView()
        this.hideImageView()
    }

    hideStreamView() {
        this._mhide("stream-player")
        this._mhide("video-controls")
        this.hideModal()
    }

    showStream() {
        this.updateStreamView('starting')
        this.showStreamView()
    }

    isViewReady() {
        return this._element('image-viewer') !== null 
    }

    updateView() {
        this.updateStatuses()
        this.updateImageView()
        this.updateLibraryView()
        this.updateVideoView()
        this.updateStreamView()
    }

    initialView( lang = null ) {

        // No language, pick one.
        if ( lang === null ) {
            console.log( 'setting default language' )
            lang = this.gc.lang ? this.gc.lang : this._hass.language
        }

        // Load language pack. Try less specific before reverting to en.
        // testing: import(`https://twrecked.github.io/lang/${lang}.js?t=${lang_date}`)
        if( !lang.startsWith(this._lang) ) {
            console.log( `importing ${lang} language` )
            import(`https://cdn.jsdelivr.net/gh/twrecked/lovelace-hass-aarlo@master/lang/${lang}.js`)
                .then( module => {
                    this._lang = lang
                    this._i = module.messages
                    this.initialView( lang )
                }, (_reason) => {
                    const lang_pieces = lang.split('-')
                    if( lang_pieces.length > 1 ) {
                        this.initialView( lang_pieces[0] )
                    } else {
                        this.initialView( "en" )
                    }
                })
            return
        }

        // Now wait for the elements to be added to the shadown DOM.
        if( !this.isViewReady() ) {
            console.log( 'waiting for an element ' )
            setTimeout( () => {
                this.initialView( lang )
            }, 100);
            return
        }

        // Set initial state
        this._ready = true
        this.updateStatuses()

        // Install the static stuff.
        this.setupImageView()
        this.setupLibraryView()
        this.setupVideoView()
        this.setupStreamView()

        // And go...
        this.updateImageView()
        this.updateLibraryView()
        this.showImageView()
    }

    resetView() {
        if ( this.ls.showing ) {
            this.showLibraryView()
        } else {
            this.showImageView()
        }
    }

    async wsLoadLibrary(at_most ) {
        try {
            const library = await this._hass.callWS({
                type: "aarlo_library",
                entity_id: this.cc.id,
                at_most: at_most,
            });
            return ( library.videos.length > 0 ) ? library.videos : null;
        } catch (err) {
            return null
        }
    }

    async wsStartStream() {
        try {
            return await this._hass.callWS({
                type: this.cc.playDirectFromArlo ? "aarlo_stream_url" : "camera/stream",
                entity_id: this.cc.id,
            })
        } catch (err) {
            return null
        }
    }

    async wsStopStream() {
        try {
            return await this._hass.callWS({
                type: "aarlo_stop_activity",
                entity_id: this.cc.id,
            })
        } catch (err) {
            return null
        }
    }

    async asyncWSUpdateSnapshot() {
        try {
            return await this._hass.callWS({
                type: "aarlo_request_snapshot",
                entity_id: this.cc.id
            })
        } catch (err) {
            return null
        }
    }

    wsUpdateSnapshot() {
        this.asyncWSUpdateSnapshot().then()
    }

    async asyncLoadLatestVideo(modal) {
        const video = await this.wsLoadLibrary(1);
        if ( video ) {
            this._modalViewer = modal
            this._video       = video[0].url;
            this._videoPoster = video[0].thumbnail;
        } else {
            this._modalViewer = false;
            this._video       = null;
            this._videoPoster = null;
        }
    }

    playLatestVideo(modal) {
        const camera = this._getState(this.cc.id,'unknown');
        this._modalViewer = modal
        this._video       = camera.attributes.last_video
        this._videoPoster = camera.attributes.last_thumbnail
        this.showVideo()
        // TODO maybe resurrect this one...
        // if ( this._video === null ) {
            // this.asyncLoadLatestVideo(modal).then( () => {
                // this.showVideo()
            // })
        // }
    }

    startVideo() {
        if( this._video ) {
            this._melement( 'video-player' ).play()
        }
    }

    stopVideo() {
        if ( this._video ) {
            this._melement('video-player' ).pause()
            this.hideModal()
            this.resetView()
            this._video = null
            this._videoState = ''
        }
    }

    async asyncPlayStream( modal ) {
        const stream = await this.wsStartStream();
        if (stream) {
            this._modalViewer  = modal;
            this._stream       = stream.url;
            this._streamPoster = this._image;
        } else {
            this._modalViewer  = false;
            this._stream       = null;
            this._streamPoster = null;
        }
    }

    playStream( modal ) {
        this.cs.autoPlayTimer = null
        if ( this._stream === null ) {
            if( this.cc.autoPlay ) {
                this.cs.autoPlay = this.cc.autoPlay
            }
            this.asyncPlayStream(modal).then( () => {
                this.showStream()
            })
        }
    }

    async asyncStopStream() {
        if( this._stream ) {
            await this.wsStopStream();
        }
    }

    stopStream() {
        this.resetView()
        this._melement('stream-player' ).pause()
        this.asyncStopStream().then( () => {
            this.cs.autoPlay = false
            this._stream = null;
            if(this._hls) {
                this._hls.stopLoad();
                this._hls.destroy();
                this._hls = null
            }
            if(this._dash) {
                this._dash.reset();
                this._dash = null;
            }
        })
    }

    showOrStopStream() {
        const camera = this._getState(this.cc.id,'unknown');
        if ( camera.state === 'streaming' ) {
            this.stopStream()
        } else {
            this.playStream()
        }
    }

    async asyncLoadLibrary() {
        this._video = null;
        this.ls.videos = await this.wsLoadLibrary(this.lc.recordings);
        // this.ls.offset = 0
    }

    openLibrary() {
        this.ls.showing = true
        this.getModalDimensions()
        this.updateLibraryView()
        this.showLibraryView()
    }

    playLibraryVideo(index) {
        index += this.ls.offset;
        if (this.ls.videos && index < this.ls.videos.length) {
            this._modalViewer = this.lc.onClick === 'modal'
            this._video       = this.ls.videos[index].url;
            this._videoPoster = this.ls.videos[index].thumbnail;
            this.showVideo()
        } 
    }

    firstLibraryPage() {
        this.ls.offset = 0
        this.updateLibraryView()
    }

    previousLibraryPage() {
        this.ls.offset = Math.max(this.ls.offset - this.ls.gridCount, 0)
        this.updateLibraryView()
    }

    nextLibraryPage() {
        const last = Math.max(this.ls.videos.length - this.ls.gridCount, 0)
        this.ls.offset = Math.min(this.ls.offset + this.ls.gridCount, last)
        this.updateLibraryView()
    }

    lastLibraryPage() {
        this.ls.offset = Math.max(this.ls.videos.length - this.ls.gridCount, 0)
        this.updateLibraryView()
    }

    resizeLibrary() {
        this.ls.sizeIndex += 1
        if( this.ls.sizeIndex === this.lc.sizes.length ) {
            this.ls.sizeIndex = 0
        }
        this.updateLibraryView()
    }

    closeLibrary() {
        this.ls.showing = false
        this.stopVideo()
        this.showImageView()
    }

    clickImage() {
        if ( this.cc.imageClick === 'modal-play' ) {
            this.playStream(true)
        } else if ( this.cc.imageClick === 'play' ) {
            this.playStream(false)
        } else if ( this.cc.imageClick === 'modal-last' ) {
            this.playLatestVideo(true)
        } else {
            this.playLatestVideo(false)
        }
    }

    clickVideo() {
        if ( this._misHidden("video-controls") ) {
            this.showVideoControls(2)
        } else {
            this.hideVideoControls();
        }
    }

    mouseOverVideo() {
        this.showVideoControls(2)
    }

    controlStopVideoOrStream() {
        this.stopVideo()
        this.stopStream()
    }

    controlPauseVideo(  ) {
        this._melement( 'video-player' ).pause()
        this.updateVideoView('paused')
    }

    controlPlayVideo( ) {
        this.updateVideoView('playing')
        this._melement( 'video-player' ).play()
    }

    controlFullScreen() {
        let video = this._melement( this._stream ? 'stream-player' : 'video-player' )
        if (video.requestFullscreen) {
            video.requestFullscreen().then()
        } else if (video.mozRequestFullScreen) {
            video.mozRequestFullScreen(); // Firefox
        } else if (video.webkitRequestFullscreen) {
            video.webkitRequestFullscreen(); // Chrome and Safari
        }
    }

    toggleCamera( ) {
        if ( this.cs.state === 'off' ) {
            this._hass.callService( 'camera','turn_on', { entity_id: this.cc.id } )
        } else {
            this._hass.callService( 'camera','turn_off', { entity_id: this.cc.id } )
        }
    }

    toggleLock( id ) {
        if ( this._getState(id,'locked').state === 'locked' ) {
            this._hass.callService( 'lock','unlock', { entity_id:id } )
        } else {
            this._hass.callService( 'lock','lock', { entity_id:id } )
        }
    }

    toggleLight( id ) {
        if ( this._getState(id,'on').state === 'on' ) {
            this._hass.callService( 'light','turn_off', { entity_id:id } )
        } else {
            this._hass.callService( 'light','turn_on', { entity_id:id } )
        }
    }

    setUpSeekBar() {
        let video = this._melement('video-player')
        let seekBar = this._melement('video-seek')

        video.addEventListener( "timeupdate", () => {
            seekBar.value = (100 / video.duration) * video.currentTime;
        });
        seekBar.addEventListener( "change", () => {
            video.currentTime = video.duration * (seekBar.value / 100);
        });
        seekBar.addEventListener( "mousedown", () => {
            this.showVideoControls(0);
            video.pause();
        });
        seekBar.addEventListener( "mouseup", () => {
            video.play();
            this.hideVideoControlsLater()
        });
    }
  
    showVideoControls(seconds = 0) {
        this._mshow("video-controls")
        this.hideVideoControlsCancel();
        if (seconds !== 0) {
            this.hideVideoControlsLater(seconds);
        }
    }

    hideVideoControls() {
        this.hideVideoControlsCancel();
        this._mhide("video-controls")
    }

    hideVideoControlsLater(seconds = 2) {
        this.hideVideoControlsCancel();
        this.cs.controlTimeout = setTimeout(() => {
            this.cs.controlTimeout = null;
            this.hideVideoControls()
        }, seconds * 1000);
    }

    hideVideoControlsCancel() {
        if ( this.cs.controlTimeout !== null ) {
            clearTimeout( this.cs.controlTimeout );
            this.cs.controlTimeout = null
        }
    }

}

// Bring in our custom scripts
const scripts = [
    "https://cdn.jsdelivr.net/npm/hls.js@latest",
    "https://cdn.dashjs.org/v3.1.1/dash.all.min.js",
]
function load_script( number ) {
    if ( number < scripts.length ) {
        const script = document.createElement("script")
        script.src = scripts[ number ]
        script.onload = () => {
            load_script( number + 1 )
        }
        document.head.appendChild(script)
    } else {
        customElements.define('aarlo-glance', AarloGlance)
    }
}
load_script( 0 )

// vim: set expandtab:ts=4:sw=4
