# WO-037 — TAXONOMY MIGRATION: the archived vocabulary is CERTIFIED

**COMPLETE. No STOP.** Base HEAD `9721f10`. **SHIP IMPACT: NO** — §3 found the runtime vocabulary
archive-ready, so §4 took the certify-only branch. **`git diff -- src/` empty; five production sha256
identical.**

| § | Deliverable | Result |
|---|---|---|
| §1 | HEAD / suite / D42 currency | **PASS** — 222 both interpreters at base; the two pending rulings were the currency gap, closed by §2 |
| §2 | Two ruled closures, own commit | **DONE — `256c936`** — pass two CLOSED (24 + 3 + 3) |
| §3 | Vocabulary enumerated + four properties measured | **DONE** — `evidence/WO-037/reason_code_vocabulary_audit.md` |
| §3.4 | Archive-readiness verdict | **YES — archive-ready** |
| §4 | Certify-only: archive-readiness guard + bite proof | **DONE** — 5 tests, bite proof PASS |

**Suite arithmetic: 222 + 5 = 227.** The five are `tests/test_archive_readiness.py`.

---

## §1 — HEAD, SUITE, ARTIFACT-CURRENCY

**Actual HEAD: `9721f10`** (`WO-036 close`). 222 passed on 3.14.6 and 3.11.15, 0 f/xf/xp.
`wo029_reverify_partition.py` → **PASS 31/31**, `.artifacts/`, clean after.

**D42 currency check.** `batch_partition.md` and `audit_node_ids.md` were current per WO-035. The
declared gap was the two rulings pending-on-tree — the Option-4 disposition and the precheck standing
form — which §2 landed before §3 read anything. That is the standing step working as designed: the
check named the lag, and the lag was closed before the dependent work began.

---

## §2 — THE TWO CLOSURES, LANDED — commit **`256c936`**

**2.1 Option-4 disposition.** `batch_partition.md` (dated amendment) +
`docs/decisions/2026-07-28-races-6-15-16-not-clock-convertible.md`. Races 6, 15, 16 are **DECLARED
NOT-CLOCK-CONVERTIBLE** — the same standing the three `asyncio.sleep` races have carried since D35 —
because their outcome-bearing read `last_frame` is the corpus's gap `open_monotonic` bound. Rationale
carried verbatim as ruled. Option 3's additional defect recorded (it would decouple what `:2667`
deliberately made identical). **Pass two CLOSED: 24 converted + 3 keepalive-blocked + 3
asyncio.sleep, denominator 30.** Races 6/15/16 stay on the flake-doctrine `diagnose-before-rerun`
discipline — permanently, not as an interim measure.

**2.2 Precheck standing form.**
`docs/decisions/2026-07-28-outcome-bearing-for-whom-consumed-by-what.md`. Both questions are now
standing form for any seam threading. Records plainly that **WO-031 §4 made no error** — an audit is
bounded by the question it was given — and notes the meta-point: D42's mode was validated on its first
firing, the precheck fired exactly at the (d) boundary and nothing was threaded.

---

## §3 — THE VOCABULARY, ENUMERATED AND MEASURED

Full enumeration: **`evidence/WO-037/reason_code_vocabulary_audit.md`**. Instrument:
`tools/wo037_vocabulary_audit.py`, which **reuses the operated scanners** from
`test_reason_code_vocabulary.py` — a second scanner would be a second source of truth waiting to
diverge.

**Declared: 44 reason codes across 5 layers, 13 event types.**

### The four properties, measured

| Property | Result |
|---|---|
| (a) EMITTED ⇒ DECLARED (reason codes, event types) | **CLEAN** |
| (b) DECLARED ⇒ PRODUCIBLE (reason codes, event types) | **CLEAN** |
| (c) NO DUPLICATE / ALIASED (prefix-freedom across the union) | **CLEAN** |
| (d) CATEGORY | catalogued — below |

### (d) The category catalogue, and why it matters

