"""SoC calculation engine for Sunrise SoC Forecast."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class BatteryConfig:
    """Battery configuration."""

    capacity_kwh: float
    floor_percent: float

    @property
    def floor_kwh(self) -> float:
        return self.capacity_kwh * self.floor_percent / 100

    @property
    def usable_kwh(self) -> float:
        return self.capacity_kwh * (100 - self.floor_percent) / 100


@dataclass
class BackupConfig:
    """Backup battery configuration."""

    enabled: bool
    capacity_kwh: float = 0.0
    floor_percent: float = 0.0
    fixed_discharge_kw: float = 0.0
    activation_hour: int = 2
    mode: str = "always"  # "always" or "target_based"

    @property
    def usable_kwh(self) -> float:
        if not self.enabled:
            return 0.0
        return self.capacity_kwh * (100 - self.floor_percent) / 100


@dataclass
class ConsumptionData:
    """Consumption averages and fallbacks."""

    avg_daily_kwh: float
    avg_overnight_kwh: float
    using_fallback: bool


@dataclass
class OvernightParams:
    """Overnight calculation parameters."""

    overnight_hours: float
    avg_overnight_kw: float
    hours_sunset_to_activation: float
    hours_activation_to_sunrise: float


@dataclass
class DayResult:
    """Result of a day's SoC prediction."""

    soc_percent: float
    predicted_kwh: float
    solcast_kwh: float = 0.0
    daytime_consumption_kwh: float = 0.0
    backup_charged_kwh: float = 0.0
    grid_needed_kwh: float = 0.0
    morning_low_kwh: float = 0.0
    morning_low_pct: float = 0.0
    floor_hour: str | None = None
    night_floor_hour: str | None = None


@dataclass
class DaytimeResult:
    """Result of daytime simulation."""

    sunset_kwh: float
    surplus_kwh: float
    morning_low_kwh: float
    day_low_hour: str | None = None
    total_consumption_kwh: float = 0.0


