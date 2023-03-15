# pylint: disable=undefined-variable
now = dt_util.now()
UNKNOWN = 'unknown'

zone_entity_id = data.get("entity_id")

if not zone_entity_id:
    raise Exception("entity_id is required to execute this script")

zone = hass.states.get(zone_entity_id)

if not zone:
    raise Exception("Entity with id {} does not exist".format(zone_entity_id))

device_name = zone.attributes.get("device_name")
zone_name = zone.attributes.get("zone_name")

if not device_name:
    raise Exception(
        "Could not find zone's device name on entity {}. Is this a BHyve zone switch entity?".format(
            zone_entity_id
        )
    )

logger.info("updating next_watering for zone: ({}: {})".format(zone_name, zone))

next_watering_entity = f"sensor.{zone_name}_next_watering".replace(" ", "_").replace("-", "_").lower()
next_watering_attrs = {"friendly_name": f"{zone_name} next watering", "device_class": "timestamp"}

rain_delay_finishing_entity = f"sensor.{device_name}_rain_delay_finishing".replace(
    " ", "_"
).replace("-", "_").lower()
rain_delay_finishing_attrs = {"friendly_name": f"{device_name} rain delay finishing", "device_class": "timestamp"}

rain_delay = hass.states.get(f"switch.{device_name}_rain_delay".replace(
    " ", "_"
).replace("-", "_").lower())

if zone.state == "unavailable":
    hass.states.set(next_watering_entity, "Unavailable", next_watering_attrs)
    hass.states.set(
        rain_delay_finishing_entity, "Unavailable", rain_delay_finishing_attrs
    )
else:
    delay_finishes_at = UNKNOWN
    next_watering = UNKNOWN

    if rain_delay.state == "on":
        started_at = dt_util.as_timestamp(rain_delay.attributes.get("started_at"))
        delay_seconds = rain_delay.attributes.get("delay") * 3600
        delay_finishes_at = dt_util.as_local(
            dt_util.utc_from_timestamp(started_at + delay_seconds)
        )
        hass.states.set(
            rain_delay_finishing_entity, delay_finishes_at.isoformat(), rain_delay_finishing_attrs
        )
    else:
        hass.states.set(
            rain_delay_finishing_entity, delay_finishes_at, rain_delay_finishing_attrs
        )

    for program_id in ["a", "b", "c", "e"]:
        program = zone.attributes.get(f"program_{program_id}")
        logger.info("program: %s", program)
        if program is None or program.get("enabled", False) is False:
            continue

        if program.get("is_smart_program"):
            for timestamp in program.get("watering_program", []):
                watering_time = dt_util.parse_datetime(str(timestamp))
                if watering_time > now and (
                    delay_finishes_at is UNKNOWN or watering_time > delay_finishes_at
                ):
                    next_watering = watering_time
                    break
        else:
            """ find the next manual watering time """
            """
                Orbit day: `0` is Sunday, `1` is Monday
                Python day: `0` is Monday, `2` is Tuesday
            """

            """
                ************
                    TODO
                ************
            """

            """
            {
                'enabled': True, 
                'name': 'Garden Morning', 
                'is_smart_program': False, 
                'start_times': ['08:30'], 
                'frequency': 
                    {'type': 'interval', 
                    'interval': 1, 
                    'interval_start_time': '2023-03-07T06:00:00.000Z'},
                'run_times': [{'run_time': 30, 'station': 1}]
            }
            """

            logger.info("Checking manual program: %s", program)
            configured_days = program.get("frequency", {}).get("days")
            start_times = program.get("start_times")
            if configured_days is None:
                continue

            # now_weekday = now.weekday()

            # next_watering_day = (
            #         filter(lambda day: (day > now_weekday), configured_days)
            #     )[0]# else configured_days[0]


    if next_watering == UNKNOWN:
        hass.states.set(next_watering_entity, next_watering, next_watering_attrs)
    else:
        hass.states.set(next_watering_entity, next_watering.isoformat(), next_watering_attrs)
