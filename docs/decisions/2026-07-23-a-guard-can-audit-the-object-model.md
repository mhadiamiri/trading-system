# Decision Log: a guard can audit the object model (WO-023 §2)

**Date:** 2026-07-23
**WO:** WO-023 §2 (FOUNDATION) — the three-field pre-connection clock/transport gate
**Authority:** Principle VIII (observability); RULINGS D34-2, D34-3; standing rule 0.1a (retire
test doubles / monkeypatching), S13/D37 (preservation duals)
**Related:** [[a-ruling-about-a-seam-must-be-written-against-its-consumers]],
[[the-exception-must-be-requested-by-name]], [[an-environment-is-strict-along-axes]], the WO-014b
`fake_ws_transport` harness, WO-015 `GAP_PERSIST_UNCONFIGURED`

---

## The entry

> "The ruled invariant — *a non-default clock is permitted ONLY where the transport is also
> non-default* — turned out to be implementable only by MAKING IT TRUE of the object first. To
> assert 'compare your clock against your transport,' the object has to be able to NAME its own
> transport; it could not. The clock was already a field (`_wall_clock`), but the transport was a
> module-level `websockets.connect` that tests reached around with `patch(...)`. So the guard's real
> first act was not to refuse a bad state — it was to EXPOSE that the object model had no seam where
> the transport lived. A well-specified guard does more than refuse bad states and preserve good
> ones (its two visible halves): it AUDITS THE OBJECT MODEL it is asked to defend, and an invariant
> the model cannot even express is a finding about the model, not a line of code to write.
>
> COROLLARY (the 0.1a direction of travel, banked as a side effect): giving the object a
> `_connect_fn` field so the gate could name the transport ALSO retires transport monkeypatching —
> the migrated suspend test now injects its transport instead of patching `websockets.connect`. The
> seam the guard demanded is the same seam that removes a test double. Guards that audit the model
> tend to pay this way."

---

**What was built (production change, RULING D34-2/D34-3).** `KrakenV2BookAdapter.__init__` gained two
symmetric seams: `monotonic_clock` (the deadline clock, D25-correct — an interval belongs on
monotonic) and `connect_fn` (the transport factory). `_connect_fn` is stored as the RAW injection
(None == default) and resolved late at the call site (`self._connect_fn or websockets.connect`), so
existing module-level patching keeps working AND the gate can read the injection sentinel to know
whether the caller named a transport. The gate (`_assert_clock_transport_gate`, pre-connection, same
discipline as `GAP_PERSIST_UNCONFIGURED`) then asserts COUPLING (a non-default clock requires a
non-default transport — a fake clock must never drive a live socket) and COHERENCE (injected clocks
must be the one-source coherent pair unless declared incoherent by name), refusing with
`CLOCK_INJECTION_REFUSED` and naming which assertion failed. The refusal half and both preservation
halves live in one bite-proved test (S13/D37).
