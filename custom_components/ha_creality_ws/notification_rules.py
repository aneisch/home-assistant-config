"""Pure notification decisions and payload construction.

This module deliberately imports nothing from Home Assistant. ``tools/tests``
stubs out the whole ``homeassistant.*`` tree and CI installs only pytest and
voluptuous, so keeping every decision here means it can be tested with no mocks
at all. Anything that needs ``hass`` -- service calls, the entity registry,
state lookups -- lives in ``coordinator.py``.

Two house rules worth knowing before editing:

* ``tools/tests/test_code_hygiene.py`` rejects ``https://`` literals anywhere in
  this package, so companion-app documentation is cited from README.md rather
  than from here.
* ``const.py`` is exec'd standalone by ``tools/tests/test_manifest_and_specs.py``
  and must stay import-free, which is why the option-coercion helpers live in
  this module instead of alongside the keys they read.
* **No user-visible text lives here.** Every label, status word and message
  template comes from ``strings.json`` and is passed in already resolved, so
  this module only decides structure. Colours and mdi slugs stay, being neither
  language nor prose.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from collections.abc import Collection, Mapping
from typing import Any

from .const import (
    CLEAR_NOTIFICATION_MARKER,
    CONF_NOTIFY_DEVICE,
    DOMAIN,
    CONF_NOTIFY_TARGETS,
    NOTIFY_COLOR_DONE,
    NOTIFY_COLOR_ERROR,
    NOTIFY_COLOR_PAUSED,
    NOTIFY_COLOR_PRINTING,
    NOTIFY_LIVE_IOS_EXPIRY_SECS,
    NOTIFY_LIVE_MAX_PUSHES_PER_JOB,
    NOTIFY_LIVE_MILESTONE_STEP,
    NOTIFY_LIVE_INTERVAL_SECS,
    NOTIFY_LIVE_MIN_INTERVAL_SECS,
    NOTIFY_LIVE_TRANSITION_FLOOR_SECS,
    NOTIFY_END_CONFIRM_SECS,
    NOTIFY_REARM_PROGRESS_MAX,
)

# Tags may only contain these characters, and are capped at 64. The printer host
# is an IP address, so a host-derived tag would be rejected outright -- hence
# sanitize_tag() and the entry_id-based base in the coordinator.
_TAG_ILLEGAL = re.compile(r"[^A-Za-z0-9_-]+")
_TAG_MAX_LEN = 64

# Phases a live card can be pushed in. "start" is also what a mid-print Home
# Assistant restart re-issues, so the card resyncs instead of sitting frozen.
PHASE_START = "start"
PHASE_PRINTING = "printing"
PHASE_PAUSED = "paused"


class PushReason(str, Enum):
    """Why a live push is being sent. A ``str`` enum so test failures read well."""

    START = "start"
    TRANSITION = "transition"
    MILESTONE = "milestone"
    REFRESH = "refresh"
    OVERRUN = "overrun"


# --------------------------------------------------------------------------- #
# Options
# --------------------------------------------------------------------------- #


def coerce_targets(options: Mapping[str, Any]) -> list[str]:
    """Resolve the configured notify targets, migrating the legacy single one.

    Reads ``notify_device`` (a single service name) only when ``notify_targets``
    is *absent*. Presence rather than truthiness is load-bearing: a user who
    deliberately empties the list must keep it empty, or the legacy device would
    be resurrected on every reload. The legacy key is never written or deleted,
    so rolling back to an earlier release keeps working.
    """
    raw = options.get(CONF_NOTIFY_TARGETS)
    if raw is None:
        legacy = options.get(CONF_NOTIFY_DEVICE)
        raw = [legacy] if isinstance(legacy, str) and legacy.strip() else []
    elif isinstance(raw, str):
        # Defends against a hand-edited .storage: iterating a str would yield
        # characters, and each one would silently fail to route.
        raw = [raw]
    elif not isinstance(raw, (list, tuple)):
        return []

    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        target = item.strip()
        if target and target not in seen:
            seen.add(target)
            out.append(target)
    return out


# Companion platforms with no live-card surface at all. macOS has neither an
# iOS-style Live Activity nor an Android progress notification, so a live push
# there is an ordinary banner that cannot be updated in place -- one every
# refresh interval, none of which supersede the last.
LIVE_INCAPABLE_OS = frozenset({"macos"})


def is_live_capable(os_name: str | None) -> bool:
    """Whether this companion platform can render the live card.

    Unknown platforms count as capable: a target we failed to identify should
    still get its notifications rather than be silently skipped.
    """
    if not os_name:
        return True
    return os_name.strip().lower() not in LIVE_INCAPABLE_OS


def notify_service_slug(target: str | None) -> str:
    """The device-name slug embedded in a `notify.mobile_app_<slug>` target."""
    if not target:
        return ""
    service = target.split(".", 1)[1] if "." in target else target
    prefix = "mobile_app_"
    return service[len(prefix):] if service.startswith(prefix) else ""


def is_mobile_target(target: str | None) -> bool:
    """Whether a notify target is a companion-app service.

    Only these may receive a ``data`` payload. Strict-schema platforms reject
    unknown keys and fail the whole call, ``notify.send_message`` has no ``data``
    field at all, and the relative ``/api/...`` URLs only authenticate from the
    companion app -- three independent reasons for the same gate.
    """
    if not target:
        return False
    service = target.split(".", 1)[1] if "." in target else target
    # The full `mobile_app_` prefix, matching `notify_service_slug`: a bare
    # `startswith("mobile_app")` also claims `notify.mobile_application_*`,
    # which would then be handed companion-only `data` and reject the call.
    return service.startswith("mobile_app_")


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #


def display_filename(raw: Any) -> str:
    """Basename of a printer-reported print file.

    K1C firmware reports a full path (``/usr/data/printer_data/gcodes/x.gcode``)
    and nothing else in the integration basenames it, so the notification bodies
    used to interpolate the whole thing. The extension is kept: users identify
    files by it. Sensor attributes deliberately keep publishing the raw value,
    because user templates depend on it.
    """
    if not isinstance(raw, str):
        return ""
    text = raw.strip()
    if not text:
        return ""
    tail = text.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].strip()
    return tail or text


def format_duration(secs: Any, templates: Mapping[str, str]) -> str:
    """Human duration from the caller's templates. Empty when unknown.

    Numbers are pre-formatted into strings before substitution so a translator
    cannot break a format spec (``{minutes:02d}``) by reordering placeholders.
    """
    try:
        parsed = float(secs)
    except (TypeError, ValueError, OverflowError):
        # OverflowError is the conversion itself failing, not the value being
        # infinite: `float(10**400)` raises "int too large to convert to
        # float", so the finiteness check below never gets a value to test.
        return ""
    # `float("inf")` succeeds and `int(inf)` then raises OverflowError, which
    # the clause above does not catch. This runs on the WebSocket frame path,
    # so one non-finite `printLeftTime` would take the whole notification
    # update down for that frame -- the same reason `derive_print_state` is
    # hardened against "nan" and "inf".
    if not math.isfinite(parsed):
        return ""
    total = int(parsed)
    if total < 0:
        return ""
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return _fill(
            templates.get("duration_hours_minutes"),
            hours=str(hours),
            minutes=f"{minutes:02d}",
        )
    if minutes:
        return _fill(templates.get("duration_minutes"), minutes=str(minutes))
    return _fill(templates.get("duration_seconds"), seconds=str(seconds))


def format_filament_length(mm: Any, template: str | None) -> str:
    """Filament used, rendered by the caller's template. Empty when unknown."""
    try:
        value = float(mm)
    except (TypeError, ValueError, OverflowError):
        # Same exposure as `format_duration`, and the same frame path:
        # `_template_values` feeds this `usedMaterialLength` on every push.
        return ""
    # NaN fails `<= 0` like every other comparison, and infinity passes it, so
    # without this the notification read "nan m" or "inf m".
    if not math.isfinite(value) or value <= 0:
        return ""
    return _fill(template, metres=f"{value / 1000.0:.1f}")


