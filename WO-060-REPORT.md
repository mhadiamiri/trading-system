# WO-060 — TRADES-ENDPOINT INVESTIGATION

## STOPPED at §2.2. Terms exist, they govern, and on their face they restrict this use.

**§2.2 is unconditional: *"If terms exist, they govern. Quote the relevant clause. If they restrict
this use, STOP — that outranks the rest of the WO."***

WO-059 checked the support/API-reference pages and found no licence. **This WO checked the place
the ruling said to look — the site-level Terms of Service — and the clauses are there.** All three
jurisdictional Terms of Service prohibit, in identical language, the exact activity §3 was about to
perform.

**§2.3's declared judgment is NOT available.** It is conditioned on *"if genuine silence persists."*
Silence does not persist. The declared-judgment form was the remedy for an absent term, not a way
past a present one, and recording it here would be using it to overrule a clause rather than to
fill a gap.

**§3, §4, §5, §6 were not executed.** §3 is a sustained backwards pagination of the entire BTC/USD
trade history — *"data extraction methods to extract any data from Our Content"* almost verbatim.
Running it after reading the clause is not something I will do on my own authority.

**This finding reaches past this WO's scope, and I am surfacing it rather than filing it under §2.**
See *THE REACH OF THE FINDING* below. **`phaseb_20260809` was not stopped** — the WO says do not
disturb it, and that call is the lead's, not mine.

---

## §1 STATE CONFIRMED

**BASE discrepancy, reported not assumed (0.1e).** The WO names HEAD `67193e2`. Actual HEAD is
**`329cb30`** — the WO-059 STOP report, committed after that WO was written. It touches
`WO-059-REPORT.md` only; `git diff 67193e2..329cb30 -- src/ tests/` is empty, so the base is the
tree the WO describes. CI run `31299001628` remains the last green run for the code.

| | |
|---|---|
| HEAD | `329cb30` (base `67193e2` + report only) |
| `git diff -- src/` | **empty** |
| pytest 3.14.6 | **572 passed, 2 skipped** (315.30 s) |
| pytest 3.11.15 | **572 passed, 2 skipped** (313.43 s, throwaway uv venv) |
| import-linter | **6 contracts kept, 0 broken** |
| `corpus_20260805` | v1 `e3ab1aec…` · `corpus_verify` **38/38**, 0 mismatched, 0 missing |
| `validation_20260809` | v1 `884f9f00…` · `corpus_verify` **3/3** |
| CI | `31299001628` — success both legs, for the code at HEAD. **No code changed in this WO.** |

### `phaseb_20260809` — AT OPEN

PID **22236** alive. **12 segments**, last frame `2026-08-09T17:05:16.562Z`,
**10.549 covered hours**. Gap ledger: **1 entry** (`run_start`) — **0 gaps, 0 seams.**

### Running gap rate — accumulating information only

**0.11 caught my own first calculation.** I divided gap-ledger *entries* by covered hours and got
1.0297/h against the WO's cited 0.515. The ledger writes **two** entries per gap:

```
corpus_20260805 ledger events: run_start 2 · open 19 · resolved 19 · run_end 2
                               19 GAPS, not 38 entries
                               19 / 36.903 covered h = 0.5149 / covered hour   <- the cited figure
```

The count is the finding, again. Entries are not gaps.

| | gaps | covered h | rate |
|---|---|---|---|
| `corpus_20260805` | 19 | 36.903 | **0.515 / h** |
| `phaseb_20260809` at open | **0** | 10.549 | **0.000 / h** |

At the reference rate, 10.549 covered hours would be expected to produce ~5.4 gaps. Observing zero
has Poisson probability e^−5.43 ≈ **0.004**, so this is unlikely to be luck — but it is one short
sample, and **the 556-hour window is NOT re-derived here** (D60). Reported as it accumulates.
*Falsifier: gaps appearing at or above the reference rate as the run lengthens would overturn the
apparent improvement entirely; a single multi-hour outage would do it.*

---

## §2 THE LICENCE — the search, and what it found

### 2.1 Documents examined — enumerated (0.11), all retrieved 2026-08-09

| # | document | URL | last updated | result |
|---|---|---|---|---|
| 1 | Legal index | `kraken.com/legal` | — | 10 documents linked; enumerated below |
| 2 | **Global Terms of Service** | `kraken.com/legal/global-terms` | **2026-08-04** | **restrictions found** |
| 3 | **Canadian Terms of Service** | `kraken.com/legal/ca-terms` | **2026-06-26** | **same restrictions, verbatim** |
| 4 | **EEA Terms of Service** | `kraken.com/legal/eea-terms` | not stated on page | **same restrictions** |
| 5 | API documentation hub | `docs.kraken.com/` and `/api/` | — | JS-rendered; **no terms text retrievable** |
| 6 | API-docs support article | `support.kraken.com/articles/206548387-…` | 2025-03-31 | **no terms, no licence, no usage grant** |
| 7 | Legacy WebSockets API doc | `docs.kraken.com/websockets/` | — | **404 now.** See the caveat below. |

