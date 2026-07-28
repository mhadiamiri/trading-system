# WO-036 — KEEPALIVE/PING CLOCK SEAM: **STOPPED AT §1's RED-LINE PRECHECK. NOTHING THREADED.**

**Outcome: the §1 precheck's escalation condition fired.** `last_frame` is **not** a pure pacing read.
It is the **`open_monotonic` opening bound of three of the five ruled gap causes**, and the
**recv-return timestamp of the throughput latency instrument**. §1 is unconditional:

> **If EITHER read reaches the gap-ledger, gap-detection timing, the checksum path, or any
> corpus-integrity machinery, STOP and escalate** — threading a corpus-integrity clock is red line (d)
> and is NOT Ops-authority.

**No `src/` file was touched. Races 6, 15, 16 are not converted. Pass two is NOT complete — 24 of 27.**

| § | Result |
|---|---|
| §1 HEAD / suite / D42 currency | **PASS** — 222 both interpreters; reverify PASS 31/31; partition current |
| §1 **RED-LINE PRECHECK** | **NOT CLEAN → STOP** — `last_frame` reaches the gap ledger ×3 + throughput instrument ×1 |
| §2 Thread the seam | **NOT BEGUN** |
| §3 Registration contract | **NOT BEGUN** |
| §4 Convert races 6/15/16 | **NOT BEGUN** |
| §5 Determinism / ledger bite | **NOT BEGUN** |

---

## §0 — RULES OF ENGAGEMENT

| Rule | Disposition |
|---|---|
| 0.1 No discretion; code wins → STOP and report | **HELD.** The precheck contradicted the WO's stated expectation ("Expected: both feed liveness/pacing logic only"); reported rather than reconciled. |
| 0.2 No monkeypatching | **N/A** — nothing edited |
| 0.3/0.4 Bite proof + preservation duals | **N/A** — no guard built, no contract extended |
| 0.5 Report every attempt | **HELD** — §Attempts |
| 0.6 **D42 standing artifact-ruling check** | **HELD** — performed at §1; no lag found this time |
| 0.7 Built-vs-operated | **All OPERATED rows verified** — see §1 |

---

## §1 — HEAD, SUITE, ARTIFACT-CURRENCY, RED-LINE PRECHECK

**Actual HEAD: `dd5a6f9`** (`WO-035 close`). The WO names base `86f0a96`; `dd5a6f9` is its docs-close.

| Interpreter | Result |
|---|---|
| 3.14.6 | **222 passed** in 247.96 s, 0 f/xf/xp |
| 3.11.15 | **222 passed** in 246.95 s, 0 f/xf/xp |

`wo029_reverify_partition.py` → **PASS 31/31**, writes `.artifacts/`, `git status` clean after.

**D42 currency check — clean this time.** `batch_partition.md` reflects everything WO-035 landed:
batch C `= **9 races**`, the `NODE ID (canonical, D42)` column, and the dated
`## AMENDMENT — 2026-07-28 (WO-035 §2, implementing D42)` section. No lag; proceeded.

### THE RED-LINE PRECHECK — full enumeration in `evidence/WO-036/red_line_precheck.md`

Every consumer of both names in `src/`. All sites are in `kraken_v2_book.py`; no other production
module references either. (`_last_frame_server_ts` is a different field — the venue's wall-clock string
off the wire, not a monotonic read — and is out of scope.)

#### `last_ping` — **CLEAN.** Pure pacing.

| Site | What it feeds |
|---|---|
| `:2691` `if mono - last_ping >= self._app_ping_interval:` | **PACING** — the app-ping interval gate |
| `:2736` `self._app_ping_interval - (mono - last_ping)` | **PACING** — remaining time, feeding the recv timeout |
| `:2552, :2683, :2716, :2718, :2773` | assignments / resets |

Two reads, both pacing. No gap-ledger, checksum or instrument consumer. **WO-031 §4's classification
holds for `last_ping`.**

#### `last_frame` — **NOT CLEAN.** Pacing *plus* four non-pacing consumers.