def _fill(template: str | None, **values: str) -> str:
    """Substitute into a translated template, tolerating a broken one.

    A translation with a renamed or malformed placeholder must not take a
    notification down with it, so a failure yields an empty segment that the
    caller drops.
    """
    if not template:
        return ""
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return ""


# --------------------------------------------------------------------------- #
# User text templates
# --------------------------------------------------------------------------- #

# What a mid-print notification can say. Everything here is filled from
# telemetry the printer actually streams: nothing is inferred, converted
# against an assumed filament density, or carried over from an earlier job,
# because a number a user reads off a notification has to be a number the
# printer said.
_FIELDS_WHILE_PRINTING = (
    "device",
    "filename",
    "progress",
    "layer",
    "total_layers",
    "eta",
    "elapsed",
    "filament",
    "nozzle",
    "bed",
    "state",
)

# Per notification, because they are composed at different moments and the
# printer has different things to say at each. The sets are deliberately closed
# and deliberately *not* all the same: a placeholder offered for a notification
# that cannot fill it is worse than one that does not exist, because it renders
# as nothing and looks like a bug in the template rather than a mistake in the
# list. The options flow refuses a name that is not in the right set here, and
# the same sets are what it lists under each field.
TEMPLATE_FIELDS: dict[str, tuple[str, ...]] = {
    "live": _FIELDS_WHILE_PRINTING,
    # Its whole point is the number of minutes left.
    "finishing_soon": _FIELDS_WHILE_PRINTING + ("minutes",),
    "error": _FIELDS_WHILE_PRINTING + ("error_code", "error_key"),
    "filament_runout": _FIELDS_WHILE_PRINTING,
    # No `eta`: the print has finished, so the remaining time is zero and
    # saying "0s left" in a completion notice is worse than not offering it.
    "completed": tuple(f for f in _FIELDS_WHILE_PRINTING if f != "eta"),
    # A stop is only visible once the printer has already reset the job: the
    # progress, the job clock, the layer and the filament length are all back
    # to zero by the frame that reveals it, and the state word is whatever the
    # printer idles in. Only what survives is offered -- the file name and the
    # progress from the last frame that showed the job running (see
    # `JobEndWatch`), and the temperatures, which are still real.
    "stopped": ("device", "filename", "progress", "nozzle", "bed"),
}

# `{name}` only, lowercase: the same spelling the shipped strings use, so a user
# reading an example in the README writes the same thing. Anything else in the
# template -- including a lone brace -- is literal text and survives untouched,
# which is why there is no escaping rule to learn.
_TEMPLATE_TOKEN = re.compile(r"\{([a-z_][a-z0-9_]*)\}")

# An optional segment: dropped whole when any placeholder inside it is empty.
# This printer's telemetry is full of values that are only sometimes there --
# no layer count on a paused resume, no estimate in the first minute, no
# filament length on an aborted job -- so without this every template would
# either omit the interesting details or render " -- left" with nothing before
# it. Not nestable: the inner class excludes both brackets, so only the
# innermost pair of a nested pair would match, and one pass is easier to explain
# than a half-recursive syntax.
_TEMPLATE_OPTIONAL = re.compile(r"\[([^\[\]]*)\]")

# Collapses the whitespace an emptied placeholder leaves behind.
_TEMPLATE_GAP = re.compile(r"[ \t]{2,}")