def simulate_daytime(
    start_kwh: float,
    solar_total_kwh: float,
    daytime_consumption_kwh: float,
    daytime_hours: float,
    battery_cap: float,
    battery_floor: float,
    hourly_consumption: list[float] | None = None,
    sunrise_hour: float = 6.0,
    hourly_solar: list[float] | None = None,
    inverter_efficiency: float = 1.0,
    sunset_hour: float = 18.0,
) -> DaytimeResult:
    """Simulate hour-by-hour daytime using a sine curve for solar production.

    If hourly_consumption is provided (24 floats, kWh per hour), uses actual
    hourly rates for the daytime hours. Otherwise falls back to flat rate.

    Returns DaytimeResult with sunset_kwh, surplus energy, and morning low.
    morning_low_kwh = lowest battery level before solar exceeds consumption.
    """
    # Calculate steps from actual hour span (fix #3)
    if hourly_consumption and len(hourly_consumption) == 24:
        steps = max(1, int(math.ceil(sunset_hour)) - int(math.floor(sunrise_hour)))
    else:
        steps = max(1, int(round(daytime_hours)))

    # Build per-step consumption from hourly data or flat rate
    if hourly_consumption and len(hourly_consumption) == 24:
        consumption_per_step = []
        sr_int = int(math.floor(sunrise_hour))
        for i in range(steps):
            hour_idx = (sr_int + i) % 24
            if i == 0:
                frac = 1.0 - (sunrise_hour - math.floor(sunrise_hour))
            elif i == steps - 1:
                frac = sunset_hour - math.floor(sunset_hour)
                if frac <= 0:
                    frac = 1.0
            else:
                frac = 1.0
            consumption_per_step.append(hourly_consumption[hour_idx] * frac)
    else:
        flat_rate = daytime_consumption_kwh / steps if steps > 0 else 0
        consumption_per_step = [flat_rate] * steps

    # Solar production per step: use forecast data if available, else sine curve
    if hourly_solar and len(hourly_solar) == 96:
        # Quarter-hourly forecast (Open-Meteo): 96 entries, run 4 steps per hour
        sr_qtr = int(math.floor(sunrise_hour * 4))
        ss_qtr = int(math.ceil(sunset_hour * 4))
        qtr_steps = max(1, ss_qtr - sr_qtr)

        # Rebuild consumption for quarter-hour steps
        if hourly_consumption and len(hourly_consumption) == 24:
            consumption_per_step = []
            for i in range(qtr_steps):
                hidx = (sr_qtr + i) // 4 % 24
                frac = 0.25  # quarter-hour = quarter the hourly rate
                if i == 0:
                    frac *= (1.0 - (sunrise_hour * 4 - math.floor(sunrise_hour * 4)))
                elif i == qtr_steps - 1:
                    f = sunset_hour * 4 - math.floor(sunset_hour * 4)
                    frac *= f if f > 0 else 1.0
                consumption_per_step.append(hourly_consumption[hidx] * frac)
        else:
            flat_qtr = daytime_consumption_kwh / qtr_steps if qtr_steps > 0 else 0
            consumption_per_step = [flat_qtr] * qtr_steps

        solar_per_step = []
        for i in range(qtr_steps):
            sidx = (sr_qtr + i) % 96
            val = hourly_solar[sidx]
            if i == 0:
                elapsed_frac = sunrise_hour * 4 - math.floor(sunrise_hour * 4)
                val *= (1.0 - elapsed_frac) if elapsed_frac > 0 else 1.0
            elif i == qtr_steps - 1:
                f = sunset_hour * 4 - math.floor(sunset_hour * 4)
                if f > 0:
                    val *= f
            solar_per_step.append(val)

        steps = qtr_steps
    elif hourly_solar and len(hourly_solar) == 48:
        # Half-hourly Solcast forecast: 48 entries, run 2 steps per hour
        sr_half = int(math.floor(sunrise_hour * 2))
        ss_half = int(math.ceil(sunset_hour * 2))
        half_steps = max(1, ss_half - sr_half)

        # Rebuild consumption for half-hour steps
        if hourly_consumption and len(hourly_consumption) == 24:
            consumption_per_step = []
            for i in range(half_steps):
                hidx = (sr_half + i) // 2 % 24
                frac = 0.5  # half-hour = half the hourly rate
                if i == 0:
                    frac *= (1.0 - (sunrise_hour * 2 - math.floor(sunrise_hour * 2)))
                elif i == half_steps - 1:
                    f = sunset_hour * 2 - math.floor(sunset_hour * 2)
                    frac *= f if f > 0 else 1.0
                consumption_per_step.append(hourly_consumption[hidx] * frac)
        else:
            flat_half = daytime_consumption_kwh / half_steps if half_steps > 0 else 0
            consumption_per_step = [flat_half] * half_steps

        solar_per_step = []
        for i in range(half_steps):
            sidx = (sr_half + i) % 48
            val = hourly_solar[sidx]
            if i == 0:
                elapsed_frac = sunrise_hour * 2 - math.floor(sunrise_hour * 2)
                val *= (1.0 - elapsed_frac) if elapsed_frac > 0 else 1.0
            elif i == half_steps - 1:
                f = sunset_hour * 2 - math.floor(sunset_hour * 2)
                if f > 0:
                    val *= f
            solar_per_step.append(val)

        steps = half_steps  # override step count for the simulation loop
    elif hourly_solar and len(hourly_solar) == 24:
        # Hourly Solcast forecast (fallback from detailedHourly)
        sr_int = int(math.floor(sunrise_hour))
        solar_per_step = []
        for i in range(steps):
            hour_idx = (sr_int + i) % 24
            val = hourly_solar[hour_idx]
            if i == 0:
                elapsed_frac = sunrise_hour - math.floor(sunrise_hour)
                val *= (1.0 - elapsed_frac) if elapsed_frac > 0 else 1.0
            elif i == steps - 1:
                f = sunset_hour - math.floor(sunset_hour)
                if f > 0:
                    val *= f
            solar_per_step.append(val)
    else:
        # Fallback: sine curve distribution
        solar_factors = [math.sin((i + 0.5) / steps * math.pi) for i in range(steps)]
        factor_sum = sum(solar_factors)
        if factor_sum > 0:
            solar_per_step = [(f / factor_sum) * solar_total_kwh for f in solar_factors]
        else:
            solar_per_step = [solar_total_kwh / steps] * steps

    battery = start_kwh
    surplus = 0.0
    day_low = start_kwh
    day_low_hour = None
    floor_hit = False

    # Determine step size in hours for time tracking
    if len(solar_per_step) == steps:
        step_hours = (sunset_hour - sunrise_hour) / steps if steps > 0 else 1.0
    else:
        step_hours = 1.0

    eff = inverter_efficiency if inverter_efficiency > 0 else 1.0

    for i in range(steps):
        consumption_dc = consumption_per_step[i] / eff
        battery += solar_per_step[i] - consumption_dc
        if battery > battery_cap:
            surplus += battery - battery_cap
            battery = battery_cap
        if battery < battery_floor:
            battery = battery_floor

        if battery < day_low:
            day_low = battery
            day_low_hour = sunrise_hour + (i + 1) * step_hours

        if battery <= battery_floor and not floor_hit:
            floor_hit = True
            day_low_hour = sunrise_hour + (i + 1) * step_hours

    # Format floor_hour as HH:MM
    floor_hour_str = None
    if floor_hit and day_low_hour is not None:
        h = int(day_low_hour)
        m = int((day_low_hour - h) * 60)
        floor_hour_str = f"{h:02d}:{m:02d}"

    return DaytimeResult(
        sunset_kwh=battery,
        surplus_kwh=surplus,
        morning_low_kwh=day_low,
        day_low_hour=floor_hour_str,
        total_consumption_kwh=round(sum(consumption_per_step), 2),
    )


