"""
WO-066 §2 term 11 — `shutdown_policy_disabled`, RE-SPECIFIED AS A MEASUREMENT.

WHY THIS EXISTS
---------------
Term 11 has been an operator declaration through every capture in this project::

    sd = os.environ.get("CORPUS_SHUTDOWN_POLICY_DISABLED", "").lower() == "true"

**An operator declaration cannot fail.** It reports the operator's intention, which is not a
property of the host, so the term was structurally incapable of going RED no matter what the
machine was about to do. On 2026-08-12 it read GREEN and the host rebooted 5 h 21 m into a 24 h
capture — Windows Update, `MoUsoCoreWorker.exe`, "Service pack (Planned)" — destroying the run.

**A gate that cannot fail is not a gate.** This is the third naming of that family in this
project (`checksum_failures_total` wired-and-always-zero; `\\Memory\\Pages/sec` counting
file-backed I/O; this). The repair is the same one that worked for the Term 2 memory gate: stop
reading a NAME and start reading the MECHANISM.

WHAT THE MECHANISM ACTUALLY IS
------------------------------
Windows may restart the host for updates **outside active hours**. Active hours are two registry
values, and they are readable::

    HKLM\\SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings
        ActiveHoursStart  (hour 0-23)   ActiveHoursEnd  (hour 0-23)

The **permitted reboot window is the COMPLEMENT of active hours**. On the host that lost the run,
`ActiveHoursStart=8, ActiveHoursEnd=1`, so reboots were permitted 01:00-08:00 local — precisely
the hours the capture was unattended in.

**Active hours cannot cover a 24 h run.** Windows caps the active-hours span at 18 of 24 hours, so
for any capture longer than 18 h an overlap is UNAVOIDABLE and no active-hours setting can close
it. The only thing that closes it is pausing updates::

    PauseUpdatesExpiryTime / PauseFeatureUpdatesEndTime / PauseQualityUpdatesEndTime

so the gate's GREEN path is "updates are paused past the end of this run", not "the operator says
so".

FAIL-CLOSED (the Term 2 doctrine, D-r59)
----------------------------------------
An unreadable policy is RED, never GREEN. A gate that cannot measure must not pass. Likewise
`SmartActiveHoursState=1` means Windows chooses active hours itself and the stored numbers no
longer describe what it will do — the measurement is then not trustworthy, so it is RED unless a
pause covers the run.

FALSIFIER (0.12)
----------------
This verdict would be shown wrong by a host that reboots for updates DURING a window this gate
called GREEN. Two known routes: an EXPEDITED update (Microsoft can force one out of band, and
`IsExpedited` is reported here for that reason), and a non-Update reboot — a driver installer, a
power event, or a human. **This gate bounds Windows Update's scheduled restart. It does not bound
"the host will stay up", and it must not be read as though it did.**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

# The registry home of every value this gate reads. Named once, cited where it is used.
UX_SETTINGS = r"SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
AU_ROOT = r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update"
CBS_ROOT = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing"

# Windows will not accept an active-hours span wider than this, so no setting covers a 24 h run.
MAX_ACTIVE_HOURS_SPAN = 18


@dataclass(frozen=True)
class HostUpdatePolicy:
    """What the host actually says, as read. `source='unreadable'` is a first-class outcome."""

    source: str                                   # "registry" | "unreadable" | "injected"
    active_hours_start: Optional[int] = None
    active_hours_end: Optional[int] = None
    pause_until: Optional[datetime] = None        # tz-aware; the latest pause expiry found
    reboot_pending: bool = False
    smart_active_hours: bool = False
    is_expedited: bool = False
    detail: str = ""


@dataclass(frozen=True)
class RebootWindowVerdict:
    green: bool
    reason: str
    overlap_hours: float = 0.0
    permitted_windows: list = field(default_factory=list)   # [(start, end)] local, within the run
    policy: Optional[HostUpdatePolicy] = None
    falsifier: str = (
        "Falsified by the host rebooting for updates inside a window this gate called GREEN. It "
        "bounds Windows Update's SCHEDULED restart only: an expedited update, a driver installer, "
        "a power event or a person are all outside it. It is not a promise that the host stays up."
    )

    def to_dict(self) -> dict:
        return {
            "green": self.green,
            "reason": self.reason,
            "overlap_hours": round(self.overlap_hours, 4),
            "permitted_reboot_windows": [(a.isoformat(), b.isoformat())
                                         for a, b in self.permitted_windows],
            "gated_on": "WINDOWS UPDATE ACTIVE HOURS + PAUSE EXPIRY (measured, not declared)",
            "policy": (dict(source=self.policy.source,
                            active_hours_start=self.policy.active_hours_start,
                            active_hours_end=self.policy.active_hours_end,
                            pause_until=(self.policy.pause_until.isoformat()
                                         if self.policy.pause_until else None),
                            reboot_pending=self.policy.reboot_pending,
                            smart_active_hours=self.policy.smart_active_hours,
                            is_expedited=self.policy.is_expedited,
                            detail=self.policy.detail)
                       if self.policy else None),
            "falsifier": self.falsifier,
        }


def permitted_reboot_windows(policy: HostUpdatePolicy, run_start: datetime,
                             run_end: datetime) -> list:
    """The intervals inside [run_start, run_end] when Windows is ALLOWED to restart the host.

    The complement of active hours, clipped to the run. Active hours wrap midnight, which is the
    ordinary case (08:00-01:00 on the host that lost the run), so the wrap is handled explicitly
    rather than assumed away.
    """
    s, e = policy.active_hours_start, policy.active_hours_end
    if s is None or e is None or s == e:
        # No usable active-hours declaration => every hour is permitted. Fail-closed shape:
        # the widest possible window, not the narrowest.
        return [(run_start, run_end)]

    def active_at(dt: datetime) -> bool:
        h = dt.hour
        return (s <= h < e) if s < e else (h >= s or h < e)

    out, cur = [], None
    t = run_start.replace(minute=0, second=0, microsecond=0)
    while t < run_end:
        nxt = t + timedelta(hours=1)
        if not active_at(t):
            cur = cur or max(t, run_start)
        elif cur is not None:
            out.append((cur, min(t, run_end)))
            cur = None
        t = nxt
    if cur is not None:
        out.append((cur, run_end))
    return out


def evaluate(policy: HostUpdatePolicy, run_start: datetime, run_hours: float
             ) -> RebootWindowVerdict:
    """Decide whether this run's window is protected. PURE — no registry, no clock.

    Kept free of I/O deliberately: the policy logic is the part that has to be bite-proved, and a
    function that reads the registry could only be tested on one operating system.
    """
    run_end = run_start + timedelta(hours=run_hours)

    if policy.source == "unreadable":
        return RebootWindowVerdict(
            False,
            f"UPDATE_POLICY_UNREADABLE: {policy.detail or 'no reading obtained'}. A gate that "
            f"cannot measure must not pass — RED, fail-closed.", policy=policy)

    if policy.reboot_pending:
        return RebootWindowVerdict(
            False,
            "REBOOT_ALREADY_PENDING: the host is holding a restart for an installed update, so "
            "it will reboot at the first permitted opportunity. Reboot first, then capture.",
            policy=policy)

    # THE ONE GREEN PATH THAT SCALES TO 24 h: updates paused past the end of the run.
    if policy.pause_until is not None and policy.pause_until >= run_end:
        return RebootWindowVerdict(
            True,
            f"UPDATES_PAUSED: paused until {policy.pause_until.isoformat()}, run ends "
            f"{run_end.isoformat()}. Scheduled update restarts cannot fire inside the window.",
            policy=policy)

    windows = permitted_reboot_windows(policy, run_start, run_end)
    overlap = sum((b - a).total_seconds() for a, b in windows) / 3600.0

    if policy.smart_active_hours:
        return RebootWindowVerdict(
            False,
            "SMART_ACTIVE_HOURS_ENABLED: Windows sets active hours itself, so the stored "
            "ActiveHoursStart/End do not describe what it will do. The measurement is not "
            "trustworthy — pause updates instead of relying on it.",
            overlap, windows, policy)

    if policy.pause_until is not None:
        return RebootWindowVerdict(
            False,
            f"PAUSE_EXPIRES_MID_RUN: paused only until {policy.pause_until.isoformat()}, but the "
            f"run ends {run_end.isoformat()}. {overlap:.2f} h of the window is unprotected.",
            overlap, windows, policy)

    if overlap > 0:
        span = ("undeclared" if policy.active_hours_start is None else
                f"{policy.active_hours_start:02d}:00-{policy.active_hours_end:02d}:00")
        extra = ("  Active hours cap at 18 of 24 h, so a run this long CANNOT be covered by "
                 "active hours at all — pausing updates is the only remedy."
                 if run_hours > MAX_ACTIVE_HOURS_SPAN else "")
        return RebootWindowVerdict(
            False,
            f"RUN_OVERLAPS_PERMITTED_REBOOT_WINDOW: active hours {span}, so Windows may restart "
            f"for {overlap:.2f} h of this {run_hours:g} h run.{extra}",
            overlap, windows, policy)

    return RebootWindowVerdict(
        True,
        f"RUN_INSIDE_ACTIVE_HOURS: the whole {run_hours:g} h window falls within active hours "
        f"{policy.active_hours_start:02d}:00-{policy.active_hours_end:02d}:00, when Windows does "
        f"not schedule restarts.", 0.0, [], policy)


# ── the host reading. Windows-only by nature; import-guarded so the Linux CI leg still loads. ──
def read_host_policy(now: Optional[datetime] = None) -> HostUpdatePolicy:
    """Read the live host policy, or return `source='unreadable'` with the reason.

    Never raises: an unreadable host is a verdict input, not a crash. `evaluate` turns it RED.
    """
    from datetime import timezone
    now = now or datetime.now(timezone.utc)
    try:
        import winreg
    except ImportError as exc:                                        # pragma: no cover - Linux CI
        return HostUpdatePolicy("unreadable", detail=f"winreg unavailable ({exc}); "
                                                     "this gate measures a Windows host")

    def val(root, path, name):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as k:
                return winreg.QueryValueEx(k, name)[0]
        except OSError:
            return None

    def key_exists(path):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path):
                return True
        except OSError:
            return False

    start = val(winreg.HKEY_LOCAL_MACHINE, UX_SETTINGS, "ActiveHoursStart")
    end = val(winreg.HKEY_LOCAL_MACHINE, UX_SETTINGS, "ActiveHoursEnd")
    if start is None and end is None:
        return HostUpdatePolicy("unreadable",
                                detail=f"neither ActiveHoursStart nor ActiveHoursEnd readable "
                                       f"under HKLM\\{UX_SETTINGS}")

    pause_until, pauses = None, []
    for name in ("PauseUpdatesExpiryTime", "PauseFeatureUpdatesEndTime",
                 "PauseQualityUpdatesEndTime"):
        raw = val(winreg.HKEY_LOCAL_MACHINE, UX_SETTINGS, name)
        if not raw:
            continue
        try:
            txt = str(raw).replace("Z", "+00:00")
            dt = datetime.fromisoformat(txt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            pauses.append((name, dt))
        except ValueError:
            continue
    if pauses:
        # The EARLIEST expiry governs: once any pause lapses the host can restart again, so
        # taking the latest would overstate the protection.
        pause_until = min(dt for _, dt in pauses)

    pending = (key_exists(CBS_ROOT + r"\RebootPending")
               or key_exists(AU_ROOT + r"\RebootRequired"))

    return HostUpdatePolicy(
        source="registry",
        active_hours_start=int(start) if start is not None else None,
        active_hours_end=int(end) if end is not None else None,
        pause_until=pause_until,
        reboot_pending=bool(pending),
        smart_active_hours=bool(val(winreg.HKEY_LOCAL_MACHINE, UX_SETTINGS,
                                    "SmartActiveHoursState") or 0),
        is_expedited=bool(val(winreg.HKEY_LOCAL_MACHINE, UX_SETTINGS, "IsExpedited") or 0),
        detail=("pauses: " + ", ".join(f"{n}={d.isoformat()}" for n, d in pauses)
                if pauses else "no pause expiry set"),
    )