The legal index also lists Brazil ToS, Privacy Notice, Cookie Settings, Candidate Privacy Notice,
Disclosures, and Exchange Trading Rules — none of which bears on data rights.

**There is no separate API terms document, licence, or data-usage grant.** Checked by three routes
(5, 6, 7) and none exists. The API is governed by the site-level ToS.

**One citation carries a caveat, stated rather than glossed (0.1e).** A search surfaced this
sentence from the legacy WebSockets 1.9.2 documentation: *"Your use of the Kraken WebSockets API is
subject to the Kraken Terms & Conditions, Privacy Notice, as well as all other applicable terms and
disclosures made available on www.kraken.com."* **I could not verify it directly — that URL now
returns 404.** It is cited as search-surfaced, not as a confirmed retrieval, and **the STOP does
not rest on it.** It corroborates a conclusion already established from documents 2–4, which were
retrieved in full and read directly.

### 2.2 THE CLAUSES — quoted verbatim

**These bind without an account.** Global ToS preamble:

> **"By accessing or using our services or Platforms, or by creating an account, you agree to these
> Terms."**

**Definitions**, from the ToS's own definition section:

> **"'Our Content'** … *collectively (1) our services and Platforms, (2) all content, materials,
> software, and trademarks found on them, (3) the selection and arrangement of them, and (4) all
> intellectual property rights in them."*
>
> **"'Platforms'** … *our websites (including kraken.com and pro.kraken.com), and mobile
> applications through which you access our services."*