def calc_overnight_drain_hourly(
    sunset_kwh: float,
    backup_charged_kwh: float,
    backup_kw: float,
    backup_activation_hour: int,
    hourly_consumption: list[float],
    sunset_hour: float,
    sunrise_hour: float,
    main_floor_kwh: float,
    main_cap: float,
    backup_mode: str = "always",
    target_kwh: float = 0.0,
    inverter_efficiency: float = 1.0,
    backup_discharge_efficiency: float = 1.0,
) -> float:
    """Calculate overnight drain using hourly consumption rates.

    Steps hour-by-hour from sunset to sunrise, applying each hour's
    consumption rate and backup battery assist after activation hour.
    """
    battery = sunset_kwh
    backup_remaining = backup_charged_kwh
    ss_int = int(math.floor(sunset_hour))
    sr_int = int(math.floor(sunrise_hour)) % 24

    # Guard: if overnight is effectively zero, return sunset value
    if ss_int == sr_int:
        return max(main_floor_kwh, min(main_cap, sunset_kwh))

    def _is_backup_active(hour: int) -> bool:
        """Check if backup should be active at this hour."""
        if backup_kw <= 0 or backup_remaining <= 0:
            return False
        h24 = hour % 24
        # Backup active from activation_hour to sunrise (wrapping through midnight)
        if backup_activation_hour <= sr_int:
            return backup_activation_hour <= h24 < sr_int
        else:
            return h24 >= backup_activation_hour or h24 < sr_int

    def _drain_hour(bat: float, br: float, h: int, frac: float, use_backup: bool) -> tuple[float, float]:
        """Drain one hour of consumption from battery."""
        eff = inverter_efficiency if inverter_efficiency > 0 else 1.0
        consumption_dc = hourly_consumption[h % 24] * frac / eff

        if use_backup and br > 0 and backup_kw > 0 and _is_backup_active(h):
            backup_energy = min(br, backup_kw * frac)
            consumption_dc -= backup_energy * backup_discharge_efficiency / eff
            br -= backup_energy

        bat -= consumption_dc
        if bat < main_floor_kwh:
            bat = main_floor_kwh
        if bat > main_cap:
            bat = main_cap
        return bat, br

    def _run_overnight(use_backup: bool) -> tuple[float, str | None]:
        """Simulate overnight drain. Returns (sunrise_kwh, floor_hour or None)."""
        nonlocal backup_remaining
        bat = sunset_kwh
        br = backup_charged_kwh if use_backup else 0.0
        h = ss_int
        night_floor_hour = None

        def _step(bat_v, br_v, hour, frac):
            nonlocal night_floor_hour
            bat_v, br_v = _drain_hour(bat_v, br_v, hour, frac, use_backup)
            if bat_v <= main_floor_kwh and night_floor_hour is None:
                nh = (hour + 1) % 24
                night_floor_hour = f"{nh:02d}:00"
            return bat_v, br_v

        # First hour: fractional entry
        entry_frac = 1.0 - (sunset_hour - math.floor(sunset_hour))
        if h == sr_int:
            frac = max(0, sunrise_hour - sunset_hour)
            bat, br = _step(bat, br, h, frac)
        else:
            bat, br = _step(bat, br, h, entry_frac)
            h = (h + 1) % 24

            # Middle hours: full consumption
            for _ in range(24):
                if h == sr_int:
                    break
                bat, br = _step(bat, br, h, 1.0)
                h = (h + 1) % 24

            # Sunrise hour: fractional exit
            if h == sr_int:
                exit_frac = sunrise_hour - math.floor(sunrise_hour)
                if exit_frac > 0:
                    bat, br = _step(bat, br, h, exit_frac)

        if use_backup:
            backup_remaining = br
        return bat, night_floor_hour

    # For target-based mode, first check without backup
    if backup_mode == "target_based" and target_kwh > 0:
        no_backup, nfh = _run_overnight(use_backup=False)
        if no_backup >= target_kwh:
            return max(main_floor_kwh, min(main_cap, no_backup)), nfh
        with_backup, nfh = _run_overnight(use_backup=True)
        if with_backup > target_kwh:
            return target_kwh, nfh
        return max(main_floor_kwh, min(main_cap, with_backup)), nfh

    # Always mode
    result, nfh = _run_overnight(use_backup=True)
    return max(main_floor_kwh, min(main_cap, result)), nfh


