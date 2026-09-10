# ExecBench — Evaluating the decisions behind delegated work

**Can an AI agent deliver a project when worker updates are unreliable, requirements are incomplete, and verification consumes the same budget as execution?**

ExecBench turns that question into a runnable evaluation environment. An executive agent delegates to simulated workers, asks stakeholders for requirements, audits progress, handles incidents, and decides when to ship. The simulator retains hidden ground truth, so a convincing status report can be compared with what actually happened.

This is a portfolio walkthrough of the problem framing, implementation choices, tools, validation, and limits. For the full interface and configuration reference, see the [technical README](README_TECHNICAL.md).

## Start here: a five-minute review

1. Read the [v15 run metadata and trajectories](results/dev_v15/README.md) and [failure analysis](#failure-analysis-where-models-lose-credit) for a rollout run with latest dev set comparing two GPT models (details below).
2. Inspect [the action and data contracts](execbench/schemas.py), [observation construction](execbench/env/observations.py), and [regression tests](tests/test_environment.py).

The repository includes the [50-scenario v1 set](scenarios/v1), its [five-scenario development subset](scenarios/v1_dev), and [all ten v15 model trajectories](results/dev_v15/README.md), alongside five scripted policies. The policies are `gpt-5.6-luna` and `gpt-5.6-terra` through OpenAI; the shared grader is Z.ai’s `GLM-5.3-Flash`. The v15 manifest matches the current implementation and supplied development scenarios.

## Problem framing and scope

The unit of evaluation is a **management decision under partial information**. A worker may claim completion early, optimize a proxy metric, or appear reliable because of outdated feedback. An executive must decide what to ask, whom to trust, when to verify, and whether intervention is worth its cost.

The first implementation deliberately uses simulated work. This makes progress, quality, hidden requirements, and misleading reports observable to the evaluator while keeping them hidden from the agent. It also allows inexpensive, repeatable experiments before introducing real document or repository workers.

ExecBench does not yet target a unified API or interface for AI executives. Its action and observation contracts are working assumptions for testing the concept, with general management operations intended to support adaptation to future real-world workflows. These contracts are provisional: integrating real workers and tools may require revising both the interface and the assumptions behind it.

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

The [project plan](execbench_project_plan.md) records the broader design. The [technical README](README_TECHNICAL.md) documents concrete resolutions of ambiguous semantics, including dependency timing, blocked-worker costs, and strict incident deadlines.

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

## Execution: removing failures unrelated to model capability

The [outcome calculation](execbench/graders/outcome.py) provides a concrete way to examine how the benchmark evaluates requirement discovery: **outcome = (weighted completed quality − requirement penalties − incident penalties) / greedy-oracle reference**. A completed task can still trigger a penalty if its assignment omits a required specification tag. To avoid that loss, the agent must discover requirements from the policy document or, when they are missing there, ask stakeholders useful clarifying questions, then include the applicable tags in `assign.spec_flags` before work begins. Asking alone does not update the assignment. This connects **clarification → correct task specifications → delivered outcome**, making requirement discovery consequential for a high score, alongside execution quality and incident handling.

Reviewing early rollouts, I used this mechanism to look for two threats to the evaluation: models losing credit because the interface was unclear, and models obtaining or applying tags through shortcuts that required little judgment. The following four changes aim to make that path from questions to outcome more credible: clarify the tool-call contract, distinguish coaching from specification changes, make discovery selective, and expose indiscriminate tagging.

1. **Make general instructions explicit so interface mistakes do not dominate the comparison.** Models should understand the action contract before being evaluated on their decisions. I emphasized **exactly one tool call per turn** in the system prompt, disabled parallel calls in OpenAI API requests, and made retry feedback explain that a rejected batch executed nothing and did not advance the simulation. Local validation still enforces the rule, and repeated invalid responses eventually force a wait. The intent was to reduce avoidable losses on a procedural requirement that does little to differentiate management ability. See [the single-tool-call contract change](https://github.com/flyeversheep/ExecBench/commit/233738d212560ec1b5aae7fbf5c62687ed318bd9).

2. **Distinguish retrospective coaching from intervention in current work.** Some rollouts used `feed_back` to send new requirements or request revisions, although the action only recorded post-hoc feedback to an individual contributor (IC). The model could appear to intervene while leaving the task unchanged and missing credit for the required action. I renamed it `coach_ic` and clarified its description, errors, and return value: coaching is evaluated at episode end and does not change specifications, progress, quality, blockers, or worker behavior during the episode. Requirements belong in `assign.spec_flags`; operational intervention must use the applicable task actions. This makes the interface better reflect the behavior the simulator actually supports. See [the coaching semantics change](https://github.com/flyeversheep/ExecBench/commit/c41c4418eed7a8a30d2d0c870eb09ba7b29c85b4).

3. **Make clarification require selective, well-formed questions.** In the original setup, keyword matches in one broad question could reveal stakeholder constraints across multiple tasks. That made requirement discovery too easy: an agent could pack trigger words into a question instead of deciding which uncertainty was worth resolving. I introduced three complementary constraints: each question targets one task and reveals only matching requirements applicable to it; patience cost grows with question length; and a configured LLM judge rejects incoherent keyword stuffing before disclosure, while still charging patience. The length charge is **one patience per 20 whitespace-delimited words, rounded up**, with a minimum of one—not a model-token count. Together, these changes make both questioning many tasks and packing many topics into one turn more expensive. Discovered tags can still be reused where applicable. See [the task-scoped clarification change](https://github.com/flyeversheep/ExecBench/commit/1e1a2a23a27a76f3d0cdebc0155d1280d0f7fe7c).

   I retained keyword-based disclosure as a deliberate tradeoff. It is less realistic and can miss valid paraphrases, but gives benchmark authors explicit control over disclosure triggers. An LLM-based disclosure mechanism could offer higher recall for semantically valid questions, at the cost of less direct control over exactly when specifications are revealed; that benefit has not been measured here. The current hybrid uses the LLM only to assess readability, without exposing hidden constraints to it. It does not eliminate every discovery shortcut, and offline runs without a grader leave readability unchecked.

4. **Measure whether specifications are relevant, not just whether required tags are present.** An agent could otherwise attach every known tag to every assignment and satisfy requirements without mapping them to the work. I added **specification precision**: relevant flags divided by all supplied flags, deduplicated within each accepted assignment. Each distinct flag also incurs a public compute cost regardless of relevance, so indiscriminate tagging consumes resources without the charge revealing hidden requirements. Precision is a separate diagnostic, not an extra outcome penalty or a measure of requirement coverage; it is omitted when no flags are supplied. This makes tag spamming visible while preserving the distinction between unnecessary specifications and missing ones. See [the specification precision change](https://github.com/flyeversheep/ExecBench/commit/ea2598308b56c022caa1a6748cd1889aa1187084).

These changes aim to make scores more informative about management decisions; they do not by themselves establish improved benchmark validity. Regression evidence is available in the [provider/runner tests](tests/test_llm_runner.py), [environment tests](tests/test_environment.py), [question-readability tests](tests/test_question_readability.py), and [specification tests](tests/test_specification.py). Supporting harness changes also preserve assistant/tool conversation structure for prompt-cache reuse and record infrastructure failures separately from scored management failures.

## Failure analysis: where models lose credit

The `dev_v15` run contains **10 completed episodes: two models on the same five scenarios, one per difficulty level**. These examples come from saved trajectories, not new model calls. [Run metadata and trajectories](results/dev_v15/README.md) are included for inspection. They describe failure mechanisms in this small development set, not their prevalence across models. Step numbers below are the trace's `index`; ticks are simulated time.

**Score attribution matters.** Outcome is `(weighted completed quality − requirement penalties − incident penalties) / oracle_outcome`. Incomplete tasks contribute zero delivered value. Detection, escalation, specification precision, report honesty, and coaching are separate metrics; their low scores are not additional outcome deductions. Differences between two trajectories are observational, while the explicit penalty terms below are exact accounting within the saved episode.

| Failure category | Observed decision and evidence | How it costs credit |
|---|---|---|
| **Slow recovery of a blocked dependency** | In L4 logging migration, Luna reassigns the blocked inventory task only at step 26 / tick 9. The ingestion adapter starts at tick 11 and is only **38.4% complete** when Luna ships at tick 14. Terra reassigns at tick 3 and completes the adapter at tick 9. [Luna trace](results/dev_v15/traces/l4_01030__gpt-5.6-luna.json.gz), [Terra trace](results/dev_v15/traces/l4_01030__gpt-5.6-terra.json.gz). | Luna completes **4/8 planned tasks**, versus Terra's 8/8; both also complete the incident task. Normalized outcome is **0.568 vs 0.912**. Unfinished work earns no delivered value. Earlier recovery is a plausible contributor to the gap, but staffing and specifications also differ. |
| **Missing an operational deadline despite eventual completion** | In L2, Luna's incident assignment at step 12 / tick 2 is rejected because the worker is busy; the successful assignment is at tick 9. Terra succeeds at tick 5. The incident requires assignment **strictly before tick 5**. [Luna trace](results/dev_v15/traces/l2_01010__gpt-5.6-luna.json.gz), [Terra trace](results/dev_v15/traces/l2_01010__gpt-5.6-terra.json.gz). | Both incur an incident penalty of **0.600 raw outcome**, or **0.136 normalized outcome** using the reference of 4.399. Completing mitigation later does not erase a missed response deadline. An attempted assignment is not an accepted assignment. |
| **Failing to translate requirements into task specifications** | L2 Terra assigns every task with empty `spec_flags`, including documentation and work requiring consent. L2 Luna applies `explicit_consent` broadly but omits the documentation accessibility requirement. | Terra loses **0.422 raw outcome** to `accessible_docs` and `explicit_consent` violations. Luna loses **0.162** to accessibility and has specification precision **2/6 = 0.333**. Extra irrelevant flags cost compute without satisfying the missing requirement. Precision measures relevance of supplied flags, not completeness of requirements coverage. |
| **Accepting a completion claim without checking current work** | L5 Terra reports readiness at step 39 and ships at step 40 / tick 16. `task_8` is still `done_claimed`, with true progress **92.4%** and no completed quality. Its only audit was earlier, at tick 9, before this task was assigned at tick 11. [Terra trace](results/dev_v15/traces/l5_01040__gpt-5.6-terra.json.gz). | `task_8` contributes **zero delivered value** despite the completion claim. Episode outcome is **0.742**. A previous audit of a worker does not verify a later assignment; the trace does not establish what quality or outcome an extra wait would have produced. |
| **Escalating decisions that do not need stakeholders** | L5 Terra escalates the tabs-versus-spaces questions at steps 13 and 21, as well as all three genuinely escalation-worthy decisions. | **TP=3, FP=2, FN=0** yields precision **0.600**, recall **1.000**, and F1 **0.750**. Luna's F1 is **1.000** on the same scenario. Escalating everything preserves recall while losing precision. |
| **Omitting or overstating the final report** | L4 Luna ships with no report; L5 Luna reaches deadline termination with no report. L5 Terra reports launch readiness while `task_8` remains incomplete and an `explicit_consent` violation remains. [L5 Luna trace](results/dev_v15/traces/l5_01040__gpt-5.6-luna.json.gz). | Missing reports deterministically score **0**. Terra's L5 report also scores **0**, from the judge's claim labels and omissions passed through the Python formula. This is a reporting metric, separate from delivery. The incomplete task is directly verifiable; other narrative judgments remain exploratory. |
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
- **Judge validity:** narrative judgments require validation against structured evidence and human ratings. Enrich and deduplicate evidence, then validate a new rubric with human raters.
- **Coverage and uncertainty:** the saved development run covers only five matched scenarios, with one episode per model at each difficulty level. Complete matched coverage, repeat trials, and report uncertainty before making ranking claims.
- **Version drift:** supplied scenarios and traces predate subsequent semantic changes. Regenerate oracle references and rerun all compared policies under the same manifest.
- **Learning and cost control:** no cross-episode learning or within-episode coaching adaptation is implemented. Add explicit API spending caps before expanding live runs.

The strongest evidence of engineering judgment here is the combination of a runnable system, explicit contracts, inspectable failures, and bounded claims. An interviewer can challenge a design choice, inspect its implementation, and run the corresponding regression test.