| Site | What it feeds |
|---|---|
| `:2661` `if mono - last_frame >= self._heartbeat_absence_timeout:` | **PACING** — absence detection |
| `:2735` `self._heartbeat_absence_timeout - (mono - last_frame)` | **PACING** — recv-timeout computation |
| **`:2674`** `open_monotonic=last_frame` in `_open_gap(cause="KEEPALIVE_RECONNECT", …)` | ⚠ **GAP LEDGER — the gap's OPEN BOUND** |
| **`:2708`** `open_monotonic=last_frame` in `_open_gap(cause="VENUE_DISCONNECT", …)` (4b) | ⚠ **GAP LEDGER — the gap's OPEN BOUND** |
| **`:2765`** `open_monotonic=last_frame` in `_open_gap(cause="VENUE_DISCONNECT", …)` (4c) | ⚠ **GAP LEDGER — the gap's OPEN BOUND** |
| **`:2817`** `self._throughput_record.record(last_frame, done_mono)` | ⚠ **THROUGHPUT INSTRUMENT — the recv-return timestamp of the latency sample** |

The gap use is deliberate and load-bearing, not incidental reuse — the code says so at `:2667`:

> *"WO-014c-2 §2: OPEN the keepalive gap at the LAST FRAME received (when emission actually stopped,
> not when the threshold tripped)."*

`open_monotonic` is a gap record's opening time bound, and **three of the five ruled gap causes take
it from `last_frame`**. Gap windows are how the corpus knows which time ranges are missing data.
Threading `last_frame` would put injected time into `open_monotonic`, and thence into `duration_s` and
every gap-window computation derived from it — corpus-integrity machinery on any reading.

The instrument use is equally explicit at `:2814`: *"receive-to-process latency (last_frame = recv
return)"*. §6 of this WO fences the throughput/lag/pong instrument clocks off as **unconvicted** — but
`last_frame` is one of the two inputs to the throughput latency sample, so threading it would inject
fake time into an instrument the measurement never convicted.

**Finding stated explicitly, as §1 requires: the precheck is NOT clean, so this WO does not proceed.**

### This does not contradict WO-031 §4

WO-031 §4 was asked which **non-injectable reads are outcome-bearing for a batch-B race**, and it
answered correctly: races 6/15/16 assert on absence detection and ping pacing, so both reads are
outcome-bearing *for those assertions*. This precheck asks a different question — **what does the read
feed in production?** A variable can be outcome-bearing for a test assertion *and* carry unrelated
production consumers. That is the case here, and it is exactly why §1 said *"confirm that from the
code, do not inherit it."* The instruction anticipated this; the check found it.

### Why a partial thread is not an obvious way out

