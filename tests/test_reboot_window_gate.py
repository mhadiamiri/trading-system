"""
WO-066 §2 term 11 — BITE PROOF for the gate that replaced an operator declaration.

WHY THIS FILE IS THE POINT. Term 11 was::

    os.environ.get("CORPUS_SHUTDOWN_POLICY_DISABLED", "").lower() == "true"

There is no host state that makes that expression RED. It reported the operator's intention, and
an intention is not a property of the machine — so the term was structurally incapable of failing.
On 2026-08-12 it read GREEN and Windows Update restarted the host 5 h 21 m into a 24 h capture.

**The single most important test here is `test_the_gate_can_actually_fail`**: it replays the real
host state of that morning and requires RED. A gate that cannot fail is not a gate, and this file
is what stops term 11 quietly becoming one again.

Every test injects a `HostUpdatePolicy` rather than reading the registry, so the POLICY LOGIC —
the part that has to be right — is proved on both CI legs, including the Linux one where no
registry exists.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trading.loop import reboot_window as rw


EDT = timezone(timedelta(hours=-4))

# The host as it actually was when the capture was launched: active hours 08:00-01:00, no pause.
# Windows restarted it at 04:16 local, inside the 01:00-08:00 complement.
HOST_2026_08_12 = rw.HostUpdatePolicy(
    source="registry", active_hours_start=8, active_hours_end=1,
    pause_until=None, reboot_pending=False, smart_active_hours=False,
    detail="no pause expiry set",
)
LAUNCH = datetime(2026, 8, 11, 22, 54, 45, tzinfo=EDT)          # 02:54:45Z, the real launch


class TestTheGateCanFail:

    def test_the_gate_can_actually_fail(self):
        """BITE — the real 2026-08-12 host state, the real 24 h request: RED.

        The old term returned GREEN for this exact host. If this ever passes GREEN again, term 11
        has reverted to a declaration.
        """
        v = rw.evaluate(HOST_2026_08_12, LAUNCH, 24.0)

        assert v.green is False, (
            "term 11 passed a host that was five hours from a Windows Update restart — the gate "
            "cannot fail, and a gate that cannot fail is not a gate")
        assert "RUN_OVERLAPS_PERMITTED_REBOOT_WINDOW" in v.reason
        assert v.overlap_hours == pytest.approx(7.0, abs=0.01), (
            "the 01:00-08:00 complement of 08:00-01:00 active hours is 7 h")

    def test_it_names_the_window_the_reboot_actually_landed_in(self):
        """The verdict must locate the exposure, not merely assert it.

        The forced restart came at 04:16 local. A gate that says "unsafe" without saying WHEN
        cannot be acted on, and the operator would have no way to schedule around it.
        """
        v = rw.evaluate(HOST_2026_08_12, LAUNCH, 24.0)
        reboot_at = datetime(2026, 8, 12, 4, 16, 2, tzinfo=EDT)

        assert any(a <= reboot_at <= b for a, b in v.permitted_windows), (
            f"the gate did not name the window containing the restart that destroyed the run; "
            f"it reported {[(a.isoformat(), b.isoformat()) for a, b in v.permitted_windows]}")

    def test_a_run_this_long_cannot_be_covered_by_active_hours_at_all(self):
        """Windows caps active hours at 18 of 24, so the advice must not be 'widen active hours'."""
        v = rw.evaluate(HOST_2026_08_12, LAUNCH, 24.0)
        assert "pausing updates is the only remedy" in v.reason
        assert rw.MAX_ACTIVE_HOURS_SPAN < 24


class TestTheGreenPaths:

    def test_dual_updates_paused_past_the_end_of_the_run_is_green(self):
        """DUAL — the one green path that scales to 24 h. Without this the gate is unusable."""
        paused = rw.HostUpdatePolicy(
            source="registry", active_hours_start=8, active_hours_end=1,
            pause_until=LAUNCH.astimezone(timezone.utc) + timedelta(days=7))
        v = rw.evaluate(paused, LAUNCH, 24.0)

        assert v.green is True
        assert "UPDATES_PAUSED" in v.reason

    def test_dual_a_short_run_inside_active_hours_is_green(self):
        """DUAL — a 4 h run starting 09:00 never touches the reboot window. It must not be refused.

        A gate that refused every run would be as useless as one that passed every run; it would
        simply be discovered later, when someone disabled it.
        """
        v = rw.evaluate(HOST_2026_08_12, datetime(2026, 8, 12, 9, 0, tzinfo=EDT), 4.0)

        assert v.green is True
        assert "RUN_INSIDE_ACTIVE_HOURS" in v.reason
        assert v.overlap_hours == 0.0

    def test_a_pause_expiring_mid_run_is_not_green(self):
        """Half a pause is not a pause — and the reason must say how much is exposed."""
        v = rw.evaluate(
            rw.HostUpdatePolicy(source="registry", active_hours_start=8, active_hours_end=1,
                                pause_until=LAUNCH.astimezone(timezone.utc) + timedelta(hours=6)),
            LAUNCH, 24.0)

        assert v.green is False
        assert "PAUSE_EXPIRES_MID_RUN" in v.reason


class TestFailClosed:

    def test_an_unreadable_policy_is_red(self):
        """The Term 2 doctrine: a gate that cannot measure must not pass.

        This is also the Linux CI leg's real state — `winreg` does not exist there — so the
        fail-closed path is exercised on every run of the suite, not only in theory.
        """
        v = rw.evaluate(rw.HostUpdatePolicy(source="unreadable", detail="winreg unavailable"),
                        LAUNCH, 24.0)
        assert v.green is False
        assert "UPDATE_POLICY_UNREADABLE" in v.reason

    def test_a_pending_reboot_is_red_whatever_the_active_hours_say(self):
        """A held restart fires at the first permitted opportunity — active hours are irrelevant."""
        v = rw.evaluate(
            rw.HostUpdatePolicy(source="registry", active_hours_start=8, active_hours_end=1,
                                reboot_pending=True),
            datetime(2026, 8, 12, 9, 0, tzinfo=EDT), 4.0)
        assert v.green is False
        assert "REBOOT_ALREADY_PENDING" in v.reason

    def test_smart_active_hours_makes_the_reading_untrustworthy(self):
        """When Windows picks active hours itself, the stored numbers stop describing behaviour.

        Reading them anyway would be the WO-058 defect — trusting a counter whose NAME matches
        while its MECHANISM does not.
        """
        v = rw.evaluate(
            rw.HostUpdatePolicy(source="registry", active_hours_start=8, active_hours_end=1,
                                smart_active_hours=True),
            datetime(2026, 8, 12, 9, 0, tzinfo=EDT), 4.0)
        assert v.green is False
        assert "SMART_ACTIVE_HOURS_ENABLED" in v.reason

    def test_an_undeclared_active_hours_window_is_treated_as_fully_permissive(self):
        """No declaration means every hour is permitted — the widest window, not the narrowest."""
        v = rw.evaluate(rw.HostUpdatePolicy(source="registry"), LAUNCH, 4.0)
        assert v.green is False
        assert v.overlap_hours == pytest.approx(4.0, abs=0.01)


class TestMutation:
    """MUTATION — the discriminating check. Neuter the overlap comparison and the BITE must fail."""

    def test_removing_the_overlap_check_makes_the_dangerous_host_pass(self, monkeypatch):
        monkeypatch.setattr(rw, "permitted_reboot_windows", lambda policy, s, e: [])

        v = rw.evaluate(HOST_2026_08_12, LAUNCH, 24.0)

        assert v.green is True, "the mutation did not reach the comparison under test"
        assert v.overlap_hours == 0.0
        # ...which is precisely the old behaviour: GREEN for a host about to reboot. The BITE above
        # is therefore an assertion about the overlap comparison and not about the fixture.


class TestWindowArithmetic:

    def test_active_hours_wrapping_midnight_is_handled_explicitly(self):
        """08:00-01:00 wraps. Treating it as an ordinary interval would invert the whole verdict."""
        windows = rw.permitted_reboot_windows(
            HOST_2026_08_12,
            datetime(2026, 8, 12, 0, 0, tzinfo=EDT), datetime(2026, 8, 13, 0, 0, tzinfo=EDT))
        covered = [h for a, b in windows
                   for h in range(a.hour, b.hour if b.hour > a.hour else 24)]

        assert 3 in covered and 7 in covered, "01:00-08:00 must be permitted-reboot time"
        assert 12 not in covered and 20 not in covered, "midday is active hours, not reboot time"

    def test_the_falsifier_is_carried_on_the_verdict(self):
        """0.12 — the observation states what would show it wrong, at the point of claim."""
        v = rw.evaluate(HOST_2026_08_12, LAUNCH, 24.0)
        assert "expedited" in v.falsifier.lower()
        assert "not a promise that the host stays up" in v.falsifier
