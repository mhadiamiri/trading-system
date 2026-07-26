# Decision Log: a transport seam is not a clock seam (WO-030)

**Date:** 2026-07-25
**WO:** WO-030 — clock seam threading (production), D38
**Authority:** D38 (both paths, both-seam registration contract); D36 (the shared-builder doctrine);
Principle VII (venue independence); the call-graph doctrine
**Related:** [[scope-intentions-do-not-survive-a-shared-implementation]],
[[an-instrument-must-not-write-into-the-evidence-record]],
[[a-ruling-about-a-seam-must-be-written-against-its-consumers]]

---

## The entry (ratified verbatim)

> A transport seam is not a clock seam; each injected dependency crosses the runner/factory/builder
> boundary on its own or not at all. Unblocking a factory-built race for its transport (WO-028's
> connect_fn) did not unblock it for its clock; the clock needed the identical threading.
>
> Sixth specimen of a-figure-traveled-as-prose (WO-027's "26" was 25 until this WO); second sourced
> from the shared builder (D36 was the first).
>
> Generalizing, since the builder will be the crossing point for every future seam:
> **the shared builder's forwarding surface is a contract inventory — every kwarg it forwards is a
> declared obligation on every live-capable builder, and the registration gate is that inventory's
> enforcement.** When a third seam needs the crossing, the checklist question is already written:
> "what else does the shared builder forward, and does every live-capable builder accept it?"

---

## What this WO built

The clock seam (`monotonic_clock` / `wall_clock`) threads `LiveCaptureRunner → create_live_capture_feed
→ _build_kraken_v2`, exactly parallel to WO-028's `connect_fn`, with declared defaults at the builder
signature — so a factory-built adapter is now clock-injectable and race #5 rejoins pass two's
denominator of 26 (WO-029 converts it; WO-030 does not).

The registration contract was **generalized, not duplicated**: `registry._LIVE_FORWARDED_PARAMS`
`= ("connect_fn", "monotonic_clock", "wall_clock")` is the forwarding inventory, and
`register(live_capture=True)` requires every live-capable builder to accept all of it. WO-028's
`LIVE_CAPABLE_BUILDER_MISSING_CONNECT_FN` was **renamed** to
`LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM` (one load-time code for the whole contract — avoiding
handing the vocabulary-split WO a second tangle, per §3).

## The one deviation from the WO's literal text (and why it was right, §0.1)

§2.1 wrote the clock defaults as `monotonic_clock=time.monotonic, wall_clock=time.time`. The D35-2
convention block (kraken_v2_book.py) makes the two clock seams **deliberately asymmetric**:
`_monotonic_clock` is eager (detection `is not time.monotonic`) and `_wall_clock` is raw-None
(detection `is not None`). A builder default of `wall_clock=time.time`, held in `_wall_clock`, would
read as **injected** and trip COHERENCE on a real capture. So the wall seam's declared default is
**`None`** — the sentinel the raw-None convention requires — and the builder sets `_wall_clock` only
when a fake wall is actually injected. `time.monotonic` for the monotonic seam is safe (reads
not-injected). Code won over the order's literal example, exactly as §0.1 anticipates.
