# ExecBench — Evaluating the decisions behind delegated work

**Can an AI agent deliver a project when worker updates are unreliable, requirements are incomplete, and verification consumes the same budget as execution?**

ExecBench turns that question into a runnable evaluation environment. An executive agent delegates to simulated workers, asks stakeholders for requirements, audits progress, handles incidents, and decides when to ship. The simulator retains hidden ground truth, so a convincing status report can be compared with what actually happened.

This is a portfolio walkthrough of the problem framing, implementation choices, tools, validation, and limits. For the full interface and configuration reference, see the [technical README](README.md).

## Start here: a five-minute review

1. Open the [stale-trust trace](demo/stale-trust.html): compare Alex's reported progress with the hidden outcome. Download and open the HTML locally; it works offline.
2. Compare the [heuristic verification trace](demo/verification.html) and [audit-cost trace](demo/audit-cost.html) for the same scenario. Detecting a problem and delivering a good outcome are different achievements.
3. Read the [baseline leaderboard](demo/leaderboard.md), then the [partial live-run report](demo/live-resumed/REPORT.md) for coverage, matched comparisons, and failure accounting.
4. Inspect [the action and data contracts](execbench/schemas.py), [observation construction](execbench/env/observations.py), and [regression tests](tests/test_environment.py).

The repository includes 50 fixed-seed scenarios, five scripted policies, 250 historical baseline results, and selected interactive traces. Bundled results are historical snapshots; later changes to action costs, prompts, and question handling require fresh evaluation.

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

Historical live evidence is more limited: the [September 5 report](demo/live-resumed/REPORT.md) records 208/350 completed episodes, including 76 executive-model episodes, before API balance depletion. Its 15-scenario matched comparison reports normalized outcome of 0.894 for GLM-5, 0.816 for GLM-5.1, and 0.793 for GLM-4.7. These are descriptive results from an incomplete, within-provider run, not a current model ranking or a result reproduced by this documentation update.

## Limitations and next steps

- **External validity:** simulated worker behavior does not establish real-world management capability. Add document/repository workers and test whether the observed behaviors transfer.
- **Judge validity:** synthetic acceptance checks passed, but live reports exposed missing truth context and overlapping omission judgments. [The grading notes](demo/live-resumed/GRADING_NOTES.md) preserve those failures. Enrich and deduplicate evidence, then validate a new rubric with human raters.
- **Coverage and uncertainty:** live coverage is incomplete and unequal, with no completed difficulty-5 results in the recorded run. Complete matched coverage, repeat trials, and report uncertainty before making ranking claims.
- **Version drift:** supplied scenarios and traces predate subsequent semantic changes. Regenerate oracle references and rerun all compared policies under the same manifest.
- **Learning and cost control:** no cross-episode learning or within-episode coaching adaptation is implemented. Add explicit API spending caps before expanding live runs.

The strongest evidence of engineering judgment here is the combination of a runnable system, explicit contracts, inspectable failures, and bounded claims. An interviewer can challenge a design choice, inspect its implementation, and run the corresponding regression test.
