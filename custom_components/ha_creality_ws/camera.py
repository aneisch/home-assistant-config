"""Camera platform for Creality 3D printers.

This module provides camera entities for Creality 3D printers, supporting both
MJPEG streams (K1 family) and WebRTC streams (K2 family) with automatic detection.

For WebRTC cameras, this integration uses Home Assistant's built-in go2rtc service
to handle WebRTC streaming, providing native WebRTC support without requiring
additional HACS integrations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiohttp import ClientError, web  # type: ignore[assignment]
from homeassistant.core import HomeAssistant, callback  # type: ignore[assignment]
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore[assignment]

_LOGGER = logging.getLogger(__name__)

# Import go2rtc client library
try:
    from go2rtc_client import Go2RtcRestClient, WebRTCSdpOffer
    from go2rtc_client.exceptions import Go2RtcClientError
    GO2RTC_CLIENT_AVAILABLE = True
except ImportError:
    GO2RTC_CLIENT_AVAILABLE = False
    _LOGGER.warning("go2rtc-client library not available, WebRTC cameras will not work")

# Import HA's go2rtc component
try:
    from homeassistant.components.go2rtc import DOMAIN as GO2RTC_DOMAIN
    GO2RTC_COMPONENT_AVAILABLE = True
except ImportError:
    GO2RTC_DOMAIN = "go2rtc"
    GO2RTC_COMPONENT_AVAILABLE = False

# Import camera components with compatibility for older Home Assistant versions
try:
    from homeassistant.components.camera import (
        Camera,
        CameraEntityFeature,  # type: ignore[attr-defined]
    )
except ImportError:  # compatibility with older cores
    from homeassistant.components.camera import Camera  # type: ignore[assignment]
    try:
        from homeassistant.components.camera import CameraEntityFeature  # type: ignore[misc]
    except ImportError:  # very old cores
        CameraEntityFeature = None  # type: ignore[assignment]

from .const import (
    DOMAIN, 
    MJPEG_URL_TEMPLATE, 
    WEBRTC_URL_TEMPLATE,
    CONF_GO2RTC_URL,
    CONF_GO2RTC_PORT,
)
from .entity import KEntity



class _FeatureMask(int):
    """Custom feature mask that supports the 'in' operator.
    
    This class extends int to provide compatibility with Home Assistant's
    camera feature detection system while supporting the 'in' operator
    for feature checking.
    """
    
    def __contains__(self, feature):
        """Check if a feature is supported by this camera."""
        return bool(self & feature)


class _BaseCamera(KEntity, Camera):
    """Base camera class with common functionality and fallback image support.
    
    This class provides common camera functionality including:
    - Fallback image handling for when the camera is unavailable
    - JPEG validation utilities
    - Common error handling patterns
    """

    # Tiny 1x1 white JPEG as last-resort fallback (valid JFIF with proper quantization tables)
    # This ensures we always have a valid image to return even when the camera is unavailable
    _TINY_JPEG = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
        b"\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xd2\xcf \xff\xd9"
    )

    def __init__(self, coordinator, name: str, unique_suffix: str) -> None:
        """Initialize the base camera.
        
        Args:
            coordinator: The printer coordinator
            name: Display name for the camera
            unique_suffix: Unique suffix for the entity ID
        """
        KEntity.__init__(self, coordinator, name, unique_suffix)
        Camera.__init__(self)
        self._last_frame: bytes | None = None

    async def _fallback_image(self) -> bytes:
        """Return a fallback image when the camera is unavailable.
        
        Returns the last successfully captured frame, or a tiny white JPEG
        if no frame has been captured yet.
        
        Returns:
            bytes: JPEG image data
        """
        return self._last_frame or self._TINY_JPEG


class CrealityMjpegCamera(_BaseCamera):
    """MJPEG camera for Creality K1 family printers.
    
    This camera handles MJPEG streams from Creality K1 family printers,
    providing both static image capture and live streaming capabilities.
    
    Features:
    - Automatic MJPEG stream detection and parsing
    - Fallback image handling when printer is offline
    - Live streaming support via handle_async_mjpeg_stream
    - JPEG validation and error recovery
    """

    def __init__(self, coordinator, url: str) -> None:
        """Initialize the MJPEG camera.
        
        Args:
            coordinator: The printer coordinator
            url: MJPEG stream URL from the printer
        """
        super().__init__(coordinator, "Printer Camera", "camera")
        self._url = url
        # Snapshot throttling to avoid repeatedly opening MJPEG streams
        self._last_snapshot_ts: float = 0.0
        self._snapshot_min_interval: float = 1.0  # seconds
        self._snapshot_lock = asyncio.Lock()
        _LOGGER.debug("ha_creality_ws: MJPEG camera initialized with URL: %s", url)

    def _is_valid_jpeg(self, data: bytes) -> bool:
        """Validate JPEG image data.
        
        Args:
            data: Raw image data to validate
            
        Returns:
            bool: True if the data is a valid JPEG image
        """
        if not data or len(data) < 20:
            return False
        return data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")

    async def _grab_snapshot_from_mjpeg(self, timeout: float = 5.0) -> bytes | None:
        """Extract a single JPEG frame from the MJPEG stream.
        
        This method opens the MJPEG stream and extracts the first complete
        JPEG frame, which can be used as a static image. This works even
        if the printer doesn't have a dedicated snapshot endpoint.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            bytes | None: JPEG image data, or None if extraction failed
        """
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(self._url, timeout=timeout) as resp:
                if resp.status != 200:
                    return None
                buf = bytearray()
                in_frame = False
                async for chunk in resp.content.iter_chunked(8192):
                    if not in_frame:
                        i = chunk.find(b"\xff\xd8")  # SOI
                        if i != -1:
                            in_frame = True
                            buf.extend(chunk[i:])
                        continue
                    buf.extend(chunk)
                    # Search EOI near the end to avoid O(n^2)
                    tail_start = max(0, len(buf) - 8192)
                    j = buf.find(b"\xff\xd9", tail_start)  # EOI
                    if j != -1:
                        return bytes(buf[: j + 2])
        except (asyncio.CancelledError, ClientError, asyncio.TimeoutError):
            return None
        except Exception:  # pragma: no cover - defensive
            _LOGGER.exception("ha_creality_ws: unexpected error grabbing MJPEG snapshot")
            return None
        return None

    async def async_camera_image(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> bytes | None:
        """Return a single camera image.
        
        This method provides static image capture for the camera entity.
        It attempts to grab a fresh frame from the MJPEG stream when the
        printer is powered, falling back to cached or default images when
        the printer is offline or unavailable.
        
        Args:
            width: Requested image width (not used for MJPEG)
            height: Requested image height (not used for MJPEG)
            
        Returns:
            bytes | None: JPEG image data
        """
        # Validate width/height parameters (MJPEG doesn't support scaling)
        if not width or width <= 0:
            width = None
        if not height or height <= 0:
            height = None

        frame: bytes | None = None

        # Respect snapshot throttle and cached frame
        now = asyncio.get_running_loop().time()
        if self._last_frame and (now - self._last_snapshot_ts) < self._snapshot_min_interval:
            return self._last_frame

        # Only try grabbing a fresh frame when the printer is powered
        if not self.coordinator.power_is_off():
            async with self._snapshot_lock:
                # Check throttle again inside the lock
                now = asyncio.get_running_loop().time()
                if self._last_frame and (now - self._last_snapshot_ts) < self._snapshot_min_interval:
                    return self._last_frame
                try:
                    frame = await self._grab_snapshot_from_mjpeg(timeout=5.0)
                except Exception:  # pragma: no cover - defensive
                    _LOGGER.exception("ha_creality_ws: unexpected error while fetching MJPEG snapshot")
                    frame = None

                # Validate and cache the frame if it's valid
                if frame and self._is_valid_jpeg(frame):
                    self._last_frame = frame
                    self._last_snapshot_ts = now
                    _LOGGER.debug("ha_creality_ws: successfully captured MJPEG frame")
                elif frame:
                    _LOGGER.debug("ha_creality_ws: dropping invalid MJPEG frame from upstream")
                else:
                    _LOGGER.debug("ha_creality_ws: printer is offline, using fallback image")

        # Return the frame or fallback image
        if frame is None:
            frame = await self._fallback_image()
        else:
            if not self._is_valid_jpeg(frame):
                _LOGGER.debug("ha_creality_ws: upstream frame invalid, returning fallback image")
                frame = await self._fallback_image()
                
        return frame

    async def handle_async_mjpeg_stream(self, request):
        """Handle live MJPEG streaming requests.
        
        This method provides live MJPEG streaming by proxying the printer's
        MJPEG stream directly to the client. It handles connection errors
        gracefully and provides appropriate HTTP status codes.
        
        Args:
            request: aiohttp request object
            
        Returns:
            web.Response: HTTP response with MJPEG stream or error
        """
        session = async_get_clientsession(self.hass)
        try:
            upstream = await session.get(self._url, timeout=None)
        except ClientError:
            _LOGGER.warning("ha_creality_ws: upstream MJPEG connection failed to %s", self._url)
            return web.Response(status=502, text="Upstream camera connection failed")
        except Exception:
            _LOGGER.exception("ha_creality_ws: unexpected error opening upstream MJPEG %s", self._url)
            return web.Response(status=502, text="Upstream camera error")

        try:
            if upstream.status != 200:
                txt = await upstream.text(errors="ignore")
                _LOGGER.warning("ha_creality_ws: upstream MJPEG returned status=%s text=%s", upstream.status, txt[:200])
                return web.Response(status=upstream.status, text=txt)

            ctype = upstream.headers.get("Content-Type", "multipart/x-mixed-replace;boundary=frame")
            resp = web.StreamResponse(status=200, headers={"Content-Type": ctype})
            await resp.prepare(request)

            try:
                async for chunk in upstream.content.iter_chunked(8192):
                    await resp.write(chunk)
            except (ClientError, ConnectionResetError, asyncio.CancelledError):
                pass
            except Exception:
                _LOGGER.exception("ha_creality_ws: error while streaming MJPEG from %s", self._url)
            finally:
                await upstream.release()
            return resp
        except Exception:
            _LOGGER.exception("ha_creality_ws: unexpected error handling MJPEG stream from %s", self._url)
            try:
                await upstream.release()
            except Exception:
                pass
            return web.Response(status=502, text="Upstream camera error")


class CrealityWebRTCCamera(_BaseCamera):
    """Native WebRTC camera for Creality K2 family printers.

    This camera provides native WebRTC streaming support for Creality K2 family
    printers by integrating with Home Assistant's built-in go2rtc service.
    
    Architecture:
    1. Configures go2rtc to pull WebRTC stream from the Creality K2 printer
    2. Exposes go2rtc's WebRTC endpoint as the camera's stream source
    3. Forwards WebRTC offers/answers between Home Assistant frontend and go2rtc
    4. Provides static image capture via go2rtc's snapshot API
    
    Features:
    - Native WebRTC streaming without additional HACS integrations
    - Automatic go2rtc stream configuration
    - Graceful fallback to static images when streaming is unavailable
    - Full WebRTC offer/answer negotiation support
    """

    def __init__(
        self, 
        coordinator, 
        signaling_url: str, 
        use_proxy: bool = False,
        go2rtc_url: str | None = None,
        go2rtc_port: int | None = None,
    ) -> None:
        """Initialize the WebRTC camera.
        
        Args:
            coordinator: The printer coordinator
            signaling_url: WebRTC signaling URL from the printer
            use_proxy: Whether to use proxy (deprecated, kept for compatibility)
            go2rtc_url: Custom go2rtc server URL (optional)
            go2rtc_port: Custom go2rtc server port (optional)
        """
        super().__init__(coordinator, "Printer Camera", "camera")
        self._upstream_signaling_url = signaling_url
        self._use_proxy = use_proxy  # Deprecated, kept for compatibility
        self._custom_go2rtc_url = go2rtc_url
        self._custom_go2rtc_port = go2rtc_port
        self._stream_name: str | None = None
        self._last_error: str | None = None
        
        # Snapshot throttling to avoid hammering go2rtc
        self._last_snapshot_ts: float = 0.0
        self._snapshot_min_interval: float = 2.0  # seconds
        self._snapshot_lock = asyncio.Lock()
        
        # Initialize go2rtc client (will be set up in async_added_to_hass)
        self._go2rtc_client: Go2RtcRestClient | None = None
        self._go2rtc_server_url: str | None = None
        self._go2rtc_version: str | None = None
        
        _LOGGER.info(
            "ha_creality_ws: WebRTC camera initialized for printer: %s",
            signaling_url
        )
        
        # Set up supported features for native WebRTC streaming
        self._setup_supported_features()
        


    def _setup_supported_features(self) -> None:
        """Set up camera features for native WebRTC streaming.
        
        Configures the camera to support WebRTC streaming according to
        Home Assistant's camera entity requirements. WebRTC cameras need
        the STREAM feature and must implement specific WebRTC methods.
        """
        mask = 0

        if "CameraEntityFeature" in globals() and CameraEntityFeature is not None:
            # For WebRTC cameras, we need the STREAM feature
            # According to HA docs: "Requires CameraEntityFeature.STREAM and the integration
            # must implement the two following methods to support native WebRTC"
            stream_val = getattr(CameraEntityFeature, "STREAM", None)
            if stream_val is not None:
                try:
                    mask |= int(stream_val)
                except Exception:
                    pass

            # Include ON_DEMAND for static image capability
            ond_val = getattr(CameraEntityFeature, "ON_DEMAND", None)
            if ond_val is not None:
                try:
                    mask |= int(ond_val)
                except Exception:
                    pass

        self._attr_supported_features = _FeatureMask(mask)
        _LOGGER.info(
            "ha_creality_ws: WebRTC camera features: STREAM=%s, ON_DEMAND=%s, mask=%d",
            bool(mask & 2),  # STREAM is bit 1 (2)
            bool(mask & 1),  # ON_DEMAND is bit 0 (1)
            mask,
        )

    @property
    def stream_source(self) -> Optional[str]:
        """Return the stream name for go2rtc.
        
        Returns the stream name that go2rtc uses to identify this camera's stream.
        HA's go2rtc component will handle the actual WebRTC connection.
        
        Returns:
            str: Stream name, or None if not configured
        """
        return self._stream_name

    async def async_get_stream_source(self) -> Optional[str]:
        """Return the stream name for go2rtc.
        
        Async version of stream_source property for compatibility with
        Home Assistant's camera entity interface.
        
        Returns:
            str: Stream name, or None if not configured
        """
        await self._ensure_stream_configured()
        return self._stream_name

    async def async_added_to_hass(self) -> None:
        """Configure go2rtc stream when camera is added to Home Assistant.
        
        This method is called when the camera entity is added to Home Assistant.
        We initialize the go2rtc client here to ensure it's ready for use.
        """
        await super().async_added_to_hass()
        
        # Initialize go2rtc client from HA's component
        if not await self._initialize_go2rtc_client():
            _LOGGER.warning(
                "ha_creality_ws: WebRTC camera will not work - "
                "go2rtc client initialization failed. "
                "Ensure default_config is enabled or go2rtc is configured."
            )
    
    async def _initialize_go2rtc_client(self) -> bool:
        """Initialize go2rtc client from HA's go2rtc component.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._go2rtc_client:
            return True  # Already initialized
        
        if not GO2RTC_CLIENT_AVAILABLE:
            _LOGGER.error(
                "ha_creality_ws: go2rtc-client library not available. "
                "This should not happen as it's in requirements."
            )
            return False
        
        # Custom go2rtc configuration
        if self._custom_go2rtc_url:
            try:
                # Use default session
                session = async_get_clientsession(self.hass)
                
                # Format URL: http://host:port/
                url = self._custom_go2rtc_url
                if "://" not in url:
                    url = f"http://{url}"
                
                if self._custom_go2rtc_port and ":" not in url.split("://")[1]:
                    url = f"{url}:{self._custom_go2rtc_port}"
                
                # Ensure trailing slash for client compatibility
                if not url.endswith("/"):
                    url += "/"
                    
                self._go2rtc_client = Go2RtcRestClient(session, url)
                self._go2rtc_server_url = url
                
                # Validate server version
                version = await self._go2rtc_client.validate_server_version()
                self._go2rtc_version = str(version)
                
                _LOGGER.info(
                    "ha_creality_ws: Connected to custom go2rtc %s at %s",
                    self._go2rtc_version, self._go2rtc_server_url
                )
                return True
                
            except Exception as exc:
                _LOGGER.warning(
                    "ha_creality_ws: Failed to connect to CUSTOM go2rtc at %s: %s. "
                    "Falling back to Home Assistant default go2rtc...",
                    self._custom_go2rtc_url, exc
                )
                # Fall through to standard discovery logic
                self._go2rtc_client = None
                self._go2rtc_server_url = None


        # Get HA's go2rtc configuration
        go2rtc_data = self.hass.data.get(GO2RTC_DOMAIN)
        if not go2rtc_data:
            _LOGGER.error(
                "ha_creality_ws: go2rtc component not loaded. "
                "Ensure default_config is enabled in configuration.yaml or "
                "configure go2rtc manually."
            )
            return False
        
        try:
            # Create client using HA's pre-configured session and URL
            # The session already has UnixConnector configured if HA is managing go2rtc
            self._go2rtc_client = Go2RtcRestClient(
                go2rtc_data.session,
                go2rtc_data.url
            )
            self._go2rtc_server_url = go2rtc_data.url
            
            # Validate server version
            version = await self._go2rtc_client.validate_server_version()
            self._go2rtc_version = str(version)
            
            _LOGGER.info(
                "ha_creality_ws: Connected to go2rtc %s at %s",
                self._go2rtc_version, self._go2rtc_server_url
            )
            return True
            
        except Go2RtcClientError as exc:
            _LOGGER.error(
                "ha_creality_ws: Failed to initialize go2rtc client: %s",
                exc, exc_info=True
            )
            return False
        except Exception as exc:
            _LOGGER.error(
                "ha_creality_ws: Unexpected error initializing go2rtc client: %s",
                exc, exc_info=True
            )
            return False

    async def async_camera_image(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> bytes | None:
        """Return a camera image using go2rtc snapshot API.
        
        Args:
            width: Desired image width (optional)
            height: Desired image height (optional)
            
        Returns:
            bytes: JPEG image data, or None if unavailable
        """
        # Sanitize dimensions
        if not width or width <= 0:
            width = None
        if not height or height <= 0:
            height = None
            
        # Ensure stream is configured and client is initialized
        await self._ensure_stream_configured()
        
        if not self._go2rtc_client or not self._stream_name:
            _LOGGER.debug(
                "ha_creality_ws: go2rtc client or stream not configured for snapshots; returning fallback image"
            )
            return await self._fallback_image()

        # Snapshot throttling: return cached frame if recent
        now = asyncio.get_running_loop().time()
        if self._last_frame and (now - self._last_snapshot_ts) < self._snapshot_min_interval:
            return self._last_frame

        try:
            async with self._snapshot_lock:
                # Throttle check again inside the lock
                now = asyncio.get_running_loop().time()
                if self._last_frame and (now - self._last_snapshot_ts) < self._snapshot_min_interval:
                    return self._last_frame

                # Use go2rtc client to get snapshot
                _LOGGER.debug("ha_creality_ws: requesting snapshot from go2rtc for stream: %s", self._stream_name)
                
                image_data = await self._go2rtc_client.get_jpeg_snapshot(
                    name=self._stream_name,
                    width=width,
                    height=height
                )
                
                if image_data and self._is_valid_jpeg(image_data):
                    self._last_frame = image_data
                    self._last_snapshot_ts = now
                    _LOGGER.debug("ha_creality_ws: successfully captured WebRTC snapshot")
                    return image_data
                else:
                    _LOGGER.warning("ha_creality_ws: invalid or empty JPEG from go2rtc snapshot")

        except Go2RtcClientError as err:
            _LOGGER.warning("ha_creality_ws: go2rtc client error getting snapshot: %s", err)
        except Exception as exc:
            _LOGGER.warning("ha_creality_ws: unexpected error getting snapshot: %s", exc)
        
        return await self._fallback_image()





    async def _ensure_stream_configured(self) -> None:
        """Ensure the go2rtc stream is configured using HA's go2rtc client."""
        if self._stream_name:
            return  # Already configured
        
        # Initialize client if needed
        if not self._go2rtc_client:
            if not await self._initialize_go2rtc_client():
                _LOGGER.error("ha_creality_ws: Cannot configure stream - go2rtc client not initialized")
                return
        
        # Generate stream name from printer IP
        try:
            printer_host = self._upstream_signaling_url.split("://")[1].split(":")[0]
            self._stream_name = f"creality_k2_{printer_host.replace('.', '_')}"
        except (IndexError, AttributeError) as exc:
            _LOGGER.error(
                "ha_creality_ws: Failed to parse printer host from URL %s: %s",
                self._upstream_signaling_url, exc
            )
            return
        
        # Configure stream source with Creality format
        go2rtc_src = f"webrtc:{self._upstream_signaling_url}#format=creality"
        
        try:
            # Check if stream already exists
            streams = await self._go2rtc_client.streams.list()
            
            if self._stream_name not in streams:
                # Add new stream
                await self._go2rtc_client.streams.add(
                    name=self._stream_name,
                    sources=go2rtc_src
                )
                _LOGGER.info(
                    "ha_creality_ws: Added stream '%s' with source '%s'",
                    self._stream_name, go2rtc_src
                )
            else:
                _LOGGER.debug(
                    "ha_creality_ws: Stream '%s' already exists in go2rtc",
                    self._stream_name
                )
                
        except Go2RtcClientError as exc:
            _LOGGER.error(
                "ha_creality_ws: Failed to configure stream: %s",
                exc, exc_info=True
            )
            self._stream_name = None  # Reset so we retry later
        except Exception as exc:
            _LOGGER.error(
                "ha_creality_ws: Unexpected error configuring stream: %s",
                exc, exc_info=True
            )
            self._stream_name = None  # Reset so we retry later



    def _wrap_send_message(self, payload: dict):
        """Wrap a dictionary payload for send_message callback.
        
        Home Assistant's WebRTC send_message callback expects objects with
        an as_dict() method. This helper wraps dictionary payloads to provide
        the required interface.
        
        Args:
            payload: Dictionary payload to wrap
            
        Returns:
            MessageWrapper: Object with as_dict() method
        """
        class MessageWrapper:
            """Wrapper class for WebRTC message payloads."""
            
            def __init__(self, data):
                self.data = data
            
            def as_dict(self):
                """Return the wrapped data as a dictionary."""
                return self.data
        
        return MessageWrapper(payload)

    async def async_handle_async_webrtc_offer(
        self, offer_sdp: str, session_id: str, send_message
    ) -> None:
        """Handle WebRTC offer using go2rtc client.

        This method is called by Home Assistant when a WebRTC offer is received
        from the frontend. It uses the go2rtc client to forward the offer and
        receive the answer.

        Args:
            offer_sdp: SDP offer from the frontend
            session_id: Unique session identifier
            send_message: Callback function to send messages to the frontend
        """
        # Ensure stream is configured and client is initialized
        await self._ensure_stream_configured()
        
        if not self._go2rtc_client or not self._stream_name:
            _LOGGER.error(
                "ha_creality_ws: Cannot handle WebRTC offer - client: %s, stream: %s",
                self._go2rtc_client is not None, self._stream_name
            )
            send_message(
                self._wrap_send_message(
                    {"type": "error", "message": "go2rtc not configured"}
                )
            )
            return

        _LOGGER.info(
            "ha_creality_ws: handling WebRTC offer for stream '%s', session '%s'",
            self._stream_name,
            session_id,
        )
        _LOGGER.debug(
            "ha_creality_ws: offer SDP preview: %s",
            offer_sdp[:200] + "..." if len(offer_sdp) > 200 else offer_sdp,
        )

        try:
            # Create offer object for go2rtc client
            offer = WebRTCSdpOffer(sdp=offer_sdp)
            
            # Forward offer to go2rtc and get answer
            _LOGGER.debug("ha_creality_ws: forwarding offer to go2rtc for stream: %s", self._stream_name)
            answer = await self._go2rtc_client.webrtc.forward_whep_sdp_offer(
                source_name=self._stream_name,
                offer=offer
            )
            
            # Extract SDP from answer
            answer_sdp = answer.sdp
            _LOGGER.debug(
                "ha_creality_ws: received answer SDP preview: %s",
                answer_sdp[:200] + "..." if len(answer_sdp) > 200 else answer_sdp,
            )

            # Send answer back to frontend
            send_message(
                self._wrap_send_message(
                    {"type": "answer", "answer": answer_sdp}
                )
            )
            _LOGGER.info("ha_creality_ws: WebRTC offer handled successfully")

        except Go2RtcClientError as exc:
            _LOGGER.error(
                "ha_creality_ws: go2rtc client error handling WebRTC offer: %s",
                exc, exc_info=True
            )
            send_message(
                self._wrap_send_message(
                    {"type": "error", "message": f"go2rtc error: {exc}"}
                )
            )
        except Exception as exc:
            _LOGGER.error(
                "ha_creality_ws: unexpected error handling WebRTC offer: %s",
                exc, exc_info=True
            )
            send_message(
                self._wrap_send_message(
                    {"type": "error", "message": f"WebRTC error: {exc}"}
                )
            )



    async def async_on_webrtc_candidate(self, session_id: str, candidate) -> None:
        """Handle WebRTC ICE candidate.
        
        This method is called when ICE candidates are received from the frontend.
        For go2rtc integration, candidates are handled internally by go2rtc,
        so this method is primarily for logging purposes.
        
        Args:
            session_id: Unique session identifier
            candidate: ICE candidate from the frontend
        """
        # For go2rtc integration, candidates are handled internally
        _LOGGER.debug("ha_creality_ws: WebRTC candidate received for session %s", session_id)

    @callback
    def close_webrtc_session(self, session_id: str) -> None:
        """Close a WebRTC session.
        
        This method is called when a WebRTC session is closed by the frontend.
        It can be used for cleanup, but for go2rtc integration, session
        management is handled internally.
        
        Args:
            session_id: Unique session identifier to close
        """
        _LOGGER.debug("ha_creality_ws: WebRTC session %s closed", session_id)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes for the camera.
        
        Provides additional information about the camera's configuration
        and status, useful for debugging and monitoring.
        
        Returns:
            dict: Dictionary of extra state attributes
        """
        attrs = {
            "go2rtc_stream_name": self._stream_name,
            "go2rtc_version": self._go2rtc_version,
            "upstream_signaling_url": self._upstream_signaling_url,
            "stream_source": self.stream_source,
        }
        if self._last_error:
            attrs["error"] = self._last_error
        return attrs

    def _is_valid_jpeg(self, data: bytes) -> bool:
        """Check if the data is a valid JPEG image.
        
        Validates JPEG image data by checking for proper JPEG markers.
        
        Args:
            data: Raw image data to validate
            
        Returns:
            bool: True if the data is a valid JPEG image
        """
        if not data or len(data) < 20:
            return False
        return data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")


async def _probe_webrtc_signaling(hass: HomeAssistant, url: str, timeout: float = 1.5) -> bool:
    """Probe the Creality WebRTC signaling endpoint.

    This function performs a lightweight probe of the printer's WebRTC signaling
    endpoint to determine if the printer supports WebRTC. It tries HEAD first
    (cheaper), then falls back to GET if HEAD is not supported.

    Printers typically answer on /call/webrtc_local even without a full offer body.
    We treat any 200-405 (method not allowed) as presence; 404/connection errors -> absent.
    
    Args:
        hass: Home Assistant instance
        url: WebRTC signaling URL to probe
        timeout: Request timeout in seconds
        
    Returns:
        bool: True if WebRTC signaling is available, False otherwise
    """
    session = async_get_clientsession(hass)
    try:
        # First try HEAD (cheap). If not supported, fall back to GET
        async with session.head(url, timeout=timeout) as resp:
            _LOGGER.debug("ha_creality_ws: probe HEAD %s -> status=%s", url, resp.status)
            if resp.status in (200, 204, 405):
                return True
    except Exception:
        pass
    try:
        async with session.get(url, timeout=timeout) as resp:
            _LOGGER.debug("ha_creality_ws: probe GET %s -> status=%s", url, resp.status)
            if resp.status in (200, 204, 405):
                return True
    except Exception:
        return False
    return False


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up camera entities for a Creality printer.
    
    This function is called by Home Assistant when setting up the camera platform.
    It determines the appropriate camera type (MJPEG or WebRTC) based on the
    printer model and user configuration, then creates the appropriate camera entity.
    
    Args:
        hass: Home Assistant instance
        entry: Configuration entry for the printer
        async_add_entities: Function to add entities to Home Assistant
    """
    coord = hass.data[DOMAIN][entry.entry_id]
    host = entry.data["host"]
    use_proxy = False  # No longer needed with go2rtc approach

    _LOGGER.debug("ha_creality_ws: setting up camera for printer at %s", host)

    # Respect user-forced camera mode first
    cam_mode = entry.options.get("camera_mode")
    if cam_mode == "webrtc":
        _LOGGER.info("ha_creality_ws: user forced WebRTC mode for %s", host)
        async_add_entities([
            CrealityWebRTCCamera(
                coord, 
                WEBRTC_URL_TEMPLATE.format(host=host), 
                use_proxy=use_proxy,
                go2rtc_url=entry.options.get(CONF_GO2RTC_URL),
                go2rtc_port=entry.options.get(CONF_GO2RTC_PORT),
            )
        ])
        return
    if cam_mode == "mjpeg":
        _LOGGER.info("ha_creality_ws: user forced MJPEG mode for %s", host)
        async_add_entities([CrealityMjpegCamera(coord, MJPEG_URL_TEMPLATE.format(host=host))])
        return

    # Use cached camera type from entry data (detected during onboarding)
    cached_camera_type = entry.data.get("_cached_camera_type", "mjpeg")
    
    # WebRTC cameras (K2 family - always present)
    webrtc_url = WEBRTC_URL_TEMPLATE.format(host=host)
    if cached_camera_type == "webrtc":
        _LOGGER.info("ha_creality_ws: using cached WebRTC camera detection for %s", host)
        async_add_entities([
            CrealityWebRTCCamera(
                coord, 
                webrtc_url, 
                use_proxy=use_proxy,
                go2rtc_url=entry.options.get(CONF_GO2RTC_URL),
                go2rtc_port=entry.options.get(CONF_GO2RTC_PORT),
            )
        ])
        return

    # MJPEG cameras (default or optional)
    mjpeg_url = MJPEG_URL_TEMPLATE.format(host=host)
    
    # Check if camera type is mjpeg_optional (K1 SE, Ender 3 V3 family)
    if cached_camera_type == "mjpeg_optional":
        _LOGGER.info("ha_creality_ws: using cached optional camera model, attempting MJPEG for %s", host)
        try:
            async_add_entities([CrealityMjpegCamera(coord, mjpeg_url)])
        except Exception:
            # Camera is optional for these models, continue without it
            _LOGGER.info("ha_creality_ws: optional camera not available for %s", host)
            pass
        return
    
    # Default MJPEG cameras
    _LOGGER.info("ha_creality_ws: using cached MJPEG camera detection for %s", host)
    async_add_entities([CrealityMjpegCamera(coord, mjpeg_url)])
