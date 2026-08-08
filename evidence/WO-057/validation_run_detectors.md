# WO-057 §4.5 — THE DETECTORS' PRODUCTION CALL SITES (rule 0.14)

Every detector built or repaired by WO-057, with the site that RUNS it. An empty cell is an open
defect, so none is left empty.

| # | Abort condition | Detector | **Run from (production call site)** | Fires? |
|---|---|---|---|---|
| 1 | trade subscribe not acked within 10 s | `KrakenV2BookAdapter._check_trade_ack_deadline(mono)` | `get_live_market_data`'s frame path — called on **every received frame**, so it is evaluated by the real loop rather than by a timer nobody drives | ✅ proven |
| 2 | a frame with `observable: true` and a **fabricated** `last_price` | `tools/corpus_fabrication_scan.py` | **the validation run's post-run step**, below — and its exit code is the gate | ✅ proven |
| 4 | retention caps trim more than once per segment | `KrakenV2BookAdapter.take_trim_events()` | `tools/live_corpus_capture.py::_close_segment` — read-and-reset at rotation, written into the **segment record** | ✅ proven |
| 3 | a trade arrives while the channel is unobservable | `TradeMerger.observe()` + the capture demux | `KrakenV2BookAdapter._demux_non_book` ← `process_raw_frame` | ✅ re-verified |
| 5 | a `GapRecord` written with a trade-channel cause | `GapRecord.__post_init__` cause validation | the gap ledger's own construction path | ✅ re-verified |
| 6 | book throughput below baseline | `ThroughputRecord` + `get_diagnostic_counters()` | `get_live_market_data` — instrument survives the second channel | ✅ re-verified |

---

## CONDITION 2 — THE POST-RUN STEP, AND WHY THE EXIT CODE MATTERS

WO-055 is to run this immediately after the validation capture closes, against the throwaway
corpus it produced:

```
python tools/corpus_fabrication_scan.py captures/<validation_corpus_path>
```

**The exit code is the gate, and the three outcomes are three distinct codes:**

| exit | outcome | what WO-055 does |
|---|---|---|
| `0` | **CLEAN** — examined N observable frames, found zero fabricated prices | §3.5 PASSES |
| `1` | **VIOLATIONS** — n frames named | **ABORT.** Condition 2 has tripped |
| `3` | **NOT_APPLICABLE** — nothing examinable | **NOT A PASS.** The capture produced no `trades` sub-object at all, which means the merge did not reach the corpus — a finding in its own right |

`NOT_APPLICABLE` is deliberately **not** `0`. Treating it as success would commit the WO-055 false
green in a shell script instead of in a report, which is the same defect wearing different clothes.

**Falsifier for a CLEAN verdict (0.12):** any observable frame with `count == 0` and a non-null
`last_price`. **Falsifier for NOT_APPLICABLE:** the presence of any frame carrying
`trades.observable`. The two are not interchangeable and the tool refuses to conflate them.