The corpus archives **decision records**, so the archive-relevant question is narrower than "is this
code declared": it is *can this code appear as `reason_code` in a `log_decision`/`log_feed_event`
record*.

- **ARCHIVABLE: 19** — can appear in the corpus. **Every one declared. Prefix-free.**
- **RAISED / LOGGED only: 25** — exception messages and logger lines; never a decision record's
  `reason_code`.

**The load-time code, labelled:** `LIVE_CAPABLE_BUILDER_MISSING_FORWARDED_PARAM` fires at **import
time** from `register(live_capture=True)` — there is no decision loop yet, so it cannot reach a
decision log. **It does not affect the (a) or (b) verdicts:** it is both declared and producible, so
it satisfies each property on its own terms and masks nothing. Several other codes are likewise
pre-loop refusals (`LIVE_CAPTURE_ENV_REFUSED`, `LIVE_CAPTURE_UNSUPPORTED`, `GAP_PERSIST_UNCONFIGURED`,
`MEAN_CYCLE_BASELINE_*`, `CLOCK_INJECTION_REFUSED`). All are labelled `RAISED`; **re-homing them is
the post-corpus SPLIT audit's job** and was not done here (§5).

### §3.4 — **VERDICT: ARCHIVE-READY (YES).** §4 is certify-only.

---

## §3.5 — THE FINDING: a latent hazard both existing properties are blind to

**`REASON_VETO_INSUFFICIENT_BALANCE = "RISK_VETO_INSUFFICIENT_BALANCE"` (`risk/engine.py:42`) is
neither declared nor producible.** It appears **exactly once in the repository** — its own definition.
Nothing references it; `check()` never returns it.

Both existing properties are structurally blind to it:

- **(a) emitted ⇒ declared** cannot see it — it is not emitted (a class constant, not a call-site
  literal).
- **(b) declared ⇒ producible** cannot see it — it is not declared.

**A code that is neither declared nor emitted falls between both properties.**

**Why it matters despite being dead.** Three production sites emit `reason_code` **indirectly**, all
landing in decision records:

| Site | Source |
|---|---|
| `live.py:227` `reason_code=signal_reason` | `"LONG_SIGNAL"` / `"SHORT_SIGNAL"` |
| `live.py:248` `reason_code=reason_code` | the risk engine's `REASON_*` constants |
| `live.py:307` `reason_code=e.reason_code` | `KillSwitchEngagedError.reason_code` |

`test_reason_code_vocabulary.py`'s docstring names this as its own blind spot and describes the exact
failure: *"a future emission adds `reason_code=new_var` … the code ships as a GOVERNED SYSTEM EMITTING
AN UNGOVERNED CODE."* This constant is that scenario **pre-loaded** — one line of wiring inside
`check()` and an undeclared code flows into a permanent archive with every existing guard green.

**Bucket, stated explicitly per §4:** it is **not** an archive-readiness violation (nothing produces
it) and **not** a category leak (it is not a load-time code among runtime ones). It is a third thing —
a dead, ungoverned constant. The YES branch forbids a `src/` change and the constant harms nothing
today, so **it was not touched**. Declare it or delete it is the lead's call.

**What was done instead:** the §4 guard pins it by name in `KNOWN_DEAD_RISK_CONSTANTS` with its
reasoning, and `test_every_wired_risk_reason_constant_is_declared` **fails the moment it is wired** —
converting a silent future archive defect into a CI failure at the exact commit that would introduce
it.

---

## §4 — CERTIFY-ONLY: `tests/test_archive_readiness.py` (5 tests)

Not a duplicate of the literal-form guard. That guard governs the vocabulary by **call-site literals**
and documents the indirection as out of scope; this one governs the **archive path specifically**,
including that indirection. It resolves all three indirect sources by AST — the `signal_reason`
ternary, the risk `REASON_*` class attributes, and `KillSwitchEngagedError`'s default — and asserts:

