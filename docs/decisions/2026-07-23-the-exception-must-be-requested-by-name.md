# Decision Log: the exception must be requested by name (WO-023 §2)

**Date:** 2026-07-23
**WO:** WO-023 §2 (FOUNDATION) — the coherence assertion and its named escape hatch
**Authority:** RULING D34-3; Principle VIII (a governed system's exceptions must be greppable);
S13/D37 (the escape hatch carries its own refusal/preservation dual)
**Related:** [[a-guard-can-audit-the-object-model]],
[[a-ruling-about-a-seam-must-be-written-against-its-consumers]],
[[a-check-is-bounded-by-the-form-it-matches]]

---

## The entry

> "The coherence gate needs an escape hatch: the suspend detector legitimately runs an INCOHERENT
> clock pair (a fake wall against a real monotonic), because the divergence between the two clocks is
> the thing it tests — a coherent pair would destroy the instrument. The tempting implementation is
> for the gate to RECOGNISE that shape ('a fake wall, a real monotonic, heartbeat drain — that's the
> suspend test, let it through'). That is INFERENCE, and INFERENCE IS VIGILANCE: a gate that deduces
> 'this looks like the suspend test' will one day bless an ACCIDENTAL incoherence that happens to
> match the shape, silently, with no record that an exception was taken. So the exception is
> REQUESTED BY NAME — an explicit per-invocation `incoherent_clocks_allowed='suspend-detector-test'`
> the gate reads and never infers. Every incoherent run in the project's history is then greppable by
> its own declaration, and an incoherence that forgot to declare itself REFUSES.
>
> The hatch carries its OWN dual (S13/D37), or it is a hole: the identical incoherent injection
> PROCEEDS when named and REFUSES when unnamed, both proven in the same test. A hatch tested only in
> its open position is indistinguishable from a gate that never closed."

---

**What was built.** `get_live_market_data` takes an explicit `incoherent_clocks_allowed` argument
(default empty = coherence enforced). The gate refuses an incoherent pair with
`CLOCK_INJECTION_REFUSED: COHERENCE` UNLESS that argument is non-empty; it inspects the argument, not
the injection pattern. The FakeClock harness (WO-023 §3) makes coherence the DEFAULT construction
(one counter, two fixed-offset interfaces sharing a `_coherence_token`) and puts incoherence behind a
separately-named factory (`incoherent_clock_pair`), so incoherence is never the default path in the
harness either. The migrated `test_host_suspend_recorded_diagnostic_not_terminal` is the SOLE
enumerated customer of the hatch, its docstring stating why. The bite proof's third assertion is the
hatch's own dual: named → proceeds, unnamed → refuses, same injection.
