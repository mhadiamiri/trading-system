# WO-034 — BATCH C: **STOPPED AT §2.2. NO CONVERSION.**

**Outcome: the §2.2 gate fired.** Node-ID regeneration found **nine** mismatches between the audit's
prose identifiers and the collected node IDs, where D41 knew of **four**. §2.2 is unconditional:

> **Any mismatch BEYOND those four is a FINDING** — a race the audit misidentified that nobody has
> caught — **STOP and report it before converting anything.**

**Batch C's 9 races are untouched.** No test, `src/`, fixture or `conftest.py` file was edited. §2 was
completed (it is classify/verify only, and §2.3 requires the table be committed); §3–§4 were not begun.

**The denominator does not move** — every one of the 37 entries resolves to exactly one collected
test — so this is an identifier finding, not a taxonomy finding. But identifiers are what every later
WO addresses a race by, and **four of batch C's nine races were among the misidentified**.

| § | Result |
|---|---|
| §1 HEAD / suite / membership | **PASS** — 222 both interpreters; reverify PASS 30/30, tree clean |
| §2 Node-ID regeneration | **BUILT** — 37/37 resolve; `evidence/WO-034/audit_node_ids.md` committed |
| §2.2 Diff gate | **FAIL → STOP** — 9 mismatches vs D41's 4 |
| §3 Convert batch C | **NOT BEGUN** |
| §4 Determinism + ledger bite | **NOT BEGUN** |

---

## §0 — RULES OF ENGAGEMENT

| Rule | Disposition |
|---|---|
| 0.1 No discretion; code wins → STOP and report | **HELD.** §2.2's condition was met and the WO stopped there rather than converting under identifiers it had just found unreliable. |
| 0.2 Transport migrated with clock injection | **N/A** — no conversion attempted |
| 0.3/0.4 Bite proof + preservation duals | **N/A** — no guard or assertion touched |
| 0.5 Report every attempt | **HELD** — §Attempts, including a transcription error of my own that under-reported the finding |
| 0.7 Built-vs-operated | **All OPERATED rows verified** — see §1 |

---

## §1 — HEAD, SUITE, MEMBERSHIP

**Actual HEAD: `ba75394`** (`WO-033 close`). The WO names base `2ece73f`; `ba75394` is its docs-close.

| Interpreter | Result |
|---|---|
| 3.14.6 | **222 passed** in 245.63 s, 0 f/xf/xp |
| 3.11.15 | **222 passed** in 244.65 s, 0 f/xf/xp |

`wo029_reverify_partition.py` → **PASS 30/30 by name**, writes `.artifacts/`, `git status` clean after.

**Batch C membership — 9, confirmed by ruling, with an artifact lag flagged.** The WO enumerates the 9
(races 12, 35, 14, 22, 23, 24, 25, 26, 27) and D41 ratified entry 35's BOUND→RACE reclassification.
**But the committed `evidence/WO-029/batch_partition.md` still reads `= 8 races`** — entry 35 was
deliberately not folded in by WO-031 (which reported the reclassification and escalated rather than
amending), and no WO has amended it since D41 ratified.

Not treated as a §1 STOP: the composition matches the WO's own enumeration exactly and the 9th member
is carried by a ratified ruling. **But it is the same class of gap WO-031 originally STOPPED on** — a
ruling that exists in the decision record and not in the tree — and it should be amended into the
partition before batch C converts, so the conversion is planned against an artifact that says 9.

---

## §2 — NODE-ID REGENERATION (D41)

### Mechanism

`tools/wo034_node_id_regeneration.py` runs **pytest's own collection**
(`pytest tests/ --collect-only -q -p no:randomly -o addopts=`) and matches each audit entry to a
collected node ID by `(file, test-name-prefix)`. **It never greps source text** — that is D41's whole
point. Prefix matching is exactly the tolerance truncations need; a prefix matching more than one
collected test is reported `AMBIGUOUS` (none were).

The full 37-row table is committed at **`evidence/WO-034/audit_node_ids.md`** and is now **canonical**
for all future enumeration. The historical audit is annotated as superseded, not rewritten.

### §2.2 The diff — **nine mismatches, not four**

**Five beyond D41's known set:**

