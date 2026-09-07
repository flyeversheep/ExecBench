# ExecBench

**An evaluation environment for AI executive agents.** The model manages a project through simulated workers; it never implements the deliverables. Hidden worker behavior, stakeholder constraints, incidents, and priority changes provide structured ground truth for management decisions.

The L0 implementation runs locally. The repository includes **50 fixed-seed scenarios, five scripted policies, 250 baseline results, and three standalone trace viewers**. Live API access now works and all live grader acceptance checks passed. The [resumed live run report](demo/live-resumed/REPORT.md) records **76 model episodes and 132 live-graded baseline episodes** completed before Z.ai again reported insufficient balance (code 1113). The run is stopped at 208/350 episodes. Matched-scenario comparisons and cumulative API cost estimates are available; full 50-scenario coverage remains pending.

Start with [the stale-trust trace](demo/stale-trust.html), [the verification trace](demo/verification.html), and [the leaderboard](demo/leaderboard.md). HTML files work offline; download/open them locally if your Git host displays their source.

## Run locally

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --extra dev --python 3.12
uv run pytest -q
uv run execbench --help
uv run execbench run-episode --scenario scenarios/v0/l2_01010.json --policy heuristic --out traces
uv run execbench view traces/l2_01010__heuristic.json.gz --out trace.html
```

Rebuild the complete baseline demo:

```sh
uv run python scripts/make_demo.py
```

This writes full traces under a directory named for the implementation hash in `results/`, and copies summary results and three selected traces to `demo/`. No API access is needed. Run from the repository root.

## Live LLM evaluation

Supply a credential either way — export the key directly, or point at a 1Password secret reference. Credentials are read into process memory only, and are never written into traces or caches.

```sh
# Option A — the API key directly in the environment
export EXECBENCH_API_KEY='your-api-key'

