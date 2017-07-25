$(function(){ //DOM Ready

    function navigate(url)
    {
        window.location.href = url;
    }

    $(document).attr("title", "308 Fraternity Row");
    content_width = (120 + 8) * 6 + 8
    $('.gridster').width(content_width)
    $(".gridster ul").gridster({
        widget_margins: [8, 8],
        widget_base_dimensions: [120, 120],
        avoid_overlapped_widgets: true,
        max_rows: 15,
        max_size_x: 6,
        shift_widgets_up: false
    }).data('gridster').disable();
    
    // Add Widgets

    var gridster = $(".gridster ul").gridster().data('gridster');
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseclock-default-clock" id="default-clock"><h1 class="date"data-bind="text: date, attr: {style: date_style}"></h1><h2 class="time" data-bind="text: time, attr: {style: time_style}"></h2></div></li>', 2, 1, 1, 1)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseweather-default-weather" id="default-weather"><h1 class="title" data-bind="text: title, attr:{ style: title_style}"></h1><div data-bind="attr: {style: main_style}">	<p class="primary-climacon" data-bind="html: dark_sky_icon"></p>	<p class="primary-info" data-bind="text: dark_sky_temperature"></p>	<p class="primary-unit" data-bind="html: unit, attr: {style: unit_style}"></p><br><div data-bind="attr: {style: sub_style}">	<p class="secondary-info">Humidity:&nbsp;</p>	<p class="secondary-info" data-bind="text: dark_sky_humidity"></p>	<p class="secondary-info">%</p>	<br>	<p class="secondary-info">Apparent Temp:&nbsp;</p>	<p class="secondary-info" data-bind="html: dark_sky_apparent_temperature"></p>	<p class="secondary-info" data-bind="html: unit"></p>	<br>	<p class="secondary-info">Rain:&nbsp;</p>	<p class="secondary-info" data-bind="text: dark_sky_precip_probability"></p>	<p class="secondary-info">&nbsp;%</p>	<p class="secondary-info">&nbsp;/&nbsp;</p>	<p class="secondary-info" data-bind="text: dark_sky_precip_intensity"></p>	<p class="secondary-info">in</p>	<br>	<p class="secondary-info">Wind:&nbsp;</p>	<p class="secondary-info" data-bind="text: dark_sky_wind_speed"></p>	<p class="secondary-info">&nbsp;Mph</p>	<p class="secondary-info">&nbsp;/&nbsp;</p>	<p class="secondary-info" data-bind="html: dark_sky_wind_bearing"></p>	<p class="secondary-info">&nbsp;&deg;</p>	<br>	<p class="secondary-info">Pressure:&nbsp;</p>	<p class="secondary-info" data-bind="text: dark_sky_pressure"></p>	<p class="secondary-info">&nbsp;Mbar</p></div></div></li>', 2, 2, 3, 1)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-basedisplay-default-sensor-front-door-status" id="default-sensor-front-door-status"><h1 class="title" data-bind="text: title, attr:{ style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{ style: title2_style}"></h1><div class="valueunit"><h2 class="value" data-bind="html: value, attr:{ style: value_style}"></h2><p class="unit" data-bind="html: unit, attr:{ style: unit_style}"></p></div><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 5, 1)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-basedisplay-default-sensor-back-door-status" id="default-sensor-back-door-status"><h1 class="title" data-bind="text: title, attr:{ style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{ style: title2_style}"></h1><div class="valueunit"><h2 class="value" data-bind="html: value, attr:{ style: value_style}"></h2><p class="unit" data-bind="html: unit, attr:{ style: unit_style}"></p></div><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 6, 1)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-basedisplay-default-moon" id="default-moon"><h1 class="title" data-bind="text: title, attr:{ style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{ style: title2_style}"></h1><div class="valueunit"><h2 class="value" data-bind="html: value, attr:{ style: value_style}"></h2><p class="unit" data-bind="html: unit, attr:{ style: unit_style}"></p></div><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 2, 1, 1, 2)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseswitch-default-living-room" id="default-living-room"><span class="toggle-area" id="switch"></span><h1 class="title" data-bind="text: title, attr:{style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{style: title2_style}"></h1><h2 class="icon" data-bind="attr:{style: icon_style}"><i data-bind="attr: {class: icon}"></i></h2><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 2, 1, 5, 2)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-basedisplay-default-thermostat-state" id="default-thermostat-state"><h1 class="title" data-bind="text: title, attr:{ style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{ style: title2_style}"></h1><div class="valueunit"><h2 class="value" data-bind="html: value, attr:{ style: value_style}"></h2><p class="unit" data-bind="html: unit, attr:{ style: unit_style}"></p></div><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 1, 3)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-basedisplay-default-sensor-thermostat-operating-mode" id="default-sensor-thermostat-operating-mode"><h1 class="title" data-bind="text: title, attr:{ style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{ style: title2_style}"></h1><div class="valueunit"><h2 class="value" data-bind="html: value, attr:{ style: value_style}"></h2><p class="unit" data-bind="html: unit, attr:{ style: unit_style}"></p></div><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 2, 3)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseclimate-default-thermostat" id="default-thermostat"><h1 class="title" data-bind="text: title, attr:{style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{style: title2_style}"></h1><div class="levelunit"><h2 class="level" data-bind="text: level, attr:{ style: level_style}"></h2><p class="unit" data-bind="html: unit, attr:{ style: unit_style}"></p></div><div class="levelunit2"><p class="level2" data-bind="text: level2, attr:{style: level2_style}"></p><p class="unit2" data-bind="html: unit, attr:{style: unit2_style}"></p></div><p class="secondary-icon minus"><i data-bind="attr: {class: icon_down, style: level_down_style}" id="level-down"></i></p><p class="secondary-icon plus"><i data-bind="attr: {class: icon_up, style: level_up_style}" id="level-up"></i></p></div></li>', 2, 1, 3, 3)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseswitch-default-living-room-lamp-1" id="default-living-room-lamp-1"><span class="toggle-area" id="switch"></span><h1 class="title" data-bind="text: title, attr:{style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{style: title2_style}"></h1><h2 class="icon" data-bind="attr:{style: icon_style}"><i data-bind="attr: {class: icon}"></i></h2><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 5, 3)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseswitch-default-living-room-lamp-2" id="default-living-room-lamp-2"><span class="toggle-area" id="switch"></span><h1 class="title" data-bind="text: title, attr:{style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{style: title2_style}"></h1><h2 class="icon" data-bind="attr:{style: icon_style}"><i data-bind="attr: {class: icon}"></i></h2><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 6, 3)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseiframe-default-weather-radar" id="default-weather-radar"><div class="outer-frame iframe"><iframe class="scaled-frame" data-bind="attr: {style: frame_style, src: frame_src}" allowfullscreen></iframe></div><div class="outer-image"><img class="img-frame" data-bind="attr: {src: img_src}"></img></div><h1 class="title" data-bind="text: title, attr: {style: title_style}"></h1></div></li>', 2, 2, 1, 4)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseswitch-default-set-75" id="default-set-75"><span class="toggle-area" id="switch"></span><h1 class="title" data-bind="text: title, attr:{style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{style: title2_style}"></h1><h2 class="icon" data-bind="attr:{style: icon_style}"><i data-bind="attr: {class: icon}"></i></h2><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 3, 4)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseswitch-default-set-78" id="default-set-78"><span class="toggle-area" id="switch"></span><h1 class="title" data-bind="text: title, attr:{style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{style: title2_style}"></h1><h2 class="icon" data-bind="attr:{style: icon_style}"><i data-bind="attr: {class: icon}"></i></h2><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 4, 4)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseswitch-default-kitchen-light" id="default-kitchen-light"><span class="toggle-area" id="switch"></span><h1 class="title" data-bind="text: title, attr:{style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{style: title2_style}"></h1><h2 class="icon" data-bind="attr:{style: icon_style}"><i data-bind="attr: {class: icon}"></i></h2><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 5, 4)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseswitch-default-set-82" id="default-set-82"><span class="toggle-area" id="switch"></span><h1 class="title" data-bind="text: title, attr:{style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{style: title2_style}"></h1><h2 class="icon" data-bind="attr:{style: icon_style}"><i data-bind="attr: {class: icon}"></i></h2><h1 class="state_text" data-bind="text: state_text, attr: {style: state_text_style}"></h1></div></li>', 1, 1, 3, 5)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-javascript-default-reload" id="default-reload"><span class="toggle-area" id="switch"></span><h1 class="title" data-bind="text: title, attr:{style: title_style}"></h1><h1 class="title2" data-bind="text: title2, attr:{style: title2_style}"></h1><h2 class="icon" data-bind="attr:{style: icon_style}"><i data-bind="attr: {class: icon}"></i></h2></div></li>', 1, 1, 4, 5)
    
        gridster.add_widget('<li><div data-bind="attr: {style: widget_style}" class="widget widget-baseiframe-default-mail" id="default-mail"><div class="outer-frame iframe"><iframe class="scaled-frame" data-bind="attr: {style: frame_style, src: frame_src}" allowfullscreen></iframe></div><div class="outer-image"><img class="img-frame" data-bind="attr: {src: img_src}"></img></div><h1 class="title" data-bind="text: title, attr: {style: title_style}"></h1></div></li>', 4, 2, 1, 6)
    
    
    
    var widgets = {}
    // Initialize Widgets
    
        widgets["default-clock"] = new baseclock("default-clock", "http://10.0.1.22:5050", "default", {'precision': 1, 'static_icons': [], 'use_hass_icon': 1, 'static_css': {'date_style': 'color: #fff;', 'time_style': 'color: #aa00ff;', 'widget_style': 'background-color: #444;'}, 'fields': {'date': '', 'time': ''}, 'icons': [], 'use_comma': 0, 'css': {}, 'widget_type': 'baseclock'})
    
        widgets["default-weather"] = new baseweather("default-weather", "http://10.0.1.22:5050", "default", {'css': {}, 'precision': 1, 'use_hass_icon': 1, 'static_css': {'unit_style': 'color: #ffaa00;', 'sub_style': 'color: #00aaff;', 'title_style': 'color: #00aaff;', 'main_style': 'color: #ffaa00;', 'widget_style': 'background-color: #444;'}, 'units': '&deg;F', 'fields': {'unit': '', 'dark_sky_temperature': '', 'dark_sky_pressure': '', 'dark_sky_wind_bearing': '', 'dark_sky_precip_intensity': '', 'dark_sky_wind_speed': '', 'dark_sky_icon': '', 'dark_sky_apparent_temperature': '', 'title': '', 'dark_sky_humidity': '', 'dark_sky_precip_probability': ''}, 'icons': [], 'use_comma': 0, 'static_icons': [], 'widget_type': 'baseweather'})
    
        widgets["default-sensor-front-door-status"] = new basedisplay("default-sensor-front-door-status", "http://10.0.1.22:5050", "default", {'static_icons': [], 'title_is_friendly_name': 1, 'precision': 1, 'css': {'unit_style': 'color: #00aaff;font-size: 100%;', 'value_style': 'color: #00aaff;font-size: 250%;', 'text_style': 'color: #fff;font-size: 100%;'}, 'sub_entity': '', 'use_hass_icon': 1, 'static_css': {'unit_style': '', 'title_style': 'color: #fff;', 'state_text_style': '', 'title2_style': 'color: #fff;', 'value_style': '', 'widget_style': 'background-color: #444;'}, 'fields': {'title': '', 'value': '', 'unit': '', 'state_text': '', 'title2': ''}, 'icons': [], 'use_comma': 0, 'entity': 'sensor.front_door_status', 'widget_type': 'basedisplay'})
    
        widgets["default-sensor-back-door-status"] = new basedisplay("default-sensor-back-door-status", "http://10.0.1.22:5050", "default", {'static_icons': [], 'title_is_friendly_name': 1, 'precision': 1, 'css': {'unit_style': 'color: #00aaff;font-size: 100%;', 'value_style': 'color: #00aaff;font-size: 250%;', 'text_style': 'color: #fff;font-size: 100%;'}, 'sub_entity': '', 'use_hass_icon': 1, 'static_css': {'unit_style': '', 'title_style': 'color: #fff;', 'state_text_style': '', 'title2_style': 'color: #fff;', 'value_style': '', 'widget_style': 'background-color: #444;'}, 'fields': {'title': '', 'value': '', 'unit': '', 'state_text': '', 'title2': ''}, 'icons': [], 'use_comma': 0, 'entity': 'sensor.back_door_status', 'widget_type': 'basedisplay'})
    
        widgets["default-moon"] = new basedisplay("default-moon", "http://10.0.1.22:5050", "default", {'entity': 'sensor.moon_phase', 'precision': 1, 'use_hass_icon': 1, 'static_css': {'unit_style': '', 'title_style': 'color: #fff;', 'state_text_style': '', 'title2_style': 'color: #fff;', 'value_style': '', 'widget_style': 'background-color: #444;'}, 'widget_type': 'basedisplay', 'fields': {'title': 'Moon Phase', 'value': '', 'unit': '', 'state_text': '', 'title2': ''}, 'icons': [], 'use_comma': 0, 'sub_entity': '', 'css': {'unit_style': 'color: #00aaff;font-size: 100%;', 'value_style': 'color: #00aaff;font-size: 250%;', 'text_style': 'color: #fff;font-size: 100%;'}, 'static_icons': []})
    
        widgets["default-living-room"] = new baseswitch("default-living-room", "http://10.0.1.22:5050", "default", {'post_service_active': {'entity_id': 'group.living_room', 'service': 'homeassistant/turn_on'}, 'icon_on': 'mdi-lightbulb-on', 'enable': 1, 'state_inactive': 'off', 'entity': 'group.living_room', 'css': {'icon_style_inactive': 'color: #888;', 'icon_style_active': 'color: #aaff00;'}, 'precision': 1, 'state_active': 'on', 'icon_off': 'mdi-lightbulb-on-outline', 'use_hass_icon': 1, 'static_css': {'widget_style': 'background-color: #444;', 'title_style': 'color: #fff;', 'state_text_style': 'color: #fff;', 'title2_style': 'color: #fff;'}, 'post_service_inactive': {'entity_id': 'group.living_room', 'service': 'homeassistant/turn_off'}, 'fields': {'title': 'Living Room Lamps Toggle', 'state_text': '', 'title2': '', 'icon': '', 'icon_style': ''}, 'icons': {'icon_off': 'mdi-lightbulb-on-outline', 'icon_on': 'mdi-lightbulb-on'}, 'use_comma': 0, 'static_icons': [], 'widget_type': 'baseswitch'})
    
        widgets["default-thermostat-state"] = new basedisplay("default-thermostat-state", "http://10.0.1.22:5050", "default", {'entity': 'sensor.thermostat_state', 'precision': 1, 'use_hass_icon': 1, 'static_css': {'unit_style': '', 'title_style': 'color: #fff;', 'state_text_style': '', 'title2_style': 'color: #fff;', 'value_style': '', 'widget_style': 'background-color: #444;'}, 'widget_type': 'basedisplay', 'fields': {'title': 'Thermostat State', 'value': '', 'unit': '', 'state_text': '', 'title2': ''}, 'icons': [], 'use_comma': 0, 'sub_entity': '', 'css': {'unit_style': 'color: #00aaff;font-size: 100%;', 'value_style': 'color: #00aaff;font-size: 250%;', 'text_style': 'color: #fff;font-size: 100%;'}, 'static_icons': []})
    
        widgets["default-sensor-thermostat-operating-mode"] = new basedisplay("default-sensor-thermostat-operating-mode", "http://10.0.1.22:5050", "default", {'static_icons': [], 'title_is_friendly_name': 1, 'precision': 1, 'css': {'unit_style': 'color: #00aaff;font-size: 100%;', 'value_style': 'color: #00aaff;font-size: 250%;', 'text_style': 'color: #fff;font-size: 100%;'}, 'sub_entity': '', 'use_hass_icon': 1, 'static_css': {'unit_style': '', 'title_style': 'color: #fff;', 'state_text_style': '', 'title2_style': 'color: #fff;', 'value_style': '', 'widget_style': 'background-color: #444;'}, 'fields': {'title': '', 'value': '', 'unit': '', 'state_text': '', 'title2': ''}, 'icons': [], 'use_comma': 0, 'entity': 'sensor.thermostat_operating_mode', 'widget_type': 'basedisplay'})
    
        widgets["default-thermostat"] = new baseclimate("default-thermostat", "http://10.0.1.22:5050", "default", {'static_icons': {'icon_down': 'fa-minus', 'icon_up': 'fa-plus'}, 'units': '&deg;F', 'css': {}, 'widget_type': 'baseclimate', 'entity': 'climate.thermostat', 'precision': 1, 'use_hass_icon': 1, 'static_css': {'unit_style': 'color: #00aaff;', 'level_style': 'color: #00aaff;', 'level2_style': 'color: #00aaff;', 'title_style': 'color: #fff;', 'level_down_style': 'color: #888;', 'title2_style': 'color: #fff;', 'unit2_style': 'color: #00aaff;', 'level_up_style': 'color: #888;', 'widget_style': 'background-color: #444;'}, 'fields': {'title': 'Thermostat Control', 'title2': 'Readout', 'unit': '', 'level2': '', 'level': ''}, 'icons': [], 'use_comma': 0, 'post_service': {'entity_id': 'climate.thermostat', 'service': 'climate/set_temperature'}})
    
        widgets["default-living-room-lamp-1"] = new baseswitch("default-living-room-lamp-1", "http://10.0.1.22:5050", "default", {'post_service_active': {'entity_id': 'switch.living_room_lamp', 'service': 'homeassistant/turn_on'}, 'icon_on': 'mdi-lightbulb-on', 'enable': 1, 'state_inactive': 'off', 'entity': 'switch.living_room_lamp', 'css': {'icon_style_inactive': 'color: #888;', 'icon_style_active': 'color: #aaff00;'}, 'precision': 1, 'state_active': 'on', 'icon_off': 'mdi-lightbulb-on-outline', 'use_hass_icon': 1, 'static_css': {'widget_style': 'background-color: #444;', 'title_style': 'color: #fff;', 'state_text_style': 'color: #fff;', 'title2_style': 'color: #fff;'}, 'post_service_inactive': {'entity_id': 'switch.living_room_lamp', 'service': 'homeassistant/turn_off'}, 'fields': {'title': 'Living Room Lamp 1 Toggle', 'state_text': '', 'title2': '', 'icon': '', 'icon_style': ''}, 'icons': {'icon_off': 'mdi-lightbulb-on-outline', 'icon_on': 'mdi-lightbulb-on'}, 'use_comma': 0, 'static_icons': [], 'widget_type': 'baseswitch'})
    
        widgets["default-living-room-lamp-2"] = new baseswitch("default-living-room-lamp-2", "http://10.0.1.22:5050", "default", {'post_service_active': {'entity_id': 'switch.wemo_switch', 'service': 'homeassistant/turn_on'}, 'icon_on': 'mdi-lightbulb-on', 'enable': 1, 'state_inactive': 'off', 'entity': 'switch.wemo_switch', 'css': {'icon_style_inactive': 'color: #888;', 'icon_style_active': 'color: #aaff00;'}, 'precision': 1, 'state_active': 'on', 'icon_off': 'mdi-lightbulb-on-outline', 'use_hass_icon': 1, 'static_css': {'widget_style': 'background-color: #444;', 'title_style': 'color: #fff;', 'state_text_style': 'color: #fff;', 'title2_style': 'color: #fff;'}, 'post_service_inactive': {'entity_id': 'switch.wemo_switch', 'service': 'homeassistant/turn_off'}, 'fields': {'title': 'Living Room Lamp 2 Toggle', 'state_text': '', 'title2': '', 'icon': '', 'icon_style': ''}, 'icons': {'icon_off': 'mdi-lightbulb-on-outline', 'icon_on': 'mdi-lightbulb-on'}, 'use_comma': 0, 'static_icons': [], 'widget_type': 'baseswitch'})
    
        widgets["default-weather-radar"] = new baseiframe("default-weather-radar", "http://10.0.1.22:5050", "default", {'css': {}, 'precision': 1, 'use_hass_icon': 1, 'static_css': {'title_style': 'color: #fff;background-color: rgba(0, 0, 0, 0.5);', 'widget_style': 'background-color: #444;'}, 'img_list': ['https://icons.wxug.com/data/weather-maps/radar/united-states/san-antonio-texas-region-current-radar-animation.gif'], 'refresh': 300, 'fields': {'title': 'Radar', 'img_src': '', 'frame_style': '""', 'frame_src': ''}, 'icons': [], 'use_comma': 0, 'static_icons': [], 'widget_type': 'baseiframe'})
    
        widgets["default-set-75"] = new baseswitch("default-set-75", "http://10.0.1.22:5050", "default", {'post_service_active': {'entity_id': 'script.set_ac_75', 'service': 'homeassistant/turn_on'}, 'ignore_state': 1, 'post_service_inactive': {'entity_id': 'script.set_ac_75', 'service': 'homeassistant/turn_off'}, 'icon_on': 'fa-thermometer-1', 'static_icons': [], 'enable': 1, 'state_inactive': 'off', 'widget_type': 'baseswitch', 'css': {'icon_style_inactive': 'color: #888;', 'icon_style_active': 'color: #aaff00;'}, 'precision': 1, 'state_active': 'on', 'icon_off': 'fa-thermometer-1', 'use_hass_icon': 1, 'static_css': {'widget_style': 'background-color: #444;', 'title_style': 'color: #fff;', 'state_text_style': 'color: #fff;', 'title2_style': 'color: #fff;'}, 'momentary': 1000, 'fields': {'title': 'Set AC to 75', 'state_text': '', 'title2': '', 'icon': '', 'icon_style': ''}, 'icons': {'icon_off': 'fa-thermometer-1', 'icon_on': 'fa-thermometer-1'}, 'use_comma': 0, 'entity': 'script.set_ac_75'})
    
        widgets["default-set-78"] = new baseswitch("default-set-78", "http://10.0.1.22:5050", "default", {'post_service_active': {'entity_id': 'script.set_ac_78', 'service': 'homeassistant/turn_on'}, 'ignore_state': 1, 'post_service_inactive': {'entity_id': 'script.set_ac_78', 'service': 'homeassistant/turn_off'}, 'icon_on': 'fa-thermometer-half', 'static_icons': [], 'enable': 1, 'state_inactive': 'off', 'widget_type': 'baseswitch', 'css': {'icon_style_inactive': 'color: #888;', 'icon_style_active': 'color: #aaff00;'}, 'precision': 1, 'state_active': 'on', 'icon_off': 'fa-thermometer-half', 'use_hass_icon': 1, 'static_css': {'widget_style': 'background-color: #444;', 'title_style': 'color: #fff;', 'state_text_style': 'color: #fff;', 'title2_style': 'color: #fff;'}, 'momentary': 1000, 'fields': {'title': 'Set AC to 78', 'state_text': '', 'title2': '', 'icon': '', 'icon_style': ''}, 'icons': {'icon_off': 'fa-thermometer-half', 'icon_on': 'fa-thermometer-half'}, 'use_comma': 0, 'entity': 'script.set_ac_78'})
    
        widgets["default-kitchen-light"] = new baseswitch("default-kitchen-light", "http://10.0.1.22:5050", "default", {'post_service_active': {'entity_id': 'switch.kitchen_table_light_switch', 'service': 'homeassistant/turn_on'}, 'icon_on': 'mdi-lightbulb-on', 'enable': 1, 'state_inactive': 'off', 'entity': 'switch.kitchen_table_light_switch', 'css': {'icon_style_inactive': 'color: #888;', 'icon_style_active': 'color: #aaff00;'}, 'precision': 1, 'state_active': 'on', 'icon_off': 'mdi-lightbulb-on-outline', 'use_hass_icon': 1, 'static_css': {'widget_style': 'background-color: #444;', 'title_style': 'color: #fff;', 'state_text_style': 'color: #fff;', 'title2_style': 'color: #fff;'}, 'post_service_inactive': {'entity_id': 'switch.kitchen_table_light_switch', 'service': 'homeassistant/turn_off'}, 'fields': {'title': 'Kitchen Table Light Toggle', 'state_text': '', 'title2': '', 'icon': '', 'icon_style': ''}, 'icons': {'icon_off': 'mdi-lightbulb-on-outline', 'icon_on': 'mdi-lightbulb-on'}, 'use_comma': 0, 'static_icons': [], 'widget_type': 'baseswitch'})
    
        widgets["default-set-82"] = new baseswitch("default-set-82", "http://10.0.1.22:5050", "default", {'post_service_active': {'entity_id': 'script.set_ac_82', 'service': 'homeassistant/turn_on'}, 'ignore_state': 1, 'post_service_inactive': {'entity_id': 'script.set_ac_82', 'service': 'homeassistant/turn_off'}, 'icon_on': 'fa-thermometer-full', 'static_icons': [], 'enable': 1, 'state_inactive': 'off', 'widget_type': 'baseswitch', 'css': {'icon_style_inactive': 'color: #888;', 'icon_style_active': 'color: #aaff00;'}, 'precision': 1, 'state_active': 'on', 'icon_off': 'fa-thermometer-full', 'use_hass_icon': 1, 'static_css': {'widget_style': 'background-color: #444;', 'title_style': 'color: #fff;', 'state_text_style': 'color: #fff;', 'title2_style': 'color: #fff;'}, 'momentary': 1000, 'fields': {'title': 'Set AC to 82', 'state_text': '', 'title2': '', 'icon': '', 'icon_style': ''}, 'icons': {'icon_off': 'fa-thermometer-full', 'icon_on': 'fa-thermometer-full'}, 'use_comma': 0, 'entity': 'script.set_ac_82'})
    
        widgets["default-reload"] = new javascript("default-reload", "http://10.0.1.22:5050", "default", {'static_icons': [], 'icon_inactive': 'fa-refresh', 'icon_active': 'fa-refresh', 'command': 'location.reload(true)', 'widget_type': 'javascript', 'precision': 1, 'use_hass_icon': 1, 'static_css': {'widget_style': 'background-color: #444;', 'title_style': 'color: #fff;', 'title2_style': 'color: #fff;'}, 'fields': {'title': 'Reload', 'title2': '', 'icon': '', 'icon_style': ''}, 'icons': {'icon_active': 'fa-refresh', 'icon_inactive': 'fa-refresh'}, 'use_comma': 0, 'css': {'icon_active_style': 'color: #fff;', 'icon_inactive_style': 'color: #fff;'}})
    
        widgets["default-mail"] = new baseiframe("default-mail", "http://10.0.1.22:5050", "default", {'entity_picture': 'https://assist.aneis.ch/api/camera_proxy/camera.mail?token=ec8bb6442d250f133e2707f7be3cdfb6ce1f4dfb4d4a7a32e29f36d8974b2fc9&api_password=winfield!', 'precision': 1, 'use_hass_icon': 1, 'static_css': {'title_style': 'color: #fff;background-color: rgba(0, 0, 0, 0.5);', 'widget_style': 'background-color: #444;'}, 'refresh': 300, 'fields': {'title': 'Mail', 'img_src': '', 'frame_style': '""', 'frame_src': ''}, 'icons': [], 'use_comma': 0, 'static_icons': [], 'css': {}, 'widget_type': 'baseiframe'})
    

    // Setup click handler to cancel timeout navigations

    $( ".gridster" ).click(function(){
        clearTimeout(myTimeout);
    });

    // Set up timeout

    var myTimeout

    if (location.search != "")
    {
        var query = location.search.substr(1);
        var result = {};
        query.split("&").forEach(function(part) {
        var item = part.split("=");
        result[item[0]] = decodeURIComponent(item[1]);
        });

        if ("timeout" in result && "return" in result)
        {
            url = result.return
            argcount = 0
            for (arg in result)
            {
                if (arg != "timeout" && arg != "return")
                {
                    if (argcount == 0)
                    {
                        url += "?";
                    }
                    else
                    {
                        url += "?";
                    }
                    argcount ++;
                    url += arg + "=" + result[arg]
                }
            }
            myTimeout = setTimeout(function() { navigate(url); }, result.timeout * 1000);
        }
    }

    // Start listening for HA Events
    if (location.protocol == 'https:')
    {
        wsprot = "wss:"
    }
    else
    {
        wsprot = "ws:"
    }
    var stream_url = wsprot + '//' + location.host + '/stream'
    ha_status(stream_url, "308 Fraternity Row", widgets);

});