# `[[` and `]]` are a literal bracket. Needed because the obvious way to write
# an error code in brackets -- `{error_key} [{error_code}]` -- is also exactly
# the optional-segment syntax, so it rendered the code with the brackets eaten.
# Doubling is the convention `str.format` uses for the same problem.
#
# Swapped for characters no text field can produce before the segment pass, so
# an escaped bracket cannot open or close a segment, and swapped back last, so
# a placeholder value that happens to contain a bracket is never re-read.
_ESCAPED_OPEN = "\x00"
_ESCAPED_CLOSE = "\x01"


def template_unknown_fields(
    template: Any, allowed: Collection[str]
) -> list[str]:
    """Placeholder names in ``template`` that ``allowed`` cannot fill.

    The options flow refuses a template this returns anything for, which is the
    only moment a typo can be reported to the person who made it: a notification
    is composed on a WebSocket frame, where the sole recourse is the log.

    ``allowed`` is per notification, so ``{minutes}`` is a real placeholder in
    the finishing-soon reminder and a mistake in the live card -- which is
    exactly what it would have been at run time, rendering as nothing.
    """
    if not isinstance(template, str):
        return []
    seen: list[str] = []
    for name in _TEMPLATE_TOKEN.findall(template):
        if name not in allowed and name not in seen:
            seen.append(name)
    return seen


def render_user_template(template: Any, values: Mapping[str, Any]) -> str:
    """Render a user's notification template. Empty when it cannot be used.

    An empty return means "fall back to the shipped text", and every caller
    does. Three things produce one: no template configured, a placeholder that
    does not exist (the options flow rejects those, but a hand-edited
    ``.storage`` does not go through it), and a template whose every segment
    turned out to be unknown. That last case is the important one -- a blank
    notification is worse than a generic one.

    ``[[`` and ``]]`` render as a literal bracket, which is the only escaping
    rule there is. Single brackets around a placeholder are an optional
    segment: the brackets themselves are the syntax and do not survive.
    """
    if not isinstance(template, str) or not template.strip():
        return ""
    # Against the values on offer rather than a global list: the caller builds
    # them from `TEMPLATE_FIELDS` for the notification being composed, so this
    # rejects exactly what the options flow would have rejected.
    if template_unknown_fields(template, values.keys()):
        return ""

    def _resolve(name: str) -> str:
        value = values.get(name)
        return "" if value is None else str(value)

    def _optional(match: "re.Match[str]") -> str:
        segment = match.group(1)
        names = _TEMPLATE_TOKEN.findall(segment)
        if not names:
            # Brackets with no placeholder inside are the user's own text --
            # "[PRINTER] finished" means the brackets -- so they stay. They only
            # become syntax when they wrap something that can go missing.
            return match.group(0)
        if not all(_resolve(name).strip() for name in names):
            return ""
        return segment

    text = template.replace("[[", _ESCAPED_OPEN).replace("]]", _ESCAPED_CLOSE)
    text = _TEMPLATE_OPTIONAL.sub(_optional, text)
    text = _TEMPLATE_TOKEN.sub(lambda m: _resolve(m.group(1)), text)
    text = text.replace(_ESCAPED_OPEN, "[").replace(_ESCAPED_CLOSE, "]")
    return _TEMPLATE_GAP.sub(" ", text).strip()


def sanitize_tag(raw: Any) -> str:
    """Coerce anything into a legal notification tag."""
    cleaned = _TAG_ILLEGAL.sub("_", str(raw or "")).strip("_")
    return (cleaned or "ha_creality_ws")[:_TAG_MAX_LEN]


def notify_tag_base(entry_id: Any, fallback: Any = None) -> str:
    """Stable tag prefix for one printer.

    Derived from the config entry id and never from the host: the host is an
    IP address and dots are illegal in a tag. It also has to survive a Home
    Assistant restart, because that is what lets an existing card be replaced
    rather than duplicated.

    Shared rather than spelled out at each call site because the two that need
    it sit at opposite ends of an entry's life: the coordinator posts cards
    under this prefix, and `async_remove_entry` builds the clear payloads that
    dismiss them. They agree today, and if they ever stopped agreeing the
    symptom would be live cards stranded on a phone after the integration was
    removed, with nothing in the log to say why.

    `fallback` covers the coordinator's case of an entry id that is not set
    yet; removal always has a real one.
    """
    return sanitize_tag(f"{DOMAIN}_{entry_id or fallback}")


def stringify_data(data: Mapping[str, Any] | None) -> dict[str, Any]:
    """Coerce a companion-app ``data`` dict to what the push relay accepts.

    Android delivery goes out as an FCM data message, whose payload is a
    map<string, string>. A native ``int`` or ``bool`` at the top level makes the
    relay reject the **whole push** with "data must only contain string values",
    so a single `live_update: True` silently costs every Android notification --
    which is exactly what it did: every live-card push to a Galaxy S24 failed
    while the log said only "Error sending notification to S24".

    Nesting is *not* uniformly exempt, which cost a release to learn. Measured
    against a real Galaxy S24, one key at a time:

    * ``actions`` -- a **list** of dicts -- is flattened into the same FCM map,
      so a bool inside it is rejected exactly like a bool at the top level.
      ``destructive: True`` on the Stop button was enough to lose every push.
    * ``push`` and ``content_state`` -- plain **dicts** -- are not flattened.
      They survive with real ints, and iOS wants them that way.

    Hence the rule: scalars are coerced at the top level and inside dicts nested
    in a *list*, while a dict value is passed through whole.

    ``None`` drops the key rather than sending the string "None", which the
    companion app would treat as a value.
    """
    out: dict[str, Any] = {}
    for key, value in (data or {}).items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            out[key] = [
                stringify_data(item) if isinstance(item, Mapping) else item
                for item in value
            ]
        elif isinstance(value, Mapping):
            out[key] = dict(value)
        else:
            out[key] = _scalar_to_str(value)
    return out


