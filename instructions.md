Two corrections to REPORT.md before this goes to review — accuracy matters more than a clean-looking table:

Change the "Raw data path is append-only" row from PASS to N/A, with the note: "Not yet exercised — the walking skeleton does not persist raw market events to disk. This invariant is UNTESTED, not satisfied. Must be verified when the live ingester writes to data/." An untested invariant must never appear as a green check.
Add a new section 9. Known gaps / not yet proven listing honestly:

The end-to-end loop has only ever run against SimulatedMarketFeed. It has never touched a live Bybit WebSocket — reconnect handling, malformed payloads, rate limiting, and data gaps are all unverified.
No raw market data has been persisted; the append-only storage path does not exist yet.
import-linter uses forbidden contracts rather than a strict layers contract (relaxed so backtest/ can orchestrate strategy/risk/data). The two critical boundaries (no ML in risk/; no adapters in strategy//risk//data/) are enforced and verified to fail the build — but full layer ordering is NOT enforced. Recorded as a deliberate, known relaxation.



Then commit as report: record known gaps and untested invariants honestly.

That's Sprint 1's core done. Take REPORT.md to the Strategy & Roadmap chat for the sanity-check against the roadmap — that was the agreed loop, and the known-gaps section is exactly what that review needs to see.