| Test | What it asserts |
|---|---|
| `test_every_archivable_reason_code_is_declared` | (a) for the archive path — nothing reaches an archived record undeclared |
| `test_archivable_codes_are_prefix_free` | (c) for the archive path |
| `test_every_wired_risk_reason_constant_is_declared` | every **wired** risk constant is declared — closes the indirection hole at the moment of wiring |
| `test_dead_risk_reason_constants_are_known` | no **unexamined** dead constant; stale entries fail too |
| `test_the_indirection_resolvers_actually_resolve` | rule 0.1d — the resolvers return real values, not an empty set |

**NO `src/` production change. SHIP IMPACT: NO.**

### Bite proof — `tools/wo037_archive_readiness_bite_proof.py` → **VERDICT: PASS**

Four artifacts, sha256 exact-restore, both directions. The mutation deliberately rides the
**indirection** path (a wired, undeclared risk `REASON_*` constant), so the proof demonstrates *new*
coverage rather than overlap.

| Artifact | Archive guard | Literal-form guard | Result |
|---|---|---|---|
| **1 — PRISTINE** | rc=0, 5 passed | rc=0, 11 passed | both green |
| **2 — THE BITE** (undeclared constant, WIRED) | **rc=1, 2 failed** — names `RISK_VETO_WO037_PROBE` | **rc=0, 11 passed** | archive guard bites; **the literal-form guard stays GREEN** |
| **3 — PRESERVATION DUAL** (same code, now declared) | rc=0, 5 passed | rc=0, 11 passed | the guard bans an **undeclared archived** code, not a new code |
| **4 — RESTORED** | rc=0, 5 passed | rc=0, 11 passed | sha256 **IDENTICAL** for both `engine.py` and `decision.py` |

Verbatim from artifact 2:

```
E   AssertionError: reason code(s) can reach a CORPUS-ARCHIVED decision record but are NOT DECLARED
    in VALID_REASON_CODES: ['RISK_VETO_WO037_PROBE']
E   AssertionError: risk REASON_* constant(s) are WIRED into check()'s return but NOT DECLARED:
    ['RISK_VETO_WO037_PROBE']
```

**Artifact 2 is the whole point:** the literal-form guard passed 11/11 while an ungoverned code became
archivable. That is not a defect in it — it is its documented blind spot, demonstrated — and it is
exactly the ground the new guard covers.

**The load-time marker:** the distinction is recorded in the §3 catalogue (ARCHIVABLE vs
RAISED/LOGGED), derived mechanically from emission form rather than from a hand-maintained list.
**This marker is new** — no prior artifact distinguished load-time from runtime codes. It labels only;
the SPLIT audit re-homes.

---

## §5 — SCOPE FENCE: HELD

| Fence | Held? |
|---|---|
| No vocabulary SPLIT / re-homing / re-prefixing | **HELD** — catalogued and labelled only |
| No gate docstring precision note | **HELD** |
| No pass-two race touched | **HELD** |
| No production change unless §3 convicts a runtime defect | **HELD** — §3 convicted none; `git diff -- src/` empty |

**Five production sha256, unchanged:** `kraken_v2_book.py` `b06c347e` · `factory.py` `103a8ba7` ·
`registry.py` `5bf833c7` · `live_capture.py` `dab18f67` · `logkit/decision.py` `3d153a11`.

---

## §6 — ACCEPTANCE

| Gate | Result |
|---|---|
| `pytest tests/ -p no:randomly -rX` → 227 both interpreters | **PASS** — 227/227, 0 f/xf/xp. **Arithmetic: 222 + 5 = 227**, the five being the new archive-readiness guard. |
| `pytest --randomly-seed=20261001` | **PASS** — 227 both interpreters |
| Archive-readiness verdict stated with §3 evidence | **PASS — YES**, `evidence/WO-037/reason_code_vocabulary_audit.md` |
| §4 guard bite proof: four artifacts, sha256 exact-restore | **PASS** |
| `git diff -- src/` empty; five sha256 identical | **PASS** |
| `wo029_reverify_partition.py` PASS 31/31 | **PASS** |
| lint 6/6 · contract 6/6 · ruff clean · annotation 0 · preflight pass | **PASS** |
| §2's two docs + partition amendment committed (own commit, before §3/§4) | **PASS — `256c936`** |
| `evidence/WO-037/` committed; progress.md block noting **PASS TWO CLOSED 24+3+3/30** | **PASS** |
| Commit, push, local == remote, CI green both legs | **see §CI** |