def _scalar_to_str(value: Any) -> Any:
    if isinstance(value, bool):
        # Lowercase: the companion app compares against "true"/"false".
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return value


# --------------------------------------------------------------------------- #
# Job-cycle detection
# --------------------------------------------------------------------------- #


def is_new_job_cycle(
    prog_val: int,
    job_restarted: bool,
    *,
    ended_at_completion: bool,
    ended_early: bool = False,
) -> bool:
    """Whether a genuinely new job has begun since the last one ended.

    The single home for this predicate; the terminal re-arm and the live-card
    reset both call it. They used to be separate expressions of the same idea,
    which is exactly the drift the comment in ``_prime_notification_state``
    warns about.

    Nothing counts until an ending has been observed, or every mid-print frame
    would look like a fresh cycle. After that there are two signals, and they
    are not interchangeable:

    * The **job clock restarting** is unambiguous and works for any ending. It
      is the only signal available for a job that was stopped part-way, which is
      why ``ended_early`` requires it.
    * A **progress drop** only means anything for a job that ended *at* 100%.
      The printer rounds progress up to 100 a second before a job ends, reports
      99 once more, and only then finishes -- so the drop has to clear that
      jitter band, or the completion notification fires twice for every print.
      Applying the same test to a job stopped at 30% would re-arm on the very
      next frame, because 30 never leaves the band.
    """
    if not (ended_at_completion or ended_early):
        return False
    if prog_val >= 100:
        # Telemetry lags: the frame that first shows a new job usually still
        # carries the previous one's 100. Re-arming here would announce that
        # completion a second time, immediately.
        return False
    if job_restarted:
        return True
    return ended_at_completion and prog_val <= NOTIFY_REARM_PROGRESS_MAX


def _milestone_of(progress: Any) -> int:
    """Which milestone bucket a progress value falls in, or -1 when unknown."""
    try:
        value = int(progress)
    except (TypeError, ValueError, OverflowError):
        return -1
    if value < 0:
        return -1
    return value // NOTIFY_LIVE_MILESTONE_STEP


# --------------------------------------------------------------------------- #
# Early-end detection
# --------------------------------------------------------------------------- #

# What a job that is genuinely under way looks like. Deliberately narrower than
# ``BUSY_PRINT_STATES``: "processing" is state 0 with a file name still
# attached, which is both the warm-up *before* a print and what the printer
# sits in *after* one is cancelled. Arming on it would make the two
# indistinguishable, so the watch below only ever arms on a job it has seen
# actually printing.
RUNNING_JOB_STATES = frozenset({"printing", "paused"})

# States that say nothing about the job: the WebSocket is down, or the power
# switch is off. A print cannot be declared stopped from a frame that only
# means "we cannot see the printer".
UNOBSERVABLE_JOB_STATES = frozenset({"unknown", "off"})


class JobEvent(str, Enum):
    """What just happened to the job being watched."""

    ENDED_EARLY = "ended_early"
    RESTARTED = "restarted"


@dataclass(slots=True)
class JobEndWatch:
    """Notices that a print ended before it finished, however it was ended.

    The printer reports *state*, not events, and it reports the same state for
    several different things -- so a stop is only visible as a transition. This
    watch is the whole of that: it remembers a job it has seen printing, and
    calls the end when that job stops printing without having reached 100%.

    It exists because ``state == 4`` ("stopped") is not the signal it looks
    like. Stopping a print from the printer's own screen, from the Creality app
    or from Home Assistant all end the same way in telemetry -- ``state`` goes
    back to 0 with the file name still attached and the progress reset to 0,
    which derives as "processing", the same word as a warm-up. Nothing fired,
    and the live card kept refreshing at 0% for a print that had been cancelled
    minutes earlier. Some firmware clears the file name instead, which dismissed
    the card and put nothing in its place.

    ``progress`` and ``job_name`` are remembered from the last frame that showed
    the job running, because both are gone by the time the end is visible: the
    notification has to say "stopped at 42%", and 42 is not in the frame that
    reveals the stop.
    """

    job_name: str = ""
    progress: int = -1
    seen_running: bool = False
    ended: bool = False
    # Set when the job stopped looking like it is running, for the ambiguous
    # states only. None means "nothing to confirm".
    pending_since: float | None = None

    def reset(self) -> None:
        """Forget the job entirely, for a new one."""
        self.job_name = ""
        self.progress = -1
        self.seen_running = False
        self.ended = False
        self.pending_since = None

    def pending(self) -> bool:
        """Whether an end is waiting to be confirmed or ruled out."""
        return self.pending_since is not None

    def observe(
        self,
        *,
        state: str,
        progress: int,
        filename: str,
        now_mono: float,
    ) -> JobEvent | None:
        """Fold one telemetry frame in, and say what it means.

        ``None`` is the ordinary answer: the job is running, or there is nothing
        being watched, or an ambiguous state has not persisted long enough to
        call.
        """
        if state in RUNNING_JOB_STATES:
            restarted = self.ended
            if restarted:
                # A job printing again after we called the end of one is a new
                # print, whoever started it. This is what re-arms the one-shot
                # latches, and it is far more direct than the job clock: a stop
                # resets `printJobTime` to 0, so reprinting the same file never
                # made it run *backwards* and the "new cycle" test missed it.
                self.reset()
            self.seen_running = True
            if filename:
                self.job_name = filename
            if progress >= 0:
                self.progress = progress
            self.pending_since = None
            return JobEvent.RESTARTED if restarted else None

        if not self.seen_running or self.ended:
            return None

        if state in UNOBSERVABLE_JOB_STATES:
            # Deliberately clears the timer rather than pausing it: a print is
            # only declared stopped off frames that actually described the
            # printer, so the confirmation starts again from the first one that
            # does.
            self.pending_since = None
            return None

        if progress >= 100:
            # A finished job, which the completion notification owns. Not left
            # to the caller's own latch alone: this is the frame *before* that
            # latch is set, and starting a confirmation here would race it.
            self.pending_since = None
            return None

        # Two signals need no confirming. `state == 4` is the printer saying so
        # outright, and a file name it has cleared means the job is gone from
        # the printer's own point of view.
        if state == "stopped" or not filename:
            self.ended = True
            self.pending_since = None
            return JobEvent.ENDED_EARLY

        # Everything else is ambiguous enough to sit on: a single "idle" or
        # "processing" frame mid-print is something this printer does, and it
        # must not cost the user a "print stopped" notification.
        if self.pending_since is None:
            self.pending_since = now_mono
            return None
        if now_mono - self.pending_since < NOTIFY_END_CONFIRM_SECS:
            return None
        self.ended = True
        self.pending_since = None
        return JobEvent.ENDED_EARLY


