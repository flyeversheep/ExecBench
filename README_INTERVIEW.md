# ExecBench — Evaluating the decisions behind delegated work

**Can an AI agent deliver a project when worker updates are unreliable, requirements are incomplete, and verification consumes the same budget as execution?**

ExecBench turns that question into a runnable evaluation environment. An executive agent delegates to simulated workers, asks stakeholders for requirements, audits progress, handles incidents, and decides when to ship. The simulator retains hidden ground truth, so a convincing status report can be compared with what actually happened.

This is a portfolio walkthrough of the problem framing, implementation choices, tools, validation, and limits. For the full interface and configuration reference, see the [technical README](README.md).

## Start here: a five-minute review

1. Open the [stale-trust trace](demo/stale-trust.html): compare Alex's reported progress with the hidden outcome. Download and open the HTML locally; it works offline.
2. Compare the [heuristic verification trace](demo/verification.html) and [audit-cost trace](demo/audit-cost.html) for the same scenario. Detecting a problem and delivering a good outcome are different achievements.
3. Read the [v15 comparison](results/dev_v15/README.md) and [failure analysis](#failure-analysis-where-models-lose-credit). The [baseline leaderboard](demo/leaderboard.md) and [partial live-run report](demo/live-resumed/REPORT.md) provide historical context.
4. Inspect [the action and data contracts](execbench/schemas.py), [observation construction](execbench/env/observations.py), and [regression tests](tests/test_environment.py).

The repository includes the [50-scenario v1 set](scenarios/v1), its [five-scenario development subset](scenarios/v1_dev), and [all ten v15 model trajectories](results/dev_v15/README.md), alongside five scripted policies and 250 historical v0 baseline results. The v15 manifest matches the current implementation and supplied development scenarios; older demo results predate later changes to costs, prompts, and question handling.

## Problem framing and scope

The unit of evaluation is a **management decision under partial information**. A worker may claim completion early, optimize a proxy metric, or appear reliable because of outdated feedback. An executive must decide what to ask, whom to trust, when to verify, and whether intervention is worth its cost.

The first implementation deliberately uses simulated work. This makes progress, quality, hidden requirements, and misleading reports observable to the evaluator while keeping them hidden from the agent. It also allows inexpensive, repeatable experiments before introducing real document or repository workers.

Success is measured across outcome, escalation, detection, verification, reporting, coaching, memory use, and efficiency. There is no composite score: a single number would hide tradeoffs such as more detection at the expense of delivery. The simulator's compute budget and actual API token/spend accounting are separate quantities.

## Design decisions and tradeoffs

| Decision | Why it matters | Cost or limitation |
|---|---|---|
| Separate public observations from hidden simulator state | Agents must discover relevant facts rather than read the answers. Public fields are explicitly copied, with leakage regression tests. | Published scenarios expose the simulator to anyone developing against it; this is not a secret test set. |
| Seeded, named random streams | Extra status or audit calls cannot perturb the underlying work draws and accidentally change the comparison. | Live model responses need the response cache for exact replay. |
| One validated action per model turn | Malformed or multiple tool calls execute nothing; retries do not advance simulated time. Repeated failures eventually force a wait. | Interface and retry behavior are part of the benchmark and must be versioned. |
| Deterministic metrics plus model-assisted narrative grading | Python calculates outcomes and formulas; a judge extracts report claims and evaluates coaching against evidence. | Narrative judgment remains imperfect and requires separate validation. |
| Several baselines and a privileged greedy oracle | TrustAll, AuditAll, Heuristic, Random, and Oracle make different failure modes inspectable. | The oracle is an empirical reference, not an upper bound; normalized outcomes can exceed 1. |
| Hashed resume manifests and cached API responses | Interrupted runs retain successful episodes and reject incompatible configurations. | A changed implementation requires a new output directory; replay is not an independent sample. |
| Full traces and standalone HTML viewers | A reviewer can follow observation → action → consequence → score evidence. | Full traces contain hidden truth and belong to evaluation, not the agent's input. |

The [project plan](execbench_project_plan.md) records the broader design. The [technical README](README.md) documents concrete resolutions of ambiguous semantics, including dependency timing, blocked-worker costs, and strict incident deadlines.

## Architecture and tool use

```text
Seed + YAML templates → Scenario with hidden truth
                              ↓
                    ExecEnv → Public observation
                       ↑             ↓
                 Validated action ← Scripted or LLM policy
                       ↓
                Episode trace → Graders → Scorecard + HTML viewer
```

| Tool or component | Concrete role |
|---|---|
| Python, Pydantic, Typer | Typed scenario/action/trace contracts and a CLI for generation, episodes, benchmarks, and viewing. |
| NumPy and YAML | Controlled randomness and six configurable project templates spanning five difficulty levels. |
| HTTPX provider adapters | OpenAI-compatible and Anthropic tool-call handling, response caching, usage accounting, and redacted errors without provider SDK dependencies. |
| Environment credentials / optional 1Password CLI | Runtime credential loading; credentials are excluded from traces and response-cache records. |
| Pytest, Ruff, uv, GitHub Actions | Regression checks, linting, locked dependencies, and automated checks on pushes and pull requests. |
| Jinja2 and standalone HTML | Inspectable traces with escaped rendered content and no hosted service required. |

The agent's tools include stakeholder questions, assignments, audits, reassignment, escalation, coaching, reporting, and shipping. Each has explicit semantics: for example, `coach_ic` evaluates retrospective feedback but does not repair work or adapt workers during the episode.

For this documentation update, Codex assisted with source inspection, drafting, and running the checks reported below. The descriptions of the implementation are grounded in repository evidence; this walkthrough does not reconstruct the original development prompts or attribute every implementation decision to a particular tool.

## Execution: changes that make the benchmark more credible

The commit history and tests show concrete iteration on the evaluation contract:

- **Constrain information gathering.** Human questions are scoped to a task, cost patience by word count, and, with a configured judge, must pass a readability check before revealing information. Offline runs explicitly leave that check unchecked.
- **Price over-specification.** Distinct assignment flags consume compute regardless of hidden relevance. A separate specification-precision diagnostic exposes indiscriminate flag use without secretly charging according to the answer key.
- **Enforce tool-call semantics.** Provider requests prohibit parallel calls, and local validation rejects batches atomically. Tests cover recovery and forced waits.
- **Preserve conversation structure.** Original assistant calls and paired tool results are replayed until history compaction, allowing provider prompt-cache reuse without rebuilding every turn's prefix.
- **Treat infrastructure failures separately.** Insufficient API balance stops queued work. Failed episodes are recorded rather than counted as poor management decisions.

See [question tests](tests/test_question_readability.py), [specification tests](tests/test_specification.py), and [provider/runner tests](tests/test_llm_runner.py) for reviewable evidence.

## Run it without an API key

Requires Python 3.11+ and uv. From the repository root:

```sh
uv sync --frozen --extra dev --python 3.13
uv run pytest -q
uv run ruff check execbench tests scripts

# Generate a fresh scenario set under the current simulator semantics.
uv run execbench generate --out scenarios/interview --count 5 --seed 1000
uv run execbench run-benchmark --scenario-set scenarios/interview \
  --policies oracle,heuristic,trust_all,audit_all,random \
  --grader-model none --workers 1 --out results/interview
uv run execbench view results/interview/traces/l1_01000__heuristic.json.gz \
  --out results/interview/trace.html
```

Open `results/interview/trace.html` and `results/interview/leaderboard.md`. The run produces 25 episodes. `--grader-model none` explicitly disables API grading; nonempty narrative reports and eligible coaching remain ungraded. It also skips the online question-readability gate, so this is not identical to live evaluation.

Resume with the same command and configuration. After code or configuration changes, choose a new output directory. For live evaluation, follow the [credential and grader setup](README.md#live-llm-evaluation); live calls incur provider charges.

## Testing and evidence

Tests target failure modes that could invalidate the benchmark: hidden-state leakage, budget underflow, tick-order dependence, nondeterministic regeneration, incorrect metric formulas, misleading worker behavior, invalid tool calls, cache/redaction errors, incompatible resumes, and unsafe HTML rendering. Twenty hand-authored seeded cases check oracle ≥ heuristic ≥ TrustAll; that ordering is deliberately not asserted for every generated scenario.

Verified on September 7, 2026 against code commit `a375ba9`, using Python 3.13.15 and the frozen dependency lock in an isolated environment:

- **95 tests passed**; Ruff reported **all checks passed**.
- Fresh generation and the five-policy offline walkthrough completed **25/25 episodes with zero failures**. Temporary output paths were used for validation.
- The trace viewer rendered successfully, and resuming the same benchmark retained **25 completed episodes**.

CI configuration is in [test.yml](.github/workflows/test.yml) and uses Python 3.12. Offline tests use controlled provider responses; they do not establish that a live model or judge behaves correctly. No new live API evaluation was run for this documentation update.

The current [v15 development snapshot](results/dev_v15/README.md) is complete at 10/10 episodes across five matched scenarios, including difficulty 5. Its manifest and embedded scenarios were checked against the supplied code and scenario files on September 9, 2026. The 95-test suite and lint checks also passed again on that date.

The older live evaluation is incomplete: the [September 5 report](demo/live-resumed/REPORT.md) records 208/350 completed episodes, including 76 executive-model episodes, before API balance depletion. Its 15-scenario matched comparison reports normalized outcome of 0.894 for GLM-5, 0.816 for GLM-5.1, and 0.793 for GLM-4.7. These are descriptive results from an incomplete, within-provider run, not a current model ranking or a result reproduced by this documentation update.

## Failure analysis: where models lose credit

The `dev_v15` run contains **10 completed episodes: two models on the same five scenarios, one per difficulty level**. These examples come from saved trajectories, not new model calls. [Run metadata and selected traces](demo/dev-v15/README.md) are included for inspection. They describe failure mechanisms in this small development set, not their prevalence across models. Step numbers below are the trace's `index`; ticks are simulated time.

**Score attribution matters.** Outcome is `(weighted completed quality − requirement penalties − incident penalties) / oracle_outcome`. Incomplete tasks contribute zero delivered value. Detection, escalation, specification precision, report honesty, and coaching are separate metrics; their low scores are not additional outcome deductions. Differences between two trajectories are observational, while the explicit penalty terms below are exact accounting within the saved episode.

| Failure category | Observed decision and evidence | How it costs credit |
|---|---|---|
| **Slow recovery of a blocked dependency** | In L4 logging migration, Luna reassigns the blocked inventory task only at step 26 / tick 9. The ingestion adapter starts at tick 11 and is only **38.4% complete** when Luna ships at tick 14. Terra reassigns at tick 3 and completes the adapter at tick 9. [Luna trace](demo/dev-v15/l4_01030__gpt-5.6-luna.json.gz), [Terra trace](demo/dev-v15/l4_01030__gpt-5.6-terra.json.gz). | Luna completes **4/8 planned tasks**, versus Terra's 8/8; both also complete the incident task. Normalized outcome is **0.568 vs 0.912**. Unfinished work earns no delivered value. Earlier recovery is a plausible contributor to the gap, but staffing and specifications also differ. |
| **Missing an operational deadline despite eventual completion** | In L2, Luna's incident assignment at step 12 / tick 2 is rejected because the worker is busy; the successful assignment is at tick 9. Terra succeeds at tick 5. The incident requires assignment **strictly before tick 5**. [Luna trace](demo/dev-v15/l2_01010__gpt-5.6-luna.json.gz), [Terra trace](demo/dev-v15/l2_01010__gpt-5.6-terra.json.gz). | Both incur an incident penalty of **0.600 raw outcome**, or **0.136 normalized outcome** using the reference of 4.399. Completing mitigation later does not erase a missed response deadline. An attempted assignment is not an accepted assignment. |
| **Failing to translate requirements into task specifications** | L2 Terra assigns every task with empty `spec_flags`, including documentation and work requiring consent. L2 Luna applies `explicit_consent` broadly but omits the documentation accessibility requirement. | Terra loses **0.422 raw outcome** to `accessible_docs` and `explicit_consent` violations. Luna loses **0.162** to accessibility and has specification precision **2/6 = 0.333**. Extra irrelevant flags cost compute without satisfying the missing requirement. Precision measures relevance of supplied flags, not completeness of requirements coverage. |
| **Accepting a completion claim without checking current work** | L5 Terra reports readiness at step 39 and ships at step 40 / tick 16. `task_8` is still `done_claimed`, with true progress **92.4%** and no completed quality. Its only audit was earlier, at tick 9, before this task was assigned at tick 11. [Terra trace](demo/dev-v15/l5_01040__gpt-5.6-terra.json.gz). | `task_8` contributes **zero delivered value** despite the completion claim. Episode outcome is **0.742**. A previous audit of a worker does not verify a later assignment; the trace does not establish what quality or outcome an extra wait would have produced. |
| **Escalating decisions that do not need stakeholders** | L5 Terra escalates the tabs-versus-spaces questions at steps 13 and 21, as well as all three genuinely escalation-worthy decisions. | **TP=3, FP=2, FN=0** yields precision **0.600**, recall **1.000**, and F1 **0.750**. Luna's F1 is **1.000** on the same scenario. Escalating everything preserves recall while losing precision. |
| **Omitting or overstating the final report** | L4 Luna ships with no report; L5 Luna reaches deadline termination with no report. L5 Terra reports launch readiness while `task_8` remains incomplete and an `explicit_consent` violation remains. [L5 Luna trace](demo/dev-v15/l5_01040__gpt-5.6-luna.json.gz). | Missing reports deterministically score **0**. Terra's L5 report also scores **0**, from the judge's claim labels and omissions passed through the Python formula. This is a reporting metric, separate from delivery. The incomplete task is directly verifiable; other narrative judgments remain exploratory. |
| **Late or absent corrective follow-through** | L5 Luna audits `ic_d` at step 28 / tick 11, seven ticks after its first material misreport. It never coaches any worker. | Detection is **1/3**, with latency **7 ticks for the detected worker only**. Coaching is **0** across three eligible workers because feedback is absent. This is missed retrospective feedback; coaching would not repair this episode's deliverables. |

### A concrete score breakdown

L2 Terra completes all six planned tasks, yet its normalized outcome is only **0.726**:

```text
Weighted completed quality                  4.215290
− missing-requirement penalties              0.422395
− late incident-assignment penalty           0.600000
= raw outcome                               3.192895
÷ same-scenario greedy-reference outcome     4.398955
= normalized outcome                        0.725830
```

The two explicit penalties account for **0.232 normalized outcome points**. Holding delivered quality fixed and removing only those penalties gives 0.958; that is an accounting illustration, not a rerun proving that prevention would have been free. The remaining gap to the reference reflects differences in weighted delivered quality. This distinction prevents attributing every lost point to a single memorable mistake.

### What the failures suggest testing next

The traces motivate targeted policy changes: verify that assignments succeed, track incident deadlines separately from task completion, recover dependencies promptly, map discovered requirements to each task, audit new completion claims when warranted, and reserve a finalization step for reporting and coaching. Each change should be tested on fresh matched scenarios with its resource costs included.

There are also evaluator limits. L4 has **zero eligible misleading workers** for both models, so detection `0/0` is not a detection failure. L5 Luna's deadline termination is a valid scored episode, not a harness error. All ten episodes have zero parse-forced waits; invalid scheduling actions are a different failure class. Finally, the narrative judge sometimes conflates a missing consent flag with bypassing review, or late incident handling with non-completion. Use the structured states and deadline rules for those distinctions rather than treating every judge explanation as established fact.

## Limitations and next steps

- **External validity:** simulated worker behavior does not establish real-world management capability. Add document/repository workers and test whether the observed behaviors transfer.
- **Judge validity:** synthetic acceptance checks passed, but live reports exposed missing truth context and overlapping omission judgments. [The grading notes](demo/live-resumed/GRADING_NOTES.md) preserve those failures. Enrich and deduplicate evidence, then validate a new rubric with human raters.
- **Coverage and uncertainty:** live coverage is incomplete and unequal, with no completed difficulty-5 results in the recorded run. Complete matched coverage, repeat trials, and report uncertainty before making ranking claims.
- **Version drift:** supplied scenarios and traces predate subsequent semantic changes. Regenerate oracle references and rerun all compared policies under the same manifest.
- **Learning and cost control:** no cross-episode learning or within-episode coaching adaptation is implemented. Add explicit API spending caps before expanding live runs.

The strongest evidence of engineering judgment here is the combination of a runnable system, explicit contracts, inspectable failures, and bounded claims. An interviewer can challenge a design choice, inspect its implementation, and run the corresponding regression test.