| Entry | Batch | Audit's prose name | Real name |
|---|---|---|---|
| **21** | **B** | `test_every_checksum_failure_captured_not_positionally` | `…_not_positionally_sampled` |
| **24** | **C** | `test_receive_to_process_latency_recorded` | `…_recorded_through_production_path` |
| **26** | **C** | `test_venue_close_unexpected_reconnects_expected_shuts` | `…_shuts_down_cleanly` |
| **27** | **C** | `test_transient_reopen_failure_retries_under_backoff` | `…_under_backoff_then_emission_resumes` |
| **35** | **C** | `test_incremental_persist_survives_unhandled_exception` | `…_mid_capture` |

**D41's four, reproduced exactly:** 5 (`…_via_factory`), 28 (`…_via_protocol_ping`),
31 (`…_with_forensic_tail`), 36 (`…_fixtures`, **plus** it is a method on `TestNoSilentFallback`).

**Rate: 6 of 30 races (20%), 9 of 37 entries (24%).**
**Four of batch C's nine races — 24, 26, 27, 35 — carried a truncated identifier.**

### What the finding is, and what it is not

**Not a denominator change.** All 37 resolve to exactly one collected test; 0 unresolved, 0 ambiguous.
Clock-injectable **27**, bounds **6**, total **30** — unchanged. No race was lost or misattributed;
every truncation is a strict prefix with a unique completion.

**It is an identifier-integrity finding**, and that is why §2.2 gates on it: a node ID is how every
subsequent WO addresses a race, and the population that needed repair was more than twice what the
ruling assumed. Converting batch C while four of its nine identifiers were known-wrong — immediately
after discovering they were wrong — is precisely the discretion §0.1 forbids.

### Why the count was under-reported until now (and by me, once)

Earlier passes — including **my own first run of this script** — diffed against
`evidence/WO-029/batch_partition.md` rather than the audit itself. The partition **silently corrected
several of the audit's names** when it re-derived the table (races 5 and 28 were repaired there, 28
with a flag). Diffing against a corrected restatement measures the restatement, not the audit.

My first run reported mismatches `[28, 31, 35, 36]` and flagged entry 5 as *"D41 expected a mismatch
but the identifier matched exactly"* — which was the tell: entry 5 matched because I had transcribed
the *repaired* name. Re-transcribing all 30 verbatim from `wall_clock_race_audit.txt` trebled the
population from three to nine. **The measurement was wrong in the same way the thing it was measuring
was wrong**, and only the internal inconsistency (a known mismatch failing to reproduce) exposed it.
Recorded because a version of this script that never checked its own source would have reported "one
extra mismatch, entry 35" and looked entirely plausible.

---

## §3 / §4 — NOT BEGUN

No race converted, no clock injected, no seam threaded, no determinism proof, no ledger-bite proof.
§2.2 stops the WO *before* conversion, and the reason is substantive rather than procedural: the
identifiers for four of the nine races to be converted had just been shown wrong, and the conversion's
per-race reporting is keyed to those identifiers.

---

## §5 — SCOPE FENCE: HELD

| Fence | Held? |
|---|---|
| Batch C's 9 races only | **HELD** — none touched |
| No batch A/B race re-touched; no keepalive-blocked race | **HELD** |
| The 3 asyncio.sleep races untouched | **HELD** |
| No production logic change; no new reason codes | **HELD** |
| No assertion weakened | **HELD** — none touched |

**`git diff -- src/ tests/ conftest.py` is empty.** Five production sha256, unchanged:
`kraken_v2_book.py` `b06c347e` · `factory.py` `103a8ba7` · `registry.py` `5bf833c7` ·
`live_capture.py` `dab18f67` · `logkit/decision.py` `3d153a11`.

---

## §6 — ACCEPTANCE (what a §2.2 STOP can and cannot satisfy)

| Gate | Result |
|---|---|
| `pytest tests/ -p no:randomly -rX` → 222 both interpreters | **PASS** — 222/222, 0 f/xf/xp |
| Node-ID table committed; diff shows exactly the 4 known mismatches | **TABLE COMMITTED; DIFF SHOWS 9 → §2.2 STOP** |
| `wo029_reverify_partition.py` PASS | **PASS** — 30/30 by name (not yet wired to node IDs; see below) |
| Five `src/` sha256 IDENTICAL; `git diff -- src/` empty | **PASS** |
| `test_evidence_write_boundary.py` (the new tool writes to `.artifacts/`) | **PASS** — 4/4 |
| lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass | **PASS** |
| `pytest --randomly-seed=<5 seeds>` all green | **NOT DONE** — §4 not begun |
| Gate ledger dispositions; ledger-still-bites bite proof | **NOT DONE** — §4 not begun |
| Gate ledger snapshotted into `evidence/WO-034/` | **NOT DONE** — no conversion to snapshot |
| progress.md WO-034 block | **PASS** |
| Commit, push, local == remote, CI green both legs | **see §CI** |