# --------------------------------------------------------------------------- #
# Live card state machine
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class LiveSnapshot:
    """The subset of telemetry the live card reacts to."""

    activity_state: str
    job_active: bool
    progress: int
    filename: str = ""
    layer: int | None = None
    total_layers: int | None = None
    seconds_left: float | None = None


@dataclass(slots=True)
class LiveCardState:
    """Bookkeeping for one printer's live card. Reset wholesale per job.

    A test asserts this dataclass equals a fresh instance after
    ``reset_for_new_job``, so a field added here without a matching reset fails
    loudly rather than leaking across jobs.
    """

    card_active: bool = False
    job_finished: bool = False
    milestone: int = -1
    last_state: str | None = None
    last_push_mono: float | None = None
    last_when: int | None = None
    last_progress: int | None = None
    pushes_this_job: int = 0
    started_epoch: float | None = None
    overrun_pushed: bool = False

    def reset_for_new_job(self, *, progress: Any = None) -> None:
        """Baseline for a new job without notifying about it.

        Milestone is baselined off the progress we can actually see rather than
        -1, so the START push is not immediately followed by a redundant
        milestone push.
        """
        self.card_active = False
        self.job_finished = False
        self.milestone = _milestone_of(progress)
        self.last_state = None
        self.last_push_mono = None
        self.last_when = None
        self.last_progress = None
        self.pushes_this_job = 0
        self.started_epoch = None
        self.overrun_pushed = False

    def is_expired(self, now_epoch: float) -> bool:
        """Whether iOS has hard-expired the activity (Apple's 8h ceiling)."""
        if self.started_epoch is None:
            return False
        return (now_epoch - self.started_epoch) >= NOTIFY_LIVE_IOS_EXPIRY_SECS

    def decide(
        self, *, snap: LiveSnapshot, now_mono: float, now_epoch: float
    ) -> PushReason | None:
        """Whether to push, and why. ``None`` means stay quiet."""
        if self.job_finished:
            # End-of-print jitter flips the derived state completed -> printing
            # -> completed, and without this latch each flip would tear the card
            # down and stand a new one up seconds later -- two iOS
            # push-to-start slots spent showing the same print twice. Only a
            # genuinely new job (reset_for_new_job) clears it.
            return None
        if not snap.job_active:
            return None
        if self.pushes_this_job >= NOTIFY_LIVE_MAX_PUSHES_PER_JOB:
            return None
        if not self.card_active:
            # Also the mid-print restart resync: priming clears card_active
            # without notifying, so the first frame of an already-running job
            # starts the card rather than leaving a frozen one on the phone.
            return PushReason.START

        since = None if self.last_push_mono is None else now_mono - self.last_push_mono

        if snap.activity_state != self.last_state:
            # Pause/resume must be visible at once, so it bypasses the interval
            # floor. The floor is 0.0 deliberately (see the constant): a state
            # that has not changed cannot reach here at all, so the only thing a
            # delay would catch is genuine alternation, which is a printer fault.
            # NOTIFY_LIVE_MAX_PUSHES_PER_JOB is the circuit breaker for that.
            if since is None or since >= NOTIFY_LIVE_TRANSITION_FLOOR_SECS:
                return PushReason.TRANSITION
            return None

        if since is not None and since < NOTIFY_LIVE_MIN_INTERVAL_SECS:
            return None

        if _milestone_of(snap.progress) > self.milestone:
            # Progress has moved a lot in little time, so refresh early rather
            # than showing a percentage the user can see is behind.
            return PushReason.MILESTONE

        if since is not None and since >= NOTIFY_LIVE_INTERVAL_SECS:
            # The ordinary cadence. Without it the card only ever moved on a 5%
            # boundary, which on a long print left the percentage and the
            # remaining estimate visibly stale for twenty minutes at a time.
            #
            # Only when the card would actually read differently, though. A
            # paused print holds its progress and has no countdown, so
            # refreshing it repaints identical pixels -- and the relay allows
            # only 500 pushes per device per day, so an idle repaint every five
            # minutes is a real cost for no information.
            if snap.progress != self.last_progress or self.last_when is not None:
                return PushReason.REFRESH

        # The chronometer counts down on-device for free, but a jumpy
        # printLeftTime can leave it frozen at 0:00 while progress stays inside
        # one milestone bucket. Replace it once, then go quiet again.
        if (
            not self.overrun_pushed
            and self.last_when is not None
            and now_epoch >= self.last_when
        ):
            return PushReason.OVERRUN

        return None

    def record_push(
        self,
        *,
        reason: PushReason,
        snap: LiveSnapshot,
        now_mono: float,
        now_epoch: float,
        when: int | None,
    ) -> None:
        """Fold a sent push back into the state."""
        if not self.card_active:
            self.card_active = True
            self.started_epoch = now_epoch
        self.last_push_mono = now_mono
        self.last_state = snap.activity_state
        self.pushes_this_job += 1
        # Assigned even when None. A push that carries no deadline (a pause, or
        # an estimate that ran out) has *stopped* the chronometer, so keeping the
        # old deadline would make decide() see it expire and fire a second,
        # pointless overrun push -- once per later push, forever.
        self.last_when = when
        self.last_progress = snap.progress
        self.overrun_pushed = reason is PushReason.OVERRUN
        milestone = _milestone_of(snap.progress)
        if milestone > self.milestone:
            self.milestone = milestone

    def finish(self) -> None:
        """The job this card was tracking has ended.

        Deliberately distinct from ``clear``: a printer that merely went quiet
        should get its card back if telemetry resumes, but a finished job must
        not, or the end-of-print progress jitter would resurrect it.
        """
        self.clear()
        self.job_finished = True

    def clear(self) -> None:
        """Mark the card gone without disturbing the per-job milestone latch."""
        self.card_active = False
        self.last_state = None
        self.last_push_mono = None
        self.last_when = None
        self.started_epoch = None
        self.overrun_pushed = False