Threading only `last_frame`'s pacing comparisons (`:2661`, `:2735`) while leaving `:2674/:2708/:2765`
and `:2817` on the real clock means **splitting one variable into two** — a fake-clock "pacing
last_frame" and a real-clock "gap/instrument last_frame". Today they are by construction the **same
instant**, and `:2667` makes that identity deliberate ("when emission actually stopped, not when the
threshold tripped"). Decoupling them changes what a gap's `open_monotonic` means relative to the
decision that opened it — a production semantic change to gap-window accounting, i.e. further into
red line (d), not around it. That is a design question for the lead.

---

## §2 / §3 / §4 / §5 — NOT BEGUN

No seam threaded, no parameter added, no registration contract touched, no race converted, no
determinism proof, no ledger bite. §1 gates all of them and its condition was met.

**For the record, since §2.1 asked the question and the answer is now known:** `last_frame` and
`last_ping` currently read **raw `time.monotonic()`** (`:2551/:2552`, `:2682/:2683`, `:2715/:2716`,
`:2718`, `:2772/:2773`, `:2777`) — they do **not** already route through `self._monotonic_clock`. So
§2.1's alternative branch ("the seam already reaches them, these races were misclassified") does
**not** apply; the seam genuinely does not reach them. Had the precheck been clean, §2.1's main branch
(thread through the existing `_monotonic_clock`, no new parameter) would have been the right shape,
matching Ops' stated expectation in §2.2.

---

## §6 — SCOPE FENCE: HELD

| Fence | Held? |
|---|---|
| Races 6/15/16 only; no other race re-touched | **HELD** — none touched |
| The 3 asyncio.sleep races untouched | **HELD** |
| Thread ONLY `{last_frame, last_ping}`; no instrument clock | **HELD** — nothing threaded at all |
| No new reason code; no gate docstring note | **HELD** |
| No assertion weakened; no speculative seam surface | **HELD** |

---

## §7 — ACCEPTANCE (what a §1 STOP can and cannot satisfy)

| Gate | Result |
|---|---|
| `pytest tests/ -p no:randomly -rX` → 222 both interpreters | **PASS** — 222/222, 0 f/xf/xp. Arithmetic: **222 + 0 = 222**; this WO edits no test. |
| `wo029_reverify_partition.py` PASS 31/31 | **PASS** |
| **`git diff -- src/` empty; all five sha256 identical** | **PASS** — `b06c347e` · `103a8ba7` · `5bf833c7` · `dab18f67` · `3d153a11`. §7's second branch applies, and more strongly than it anticipated: §2 touched no `src/` **because it never ran**, not because the seam already reached the reads. |
| lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass | **PASS** |
| `evidence/WO-036/` committed | **PASS** — the precheck artifact (there is no conversion evidence to commit) |
| progress.md WO-036 block | **PASS** |
| `pytest --randomly-seed=<5 seeds>` all green | **NOT DONE** — §5 not begun |
| Gate ledger dispositions for races 6/15/16; ledger-still-bites bite proof | **NOT DONE** — §5 not begun |
| Gate ledger snapshot | **NOT DONE** — no conversion to snapshot |
| **progress.md noting "PASS TWO COMPLETE: 27/27"** | **NOT DONE, and must not be** — pass two stands at **24/27** |
| Commit, push, local == remote, CI green both legs | **see §CI** |

---

## §Attempts — every one

1. **Re-read `instructions.md` from disk** (sha256 `7238C1D5…`, 9524 bytes) before acting.
2. **Launched both suite legs in the background first**, then did the read-only §1 work while they ran.
3. **Ran the D42 currency check as a real check.** It found no lag this time — `batch_partition.md`
   carries WO-035's amendments. Recorded because a standing check that only gets reported when it
   fires is indistinguishable from one nobody runs.
4. **Did the precheck by reading the call sites, not by grepping and inferring.** The grep found
   `open_monotonic=last_frame` three times, but "reaches the gap ledger" is a claim about what the
   value *becomes*, so each site was opened and read in context. The comments at `:2667`, `:2702`,
   `:2760` and `:2814` are what make the finding conclusive rather than suggestive — they state the
   intent explicitly.
5. **Checked `last_ping` separately rather than treating the pair as one unit.** It is clean, and
   saying so precisely matters: the escalation is about **one** of the two reads, and a lead deciding
   next steps needs to know the other is threadable at Ops authority.
6. **Excluded `_last_frame_server_ts` deliberately.** It matches a `last_frame` grep but is the venue's
   wall-clock string off the wire, not a monotonic read — including it would have inflated the finding.
7. **Considered and rejected proceeding with a partial thread.** §1 makes the precheck a gate, not a
   risk assessment, and the partial thread is itself a deeper production change (see §1). Reported as
   an option for the lead rather than taken.
8. **`PYTHONUTF8=1` on every invocation** — without it `contract_count_check.py` aborts at
   `pytest_sessionstart`. Environmental; CI is Linux/UTF-8.

---

## What unblocks this WO

The lead's call, since red line (d) is not Ops authority. Three shapes, in increasing cost:

1. **Split the WO: thread `last_ping` now, escalate `last_frame`.** `last_ping` is clean and would be
   convicted by race 16's `assert len(pings) >= 3`. This closes part of race 16 but neither race 6 nor
   race 15, both of which rest on `last_frame`'s absence detection — so batch B would go 3 → still 3
   blocked, with partial progress. Probably not worth splitting for.
2. **Authorize threading `last_frame` as a corpus-integrity change**, under whatever discipline red
   line (d) carries — with the explicit consequence that gap `open_monotonic` and the throughput
   latency sample become injectable, and every gap-window and latency assertion in the suite must be
   re-examined under that.
3. **Split the variable in production** — a pacing clock distinct from the gap/instrument stamp. This
   is the largest change and alters what `open_monotonic` means relative to the decision that opened
   the gap; it needs its own WO and its own ruling.

**Pass two stands at 24 of 27.** Races 6, 15, 16 remain blocked.

---

## §CI

- **Commit:** `cb1a280`
- **Local == remote:** `cb1a280013e43a6e067f238484c4bebf8a5b14e7` == `origin/master`
- **CI run `30365970977`** — **`test (3.11)` success · `test (3.14)` success**, both legs, first attempt.

CI green carries no weight here: this WO edited no test and no `src/` file. It confirms the STOP left the tree exactly as it found it.
