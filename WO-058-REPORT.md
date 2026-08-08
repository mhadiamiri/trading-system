# WO-058 — FLOW GATE + RETIREMENTS. **Term 2 = RED. §4 did not run.**

**NO SOCKET OPENED. The grant is unspent.** **SHIP IMPACT: YES** — gate logic and a rename.
Corpus v1 `e3ab1aec…` unchanged, 38/38 capture hashes verify.

> ## §3 THE VERDICT — RED, ON FLOW
>
> | | measured over the declared 60 s / 2 s / 30-sample window | bound | |
> |---|---:|---:|---|
> | **FLOW — the gate** | **max 991.90 · mean 53.089 pages/sec** | 10.0 / 1.0 | 🔴 |
> | STOCK — context only | 495 MiB swap in use | *(never gates)* | — |
> | FREE memory | 3,956 MiB | 512 MiB floor | 🟢 |
>
> 19 of 30 samples read exactly zero; 11 did not, several in the hundreds. **The host is paging at
> idle** — not holding parked bytes, actually servicing faults from disk. This is D46's mechanism,
> measured directly for the first time.
>
> Per §3's pre-ruled fork: **flow non-zero → RED, report the flow figure as the operator's target,
> STOP. §4 did not run.**

---

## §1 STATE

HEAD `b8b877f` (WO-057 close, CI 31277333073, 558/2). `git diff -- src/` clean. Baseline
**558 passed, 2 skipped**. All gates green; corpus v1 `e3ab1aec…` and 38/38 verified.

---

## §2.1 THE RETIREMENT — ⚠ **four sites, not three**

§2.1 named three (WO-054/055/056 reports). **0.11 again: `evidence/WO-054/phase_b_preconditions.md`
was outside the reported count** — the checklist that the grant is issued against, which is the one
place the figure did operational work.

| # | Site | In the reported three? |
|---|---|---|
| 1 | `WO-054-REPORT.md:360` | yes |
| 2 | `WO-055-VALIDATION-REPORT.md:6` and `:29` | yes |
| 3 | `WO-056-REPORT.md:37` | yes |
| **4** | **`evidence/WO-054/phase_b_preconditions.md:50`** | **NO — missed** |

All four annotated in D47 form (dated, in place, reports not rewritten), each carrying the
consequence verbatim: *an unreachable gate demanding ~3.6× more headroom than the reference capture
itself ever had, blocking a capture the host was always able to run.*

**Deliberately NOT annotated:** the corpus's own `MANIFEST.json` / `PREFLIGHT.json` records. Those
are the read-only source data where the number is *correct* — it really is memory used. The defect
was in reading it, not in recording it. Annotating them would also change the v1 digest.

Decision doc: `docs/decisions/2026-08-08-a-number-wrong-in-a-way-that-survives-being-questioned.md`,
carrying the ratified line and the point that matters — **WO-057 *did* question this figure and was
right that it was underived; it asked about the derivation and never about the identity. Passing an
audit aimed one layer away from the defect is not evidence.**

## §2.2 THE RENAME

`LoadRecord.memory_gb` → **`memory_used_gb`**. Third document-vs-reality naming defect; the name now
states the *quantity*, not just the unit.

**Corpus readability — `corpus_20260805` remains readable, and here is exactly how.** The persisted
records now write **both** keys:

```json
"load_record": { "memory_used_gb": 12.33, "memory_gb": 12.33, ... }
```

`memory_gb` is a **compatibility alias carrying the same value**, not a second quantity. So:

- **existing corpora** (written with only `memory_gb`) — unchanged on disk, read exactly as before;
- **new corpora** — carry both, so a reader written against either name works;
- **no declared break.** The alias is deliberate: the corpora are ratified artifacts and a rename
  that made them unreadable would be a far worse defect than the one being fixed.

The preflight's printed line now reads `Memory USED: … (host-wide; NOT free, NOT this process)` —
the sentence whose absence started this.

## §2.3 THE FLOW GATE

### Which counter, and why — enumerated on this host (0.11)

`psutil.swap_memory().sin/sout` are documented-unsupported on Windows and read 0 unconditionally,
so they cannot be the source. The Windows counters, sampled directly:

| counter | reading | |
|---|---:|---|
| `\Memory\Pages/sec` | **0.00** *(at the time of first probe)* | hard faults, disk I/O either way — **THE GATE** |
| `\Memory\Pages Input/sec` | 0.00 | the read half; D46's stall specifically |
| `\Memory\Pages Output/sec` | 0.00 | |
| `\Memory\Page Faults/sec` | **4,165–5,410** | **mostly SOFT** — satisfied from RAM |