# --------------------------------------------------------------------------- #
# Payload construction
# --------------------------------------------------------------------------- #

# Lifecycle and alert flavours. Kept as constants so a typo is an ImportError
# rather than a silently wrong icon.
EVENT_COMPLETED = "completed"
EVENT_STOPPED = "stopped"
EVENT_SOON = "soon"
ALERT_ERROR = "error"
ALERT_RUNOUT = "runout"

# Icon and colour per lifecycle flavour.
_EVENT_STYLE = {
    EVENT_COMPLETED: ("mdi:check-circle", NOTIFY_COLOR_DONE),
    EVENT_STOPPED: ("mdi:stop-circle", NOTIFY_COLOR_PAUSED),
    EVENT_SOON: ("mdi:clock-fast", NOTIFY_COLOR_PRINTING),
}


@dataclass(frozen=True, slots=True)
class NotifyVisuals:
    """Resolved, already-gated media URLs.

    Both are relative ``/api/...`` paths, which the companion app fetches with
    its own credentials -- no token and no signed path needed. The caller is
    responsible for the gating: ``preview_url`` must be ``None`` when the image
    entity reports a ``preview_reason`` in ``PREVIEW_REASONS_UNUSABLE``, and
    ``snapshot_url`` unless the camera reports ``snapshot_supported``. Both
    entities otherwise serve a 1x1 placeholder, which renders as an empty grey
    box.

    Deliberately *not* ``preview_reason == "ok"``: the attribute is only set once
    something has asked the image entity for bytes, so an unset value means "not
    tried yet" rather than "no good", and requiring ``"ok"`` would drop the
    preview from the first notification of every print. See
    ``KCoordinator._notify_media``, which is the only producer.
    """

    preview_url: str | None = None
    snapshot_url: str | None = None


@dataclass(frozen=True, slots=True)
class NotifyLinks:
    """Tap targets. Both ship together; each platform ignores the other's key.

    ``click_action`` is Android's and accepts ``entityId:<id>`` to open a
    more-info dialog. iOS's ``url`` does not support that form, so it only gets a
    value when the user configured a dashboard path.
    """

    click_action: str | None = None
    tap_path: str | None = None


def compute_when(now_epoch: float, seconds_left: Any) -> int | None:
    """Absolute epoch the print is expected to finish, for ``when``.

    Wall clock, never ``hass.loop.time()``. The prime deadline elsewhere in the
    coordinator is monotonic, and feeding one of those into ``when`` would put
    the chronometer in 1970.
    """
    try:
        remaining = float(seconds_left)
    except (TypeError, ValueError, OverflowError):
        # As in `format_duration`: an oversized int fails in the conversion,
        # before there is anything for `math.isfinite` to reject.
        return None
    # The conversion below sits outside any try, so a non-finite value raises
    # straight out: NaN as ValueError, infinity as OverflowError. NaN also
    # slips past `<= 0`, every comparison against it being false.
    if not math.isfinite(remaining) or remaining <= 0:
        return None
    return int(now_epoch + remaining)


def _clamp_progress(progress: Any) -> int | None:
    try:
        value = int(progress)
    except (TypeError, ValueError, OverflowError):
        return None
    return max(0, min(100, value))


def _apply_common(
    data: dict[str, Any],
    *,
    group: str | None,
    links: NotifyLinks | None,
    actions: list[dict[str, Any]] | None,
) -> None:
    if group:
        data["group"] = group
    if links is not None:
        # Never emit "entityId:None" or an empty url -- the caller passes None
        # when nothing resolved.
        if links.click_action:
            data["clickAction"] = links.click_action
        if links.tap_path:
            data["url"] = links.tap_path
    if actions:
        data["actions"] = list(actions)


