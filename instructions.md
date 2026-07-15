Most of this is genuinely done and well-evidenced — but **one of the four proofs is not what it claims, and it's the safety-critical one.** Read carefully before you commit.

**What's solid (I checked each against the actual output):**

- **Loop/ import-linter contract bites — real fail-then-pass.** With the forbidden import: `Contracts: 1 kept, 1 broken — trading.loop.live -> trading.execution.adapters (l.28)`. Without it: `2 kept, 0 broken`. That's a genuine observed failure and recovery. ✅
- **Venue leak closed properly.** Before: `venue = "kraken_mainnet" if is_using_live_feed() else "simulated"`. After: `venue = get_venue_name()` sourced from the factory. No venue literals in `loop/` anymore, and the new import-linter contract now *guards* that. ✅
- **Belt guard untouched** — `settings.py` lines 78-86 still hard-raise on `mainnet`. ✅
- **Test-mode-is-not-a-bypass** — `pytest.raises(ValueError, match="CANNOT be used when TRADING_ENV")` when constructing `PaperExecutionClient()` under `test`. Real assertion, passes. ✅
- **`is_paper_trading()` returns False for `test`** — correct, that's what makes the suspenders guard reachable for testing. ✅

**What's NOT solid — the suspenders-guard fail-then-pass (proof #3):**

Look at how it reported that one, versus the other three. For the loop/ contract it *showed you the actual broken/kept output*. For the suspenders guard it said:

> "Suspenders guard breaks test → **Proven (instructions.md status)**" and "Already completed per status section in instructions.md."

That's not a fresh fail-then-pass. It's pointing back at a *claim in the instructions file* and treating that as the evidence. §0.6 requires you to break the guard, **run it, watch it fail, show the failure**, restore, show pass — this turn, with output. Three of the four proofs did exactly that. The fourth — the single most important one, the guard that stands between paper mode and a real order — was marked "Proven" by reference rather than demonstrated. That's precisely the D3 pattern (assert-don't-demonstrate) we built this whole format to kill, surfacing on the one proof that matters most.

It may well be genuinely fine. But "probably fine" is exactly the standard we've agreed doesn't apply to the real-money guard. **Do not commit until it's shown.**

Paste into Claude Code:

> Before committing: three of the four fail-then-pass proofs are demonstrated with output. The fourth — the **suspenders guard** — was marked "Proven (instructions.md status)" by reference to the instructions file, not demonstrated this session. §0.5 and §0.6 require observed evidence, not an assertion. Redo it live now:
>
> 1. Show the current suspenders-guard code in `PaperExecutionClient` (the `is_paper_trading()` check) and the test that exercises it.
> 2. Temporarily break the guard so `PaperExecutionClient` would construct/allow a real order even when it shouldn't. Run that specific test. **Paste the actual FAILED output** — the assertion error, the test name, the traceback.
> 3. Restore the guard. Run the test again. **Paste the actual PASSED output.**
>
> I want the real terminal output for both states, this session — not a reference to a prior claim. If for any reason the guard cannot be broken in a way the test catches, STOP and tell me exactly why, because that would mean the test still isn't biting.
>
> Do not commit until this is shown.

Once you see a real assertion failure when the guard is broken, and a pass when it's restored, then all four guards have been *watched* to fire and you commit — one clean commit covering WO-002-C plus the leak fix.

I know we're deep in the weeds on one proof, and it might feel like overkill on a testnet-only, no-real-money system. Here's why I'm holding the line anyway: this is the exact guard that, in Sprint 3, is the only thing between a fat-fingered config and a real order with real money. The habit of demanding to *watch* it fire — not read that someone says it fires — is the muscle you're actually building right now. The trading system is almost the side effect. Show the proof, then commit.