**`Pages/sec` is the gate.** It counts only faults that required disk I/O. Both directions are
included: page-*out* is the OS trimming working sets, which is evidence of pressure even though it
does not stall the loop — conservative in the safe direction.

**`Page Faults/sec` is deliberately not used.** It counts soft faults — a resident page, a
standby-list hit, first touch of a committed page — costing microseconds and never reaching disk.
It reads thousands per second on any idle Windows box, so a gate on it would be **permanently RED**:
precisely the failure this WO exists to end.

### "~zero", declared numerically (0.15)

**Every sample ≤ 10.0 pages/sec, and the mean ≤ 1.0.**

*Derivation.* A 4 KiB page read from this host's SSD costs ~50–100 µs. At 10 pages/sec that is
~1 ms of disk wait per second — 0.1% of wall time — against a capture whose frame budget is ~30 ms
at 24–32 frames/s. To threaten the multi-second `HEARTBEAT_ABSENCE` timeout D46 describes, paging
must stall the loop for *seconds*, needing tens of thousands of pages/sec. The per-sample bound sits
roughly **three orders of magnitude** below the level that could plausibly matter. The mean bound
catches the other shape: a steady trickle that never trips the per-sample bound.

**Rounded, and said so (0.15):** 10.0 and 1.0 are round numbers chosen *above* the derivation, not
fitted to it. A bound resting on an order-of-magnitude argument about disk latency does not deserve
more precision.

### Fail closed

If the counter cannot be read, the gate is **RED**. `read_paging_flow()` returns `None`, never
`0.0` — `0.0` would be a claim that the host is not paging; `None` is the absence of a claim. **A
gate that cannot measure must not pass** is the whole lesson of the figures this replaced.

### Bite proof — `tools/wo058_flow_gate_bite_proof.py`, **VERDICT: PASS**

**MUTATION: gate on STOCK instead of FLOW** — WO-057's criterion, restored.

| set | under the mutation |
|---|---|
| **DUAL** (zero flow, 512 MiB stock → GREEN) | **FAILS** |
| BITE (real paging → RED) | still passes |

```
capture_gate.py sha256 BEFORE/AFTER : a377d1db…   IDENTICAL: True
DUAL fails under stock-gating (the pre-ruled case) : True
BITE still passes under stock-gating              : True
```

**The asymmetry is the proof.** A genuinely paging host is RED under *both* criteria, so the bite
cannot tell them apart. Only the dual separates *the host is paging* from *the host is holding
pagefile bytes it is not reading* — and that distinction is what made a runnable capture look
impossible twice.

---

## §3 THE TERM 2 VERDICT — flow and stock side by side

```
FLOW  (\Memory\Pages/sec)   max 991.90  mean 53.089 pages/sec   over 30 samples   <- GATES  🔴
      19 of 30 samples were exactly 0.00; 11 were not.
STOCK (swap bytes in use)   495 MiB                                               <- CONTEXT  —
FREE  memory                3,956 MiB  (floor 512)                                <- 🟢
```

**RED on flow. §4 did not run. The grant is unspent and its 14-day expiry is intact.**

### The operator's target — the right phantom this time

The paging is not noise; it has a structural cause, and it is measurable:

| | |
|---|---:|
| physical RAM | **15.71 GB** |
| **committed** | **17.25 GB** |
| **excess over physical** | **+1.54 GB** |
| commit limit (RAM + pagefile) | 26.71 GB |

**Committed memory exceeds physical RAM by 1.54 GB, so Windows *must* page — it has no choice.**
That is the mechanism, and it is why flow is non-zero while nothing dramatic is happening.

Top committers, aggregated: **chrome 3,042 MB · Code 1,275 MB · claude 1,065 MB · dwm 882 MB ·
Wispr Flow 871 MB · svchost 733 MB.**

**Target: bring committed below ~15.7 GB — roughly 1.6–2 GB to free — then re-run the gate.**
Unlike the retired figure, this one names a mechanism (`commit > physical ⇒ mandatory paging`), a
measurement, and an amount.

**Honest caveat on the measurement:** the host was not idle in the strict sense — this session's own
tooling (claude 1,065 MB) was running, and there is no way to measure an idle host while operating
it. But the commit-over-physical excess is **structural, not session noise**: chrome and Code alone
account for 4.3 GB.

---

## EVERY ATTEMPT

