# My Home Assistant Config
[![Build Status](https://travis-ci.org/aneisch/home-assistant-config.svg?branch=master)](https://travis-ci.org/aneisch/home-assistant-config)
[![GitHub last commit](https://img.shields.io/github/last-commit/aneisch/home-assistant-config)](https://github.com/aneisch/home-assistant-config/commits/master)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/y/aneisch/home-assistant-config)](https://github.com/aneisch/home-assistant-config/graphs/commit-activity)
[![HA Version](https://img.shields.io/badge/Running%20Home%20Assistant%20-2021.1.4%20(Out%20of%20Date)-Red)](https://github.com/home-assistant/home-assistant/releases/latest)
<br><a href="https://www.buymeacoffee.com/aneisch" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a>


I do my best to keep [Home Assistant](https://github.com/home-assistant/home-assistant) on the [latest release](https://github.com/home-assistant/home-assistant/releases/latest). I'm heavily utilizing [AppDaemon](http://appdaemon.readthedocs.io/en/latest/) and [NodeRed](https://flows.nodered.org/node/node-red-contrib-home-assistant-websocket) for advanced/templated automations. See [Appdaemon config](https://github.com/aneisch/home-assistant-config/tree/master/extras/appdaemon) and my NodeRed screenshots below for details. Using [Home Assistant Companion](https://itunes.apple.com/us/app/home-assistant-companion/id1099568401?mt=8) for iOS, built-in browser shortcut in Android. Also using [Tasker Plugin](https://github.com/MarkAdamson/home-assistant-plugin-for-tasker) from [MarkAdamsom](https://github.com/MarkAdamson) to trigger some automations and scripts from the client-side. Most of my home automation software pieces run as Docker containers (see [docker-compose for container list](https://github.com/aneisch/home-assistant-config/tree/master/extras/docker-compose)). 

My Home Assistant installation contains many different components and runs on a [Gen7 i3 NUC](https://amzn.to/2K0vab6) running Centos 7:

- Home Assistant Companion for iOS and Android device tracking
- Lots of Docker containers, some described below. See [Docker Compose](https://github.com/aneisch/home-assistant-config/tree/master/extras/docker-compose)
- [Raspberry Pi](https://amzn.to/3oAyKrp) hosted USB Camera with M-JPEG streamer
- [ESP32](https://amzn.to/3gocrT9) with camera running [ESPHome](https://esphome.io/)
- Numerous Wemos [D1 Mini](https://amzn.to/39XyIps) sensors via [ESPHome](https://esphome.io/components/api.html) (using ESPHome API, not MQTT). See [/extras/esphome](https://github.com/aneisch/home-assistant-config/tree/master/extras/esphome) for configs. 
- Milights with [Homebrew MiLight controller](http://blog.christophermullins.com/2017/02/11/milight-wifi-gateway-emulator-on-an-esp8266/) using D1 Mini and NRF24L01. 
- Wemo wall plugs
- ZHA using [CC2531](https://amzn.to/2L5xKNB) running zigbee2mqtt firmware with various devices
  - 1 LDS ZBT-CCTSwitch-D0001
  - 1 LUMI lumi.sensor_cube
  - 8 The Home Depot Ecosmart-ZBT-A19-CCT-Bulb
- [Lustreon E27](https://www.banggood.com/LUSTREON-E27-Smart-WiFi-Bulb-Adapter-Socket-Lamp-Holder-Work-With-Alexa-Google-Home-IFTTT-AC85-265V-p-1285550.html) bulb holders for lamp control using ~~Tasmota/MQTT~~ ESPHome (1MB flash)
  - Check out [my blog post](http://blog.aneis.ch/2019/01/tuya-convert-for-lustreon.html) for alternative firmware flashing instructions
- OpenZWave (beta) using [Aeon Labs USB stick](https://amzn.to/39cmb1b) with various devices
  - 1 12719 Plug-in Smart Switch
  - 1 [12720 Outdoor Smart Switch](https://amzn.to/3m4Rsqi)
  - 1 12722 On/Off Relay Switch
  - 1 Leviton DZPA1 Plug-In Outlet
  - 1 Unknown: type=0000, id=0000
  - 1 [WAPIRZ-1 Motion Sensor](https://amzn.to/2LhyH5F)
  - 1 [ZW090 Z-Stick Gen5 US](https://amzn.to/39cmb1b)
  - 2 12730 Fan Control Switch
  - 2 WADWAZ-1 Door/Window Sensor
  - 2 [ZCombo-G Smoke/CO Alarm](https://amzn.to/2VOXBLY)
  - 3 [ZEN30 Double Switch](https://amzn.to/39kGkSC)
  - 5 [ZEN21 Switch V3](https://amzn.to/33hhTBT)
  - 6 [ZEN27 S2 Dimmer Wall Switch](https://amzn.to/3q2hm0C)
- MQTT remote and local server (via [Docker](https://github.com/aneisch/home-assistant-config/tree/master/extras/docker-compose)). Using remote with SSL for Owntracks (on a box through Digital Ocean with static public IP), and local MQTT to communicate with various sensors/switches around the house. The remote MQTT shares messages with the local via a MQTT bridge.
- Various MQTT Sensors (some in [extras/scripts](https://github.com/aneisch/home-assistant-config/tree/master/extras/scripts))
- [Arlo Cameras](https://amzn.to/2VOXXlM) (controlled through [aarlo custom component](https://github.com/twrecked/hass-aarlo))
- [AppDaemon](https://appdaemon.readthedocs.io/en/latest/) controlling a handful of automations and intelligent AC control. See [/extras/appdaemon](https://github.com/aneisch/home-assistant-config/tree/master/extras/appdaemon) for configs.
- [NodeRed](https://flows.nodered.org/node/node-red-contrib-home-assistant-websocket) for a few others (see screenshot below)
- [Amazon Echos](https://amzn.to/2VLPPm0)
  - [Amazon Alexa Smart Home API](https://www.home-assistant.io/components/alexa.smart_home/) using AWS Lambda 
  - Custom routines configured in the Alexa App.
  - [Alexa Media Player Custom Component](https://github.com/keatontaylor/alexa_media_player)
- UPS monitoring using [apcupsd](https://github.com/gersilex/apcupsd-docker)
- Github actions to test beta and stable builds against config.

Also using Grafana/Influx for graphing, both running in Docker containers on NUC, see [docker-compose](https://github.com/aneisch/home-assistant-config/tree/master/extras/docker-compose) for container list. Home Assistant, along with a few other web apps, are proxied through my firewall and fronted and secured by Cloudflare.
 

## Some statistics about my installation:
Description | value
-- | --
Lines of ESPHome YAML | 1554
Lines of Home Assistant YAML | 5045
[Integrations](https://www.home-assistant.io/integrations/) in use | 26
Zigbee devices in [`zha`](https://www.home-assistant.io/integrations/zha/) | 11
 
Description | value
-- | --
Entities in the [`alarm_control_panel`](https://www.home-assistant.io/components/alarm_control_panel) domain | 3
Entities in the [`automation`](https://www.home-assistant.io/components/automation) domain | 31
Entities in the [`binary_sensor`](https://www.home-assistant.io/components/binary_sensor) domain | 16
Entities in the [`camera`](https://www.home-assistant.io/components/camera) domain | 12
Entities in the [`climate`](https://www.home-assistant.io/components/climate) domain | 1
Entities in the [`device_tracker`](https://www.home-assistant.io/components/device_tracker) domain | 10
Entities in the [`fan`](https://www.home-assistant.io/components/fan) domain | 4
Entities in the [`group`](https://www.home-assistant.io/components/group) domain | 10
Entities in the [`input_boolean`](https://www.home-assistant.io/components/input_boolean) domain | 10
Entities in the [`input_datetime`](https://www.home-assistant.io/components/input_datetime) domain | 5
Entities in the [`input_number`](https://www.home-assistant.io/components/input_number) domain | 5
Entities in the [`input_select`](https://www.home-assistant.io/components/input_select) domain | 1
Entities in the [`light`](https://www.home-assistant.io/components/light) domain | 10
Entities in the [`media_player`](https://www.home-assistant.io/components/media_player) domain | 8
Entities in the [`persistent_notification`](https://www.home-assistant.io/components/persistent_notification) domain | 1
Entities in the [`person`](https://www.home-assistant.io/components/person) domain | 2
Entities in the [`plant`](https://www.home-assistant.io/components/plant) domain | 1
Entities in the [`scene`](https://www.home-assistant.io/components/scene) domain | 6
Entities in the [`script`](https://www.home-assistant.io/components/script) domain | 19
Entities in the [`sensor`](https://www.home-assistant.io/components/sensor) domain | 212
Entities in the [`sun`](https://www.home-assistant.io/components/sun) domain | 1
Entities in the [`switch`](https://www.home-assistant.io/components/switch) domain | 79
Entities in the [`weather`](https://www.home-assistant.io/components/weather) domain | 2
Entities in the [`zone`](https://www.home-assistant.io/components/zone) domain | 7
Entities in the [`zwave`](https://www.home-assistant.io/components/zwave) domain | 11
**Total state objects** | **467**
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
[PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor](https://github.com/PiotrMachowski/Home-Assistant-custom-components-Xiaomi-Cloud-Map-Extractor)<br>
[bruxy70/Garbage-Collection](https://github.com/bruxy70/Garbage-Collection)<br>
[claytonjn/hass-circadian_lighting](https://github.com/claytonjn/hass-circadian_lighting)<br>
[custom-components/alexa_media_player](https://github.com/custom-components/alexa_media_player)<br>
[custom-components/readme](https://github.com/custom-components/readme)<br>
[hacs/integration](https://github.com/hacs/integration)<br>
[jaruba/ha-samsungtv-tizen](https://github.com/jaruba/ha-samsungtv-tizen)<br>
[moralmunky/Home-Assistant-Mail-And-Packages](https://github.com/moralmunky/Home-Assistant-Mail-And-Packages)<br>
[rospogrigio/localtuya](https://github.com/rospogrigio/localtuya)<br>
[twrecked/hass-aarlo](https://github.com/twrecked/hass-aarlo)<br>
[ualex73/monitor_docker](https://github.com/ualex73/monitor_docker)<br>
[zha-ng/zha-map](https://github.com/zha-ng/zha-map)<br>

**Plugin**:<br>
[abmantis/ozw-network-visualization-card](https://github.com/abmantis/ozw-network-visualization-card)<br>
[bramkragten/weather-card](https://github.com/bramkragten/weather-card)<br>
[custom-cards/bignumber-card](https://github.com/custom-cards/bignumber-card)<br>
[custom-cards/favicon-counter](https://github.com/custom-cards/favicon-counter)<br>
[dmulcahey/zha-network-visualization-card](https://github.com/dmulcahey/zha-network-visualization-card)<br>
[gadgetchnnel/lovelace-card-templater](https://github.com/gadgetchnnel/lovelace-card-templater)<br>
[gadgetchnnel/lovelace-text-input-row](https://github.com/gadgetchnnel/lovelace-text-input-row)<br>
[kalkih/mini-media-player](https://github.com/kalkih/mini-media-player)<br>
[nervetattoo/simple-thermostat](https://github.com/nervetattoo/simple-thermostat)<br>
[ofekashery/vertical-stack-in-card](https://github.com/ofekashery/vertical-stack-in-card)<br>
[thomasloven/lovelace-auto-entities](https://github.com/thomasloven/lovelace-auto-entities)<br>
[thomasloven/lovelace-card-mod](https://github.com/thomasloven/lovelace-card-mod)<br>
[thomasloven/lovelace-slider-entity-row](https://github.com/thomasloven/lovelace-slider-entity-row)<br>
[twrecked/lovelace-hass-aarlo](https://github.com/twrecked/lovelace-hass-aarlo)<br>


# Interface
![UI](images/screenshot1.png)  
![UI](images/screenshot2.png)  
![UI](images/screenshot3.png)
![UI](images/screenshot4.png)
![UI](images/screenshot5.png)
![UI](images/screenshot6.png)
![UI](images/screenshot7.png)
![UI](images/screenshot8.png)
![Grafana](images/grafana.png)
![Node-Red](images/nodered_1.png)
![Node-Red](images/nodered_2.png)
![Node-Red](images/nodered_3.png)
Auto generated using: `docker run --rm -it --cap-add=SYS_ADMIN -v /tmp:/output tonious/chromeshot --delay=1000 --url=http://10.0.1.22:1880 --viewportWidth=2000 --viewportHeight=1800 --output=/output/nodered.png; sudo convert /tmp/nodered.png -crop 1350x1400+180+10 /tmp/ss.png`
