set zoomStatus to "closed"
set muteStatusOld to ""
set videoStatusOld to ""
set muteStatus to ""
set videoStatus to ""
repeat
        tell application "System Events"
                if exists (window 1 of process "zoom.us") then
                        set zoomStatus to "open"
                        tell application process "zoom.us"
                                if exists (menu bar item "Meeting" of menu bar 1) then
                                        set zoomStatus to "call"
                                        if exists (menu item "Mute audio" of menu 1 of menu bar item "Meeting" of menu bar 1) then
                                                set muteStatus to "unmuted"
                                        else
                                                set muteStatus to "muted"
                                        end if
                                        if exists (menu item "Start Video" of menu 1 of menu bar item "Meeting" of menu bar 1) then
                                                set videoStatus to "inactive"
                                        else
                                                set videoStatus to "active"
                                        end if
                                else
                                        delay 5
                                end if
                        end tell
                else
                        delay 10
                end if
        end tell
        if (muteStatusOld ≠ muteStatus) or (videoStatusOld ≠ videoStatus) then
                set muteStatusOld to muteStatus
                set videoStatusOld to videoStatus
                do shell script "/usr/local/bin/mosquitto_pub -h HOSTNAME -p 8883 --cafile /etc/ssl/certs/trustid-x3-root.pem -u MQTT_USER -P MQTT_PASSWORD -t 'sensor/zoom_comms' -m '{\"mute\":\"" & muteStatus & "\",\"video\":\"" & videoStatus & "\"}'"
        end if
        delay 0.2
end repeat