def get_consumption(
    daily_avg: float | None,
    overnight_avg: float | None,
    default_daily: float,
    default_overnight: float,
    guard_threshold: float,
) -> ConsumptionData:
    """Get consumption data with fallback logic."""
    daily_valid = daily_avg is not None and daily_avg > guard_threshold
    overnight_valid = overnight_avg is not None and overnight_avg > guard_threshold
    both_valid = daily_valid and overnight_valid
    # Daily must be >= overnight — if not, data is corrupt
    sane = both_valid and daily_avg >= overnight_avg

    if sane:
        return ConsumptionData(
            avg_daily_kwh=daily_avg,
            avg_overnight_kwh=overnight_avg,
            using_fallback=False,
        )
    return ConsumptionData(
        avg_daily_kwh=default_daily,
        avg_overnight_kwh=default_overnight,
        using_fallback=True,
    )


def get_overnight_params(
    sunrise: datetime,
    sunset: datetime,
    overnight_kwh: float,
    activation_hour: int,
) -> OvernightParams:
    """Calculate overnight timing parameters."""
    overnight_hours = abs((sunrise - sunset).total_seconds() / 3600)
    if overnight_hours <= 0:
        overnight_hours = 12.0

    avg_overnight_kw = overnight_kwh / overnight_hours

    # Phase split: sunset → activation hour, activation → sunrise
    sunset_local = sunset.astimezone()
    sunset_hour = sunset_local.hour + sunset_local.minute / 60
    hours_to_activation = (24 - sunset_hour) + activation_hour
    if hours_to_activation > overnight_hours:
        hours_to_activation = overnight_hours
    hours_after_activation = overnight_hours - hours_to_activation
    if hours_after_activation < 0:
        hours_after_activation = 0.0

    return OvernightParams(
        overnight_hours=overnight_hours,
        avg_overnight_kw=avg_overnight_kw,
        hours_sunset_to_activation=hours_to_activation,
        hours_activation_to_sunrise=hours_after_activation,
    )


def calc_overnight_drain_no_backup(
    sunset_kwh: float,
    params: OvernightParams,
    main_floor_kwh: float,
    main_cap: float,
    inverter_efficiency: float = 1.0,
) -> float:
    """Calculate sunrise kWh with NO backup assist."""
    eff = inverter_efficiency if inverter_efficiency > 0 else 1.0
    main_kwh = sunset_kwh - (params.avg_overnight_kw * params.overnight_hours / eff)
    return max(main_floor_kwh, min(main_cap, main_kwh))