def build_live_payload(
    *,
    tag: str,
    title: str,
    message: str,
    phase: str,
    progress: Any,
    when: int | None,
    channel: str,
    status_text: str = "",
    live_update: bool = True,
    group: str | None = None,
    visuals: NotifyVisuals | None = None,
    links: NotifyLinks | None = None,
    actions: list[dict[str, Any]] | None = None,
    refresh: bool = False,
    job_name: str = "",
    device_name: str = "",
) -> dict[str, Any]:
    """A live-card push.

    ``title`` must be the printer's name and identical on every push of a job:
    it is required on Android and cannot be changed once the activity has
    started, so anything job-specific belongs in ``message``.

    ``live_update=False`` degrades to a plain tagged notification, which still
    replaces itself in place and still shows an Android progress bar. That is
    the path taken once iOS has expired the activity.
    """
    paused = phase == PHASE_PAUSED
    color = NOTIFY_COLOR_PAUSED if paused else NOTIFY_COLOR_PRINTING

    data: dict[str, Any] = {
        "tag": sanitize_tag(tag),
        "notification_icon": "mdi:pause-circle" if paused else "mdi:printer-3d-nozzle",
        "channel": channel,
        # Progress pushes only. Terminal pushes reuse this tag, and alert_once
        # there would update the card silently -- the "finished" ping would
        # never sound. build_event_payload deliberately omits it.
        "alert_once": True,
    }
    # Deliberately absent: `persistent`, `sticky` and `importance`.
    #
    # Not because they make the card swipeable, but because they do not stop
    # it. The card is swipeable on Android 16 either way -- tested on a real
    # handset with and without `persistent`, and again with the action buttons
    # removed, and it can be swiped away in every combination. The companion's
    # own documentation says as much: "starting in Android 14 persistent
    # notifications will be dismissable except when the device is locked".
    #
    # So an unswipeable card is not something this payload can ask for, and
    # these three were only ever asking. `importance: low` additionally
    # requested a minimised presentation, which is the opposite of what a live
    # card wants. Quietness comes from `alert_once` on Android and `silent` on
    # iOS below.
    #
    # The Hide action is therefore the way out of the card, not a fallback for
    # one. If a future Android or companion release does offer a genuine pin,
    # `persistent` plus a `tag` is where to look first.
    if refresh:
        # iOS alerts on every push unless told otherwise, so a 5-minute refresh
        # cadence buzzes the phone for the whole print. `alert_once` above is
        # Android-only and does nothing here, so these are its iOS counterpart
        # rather than a duplicate. Deliberately *not* set on the push that
        # starts the card: that one is the "your print is now on the Lock
        # Screen" cue and should be felt once.
        data["silent"] = True
        data["push"] = {"interruption-level": "passive"}
    else:
        # Tells iOS to begin a Live Activity rather than update one.
        data["activity"] = "start"

    if live_update:
        # What an iOS Live Activity actually renders from. `activity` alone only
        # says "start one" -- with no state to draw, iOS falls back to an
        # ordinary notification, and an ordinary iOS notification is dismissed
        # by a tap with no key able to prevent it. That was the whole iOS
        # symptom: a card that vanished when touched.
        #
        # A nested dict, so the FCM string rule does not apply to its values
        # and these stay real numbers.
        content: dict[str, Any] = {
            "state": "paused" if paused else "printing",
            "device": device_name or title,
        }
        pct_for_state = _clamp_progress(progress)
        if pct_for_state is not None:
            content["progress_pct"] = pct_for_state
        if when is not None:
            content["eta_timestamp"] = when
        if job_name:
            content["program"] = job_name
            data["subtitle"] = job_name
        data["content_state"] = content

    pct = _clamp_progress(progress)
    if pct is None:
        data["progress_indeterminate"] = True
    else:
        data["progress"] = pct
        data["progress_max"] = 100

    if live_update:
        data["live_update"] = True
        data["progress_bar_direction"] = "increasing"
        data["progress_bar_color"] = color
        data["notification_icon_color"] = color
        if when is not None and not paused:
            # Ticks on-device, so the countdown costs no further pushes.
            data["chronometer"] = True
            data["when"] = when
        else:
            # Stopped explicitly rather than by omitting the key: whether
            # dropping it clears a chronometer already running on the phone is
            # undocumented, and both cases here exist precisely to get rid of
            # one. A timer counting down through a pause is bad; a timer frozen
            # at 0:00 because the estimate ran out is the whole reason the
            # overrun push exists, and omitting the key could leave it there.
            data["chronometer"] = False
            if status_text:
                data["critical_text"] = status_text

    # No snapshot on live pushes: Android re-downloads a big picture every time
    # and an iOS Live Activity has no image slot, so it would be pure waste on
    # the hottest path.
    if visuals is not None and visuals.preview_url:
        data["icon_url"] = visuals.preview_url

    _apply_common(data, group=group, links=links, actions=actions)
    return {"title": title, "message": message, "data": data}


def build_event_payload(
    *,
    tag: str,
    title: str,
    message: str,
    kind: str,
    channel: str,
    group: str | None = None,
    visuals: NotifyVisuals | None = None,
    links: NotifyLinks | None = None,
    ends_activity: bool = False,
) -> dict[str, Any]:
    """A job-lifecycle banner: completed, stopped, or finishing soon.

    Carries no ``live_update`` (it is not an activity) and, crucially, no
    ``alert_once``: a terminal banner posted on the live card's own tag would
    otherwise replace it *silently* and the "print finished" ping would never
    sound.

    Carries **no progress bar either**, which is the whole difference between
    this and a live push. A completion banner used to ship ``progress: 100``, so
    the notification announcing that a print had finished still rendered the
    live card's bar, full, with nothing left to track -- and on Android it
    arrives on the live card's own tag, which made the "finished" notice read as
    one more refresh of the card rather than as the end of it. A confirmation
    needs its text, its tick and the snapshot of the bed, and none of the
    chrome of something still in progress. ``EVENT_SOON`` wanted the same thing
    for its own reason: with a bar it rendered as a second live card sitting
    under the real one.

    ``ends_activity`` marks the terminal ones, which are posted on the live tag
    and close the iOS Live Activity with ``activity: "end"``. The card is
    dismissed first and this posted in its place -- see ``_replace_card_with``
    -- because an ongoing Android notification is not taken down by an ordinary
    banner arriving on the same tag.
    """
    icon, color = _EVENT_STYLE.get(kind, _EVENT_STYLE[EVENT_COMPLETED])
    data: dict[str, Any] = {
        "tag": sanitize_tag(tag),
        "notification_icon": icon,
        "notification_icon_color": color,
        "color": color,
        "channel": channel,
        "importance": "high",
        "push": {"interruption-level": "time-sensitive"},
    }
    if ends_activity:
        data["activity"] = "end"

    if visuals is not None:
        if visuals.preview_url:
            data["icon_url"] = visuals.preview_url
        if visuals.snapshot_url:
            # What the bed actually looks like, which is the whole point of a
            # completion notification you read from another room.
            data["image"] = visuals.snapshot_url

    _apply_common(data, group=group, links=links, actions=None)
    return {"title": title, "message": message, "data": data}


