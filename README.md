# My Home Assistant Config

[![Build Status](https://github.com/aneisch/home-assistant-config/actions/workflows/check-ha-release-compatibility.yml/badge.svg)](https://github.com/aneisch/home-assistant-config/actions)
[![GitHub last commit](https://img.shields.io/github/last-commit/aneisch/home-assistant-config)](https://github.com/aneisch/home-assistant-config/commits/master)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/y/aneisch/home-assistant-config)](https://github.com/aneisch/home-assistant-config/graphs/commit-activity)
[![HA Version](https://img.shields.io/badge/Running%20Home%20Assistant-2025.6.1%20(Latest)-brightgreen)](https://github.com/home-assistant/home-assistant/releases/latest)
<br><a href="https://www.buymeacoffee.com/aneisch" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a>

I do my best to keep [Home Assistant](https://github.com/home-assistant/home-assistant) on the [latest release](https://github.com/home-assistant/home-assistant/releases/latest). I'm heavily utilizing [AppDaemon](http://appdaemon.readthedocs.io/en/latest/) and [NodeRed](https://flows.nodered.org/node/node-red-contrib-home-assistant-websocket) for advanced/templated automations. See [Appdaemon config](https://github.com/aneisch/home-assistant-config/tree/master/extras/appdaemon) and my NodeRed screenshots below for details. Most of my setup is run as Docker containers (see [docker-compose](https://github.com/aneisch/home-assistant-config/tree/master/extras/docker-compose) for container list).

My Home Assistant installation runs on a [Gen7 i3 NUC](https://amzn.to/2K0vab6) with Centos 7:

- Lots of Docker containers, some described below. See [Docker Compose](https://github.com/aneisch/home-assistant-config/tree/master/extras/docker-compose)
- [Frigate](https://frigate.video/) for security camera recording and object detection
- Home Assistant Companion for iOS and Android device tracking
- A plethora of Lolin D1 Mini and S2 Mini sensors via [ESPHome](https://esphome.io/components/api.html) (using ESPHome API, not MQTT). See [/extras/esphome](https://github.com/aneisch/home-assistant-config/tree/master/extras/esphome) for configs
- Milights with [Homebrew MiLight controller](http://blog.christophermullins.com/2017/02/11/milight-wifi-gateway-emulator-on-an-esp8266/) using D1 Mini and NRF24L01
- Zwave, Zigbee, and Wifi (ESPHome) smart plugs
- ZHA using [CC2531](https://amzn.to/2L5xKNB) running zigbee2mqtt firmware
- Z-Wave JS using Aeon Labs USB stick with:
    - 1 AEON Labs DSA03XXX-ZW
  - 1 AEON Labs ZW090
  - 2 First Alert (BRK Brands Inc) ZCOMBO
  - 1 GE 12719 / ZW4101
  - 2 GE 12720 / ZW4201
  - 2 GE 12730 / ZW4002
  - 1 Kwikset 910
  - 1 Leviton DZPA1
  - 1 Nortek Security + Control LLC WADWAZ-1
  - 1 Nortek Security + Control LLC WAPIRZ-1
  - 1 Zooz ZAC36
  - 5 Zooz ZEN21
  - 6 Zooz ZEN27
  - 6 Zooz ZEN30
  - 3 Zooz ZEN37 800LR
  - 2 Zooz ZEN55 LR
  - 5 Zooz ZEN71
  - 1 Zooz ZEN77
  - 5 Zooz ZSE42
- MQTT remote and local server (via [Docker](https://github.com/aneisch/home-assistant-config/tree/master/extras/docker-compose))
- Various MQTT Sensors (some in [extras/scripts](https://github.com/aneisch/home-assistant-config/tree/master/extras/scripts))
- RTL_433 to capture data from various off-the-shelf sensors
- [AppDaemon](https://appdaemon.readthedocs.io/en/latest/) controlling a large number of automations and intelligent AC control. See [/extras/appdaemon](https://github.com/aneisch/home-assistant-config/tree/master/extras/appdaemon) for configs.
- [NodeRed](https://flows.nodered.org/node/node-red-contrib-home-assistant-websocket) for irrigation and other automations (see screenshot below)
- [Amazon Echos](https://amzn.to/2VLPPm0)

  - [Amazon Alexa Smart Home API](https://www.home-assistant.io/components/alexa.smart_home/) using AWS Lambda
  - Custom routines configured in the Alexa App
  - [Alexa Media Player Custom Component](https://github.com/keatontaylor/alexa_media_player)
- UPS monitoring using [apcupsd](https://github.com/gersilex/apcupsd-docker)
- Whole home power monitoring with ESPHome-flashed Emporia View
- Github actions to test beta and stable builds against config

Home Assistant and other containers have ingress handled automatically by [Traefik](https://doc.traefik.io/traefik/) and are accessible locally or fronted and secured by Cloudflare Zero Trust Network Access.

## Some statistics about my installation:
Description | value
-- | --
Lines of ESPHome YAML | 5856
Lines of Home Assistant YAML | 11595
[Integrations](https://www.home-assistant.io/integrations/) in use | 71
Zigbee devices in [`zha`](https://www.home-assistant.io/integrations/zha/) | 26
Z-Wave devices in [`zwave_js`](https://www.home-assistant.io/integrations/zwave_js/) | 37
 
Description | value
-- | --
Entities in the [`assist_satellite`](https://www.home-assistant.io/components/assist_satellite) domain | 1
Entities in the [`automation`](https://www.home-assistant.io/components/automation) domain | 145
Entities in the [`binary_sensor`](https://www.home-assistant.io/components/binary_sensor) domain | 176
Entities in the [`button`](https://www.home-assistant.io/components/button) domain | 62
Entities in the [`camera`](https://www.home-assistant.io/components/camera) domain | 13
Entities in the [`climate`](https://www.home-assistant.io/components/climate) domain | 1
Entities in the [`conversation`](https://www.home-assistant.io/components/conversation) domain | 3
Entities in the [`counter`](https://www.home-assistant.io/components/counter) domain | 1
Entities in the [`cover`](https://www.home-assistant.io/components/cover) domain | 19
Entities in the [`datetime`](https://www.home-assistant.io/components/datetime) domain | 6
Entities in the [`device_tracker`](https://www.home-assistant.io/components/device_tracker) domain | 7
Entities in the [`event`](https://www.home-assistant.io/components/event) domain | 17
Entities in the [`fan`](https://www.home-assistant.io/components/fan) domain | 3
Entities in the [`group`](https://www.home-assistant.io/components/group) domain | 19
Entities in the [`image`](https://www.home-assistant.io/components/image) domain | 7
Entities in the [`input_boolean`](https://www.home-assistant.io/components/input_boolean) domain | 33
Entities in the [`input_datetime`](https://www.home-assistant.io/components/input_datetime) domain | 33
Entities in the [`input_number`](https://www.home-assistant.io/components/input_number) domain | 7
Entities in the [`input_select`](https://www.home-assistant.io/components/input_select) domain | 20
Entities in the [`input_text`](https://www.home-assistant.io/components/input_text) domain | 18
Entities in the [`light`](https://www.home-assistant.io/components/light) domain | 40
Entities in the [`lock`](https://www.home-assistant.io/components/lock) domain | 5
Entities in the [`media_player`](https://www.home-assistant.io/components/media_player) domain | 14
Entities in the [`number`](https://www.home-assistant.io/components/number) domain | 24
Entities in the [`person`](https://www.home-assistant.io/components/person) domain | 2
Entities in the [`plant`](https://www.home-assistant.io/components/plant) domain | 1
Entities in the [`remote`](https://www.home-assistant.io/components/remote) domain | 4
Entities in the [`script`](https://www.home-assistant.io/components/script) domain | 54
Entities in the [`select`](https://www.home-assistant.io/components/select) domain | 14
Entities in the [`sensor`](https://www.home-assistant.io/components/sensor) domain | 726
Entities in the [`setter`](https://www.home-assistant.io/components/setter) domain | 1
Entities in the [`siren`](https://www.home-assistant.io/components/siren) domain | 1
Entities in the [`stt`](https://www.home-assistant.io/components/stt) domain | 1
Entities in the [`sun`](https://www.home-assistant.io/components/sun) domain | 1
Entities in the [`switch`](https://www.home-assistant.io/components/switch) domain | 199
Entities in the [`text`](https://www.home-assistant.io/components/text) domain | 1
Entities in the [`timer`](https://www.home-assistant.io/components/timer) domain | 7
Entities in the [`tts`](https://www.home-assistant.io/components/tts) domain | 2
Entities in the [`update`](https://www.home-assistant.io/components/update) domain | 86
Entities in the [`vacuum`](https://www.home-assistant.io/components/vacuum) domain | 1
Entities in the [`weather`](https://www.home-assistant.io/components/weather) domain | 1
Entities in the [`zone`](https://www.home-assistant.io/components/zone) domain | 8
**Total state objects** | **1784**
## The HACS integrations/plugins that I use:

**Appdaemon**:<br>
[aneisch/follow_me_appdaemon](https://github.com/aneisch/follow_me_appdaemon)<br>

**Theme**:<br>
[JuanMTech/google_dark_theme](https://github.com/JuanMTech/google_dark_theme)<br>
[aFFekopp/dark_teal](https://github.com/aFFekopp/dark_teal)<br>
[home-assistant-community-themes/amoled](https://github.com/home-assistant-community-themes/amoled)<br>
[home-assistant-community-themes/aqua-fiesta](https://github.com/home-assistant-community-themes/aqua-fiesta)<br>
[home-assistant-community-themes/blue-night](https://github.com/home-assistant-community-themes/blue-night)<br>
[home-assistant-community-themes/dark-mint](https://github.com/home-assistant-community-themes/dark-mint)<br>
[home-assistant-community-themes/grey-night](https://github.com/home-assistant-community-themes/grey-night)<br>
[naofireblade/clear-theme-dark](https://github.com/naofireblade/clear-theme-dark)<br>
[seangreen2/slate_theme](https://github.com/seangreen2/slate_theme)<br>

**Integration**:<br>
[AlexxIT/SonoffLAN](https://github.com/AlexxIT/SonoffLAN)<br>
[AlexxIT/WebRTC](https://github.com/AlexxIT/WebRTC)<br>
[BJReplay/ha-solcast-solar](https://github.com/BJReplay/ha-solcast-solar)<br>
[PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor](https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor)<br>
[alandtse/alexa_media_player](https://github.com/alandtse/alexa_media_player)<br>
[alandtse/tesla](https://github.com/alandtse/tesla)<br>
[blakeblackshear/frigate-hass-integration](https://github.com/blakeblackshear/frigate-hass-integration)<br>
[claytonjn/hass-circadian_lighting](https://github.com/claytonjn/hass-circadian_lighting)<br>
[custom-components/readme](https://github.com/custom-components/readme)<br>
[dlashua/hass-setter](https://github.com/dlashua/hass-setter)<br>
[frenck/spook](https://github.com/frenck/spook)<br>
[hacs/integration](https://github.com/hacs/integration)<br>
[jmcollin78/solar_optimizer](https://github.com/jmcollin78/solar_optimizer)<br>
[magico13/ha-emporia-vue](https://github.com/magico13/ha-emporia-vue)<br>
[moralmunky/Home-Assistant-Mail-And-Packages](https://github.com/moralmunky/Home-Assistant-Mail-And-Packages)<br>
[rospogrigio/localtuya](https://github.com/rospogrigio/localtuya)<br>
[rroller/dahua](https://github.com/rroller/dahua)<br>
[sdrapha/home-assistant-custom-components-pfsense-gateways](https://github.com/sdrapha/home-assistant-custom-components-pfsense-gateways)<br>
[sebr/bhyve-home-assistant](https://github.com/sebr/bhyve-home-assistant)<br>
[ualex73/monitor_docker](https://github.com/ualex73/monitor_docker)<br>

**Plugin**:<br>
[PiotrMachowski/lovelace-xiaomi-vacuum-map-card](https://github.com/PiotrMachowski/lovelace-xiaomi-vacuum-map-card)<br>
[bramkragten/weather-card](https://github.com/bramkragten/weather-card)<br>
[custom-cards/bignumber-card](https://github.com/custom-cards/bignumber-card)<br>
[dermotduffy/advanced-camera-card](https://github.com/dermotduffy/advanced-camera-card)<br>
[dmulcahey/zha-network-visualization-card](https://github.com/dmulcahey/zha-network-visualization-card)<br>
[dylandoamaral/uptime-card](https://github.com/dylandoamaral/uptime-card)<br>
[gadgetchnnel/lovelace-card-templater](https://github.com/gadgetchnnel/lovelace-card-templater)<br>
[gadgetchnnel/lovelace-text-input-row](https://github.com/gadgetchnnel/lovelace-text-input-row)<br>
[j-a-n/lovelace-wallpanel](https://github.com/j-a-n/lovelace-wallpanel)<br>
[junkfix/numberbox-card](https://github.com/junkfix/numberbox-card)<br>
[kalkih/mini-media-player](https://github.com/kalkih/mini-media-player)<br>
[nervetattoo/simple-thermostat](https://github.com/nervetattoo/simple-thermostat)<br>
[ofekashery/vertical-stack-in-card](https://github.com/ofekashery/vertical-stack-in-card)<br>
[piitaya/lovelace-mushroom](https://github.com/piitaya/lovelace-mushroom)<br>
[pmongloid/flipdown-timer-card](https://github.com/pmongloid/flipdown-timer-card)<br>
[slipx06/sunsynk-power-flow-card](https://github.com/slipx06/sunsynk-power-flow-card)<br>
[thomasloven/lovelace-auto-entities](https://github.com/thomasloven/lovelace-auto-entities)<br>
[thomasloven/lovelace-card-mod](https://github.com/thomasloven/lovelace-card-mod)<br>
[thomasloven/lovelace-card-tools](https://github.com/thomasloven/lovelace-card-tools)<br>
[thomasloven/lovelace-fold-entity-row](https://github.com/thomasloven/lovelace-fold-entity-row)<br>
[thomasloven/lovelace-slider-entity-row](https://github.com/thomasloven/lovelace-slider-entity-row)<br>


# Interface

![UI](images/1.png)
![UI](images/2.png)
![UI](images/3.png)
![UI](images/4.png)
![UI](images/5.png)
![Grafana](images/grafana.png)
![Node-Red](images/nodered_1.png)
![Node-Red](images/nodered_2.png)
Auto generated using: `docker run -it -v /tmp:/usr/src/app/out --rm nevermendel/chrome-headless-screenshots --width=$viewportWidth1 --height=$viewportHeight1 --filename=nodered_1 --delay=3000 http://10.0.1.22:1880/#flow/9584418c.dafc2`
