# ExecBench — Technical reference

**Reviewing this project for an interview?** Start with the [interviewer walkthrough](README.md) for the problem framing, design decisions, tool use, testing, and limitations.

**An evaluation environment for AI executive agents.** The model manages a project through simulated workers; it never implements the deliverables. Hidden worker behavior, stakeholder constraints, incidents, and priority changes provide structured ground truth for management decisions.

The L0 implementation runs locally. The current interview snapshot is [dev_v15](results/dev_v15/README.md): **10/10 completed model episodes**, comparing the recorded policies `gpt-5.6-luna` and `gpt-5.6-terra` on five matched scenarios, one per difficulty level, with Z.ai’s `GLM-5.3-Flash` as the grader. Review the [comparison viewer](results/dev_v15/luna_vs_terra.html), [leaderboard](results/dev_v15/leaderboard.md), and [failure analysis](README.md#failure-analysis-where-models-lose-credit). Download HTML files and open them locally; no API key is needed to inspect saved results.

The repository also includes the [full v1 scenario set](scenarios/v1) (50 scenarios), its [five-scenario development subset](scenarios/v1_dev), and five scripted policies. The v15 development run covers five scenarios, not a complete model comparison over all 50 v1 scenarios.

## Run locally

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --frozen --extra dev --python 3.12
uv run pytest -q
uv run execbench --help
uv run execbench run-episode --scenario scenarios/v1_dev/l2_01010.json \
  --policy heuristic --grader-model none --out traces
uv run execbench view traces/l2_01010__heuristic.json.gz --out trace.html
```

The quickstart explicitly disables the API grader. Nonempty narrative reports remain ungraded and the online question-readability check is skipped. For a five-policy offline run on the supplied development scenarios:

```sh
uv run execbench run-benchmark --scenario-set scenarios/v1_dev \
  --policies oracle,heuristic,trust_all,audit_all,random \
  --grader-model none --out results/offline-v1-dev
```

## Live LLM evaluation

The v15 demo uses `gpt-5.6-luna` and `gpt-5.6-terra` as policy models through OpenAI, with Z.ai’s `GLM-5.3-Flash` as the grader. Configure separate credentials and endpoints for the two roles. Supply credentials either way — export the keys directly, or point at 1Password secret references. Credentials are read into process memory only, and are never written into traces or caches.

```sh
# Option A — the API key directly in the environment
export EXECBENCH_API_KEY='your-openai-api-key'
export EXECBENCH_GRADER_API_KEY='your-zai-api-key'

# Option B — a 1Password secret reference, resolved at first use with `op read`
export EXECBENCH_API_KEY_REF='op://AI agents/OpenAI API/credential'
export EXECBENCH_GRADER_API_KEY_REF='op://AI agents/Z.ai API/credential'
```

Choose one credential method for each role and substitute your own keys or secret references. If both methods are set, the direct key wins. `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are also read for the matching provider, so an existing shell setup often needs no extra variable. For option B, install the [1Password CLI](https://developer.1password.com/docs/cli/get-started/), unlock the 1Password app, and enable/approve its CLI integration before running — otherwise `op read` fails or times out.

```sh
# Policy models: OpenAI
export EXECBENCH_PROVIDER='openai'
export EXECBENCH_BASE_URL='https://api.openai.com/v1'

# Grader: Z.ai, using the OpenAI-compatible adapter
export EXECBENCH_GRADER_PROVIDER='openai'
export EXECBENCH_GRADER_BASE_URL='https://api.z.ai/api/paas/v4'
export EXECBENCH_GRADER_MODEL='GLM-5.3-Flash'

uv run execbench check-api --model gpt-5.6-luna
uv run execbench check-api --model gpt-5.6-terra

# The validation script reads unprefixed settings; override them for this command.
EXECBENCH_PROVIDER="$EXECBENCH_GRADER_PROVIDER" \
EXECBENCH_BASE_URL="$EXECBENCH_GRADER_BASE_URL" \
EXECBENCH_API_KEY="${EXECBENCH_GRADER_API_KEY:-}" \
EXECBENCH_API_KEY_REF="${EXECBENCH_GRADER_API_KEY_REF:-}" \
OPENAI_API_KEY='' \
uv run python scripts/validate_live_graders.py --model "$EXECBENCH_GRADER_MODEL"

uv run execbench run-episode --scenario scenarios/v1_dev/l2_01010.json \
  --policy gpt-5.6-luna --grader-model GLM-5.3-Flash --out traces
uv run execbench run-benchmark --scenario-set scenarios/v1_dev \
  --policies gpt-5.6-luna,gpt-5.6-terra \
  --grader-model GLM-5.3-Flash --workers 6 --out results/live-v1-dev-new
uv run execbench leaderboard results/live-v1-dev-new
```

These are the model identifiers and endpoints recorded in the [v15 manifest](results/dev_v15/manifest.json); model access depends on your credentials. The benchmark command runs the same two policies on five scenarios (ten episodes) into a new directory. Scripted baselines can be added to `--policies` for a separate comparison. The policy comparison is between two GPT models; Z.ai supplies the shared grader.

Failed episodes are recorded and retried on resume; successful episodes are retained. An empty API balance stops queued work. Resume only with the original manifest-compatible code, scenarios, and settings. Use a new output directory after changes. Cached calls are reused only when their request keys match.

| Setting | Purpose |
|---|---|
| `EXECBENCH_API_KEY` | Direct environment credential; takes precedence over the reference |
| `EXECBENCH_API_KEY_REF` | Alternative to the above: a 1Password secret reference, resolved with `op read` (requires the 1Password CLI) |
| `EXECBENCH_PROVIDER` | `openai` for OpenAI-compatible HTTP, or `anthropic` |
| `EXECBENCH_BASE_URL` | Policy endpoint; defaults to Z.ai, or Anthropic for that provider. Set explicitly to `https://api.openai.com/v1` for the demo’s GPT policies |
| `EXECBENCH_GRADER_MODEL` | Default judge model when `--grader-model` is not given; defaults to `glm-4.7-flash`. Set either to `none` to score without an LLM |
| `EXECBENCH_GRADER_PROVIDER`, `EXECBENCH_GRADER_BASE_URL`, `EXECBENCH_GRADER_API_KEY`, `EXECBENCH_GRADER_API_KEY_REF` | Same meaning as the unprefixed settings, for both `--grader-model` and `--memory-model`; each falls back to its unprefixed counterpart when unset, so the grader can run against a different provider/credential than the policy model |
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

Policy requests send the initial observation once, then append the original assistant tool call
and its matching tool-result observation on each turn. Earlier messages remain unchanged between
history compactions, allowing provider prompt caches to reuse conversation prefixes. The existing
`EXECBENCH_HISTORY_CHARS` limit still measures serialized action/observation history: older complete
turns become a compact journal, which resets the prefix when it changes. Rejected proposals remain
text, and harness-forced waits are recorded separately from executed model tool calls. Use a new
results directory for this message format; the implementation hash prevents mixing it with old runs.

Token usage is always recorded. Dollar values are **estimates** based on explicitly configured prices; without prices, `llm_cost_known=0` and the leaderboard omits the dollar estimate. Provider cache discounts, tiered pricing, and taxes are not inferred. Local cache hits have zero additional API spend. Grader tokens and estimated spend are recorded separately. Configure prices for both the GPT policy models and the Z.ai grader using their respective provider pricing before reporting dollar estimates.

## Scenarios and reproducibility

```sh
uv run execbench generate --out scenarios/generated-review --count 50 --seed 1000 --config configs/default.yaml
# Optional natural-language memory rendering, with a second model validation and three-attempt fallback:
uv run execbench generate --out scenarios/llm-memory --count 50 --seed 1000 --memory-model GLM-5.3-Flash
```

The checked-in `scenarios/v1_dev` files are byte-identical selections from `scenarios/v1`: seeds 1000, 1010, 1020, 1030, and 1040. They match the scenario hashes and embedded scenarios in `results/dev_v15`. The folder name `v1` identifies this generated dataset, not a package release: the package and trace schema still use version `0.1.0`. The older `scenarios/v0` is retained for historical scenario provenance. Generate into a new directory to preserve these snapshots.

Six YAML templates cover rate limiting, recommendations, logging migration, data export, onboarding, and billing. Seeds 1000–1049 span five difficulty levels, ten per level. Generation runs the privileged reference once to estimate usage/deadline and again under the calibrated budget to record its outcome. Every scenario includes simulator constants, generation provenance, hidden memory events, and rendered memory.

The supplied set, including the v15 scenarios, uses deterministic memory templates. The optional command above uses `GLM-5.3-Flash` for memory rendering and validation; it is separate from the saved demo. `--memory-model` enables cached rendering and validation using the grader provider, endpoint, and credentials (`EXECBENCH_GRADER_*`, falling back to the unprefixed settings). The supplied model name selects the memory model independently of `EXECBENCH_GRADER_MODEL`; invalid rendering falls back to templates. Keep the generation cache alongside any LLM-rendered scenario set you distribute. Template generation makes no LLM calls and needs no cache files.

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
| Specification precision | Applicable flags / all flags across accepted assignments; undefined with no flags, and separate from requirement coverage |
| Efficiency | Compute, patience, ticks, action counts, token usage, configured cost estimates, and forced parse-failure waits |

The v15 demo explicitly uses Z.ai’s `GLM-5.3-Flash` for narrative grading and the online question-readability check. The package default remains `glm-4.7-flash`, so set `--grader-model` or `EXECBENCH_GRADER_MODEL` as shown above to match the demo. Pass `--grader-model none` (or set `EXECBENCH_GRADER_MODEL=none`) to run without a judge. With no grader model, nonempty reports and feedback requiring judgments are explicitly ungraded. Empty reports and missing coaching can be scored zero without an LLM. The leaderboard marks partial metric coverage as `[graded/episodes]`; JSON includes every metric's sample count. Baseline zeros do not imply that live grader acceptance has passed.

## Verification and remaining acceptance

The offline suite covers formulas, all six personas, dependencies, budgets, incident deadlines, default resolutions, drift, feedback, observation isolation, deterministic regeneration, escalation and detection, grading formulas, memory fallback, provider contracts, credential redaction, parse retries, resumable runs, and HTML escaping. Twenty seeded hand-authored scenarios satisfy oracle ≥ heuristic ≥ TrustAll; this is not asserted for every generated scenario.

Run `uv run pytest -q` and `uv run ruff check execbench tests scripts`. The viewer has also been inspected in a browser. `scripts/validate_live_graders.py` contains five report and five feedback acceptance examples. Narrative grading still requires human-rater validation. The separately saved v15 run completed all ten planned episodes, including difficulty 5, but does not cover the full 50-scenario set. On September 9, 2026, the current offline suite passed all **95 tests**, and Ruff passed (Python 3.13.15, frozen dependencies).

L1 document workers, L2 repository workers, persona adaptation to episode feedback, cross-episode learning, and human-rater validation remain outside v0.1.

`ask_human(human_id, task_id, question)` reveals only keyword-matched constraints owned by that human and required by the specified task. Discovered tags may be reused on other applicable tasks. Questions cost one patience per 20 whitespace-delimited words, rounded up (minimum one), replacing the duplicate-question surcharge. If the cost exceeds remaining patience, the balance is exhausted and the answer is minimal. Unknown task IDs are rejected without spending patience.

When a grader LLM is configured, ask_human questions must pass its readability check before any information is revealed. Ask coherent, natural questions; keyword stuffing or instructions to manipulate the judge are rejected and still consume the normal word-based patience cost. Readable multi-part questions are allowed. Runs without a grader skip this check and are marked unchecked in trace.grading.question_readability.

Assignment flag cost: `SimConfig.spec_flag_cost` (default 0.25 compute, nonnegative) is charged for every distinct flag in each accepted assignment, in addition to specification detail. The public observation exposes `costs.per_spec_flag`. Duplicate flags are stored and charged once. Charges do not depend on hidden relevance. Reassigning an existing work item does not reapply this charge; cancelling and assigning again does.

The end-of-episode `specification_precision` diagnostic is the number of applicable flags divided by all flags across accepted assignments, deduplicated within each assignment. Cancelled/replaced assignments remain included; rejected assignments are excluded. `specification_flag_count` and `specification_relevant_flag_count` report the denominator and numerator. With no flags, precision is undefined and omitted. This metric is separate from outcome; flag costs affect outcome through the compute budget. Regenerate scenarios with stored oracle outcomes and rerun benchmarks when comparing under the new cost semantics.