def build_alert_payload(
    *,
    tag: str,
    title: str,
    message: str,
    kind: str,
    channel: str,
    group: str | None = None,
    visuals: NotifyVisuals | None = None,
    links: NotifyLinks | None = None,
    actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """An error or filament-runout alert.

    Uses its own tag so a lifecycle update cannot overwrite it, and no
    ``alert_once`` so it always breaks through.
    """
    runout = kind == ALERT_RUNOUT
    data: dict[str, Any] = {
        "tag": sanitize_tag(tag),
        "notification_icon": (
            "mdi:printer-3d-nozzle-alert" if runout else "mdi:alert-circle"
        ),
        "notification_icon_color": NOTIFY_COLOR_ERROR,
        "color": NOTIFY_COLOR_ERROR,
        "channel": channel,
        "importance": "high",
        "push": {"interruption-level": "time-sensitive"},
    }

    if visuals is not None and visuals.snapshot_url:
        data["image"] = visuals.snapshot_url

    _apply_common(data, group=group, links=links, actions=actions)
    return {"title": title, "message": message, "data": data}


def build_clear_payload(tag: str) -> dict[str, Any]:
    """Dismiss a notification, and end a Live Activity, carrying ``tag``.

    ``title`` is omitted rather than sent as ``None``. The message is a sentinel
    the companion app interprets; every other notify platform would render it as
    visible text, which is why delivery hard-gates it on mobile targets.
    """
    return {
        "message": CLEAR_NOTIFICATION_MARKER,
        "data": {"tag": sanitize_tag(tag)},
    }


# --------------------------------------------------------------------------- #
# Live-card buttons
# --------------------------------------------------------------------------- #

ACTION_PAUSE = "pause"
ACTION_RESUME = "resume"
ACTION_STOP = "stop"
# A swipe only clears the notification currently on screen: the next live-card
# refresh re-posts it under the same tag. This is the way to retire the card for
# the rest of the print, so it must always be offered -- a card that comes back
# every 30 seconds with no way to stop it is a trap. See `build_live_payload`
# for why `persistent` is not what makes this necessary.
ACTION_DISMISS = "dismiss"


def action_ids(entry_key: str) -> dict[str, str]:
    """Action ids for one printer, namespaced so two cannot cross-fire.

    The handler matches these exactly, which is the whole guard: a tap on one
    printer's card must never pause another's print.

    The *whole* key is used, not a prefix. Home Assistant entry ids are ULIDs
    whose leading characters encode the creation time and carry no randomness,
    so two printers added in the same second would have shared a truncated id --
    and a Stop tap would have gone to whichever one matched first.
    """
    suffix = sanitize_tag(entry_key).upper() or "CREALITY"
    return {
        ACTION_PAUSE: f"CREALITY_PAUSE_{suffix}",
        ACTION_RESUME: f"CREALITY_RESUME_{suffix}",
        ACTION_STOP: f"CREALITY_STOP_{suffix}",
        ACTION_DISMISS: f"CREALITY_DISMISS_{suffix}",
    }


def build_actions(
    *,
    paused: bool,
    ids: Mapping[str, str],
    labels: Mapping[str, str],
    controls: bool = True,
) -> list[dict[str, Any]]:
    """Buttons for a live card: the useful one, Stop, and Dismiss.

    ``labels`` supplies the translated button titles, keyed by ACTION_*.

    Stop is marked destructive and authentication-required. A mis-tap on a lock
    screen must not be able to end a fourteen-hour print.

    ``controls=False`` drops Pause/Resume and Stop, for the user who does not
    want to drive the printer from a lock screen. Dismiss survives that: a swipe
    only removes the notification on screen, and the next refresh posts it again
    under the same tag, so Dismiss is the only way to retire the card for the
    rest of the print. It leaves the print alone, which is what distinguishes it
    from Stop.
    """
    buttons: list[dict[str, Any]] = []
    if controls:
        primary_key = ACTION_RESUME if paused else ACTION_PAUSE
        primary_icon = (
            "sfsymbols:play.circle" if paused else "sfsymbols:pause.circle"
        )
        buttons.append(
            {
                "action": ids[primary_key],
                "title": labels.get(primary_key, ""),
                "icon": primary_icon,
            }
        )
        buttons.append(
            {
                "action": ids[ACTION_STOP],
                "title": labels.get(ACTION_STOP, ""),
                "icon": "sfsymbols:stop.circle",
                "destructive": True,
                "authenticationRequired": True,
            }
        )
    buttons.append(
        {
            "action": ids[ACTION_DISMISS],
            "title": labels.get(ACTION_DISMISS, ""),
            "icon": "sfsymbols:xmark.circle",
        }
    )
    return buttons