# Option B — a 1Password secret reference, resolved at first use with `op read`
export EXECBENCH_API_KEY_REF='op://AI agents/Z.ai API/credential'
```

Either one is enough; pick whichever fits your setup. If both are set, the direct key wins. `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are also read for the matching provider, so an existing shell setup often needs no extra variable. For option B, install the [1Password CLI](https://developer.1password.com/docs/cli/get-started/), unlock the 1Password app, and enable/approve its CLI integration before running — otherwise `op read` fails or times out.

```sh
export EXECBENCH_BASE_URL='https://api.z.ai/api/paas/v4'
uv run execbench check-api --model glm-4.7
uv run python scripts/validate_live_graders.py --model glm-4.7
uv run execbench run-episode --scenario scenarios/v0/l2_01010.json \
  --policy glm-4.7 --grader-model glm-4.7 --out traces
uv run execbench run-benchmark --scenario-set scenarios/v0 \
  --policies oracle,heuristic,trust_all,audit_all,glm-5.1,glm-5,glm-4.7 \
  --grader-model glm-4.7 --workers 6 --out results/live-demo-resumed
uv run execbench leaderboard results/live-demo
```

Model access depends on the credential's entitlement. These model names and the general API endpoint are documented by [Z.ai](https://docs.z.ai/api-reference/llm/chat-completion). A coding-plan credential may require a different configured base URL. Three Z.ai models are a within-provider comparison, not evidence about multiple model vendors.

Alternatively, `scripts/run_live_demo.py` performs API preflights, validates the frozen grader, and runs the model/baseline benchmark. Failed episodes are recorded and retried when the same command is resumed; successful episodes are retained. An empty API balance stops queued work. For this checkout, use `--out results/live-demo-resumed`: the original run remains in `results/live-demo` with its original implementation manifest, and cached calls will be reused by the updated client. Calls already in the cache are replayed without a new request.

| Setting | Purpose |
|---|---|
| `EXECBENCH_API_KEY` | Direct environment credential; takes precedence over the reference |
| `EXECBENCH_API_KEY_REF` | Alternative to the above: a 1Password secret reference, resolved with `op read` (requires the 1Password CLI) |
| `EXECBENCH_PROVIDER` | `openai` for OpenAI-compatible HTTP, or `anthropic` |
| `EXECBENCH_BASE_URL` | Provider endpoint; defaults to Z.ai, or Anthropic for that provider |
| `EXECBENCH_GRADER_MODEL` | Default judge model when `--grader-model` is not given; defaults to `glm-4.7-flash`. Set either to `none` to score without an LLM |
| `EXECBENCH_GRADER_PROVIDER`, `EXECBENCH_GRADER_BASE_URL`, `EXECBENCH_GRADER_API_KEY`, `EXECBENCH_GRADER_API_KEY_REF` | Same meaning as the unprefixed settings, but for `--grader-model` only; each falls back to its unprefixed counterpart when unset, so the grader can run against a different provider/credential than the policy model |
| `EXECBENCH_CACHE_DIR` | Content-addressed cache, default `.cache/llm` |
| `EXECBENCH_HISTORY_CHARS` | Recent-history window, default 60,000 characters; older turns become a compact action/result journal |
| `EXECBENCH_PRICES_JSON` | Per-model input/output prices in USD per million tokens, e.g. `{"model":{"input":0.6,"output":2.2}}` |

The adapters use `httpx` directly, so provider SDKs are unnecessary. The Anthropic adapter uses its native [tool-use contract](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools).

Tool requests enforce the one-action-per-turn contract: OpenAI-compatible requests send
`tool_choice="required"` with `parallel_tool_calls=false`; Anthropic requests send
`tool_choice={"type":"any","disable_parallel_tool_use":true}`. Responses are still validated
locally in case a compatible endpoint ignores the setting. Rejected batches execute nothing;
retries include the call count or argument error and do not advance the simulation. After three
invalid responses, the existing forced-wait rule applies. These request settings are recorded in
traces and included in cache keys. Compare the corrected interface using a new results directory;
old benchmark results remain evidence of the previous interface.

Token usage is always recorded. Dollar values are **estimates** based on explicitly configured prices; without prices, `llm_cost_known=0` and the leaderboard omits the dollar estimate. Provider cache discounts, tiered pricing, and taxes are not inferred. Local cache hits have zero additional API spend. Grader tokens and estimated spend are recorded separately. Check [current provider pricing](https://docs.z.ai/guides/overview/pricing) before populating price settings.

## Scenarios and reproducibility

```sh
uv run execbench generate --out scenarios/v0 --count 50 --seed 1000 --config configs/default.yaml
# Optional natural-language memory rendering, with a second model validation and three-attempt fallback:
uv run execbench generate --out scenarios/llm-memory --count 50 --seed 1000 --memory-model glm-4.7
```

Six YAML templates cover rate limiting, recommendations, logging migration, data export, onboarding, and billing. Seeds 1000–1049 span five difficulty levels, ten per level. Generation runs the privileged reference once to estimate usage/deadline and again under the calibrated budget to record its outcome. Every scenario includes simulator constants, generation provenance, hidden memory events, and rendered memory.

The supplied set uses deterministic memory templates. `--memory-model` enables cached rendering and validation; invalid rendering falls back to templates. Keep the generation cache alongside any LLM-rendered scenario set you distribute. Template generation makes no LLM calls and needs no cache files.

All stochastic simulation uses NumPy generators derived from the scenario seed and a stable named stream. Work draws depend on task, IC, and tick, so extra status/audit calls cannot perturb the work RNG. Gzip traces have a fixed timestamp. Scenario regeneration is byte-identical under the locked dependencies; LLM behavior is reproducible with the same response cache. Accounting fields distinguish original calls from cache replays.

Resume manifests check scenario hashes, package and prompt hashes, provider settings, history settings, and pricing. A changed configuration requires a new output directory rather than silently mixing benchmark versions. Frozen grader prompts are `grade_report_v1.md` and `grade_feedback_v1.md`; changing their meaning requires a benchmark-version bump.

## Environment contract

`ExecEnv.reset()` and `ExecEnv.step(Action(...))` return an `Observation`. After termination, `ExecEnv.trace()` returns the full `EpisodeTrace`; this keeps the step return type stable. The runner attaches the scorecard and writes JSON or deterministic gzip.

The frozen action names are `read_policy_doc`, `ask_human`, `assign`, `status`, `audit`, `reassign`, `cancel`, `escalate`, `coach_ic`, `report`, `wait`, and `ship`. Argument schemas are generated from the single contract in `schemas.py`. `assign` supports optional `force=false`, as described in the plan's semantics. A maximum of 40 actions per tick prevents infinite free-action loops.

`coach_ic` records evidence-based IC coaching to identify weaknesses and improve future working or reporting practices. It is eligible after that IC has a claimed-done or cancelled task and is evaluated at episode end. It does not change task requirements, progress, quality, blockers, or IC behavior during the episode. Put task requirements in `assign.spec_flags`; feedback cannot update an existing assignment or request rework.

`coach_ic` replaces the former `feed_back` action. New policies must use `coach_ic`; `feed_back` is no longer executable or exposed to agents. Historical traces retain their original action names and remain readable, renderable, and gradable. Stored feedback records and coaching score names are unchanged.

Public models are constructed by explicit field copying. Hidden persona labels, competence, task size, exact quality, undisclosed flags, memory IDs, decision labels, and generation logs are never serialized into ordinary observations. The oracle is intentionally privileged. Audits disclose only the specified truthful progress, completion, quality estimate, and blocked state.

Interpretations needed to resolve underspecified behavior in the original plan:

- Claimed completion continues to consume work until true completion; early claims do not release a busy worker. Sandbagging applies its quality penalty once at the first claim.
- Blocked workers still consume compute while assigned. Insufficient funds reject paid actions and stop unaffordable work; balances never become negative. `denied_compute` records unmet spending requests.
- An external access blocker remains until reassignment. An audit detects it but does not repair it. Reassignment retains 70% of progress and clears the access blocker.
- Dependencies use a tick-start snapshot, preventing iteration order from advancing multiple dependency stages in one tick.
- Incident handling means assignment strictly before its deadline, as specified; completion is separate. Events that have not surfaced before an early shipment are outside that episode's scoring opportunities.
- A missing flag penalizes completed, shipped work once per constraint, irrespective of how many tasks violate it. Undelivered work already contributes zero quality.
- Feedback eligibility persists after an IC has claimed completion or had work cancelled. Episode feedback never changes behavior. Historical feedback attenuates existing distortion parameters; the most recent feedback supersedes older entries instead of stacking indefinitely.
- Status is automatically delivered on each work tick as well as on explicit requests. Misleadingness is sampled once per IC/task/tick, preventing free polling from inflating the calibration metric.
- No-opportunity escalation precision/recall are 1; detection/prior rates with no eligible ICs are 0. Undefined Spearman correlation is 0 with `verification_defined=0`. Counts are retained for interpretation.
- Random samples uniformly from a finite legal-action catalog, including forced assignments and templated text. There is no uniform distribution over arbitrary natural-language arguments.

The specified greedy oracle is an **empirical reference, not a mathematical upper bound**. It assigns the highest-competence free worker, knows requirements and blockers, and escalates exactly the worthy decisions. It can still make suboptimal scheduling choices. Normalized outcome can exceed 1 and regret can be negative; those results are preserved. A nonpositive reference uses denominator 1 and remains visible as `oracle_outcome`.

## Metrics

No composite score is produced.

| Metric | Ground truth / interpretation |
|---|---|
| Outcome, regret | Weighted completed quality minus requirement and incident penalties, relative to the same-scenario greedy reference |
| Escalation precision/recall/F1 | Unique surfaced decision IDs, escalation worthiness, and strict deadlines |
| Detection rate, latency | First material misleading observation to the first successful corrective action; latency averages only detected ICs |
| Verification calibration | Spearman correlation of per-IC audit counts and accumulated report divergence, with average tie ranks |
| Report honesty | Fixed LLM extracts supported/contradicted/unverifiable claims and material omissions; Python computes the formula |
| Coaching quality / false positives | Fixed LLM checks feedback against actual prior incidents; missed coaching scores zero |
| Prior utilization | Early audits within three ticks of first assignment for issue-memory ICs, compared with no-memory ICs |
| Stale trust | Never-audited ICs with decayed feedback at least 60 days old |
| Efficiency | Compute, patience, ticks, action counts, token usage, configured cost estimates, and forced parse-failure waits |

Grading defaults to `glm-4.7-flash`; pass `--grader-model none` (or set `EXECBENCH_GRADER_MODEL=none`) to run without a judge. With no grader model, nonempty reports and feedback requiring judgments are explicitly ungraded. Empty reports and missing coaching can be scored zero without an LLM. The leaderboard marks partial metric coverage as `[graded/episodes]`; JSON includes every metric's sample count. Baseline zeros do not imply that live grader acceptance has passed.

## Findings from the bundled baseline run

These are descriptive results for the supplied seeds, not claims about frontier models or causal effects of memory.

1. **Management errors are observable without executing real work.** In [the stale-trust trace, day 5](demo/stale-trust.html#step-9), Alex's proxy metric reaches 1.0 while completed work has quality about 0.17. TrustAll never audits Alex. The hidden truth and public worker updates appear side by side; the viewer also marks the missed stakeholder escalation.
2. **Verification has a resource tradeoff.** Across 50 scenarios, AuditAll uses about 99.3% of compute and achieves normalized outcome 0.372; the heuristic reaches 0.563, while TrustAll reaches 0.546 using about 60.2% of compute. In [the same-scenario audit trace](demo/audit-cost.html), audits alone consume about 63.3% of the budget. [The heuristic trace](demo/verification.html) detects the misleading worker but also nearly exhausts compute. These are policy profiles, not a universal ranking.
3. **A stale-trust failure is reproducible.** The [briefing](demo/stale-trust.html#step-0) says Alex received feedback 120 days earlier and improved at the time. His current gaming penalty has mostly returned. TrustAll's stale-trust score is 1.0 on this case; the heuristic audits Alex and scores 0.0. Recent adverse notes are also present, so this case demonstrates an ignored warning rather than proving that stale feedback caused the behavior.

Full per-difficulty results: [Markdown](demo/leaderboard.md), [JSON](demo/leaderboard.json), [episode scores](demo/scores.jsonl). The selected traces retain the complete structured scenario and grading evidence.

## Verification and remaining acceptance

The offline suite covers formulas, all six personas, dependencies, budgets, incident deadlines, default resolutions, drift, feedback, observation isolation, deterministic regeneration, escalation and detection, grading formulas, memory fallback, provider contracts, credential redaction, parse retries, resumable runs, and HTML escaping. Twenty seeded hand-authored scenarios satisfy oracle ≥ heuristic ≥ TrustAll; this is not asserted for every generated scenario.

Run `uv run pytest -q` and `uv run ruff check execbench tests scripts`. The viewer has also been inspected in a browser. `scripts/validate_live_graders.py` contains five report and five feedback acceptance examples. All five live grader acceptance checks passed, including honesty ordering and feedback ordering. The 76 completed live model episodes had zero parse-failure forced waits across 2,652 actions. Actual narrative grading has [documented limitations](demo/live-resumed/GRADING_NOTES.md), despite passing the synthetic checks. Full model completion across 50 scenarios and the complete 3-model leaderboard remain pending API credit. The latest offline suite has 40 passing tests, including non-retryable balance-error handling.

L1 document workers, L2 repository workers, persona adaptation to episode feedback, cross-episode learning, and human-rater validation remain outside v0.1.

`ask_human(human_id, task_id, question)` reveals only keyword-matched constraints owned by that human and required by the specified task. Discovered tags may be reused on other applicable tasks. Questions cost one patience per 20 whitespace-delimited words, rounded up (minimum one), replacing the duplicate-question surcharge. If the cost exceeds remaining patience, the balance is exhausted and the answer is minimal. Unknown task IDs are rejected without spending patience.

When a grader LLM is configured, ask_human questions must pass its readability check before any information is revealed. Ask coherent, natural questions; keyword stuffing or instructions to manipulate the judge are rejected and still consume the normal word-based patience cost. Readable multi-part questions are allowed. Runs without a grader skip this check and are marked unchecked in trace.grading.question_readability.