1. **Enumerated the counters on this host before choosing one** — which is how `Page Faults/sec`
   was excluded. Choosing it would have produced a permanently-RED gate, i.e. the same defect in a
   new costume.
2. **⚠ MY FIRST FLOW SAMPLER MEASURED ITSELF.** It called `read_paging_flow()` once per sample —
   30 PowerShell launches across the window — and launching PowerShell loads its executable and
   .NET assemblies from disk, a burst of hard page faults. Over the same window: **30 processes
   reported mean 859 pages/sec where one process reported 277.** A 3× inflation, caused by the
   instrument. Fixed: the whole window is now taken in **one** `Get-Counter` call. The verdict did
   not turn on it — both readings exceeded the bound — but a measurement that inflates 3× is not
   one to keep, and on a quieter host it would be the difference between GREEN and RED.
3. **My first BITE fixture modelled an impossible host** — paging with *zero* pagefile stock. Under
   the stock-gating mutation it failed too, collapsing the asymmetry the proof depends on. A host
   that is actively paging necessarily has stock; the fixture now says so, and the discrimination
   is real.
4. **Found a fourth retirement site** the WO's count did not include (0.11), and it was the
   checklist the grant is issued against.
5. **Did not annotate the corpus's own records**, where the figure is correct — and where an edit
   would change the v1 digest.
6. **A docstring containing `\Memory\Pages/sec` raised a `SyntaxWarning`** (invalid escape); made
   raw.
7. **No socket opened.**

---

## §5 ACCEPTANCE

- [x] 12.33 retired at **every grepped site (four, not three)**, D47 form, decision doc ratified
- [x] Rename landed with the compatibility statement — **`corpus_20260805` remains readable**
- [x] Flow gate bite-proved **with the stock-gating mutation and its asymmetry**
- [x] Term 2 verdict reported with **flow and stock side by side**
- [ ] §4 — **did not run.** Pre-ruled: flow non-zero → RED → STOP. Grant unspent.
- [x] `corpus_20260805` untouched — v1 `e3ab1aec…`, 38/38
- [x] Gates: lint 6/6 · contract 6/6 · ruff · annotation 0 · preflight · partition 31/31

### Test count arithmetic

```
  558  baseline at HEAD b8b877f (WO-057 close, CI 31277333073)
+   5  tests/test_capture_gate.py (13 -> 18: flow bite, stock dual, trickle,
       fail-closed, bounds/counter declarations)
─────
  563  expected  (+ 2 skipped)
```

| Leg | Order A | Order B (seed 58058) |
|---|---|---|
| Python 3.14.6 | **563 passed, 2 skipped** (315.31s) | **563 passed, 2 skipped** (315.39s) |
| Python 3.11.15 | **563 passed, 2 skipped** (314.04s) | **563 passed, 2 skipped** (313.65s) |

*Attempt noted:* the first full-suite run showed **21 failures** — changing `GateVerdict`'s field
names (`swap_green`/`swap_samples_mib` → `flow_green`/`flow_samples`) broke the two fixtures that
CONSTRUCT a green verdict to satisfy the preflight. Caught by the suite, fixed at both sites. A
signature change is only as safe as the enumeration of its constructors.

### CI — **run `31280490647`, GREEN both legs** (commit `2861753`)

| Job | Deterministic | Randomised |
|---|---|---|
| `test (3.11)` — 93160870061, 10m50s | **563 passed, 2 skipped** (313.75s) | **563 passed, 2 skipped** (308.22s) |
| `test (3.14)` — 93160870100, 10m57s | **563 passed, 2 skipped** (311.74s) | **563 passed, 2 skipped** (309.20s) |

Eight independent runs (four local, four CI) all report 563/2. CI cannot see the Term 2 verdict —
it is a host condition, and the gate is patched green in every fixture test so they can exercise
other things. `test_a_red_gate_makes_the_preflight_refuse` is what proves it can still refuse.

---

## WHAT HAPPENS NEXT

The gate is now tied to the mechanism and **both its outcomes are reachable** — this WO proved RED
by measurement and GREEN by the pre-ruled dual. The remaining work is the operator's:

> **Free ~1.6–2 GB of committed memory (chrome 3.0 GB and Code 1.3 GB are the obvious candidates),
> then re-run `capture_gate.evaluate()`. If flow reads ~zero, Term 2 is GREEN and WO-055 executes
> under the standing pre-authorization with no return to the lead.**

Everything downstream is built, wired, bite-proved and waiting: the trade channel is reachable
(WO-056), all six abort detectors fire (WO-057), and the fabrication scanner gates the result.