def calc_overnight_drain_with_backup(
    sunset_kwh: float,
    backup_charged_kwh: float,
    backup_kw: float,
    params: OvernightParams,
    main_floor_kwh: float,
    main_cap: float,
    inverter_efficiency: float = 1.0,
    backup_discharge_efficiency: float = 1.0,
) -> float:
    """Calculate sunrise kWh with backup assist (always mode)."""
    avg_kw = params.avg_overnight_kw
    eff = inverter_efficiency if inverter_efficiency > 0 else 1.0

    # Phase 1: sunset → backup activation, main covers all load
    main_kwh = sunset_kwh - (avg_kw * params.hours_sunset_to_activation / eff)

    # Phase 2: activation → sunrise, backup assists
    h2 = params.hours_activation_to_sunrise
    if backup_charged_kwh > 0 and backup_kw > 0 and h2 > 0:
        backup_hours = backup_charged_kwh / backup_kw
        net_kw = backup_kw * backup_discharge_efficiency / eff - avg_kw / eff
        if backup_hours >= h2:
            main_kwh += net_kw * h2
        else:
            main_kwh += net_kw * backup_hours
            remaining = h2 - backup_hours
            main_kwh -= avg_kw / eff * remaining
    else:
        main_kwh -= avg_kw / eff * h2

    return max(main_floor_kwh, min(main_cap, main_kwh))


def calc_overnight_drain(
    sunset_kwh: float,
    backup_charged_kwh: float,
    backup_kw: float,
    params: OvernightParams,
    main_floor_kwh: float,
    main_cap: float,
    backup_mode: str = "always",
    target_kwh: float = 0.0,
    inverter_efficiency: float = 1.0,
    backup_discharge_efficiency: float = 1.0,
) -> float:
    """Calculate main battery kWh at sunrise after overnight drain.

    backup_mode:
        "always" — backup activates every night at the set hour
        "target_based" — backup only activates if main would drop below target
                         and only discharges enough to reach target
    """
    if backup_mode == "always":
        return calc_overnight_drain_with_backup(
            sunset_kwh, backup_charged_kwh, backup_kw,
            params, main_floor_kwh, main_cap,
            inverter_efficiency=inverter_efficiency,
            backup_discharge_efficiency=backup_discharge_efficiency,
        )

    # Target-based mode: first calculate without backup
    sunrise_no_backup = calc_overnight_drain_no_backup(
        sunset_kwh, params, main_floor_kwh, main_cap,
        inverter_efficiency=inverter_efficiency,
    )

    if sunrise_no_backup >= target_kwh or target_kwh <= 0:
        # Main can handle it alone — backup stays idle
        return sunrise_no_backup

    # Main falls short — calculate with full backup
    sunrise_with_backup = calc_overnight_drain_with_backup(
        sunset_kwh, backup_charged_kwh, backup_kw,
        params, main_floor_kwh, main_cap,
        inverter_efficiency=inverter_efficiency,
        backup_discharge_efficiency=backup_discharge_efficiency,
    )

    # Cap at target — don't use more backup than needed
    if sunrise_with_backup > target_kwh:
        return target_kwh

    # Even with full backup, can't reach target
    return sunrise_with_backup