The public REST API is one of Kraken's **services**, and the market data it returns is *content and
materials found on them*. It is therefore inside "Our Content" — and **Section 9 contains no
carve-out for API access**. The only substantive mention of the API anywhere in the ToS body
concerns order submission (*"Trades in which you submit limit or market buy and sell orders,
including through Application Programming Interface (API) access … are executed by us on an agency
basis"*), which grants nothing about data.

**Section 9, "Restrictions" — "You will not:"**

> **"use any web scraping, web harvesting, or data extraction methods to extract any data from Our
> Content,"**
>
> **"create, use, operate, or employ any bots, robots, parsers, spiders, scripts, programs,
> routines, or any other forms of automation to engage in any activity on Our Content,"**
>
> **"develop any third-party applications that interact with Our Content without our prior written
> consent,"**

And two more that bear on any downstream use:

> *"use (except as expressly permitted in these Terms), license, sublicense, sell, resell, transfer,
> assign, distribute or otherwise commercially exploit or make available to any third party Our
> Content in any way,"*
>
> *"access or use Our Content to build or support products or services competitive to our products
> or services,"*

**The jurisdiction question is moot.** The Global ToS applies *"unless you live in Brazil, Canada or
the European Economic Area."* I do not know which governs here — the host clock is UTC−04:00, which
covers US Eastern **and** Canada Eastern, and **I will not infer a jurisdiction from a timezone.**
So I checked the alternatives: **the Canadian and EEA ToS carry the same three clauses in the same
words.** Whichever governs, the answer is identical.

### What I am and am not asserting

I am not a lawyer and this is not a legal opinion. What I am reporting is narrow and checkable:
**the clauses exist, they are drafted broadly enough to cover both what §3 planned and what we are
already doing, and there is no carve-out, no API terms document, and no data grant anywhere I
looked.** §2.2 asks for exactly that and then says STOP.

**The counter-reading deserves to be on the table, because the lead should rule on the real
question, not a one-sided one.** Kraken publishes these endpoints, documents them, and assigns them
rate limits — an invitation to programmatic use. A reading in which every API client breaches
Section 9 would make Kraken's own API business impossible, and the *"third-party applications …
without our prior written consent"* clause would, read literally, prohibit every openly-operating
Kraken integration in existence. Section 9 is plausibly aimed at website scraping and abusive bots
rather than at documented API consumption.

**But that reading is an inference about intent, and the clause is a text.** Choosing the
convenient inference over the written restriction is the decision §2.2 removed from me. It is
available to the lead — with the residual named — and it is not available to me.

---

## §3 · §4 · §5 · §6 — NOT EXECUTED

Not attempted, deliberately. §3's campaign — paginating the full BTC/USD trade history — is the
activity Section 9 names. §4 and §5 exist to support it. §6's verdict presupposes it.

**One thing §6.4 anticipated is worth recording as settled**: it asked me to stop and say so if the
campaign's scale warranted a grant. It does — but the stop arrives one section earlier and for a
stronger reason. The scale question is now moot unless the licence question is resolved first.

**Reach, limits, and sanity remain genuinely unknown.** WO-059 measured only that `/0/public/Trades`
returns 1,000 rows per call with an advancing cursor over a two-hour window. Whether it reaches
2013 or hits a wall is **unmeasured**, and nothing in this report should be read as evidence either
way — that would be exactly the doc-asserted-versus-measured conflation this WO was written to
prevent.

---

## THE REACH OF THE FINDING — beyond this WO

The clauses do not distinguish between the pull that was planned and the collection already
running. Stated plainly, because burying it under §2 would be the more comfortable choice:

| activity | status | falls under |
|---|---|---|
| WO-060 §3 bulk trades pull | **not started** | *data extraction methods* |
| **`phaseb_20260809`** — live WebSocket capture, running now | **RUNNING** | *scripts, programs, routines … automation to engage in any activity* |
| `corpus_20260805`, `validation_20260809` | already captured and ratified | same |
| WO-059 REST probes | already performed | *data extraction* |
| The trading system itself | in the tree | *third-party applications that interact with Our Content without our prior written consent* |

Two things follow that are **not** mine to decide, and I have decided neither:

1. **Whether `phaseb_20260809` continues.** The WO says do not disturb and do not stop it. I have
   not. It is still writing.
2. **Whether the ratified corpora remain usable.** They are the apparatus's foundation. Nothing was
   touched; both verify unchanged.

The one thing I will say without hedging: **if the declared judgment of §2.3 is going to be
exercised anyway, it should be exercised knowingly against a quoted clause, not recorded as though
the silence it was written for still existed.** Those are different acts and the record should not
confuse them. The §2.3 residual — *"Kraken could later assert restrictions, in which case the basis
is quarantined"* — was written for a hypothetical. It is no longer hypothetical, and a residual
that has already materialised is not a residual.

---

## §0.5 — EVERY ATTEMPT

| # | attempt | outcome |
|---|---|---|
| 1 | `git log`, `git diff -- src/` | HEAD `329cb30`, not `67193e2`; src diff **empty**; discrepancy reported |
| 2 | Phase-B open reading | PID 22236 alive, 12 segments, 10.549 covered h, **0 gaps** |
| 3 | Gap rate, first calculation | **WRONG** — 38 ledger *entries* / 36.903 h = 1.0297/h, double the cited figure |
| 4 | Gap rate, corrected | Ledger writes `open` + `resolved` per gap → **19 gaps** → **0.5149/h**, matching the citation exactly |
| 5 | `kraken.com/legal` index | 10 documents enumerated |
| 6 | Global ToS, full text pulled and read directly | **Section 9 restrictions found.** Last updated 2026-08-04 |
| 7 | Definition of "Our Content" / "Platforms" | Covers *services*; **no API carve-out** |
| 8 | Search ToS body for API provisions | One mention only — order submission, agency basis. Grants nothing about data. |
| 9 | Canadian ToS | **Same three clauses, verbatim.** Last updated 2026-06-26 |
| 10 | EEA ToS | **Same clauses.** Last-updated not stated on page |
| 11 | `docs.kraken.com/` and `/api/` | JS-rendered; no terms text retrievable |
| 12 | `docs.kraken.com/websockets/` | **404.** Legacy doc's terms sentence cited as search-surfaced only; STOP does not rest on it |
| 13 | API-docs support article | **No terms, no licence, no usage grant** |
| 14 | §3 reach measurement | **NOT ATTEMPTED** — the clause names this activity |
| 15 | §4 rate limits, §5 sanity, §6 verdict | **NOT ATTEMPTED** — all downstream of §3 |

**Zero requests were made to `api.kraken.com` in this WO.** Every retrieval above was of a published
legal or documentation page.

---

## §7 ACCEPTANCE — what is and is not met

| requirement | status |
|---|---|
| Licence documents enumerated and cited | **met** — 7 documents, table above |
| Terms quoted **or** silence recorded with declared judgment | **met — terms quoted.** The declared judgment is deliberately NOT recorded: §2.3 is conditioned on silence |
| Reach measured, falsifier, silent-wall check | **not met — §2.2 STOP** |
| Rate limits cited, estimate re-derived | **not met — §2.2 STOP** |
| Earliest-data sanity, ≥3 eras | **not met — §2.2 STOP** |
| Verdict + polling plan or wall | **not met — §2.2 STOP** |
| MAY / MAY-NOT declared | **not declared.** It presupposes an admissible basis; that question is now upstream |
| `git diff -- src/` empty | **met** — pasted, empty |
| captures untouched | **met** — both corpora verify unchanged |
| `phaseb_20260809` still writing | **met** — see close reading |
| all gates | **met** — see close |
| CI green, last green run for HEAD | **met** — `31299001628`, no code changed |

---

## `phaseb_20260809` — AT CLOSE

PID **22236** alive, 73 MB working set. **12 segments**, last frame `2026-08-09T17:15:55.768Z`,
**10.727 covered hours** — advanced from 10.549 at open, so it was writing throughout this WO.
Gap ledger still **one line** (`run_start`): **0 gaps, 0 seams, running rate 0.000 / covered hour**
against the reference 0.515.

Not disturbed, not stopped, not touched. **Nothing in this WO wrote to `captures/`, and no request
was made to `api.kraken.com`.**