**On wiring §2 into the reverify tool (§6 asks to state whether I did):** **I did not.** The reverify
tool still matches by name and passes 30/30. Rewiring it to consume the node-ID table is the natural
follow-on, but it would edit a tool whose current output this WO's §1 depends on, on the far side of a
STOP — out of scope here. Flagged as the obvious first task of the resumed WO.

---

## §Attempts — every one, including the failures

1. **Re-read `instructions.md` from disk** (sha256 `B83694A5…`, 10093 bytes) before acting.
2. **Launched both suite legs in the background first**, then built §2 while they ran.
3. **The collection call returned pytest's indented TREE, not node IDs.** `pytest.ini` sets
   `addopts = -v`, and ini verbosity beat the `-q` on the command line, so `--collect-only -q` printed
   `<Module>/<Class>/<Function>` blocks. My parser found zero `tests/…::…` lines. Fixed with
   `-o addopts=` to clear the ini options. **Worth recording because the failure mode is silent-ish:**
   a parser that tolerated an empty result would have reported "0 mismatches, all exact" — a perfect
   score produced by collecting nothing.
4. **My first diff was against the wrong source, and under-reported the finding.** I transcribed the
   audit's 30 from `batch_partition.md` — the D39-amended restatement — instead of from
   `wall_clock_race_audit.txt`. The partition had silently repaired several names, so the diff measured
   the partition's accuracy, not the audit's: it reported four mismatches `[28, 31, 35, 36]` and, tellingly,
   **that entry 5 matched exactly when D41 said it should not**. That inconsistency is what exposed it.
   Re-transcribed all 30 verbatim from the audit; the population went from three-plus-one to **nine**.
   This is the apparatus-honesty rule (D41) applied to my own instrument: before reading a measurement
   as a property of the system, ask what the apparatus was actually pointed at.
5. **Checked that every truncation resolves uniquely** before characterising the finding as
   identifier-only. The matcher reports `AMBIGUOUS` when a prose prefix matches more than one collected
   test; none did, and none were UNRESOLVED. That is what licenses "no denominator movement" — it is a
   measured claim, not an assumption.
6. **Regenerated the 7 bounds as well as the 30 races**, though only the races were strictly asked for.
   Entries 31, 35 and 36 are all in the bounds block, and two of the nine mismatches would have been
   invisible had the regeneration covered races only.
7. **Noticed `batch_partition.md` still says batch C = 8** while the WO and D41 say 9. Reported at §1
   as an artifact lag rather than a STOP, since the WO enumerates the 9 explicitly and D41 ratified the
   9th. It is the same shape as the gap WO-031 originally stopped on.
8. **Did not convert anything after the gate fired**, including the five races whose identifiers were
   never in question. Splitting a batch on identifier-confidence grounds is exactly the discretion
   §0.1 forbids, and the amended partition forbids splitting a file across batches anyway.
9. **`PYTHONUTF8=1` on every invocation** — without it `contract_count_check.py` aborts at
   `pytest_sessionstart`. Environmental; CI is Linux/UTF-8.

---

## What unblocks this WO

1. **Ratify the nine-mismatch finding** and accept `evidence/WO-034/audit_node_ids.md` as the canonical
   identifier set (it is already committed and complete — no further measurement is needed).
2. **Amend `batch_partition.md`**: fold entry 35 in so batch C reads **9**, and — the natural companion
   — restate its race identifiers as node IDs.
3. Optionally **rewire `wo029_reverify_partition.py`** to consume the node-ID table instead of matching
   by name.
4. Then **WO-034 resumes at §3** and converts batch C's 9 races against identifiers that have been
   mechanically verified rather than retyped.

**STOPPED. Batch C not converted. Awaiting the lead.**

---

## §CI

- **Commit:** `<filled at close>`
- **Local == remote:** `<filled at close>`
- **CI run:** `<filled at close>` — `test (3.11)` / `test (3.14)`