def predict_day1_daytime(
    current_kwh: float,
    remaining_solar: float,
    hours_to_sunset: float,
    sunrise_hour: float,
    consumption: ConsumptionData,
    main: BatteryConfig,
    backup: BackupConfig,
    backup_soc_pct: float,
    overnight_params: OvernightParams,
    target_kwh: float = 0.0,
    hourly_consumption: list[float] | None = None,
    current_hour: float = 12.0,
    sunset_hour: float = 18.0,
    hourly_solar: list[float] | None = None,
    inverter_efficiency: float = 1.0,
    backup_charge_efficiency: float = 1.0,
    backup_discharge_efficiency: float = 1.0,
    dump_load_profile: list[float] | None = None,
) -> DayResult:
    """Day 1 prediction: continuous simulation from current time to next sunrise.

    One loop from now to sunrise — solar curve naturally tapers to zero after
    sunset, consumption and backup assist continue through the night. No separate
    daytime/nighttime phases or handoff.
    """

    eff = inverter_efficiency if inverter_efficiency > 0 else 1.0

    # Determine step resolution based on solar data
    if hourly_solar and len(hourly_solar) == 96:
        steps_per_hour = 4
    elif hourly_solar and len(hourly_solar) == 48:
        steps_per_hour = 2
    else:
        steps_per_hour = 1

    step_hours = 1.0 / steps_per_hour
    array_len = len(hourly_solar) if hourly_solar else 24

    # Calculate start/end indices and total steps (wrapping through midnight)
    start_idx = int(math.floor(current_hour * steps_per_hour))
    end_idx = int(math.ceil(sunrise_hour * steps_per_hour))

    if hours_to_sunset > 0:
        # Daytime: ~24 hour simulation, always wraps through midnight
        total_steps = (array_len - start_idx) + end_idx
    elif end_idx < start_idx:
        # Nighttime past midnight: wraps (e.g., 23:00 → 06:00)
        total_steps = (array_len - start_idx) + end_idx
    else:
        # Nighttime before sunrise (or right at it): no wrap.
        # When start_idx == end_idx (current_hour ≈ sunrise_hour), this is 0 —
        # avoids a spurious 24h overnight drain at the sunrise boundary.
        total_steps = end_idx - start_idx

    if total_steps <= 0:
        total_steps = 0

    # Build solar values for sine fallback (full 24h, 0 outside solar window)
    if not hourly_solar:
        sr_int = int(math.floor(sunrise_hour))
        ss_int = int(math.ceil(sunset_hour))
        full_day_steps = max(1, ss_int - sr_int)

        sine_solar = [0.0] * 24
        solar_factors = []
        for h in range(sr_int, ss_int):
            t = (h - sr_int + 0.5) / full_day_steps
            solar_factors.append((h % 24, max(0, math.sin(t * math.pi))))
        factor_sum = sum(f for _, f in solar_factors)
        if factor_sum > 0 and remaining_solar > 0:
            for h, f in solar_factors:
                sine_solar[h] = (f / factor_sum) * remaining_solar
        solar_array = sine_solar
    else:
        solar_array = hourly_solar

    # Pre-compute total solar per hour for dump-load excess-solar gating.
    # Dump loads run only if solar covers the base (non-dump) consumption that hour.
    have_dump = bool(dump_load_profile) and len(dump_load_profile or []) == 24
    solar_per_hour: list[float] = [0.0] * 24
    if have_dump:
        for j, v in enumerate(solar_array):
            h = (j // steps_per_hour) % 24
            solar_per_hour[h] += v

    # Backup setup
    backup_current = 0.0
    if backup.enabled:
        backup_current = max(0, (backup_soc_pct - backup.floor_percent) / 100 * backup.capacity_kwh)
    br = backup_current
    backup_kw = backup.fixed_discharge_kw if backup.enabled else 0.0
    activation_hour = backup.activation_hour if backup.enabled else 2

    def _is_backup_active(h: int) -> bool:
        if not backup.enabled or backup_kw <= 0:
            return False
        h24 = h % 24
        sr = int(math.floor(sunrise_hour))
        if activation_hour <= sr:
            return activation_hour <= h24 < sr
        else:
            return h24 >= activation_hour or h24 < sr

    # Continuous simulation: current_hour → sunrise_hour
    battery = current_kwh
    surplus = 0.0
    day_low = current_kwh
    day_low_time = None
    floor_hit = False
    total_consumption = 0.0
    total_solar = 0.0

    for i in range(total_steps):
        idx = (start_idx + i) % array_len
        hour = (idx // steps_per_hour) % 24

        # Fractional first/last steps
        if total_steps == 1:
            frac = max(0.001, sunrise_hour - current_hour)  # actual remaining time
        elif i == 0:
            elapsed = current_hour * steps_per_hour - math.floor(current_hour * steps_per_hour)
            frac = step_hours * (1.0 - elapsed)
        elif i == total_steps - 1:
            end_frac = sunrise_hour * steps_per_hour - math.floor(sunrise_hour * steps_per_hour)
            frac = step_hours * end_frac if end_frac > 0 else step_hours
        else:
            frac = step_hours

        if frac <= 0:
            continue

        # Solar (already 0 for nighttime indices)
        solar_val = solar_array[idx] if idx < len(solar_array) else 0.0
        solar_scaled = solar_val * (frac / step_hours) if step_hours > 0 else 0.0

        # Consumption — gate dump loads against solar availability per hour.
        # Recorded consumption already includes the dump load when it ran;
        # if solar can't cover the base (consumption - dump_load), assume the
        # dump load is shut off this hour and use base only.
        if hourly_consumption and len(hourly_consumption) == 24:
            cons_kwh = hourly_consumption[hour]
            if have_dump:
                dump = dump_load_profile[hour]
                if dump > 0:
                    base = max(0.0, cons_kwh - dump)
                    if solar_per_hour[hour] < base:
                        cons_kwh = base
            cons_dc = cons_kwh * frac / eff
        else:
            cons_dc = 0.0

        # Backup assist
        if br > 0 and backup_kw > 0 and _is_backup_active(hour):
            backup_energy = min(br, backup_kw * frac)
            cons_dc -= backup_energy * backup_discharge_efficiency / eff
            br -= backup_energy

        total_solar += solar_scaled
        # Only count consumption during solar hours for the daytime attribute
        if solar_val > 0 and hourly_consumption:
            total_consumption += hourly_consumption[hour] * frac

        battery += solar_scaled - cons_dc
        if battery > main.capacity_kwh:
            clip = battery - main.capacity_kwh
            surplus += clip
            # Charge backup from surplus in real-time
            if backup.enabled and br < backup.usable_kwh:
                charge = min(clip * backup_charge_efficiency, backup.usable_kwh - br)
                br += charge
            battery = main.capacity_kwh
        if battery < main.floor_kwh:
            battery = main.floor_kwh

        # Track day low and floor hour
        if battery < day_low:
            day_low = battery
            step_time = current_hour + (i + 1) * step_hours
            day_low_time = step_time

        if battery <= main.floor_kwh and not floor_hit:
            floor_hit = True
            step_time = current_hour + (i + 1) * step_hours
            day_low_time = step_time

    # Format floor_hour as HH:MM (handles wrap past 24)
    floor_hour_str = None
    if floor_hit and day_low_time is not None:
        t = day_low_time % 24
        h = int(t)
        m = int((t - h) * 60)
        floor_hour_str = f"{h:02d}:{m:02d}"

    sunrise_kwh = battery

    # Backup charge for Days 2-7 grid_needed reference
    backup_charged = min(backup.usable_kwh, backup_current + surplus * backup_charge_efficiency) if backup.enabled else 0.0

    return DayResult(
        soc_percent=round(sunrise_kwh / main.capacity_kwh * 100, 1),
        predicted_kwh=round(sunrise_kwh, 2),
        solcast_kwh=round(total_solar, 2),
        daytime_consumption_kwh=round(total_consumption, 2),
        backup_charged_kwh=round(backup_charged, 2),
        morning_low_kwh=round(day_low, 2),
        morning_low_pct=round(day_low / main.capacity_kwh * 100, 1),
        floor_hour=floor_hour_str,
    )


def predict_future_day(
    prev_kwh: float,
    solar_kwh: float,
    consumption: ConsumptionData,
    main: BatteryConfig,
    backup: BackupConfig,
    overnight_params: OvernightParams,
    target_kwh: float = 0.0,
    hourly_consumption: list[float] | None = None,
    sunrise_hour: float = 6.0,
    sunset_hour: float = 18.0,
    hourly_solar: list[float] | None = None,
    inverter_efficiency: float = 1.0,
    backup_charge_efficiency: float = 1.0,
    backup_discharge_efficiency: float = 1.0,
    dump_load_profile: list[float] | None = None,
) -> DayResult:
    """Predict SoC for Days 2-7 using the same continuous loop as Day 1."""
    return predict_day1_daytime(
        current_kwh=prev_kwh,
        remaining_solar=solar_kwh,
        hours_to_sunset=sunset_hour - sunrise_hour,
        sunrise_hour=sunrise_hour,
        consumption=consumption,
        main=main,
        backup=backup,
        backup_soc_pct=backup.floor_percent,
        overnight_params=overnight_params,
        target_kwh=target_kwh,
        hourly_consumption=hourly_consumption,
        current_hour=sunrise_hour,
        sunset_hour=sunset_hour,
        hourly_solar=hourly_solar,
        inverter_efficiency=inverter_efficiency,
        backup_charge_efficiency=backup_charge_efficiency,
        backup_discharge_efficiency=backup_discharge_efficiency,
        dump_load_profile=dump_load_profile,
    )
