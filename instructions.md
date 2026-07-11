now : 

/speckit-tasks
When generating the task list, honor these sequencing constraints:

import-linter goes in the very first task, alongside repo scaffolding — with the layer contracts written and wired into the test command while the modules are still near-empty. It must be able to fail the build from day one. Do not defer it to a later "quality" or "CI" task.
.gitignore and .env.example also land in that first task, before any code that could touch a credential exists.
P1 tasks (live end-to-end paper loop) must complete before P2 tasks (backtest) begin. Walking skeleton first — do not interleave.
The risk engine's tests must include a clamp case that actually fires (per SC-010) and a "kill switch engaged → place_order refused AND cancel_order still succeeds" case.

Then stop and report the task list: IDs, one-line each, grouped by story/phase, with the parallel [P] markers. Do not run /speckit-implement yet.

I want to see the task list before any code gets written — mainly to check that task 1 really does stand up the guardrail, and that the P1/P2 boundary didn't blur. Paste it back and, if it's sound, the next command actually builds the thing.