---

## §Attempts — every one, including the failures

1. **Re-read `instructions.md` from disk** (sha256 `1F37F504…`, 10297 bytes) before acting.
2. **Landed §2 as its own commit before §3 read the partition**, per §2.4 — and re-ran the reverify
   tool after the amendment to confirm the artifact still parses (PASS 31/31).
3. **Reused the operated scanners instead of writing new ones.** `tools/wo037_vocabulary_audit.py`
   imports `_declared_reason_codes`, `_emitted_reason_codes`, `_is_producible`, `_prefix_collisions`
   from the standing guard. A fresh scanner would have been a second source of truth, and any drift
   between them would be invisible.
4. **My first classification was WRONG and I caught it by disbelieving my own output.** The audit's
   first run reported 9 archivable codes and 13 "INDIRECT-ONLY" — a bucket that included every risk
   `RISK_*` code. "Indirect-only" was not a property of the system; it was **my regex failing to see
   variable-indirection emission**. Reading the `log_decision` call sites showed three indirect sites
   that all land in decision records, so the true archivable set is **19**, not 9. Recorded because
   the first output *looked* clean — verdict ARCHIVE-READY, exit 0 — and shipping it would have
   certified the archive on an undercount. This is D41's apparatus-honesty rule turned on my own
   instrument: before reading a measurement as a system property, ask what the apparatus could not see.
5. **The finding came out of that correction, not out of the happy path.** Tracing `live.py:248` back
   to the engine's `REASON_*` constants is what surfaced `REASON_VETO_INSUFFICIENT_BALANCE` — a code
   the clean first run would never have mentioned.
6. **The guard's first version returned an empty set and its own 0.1d self-test caught it.** I wrote
   `_risk_reason_constants()` walking `tree.body`, assuming module-level constants; they are **class
   attributes** on `RiskEngine`, and references are `self.REASON_*` **attributes**, not bare names.
   `test_the_indirection_resolvers_actually_resolve` failed with `assert 'REASON_PASS' in {}`. Without
   that test the guard would have passed on any tree by looking in the wrong scope — a green guard
   that checks nothing, which is the failure mode this whole family of work exists to prevent.
7. **The bite proof's first run aborted on a non-unique anchor** (`# Reason codes` at a different
   indentation than assumed). Rewritten to a single anchor that both defines *and* wires the probe —
   a dead probe constant would only have landed on the known-dead list rather than biting, so the
   wiring is load-bearing to the proof.
8. **Chose "wired-or-known-dead" over "every constant must be declared"** for the risk-constant guard.
   The stricter rule would have failed immediately on `REASON_VETO_INSUFFICIENT_BALANCE`, and shipping
   a red guard — or forcing a `src/` change the §3.4 YES branch forbids — would have been the wrong
   way to register a finding. The chosen rule is green today, names the dead constant explicitly, and
   fires at the exact commit that wires it.
9. **`PYTHONUTF8=1` on every invocation** — without it `contract_count_check.py` aborts the session at
   `pytest_sessionstart`. Environmental; CI is Linux/UTF-8.

---

## §CI

- **§2 commit:** `256c936` (the closures, verifiable on their own) · **§3/§4 commit:** `3385cf6`
- **Local == remote:** `3385cf644129ec0f35450a40f4acf0dce5bbcd96` == `origin/master`
- **CI run `30372537642`** — **`test (3.11)` success · `test (3.14)` success**, both legs, first attempt, both orders.

**THEN STOP.** Next (corpus-blocking): capture-loop baseline → corpus preconditions → 24h corpus.
