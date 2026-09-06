import json
import time

import httpx
import pytest

from execbench.llm.client import LLMClient
from execbench.policies.llm_policy import LLMPolicy
from execbench.runner.leaderboard import leaderboard
from execbench.runner.run_benchmark import run_benchmark
from execbench.runner.run_episode import run_episode
from execbench.schemas import tool_schemas


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_single_tool_request_and_cache(monkeypatch, tmp_path, provider):
    requests = []

    def post(url, **kwargs):
        requests.append(kwargs["json"])
        return httpx.Response(200, json=(
            {"content": [{"type": "text", "text": "ok"}]}
            if provider == "anthropic" else {"choices": [{"message": {"content": "ok"}}]}
        ))

    monkeypatch.setattr(httpx, "post", post)
    client = LLMClient("model", provider=provider, api_key="test", cache_dir=tmp_path)
    messages = [{"role": "user", "content": "go"}]
    client.complete(messages)
    result = client.complete(messages, tools=tool_schemas())
    assert client.complete(messages, tools=tool_schemas())["cached"]
    assert len(requests) == 2
    assert "tool_choice" not in requests[0]
    assert "parallel_tool_calls" not in requests[0]
    if provider == "anthropic":
        assert requests[1]["tool_choice"] == {"type": "any", "disable_parallel_tool_use": True}
        assert "parallel_tool_calls" not in requests[1]
    else:
        assert requests[1]["tool_choice"] == "required"
        assert requests[1]["parallel_tool_calls"] is False
    saved = json.loads((tmp_path / f"{result['cache_key']}.json").read_text())
    assert saved["request"]["request"] == requests[1]


@pytest.mark.parametrize("rejected, error", [
    ([{"name": "ship", "args": {}}, {"name": "wait", "args": {}}], "returned 2 tool calls"),
    ([], "returned 0 tool calls"),
    ([{"name": "audit", "args": {"task_id": "task_0"}}],
     "audit: missing arguments ['ic_id']; unexpected arguments ['task_id']"),
    ([{"name": "audit", "args": {"ic_id": 5}}], "audit.ic_id: expected string"),
    ([{"name": "audit", "args": "not JSON"}], "args"),
    ([{"name": "unknown", "args": {}}], "name"),
    ([{"name": "feed_back", "args": {"ic_id": "ic_0", "text": "Improve"}}], "name"),
    ([{"name": "assign", "args": {
        "ic_id": "ic_a", "task_id": "task_0", "spec_detail": 12, "spec_flags": [],
    }}], "assign.spec_detail: expected an integer from 0 to 3"),
])
def test_rejected_calls_recover_without_advancing_or_executing(scenario, rejected, error):
    class RecoveringClient:
        def __init__(self):
            self.calls = []

        def complete(self, messages, **kwargs):
            calls = rejected if not self.calls else [{"name": "ship", "args": {}}]
            result = {"tool_calls": calls, "text": "proposal", "messages": messages}
            self.calls.append(result)
            return result

    client = RecoveringClient()
    trace = run_episode(scenario, LLMPolicy(client), grade=False)
    assert len(client.calls) == 2
    assert len(client.calls[0]["messages"]) == 2  # Retry must not mutate earlier trace requests.
    feedback = client.calls[1]["messages"][-1]["content"]
    assert error in feedback
    assert "No tool calls were executed" in feedback
    assert "simulation has not advanced" in feedback
    assert len(trace.steps) == 2
    assert trace.steps[-1].action.name == "ship"
    assert trace.steps[-1].observation.tick == 0
    assert len(trace.steps[-1].llm_calls) == 2


def test_repeated_batches_still_fail_atomically(scenario):
    class BatchClient:
        def __init__(self):
            self.calls = []

        def complete(self, *args, **kwargs):
            result = {"tool_calls": [{"name": "ship", "args": {}}] * 2, "text": ""}
            self.calls.append(result)
            return result

    client = BatchClient()
    scenario.budgets.max_ticks = 1
    trace = run_episode(scenario, LLMPolicy(client))
    assert len(client.calls) == 3 * (len(trace.steps) - 1)
    assert all(step.action.name == "wait" for step in trace.steps[1:])
    assert trace.scores["parse_forced_wait_rate"] == 1


def test_openai_cache_redaction_usage_and_tool_parsing(monkeypatch, tmp_path):
    requests = []

    def post(url, **kwargs):
        requests.append((url, kwargs))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [{"function": {"name": "wait", "arguments": "{}"}}],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            },
        )

    monkeypatch.setattr(httpx, "post", post)
    a = LLMClient(
        "model", api_key="private-secret-sentinel", cache_dir=tmp_path, input_price=1, output_price=2
    )
    result = a.complete([{"role": "user", "content": "hello"}])
    assert result["tool_calls"] == [{"name": "wait", "args": {}}]
    assert result["cost_usd"] == pytest.approx(18e-6)
    b = LLMClient("model", cache_dir=tmp_path)
    assert b.complete([{"role": "user", "content": "hello"}])["cached"]
    assert len(requests) == 1
    assert "private-secret-sentinel" not in json.dumps(a.calls)
    assert "private-secret-sentinel" not in next(tmp_path.glob("*.json")).read_text()


def test_reasoning_effort_set_for_reasoning_models_only(monkeypatch, tmp_path):
    requests = []

    def post(url, **kwargs):
        requests.append(kwargs["json"])
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}], "usage": {}},
        )

    monkeypatch.setattr(httpx, "post", post)
    kwargs = {"api_key": "test", "cache_dir": tmp_path, "base_url": "https://api.openai.com/v1"}
    LLMClient("gpt-5", **kwargs).complete([{"role": "user", "content": "go"}])
    LLMClient("gpt-4o", **kwargs).complete([{"role": "user", "content": "go"}])
    assert requests[0]["reasoning_effort"] == "minimal"
    assert "reasoning_effort" not in requests[1]
    # Reasoning models reject max_tokens and temperature=0; non-reasoning models still take both.
    assert requests[0]["max_completion_tokens"] == 2048
    assert "max_tokens" not in requests[0]
    assert "temperature" not in requests[0]
    assert requests[1]["max_tokens"] == 2048
    assert requests[1]["temperature"] == 0


def test_lowest_reasoning_effort_matches_the_model_family():
    from execbench.llm.client import reasoning_effort_for

    # The gpt-5 family takes "minimal" and 400s on "none"; gpt-5.1+ is the reverse.
    for model in ("gpt-5", "gpt-5-nano", "gpt-5-mini", "gpt-5-2025-08-07", "gpt-5-nano-2025-08-07"):
        assert reasoning_effort_for(model) == "minimal", model
    for model in ("gpt-5.1", "gpt-5.2", "gpt-5.4-nano", "gpt-5.4-nano-2026-03-17", "gpt-5.5"):
        assert reasoning_effort_for(model) == "none", model


def test_anthropic_adapter(monkeypatch, tmp_path):
    def post(url, **kwargs):
        assert url.endswith("/messages")
        assert kwargs["json"]["system"] == "system"
        assert kwargs["json"]["messages"] == [{"role": "user", "content": "go"}]
        assert kwargs["headers"]["x-api-key"] == "test"
        return httpx.Response(
            200,
            json={
                "content": [{"type": "tool_use", "name": "ship", "input": {}}],
                "usage": {"input_tokens": 2, "output_tokens": 3},
            },
        )

    monkeypatch.setattr(httpx, "post", post)
    client = LLMClient("claude-test", provider="anthropic", api_key="test", cache_dir=tmp_path)
    result = client.complete([{"role": "system", "content": "system"}, {"role": "user", "content": "go"}])
    assert result["tool_calls"][0]["name"] == "ship"


def test_http_failure_does_not_expose_body(monkeypatch, tmp_path):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(401, text="private-secret-sentinel"))
    client = LLMClient("model", api_key="test", cache_dir=tmp_path)
    with pytest.raises(RuntimeError, match="HTTP 401") as error:
        client.complete([{"role": "user", "content": "go"}])
    assert "sentinel" not in str(error.value)


def test_model_parse_retry_then_forced_wait(scenario):
    class BrokenClient:
        def __init__(self):
            self.calls = []

        def complete(self, *a, **kw):
            response = {"tool_calls": [{"name": "assign", "args": {"spec_detail": 12}}], "text": ""}
            self.calls.append(response)
            return response

    client = BrokenClient()
    policy = LLMPolicy(client)
    scenario.budgets.max_ticks = 1
    trace = run_episode(scenario, policy)
    assert len(client.calls) == 6
    assert all("three invalid model responses; forced wait" in s.observation.errors for s in trace.steps[1:])
    assert trace.scores["parse_forced_wait_rate"] == 1


def test_no_persona_hints_in_executive_prompt():
    from execbench.llm.client import prompt

    system = prompt("exec_system.md").lower()
    for forbidden in ["sandbagger", "overconfident", "metric_gamer", "silent_blocker", "scoring", "regret"]:
        assert forbidden not in system


def test_benchmark_resume_and_manifest(scenario, tmp_path):
    source = tmp_path / "scenarios"
    source.mkdir()
    (source / "one.json").write_text(scenario.model_dump_json())
    out = tmp_path / "results"
    rows = run_benchmark(source, ["oracle", "trust_all"], out, workers=2)
    assert len(rows) == 2 and all(r["status"] == "ok" for r in rows)
    assert run_benchmark(source, ["oracle", "trust_all"], out, workers=2) == rows
    board = leaderboard(out)
    assert len(board) == 4
    assert (out / "leaderboard.md").exists()
    with pytest.raises(ValueError, match="different run"):
        run_benchmark(source, ["heuristic"], out)


def test_z_ai_thinking_flag_skipped_for_forced_reasoning_models(monkeypatch, tmp_path):
    """GLM-5.3 rejects any `thinking` object (HTTP 400, code 1210); it wants reasoning_effort."""
    requests = []

    def post(url, **kwargs):
        requests.append(kwargs["json"])
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {}})

    monkeypatch.setattr(httpx, "post", post)
    kwargs = {"api_key": "test", "cache_dir": tmp_path, "base_url": "https://api.z.ai/api/paas/v4"}
    # Mixed case, because Z.ai matches model ids case-insensitively.
    LLMClient("GLM-5.3-Flash", **kwargs).complete([{"role": "user", "content": "go"}])
    LLMClient("glm-4.5-flash", **kwargs).complete([{"role": "user", "content": "go"}])
    assert "thinking" not in requests[0]
    assert requests[0]["reasoning_effort"] == "low"
    assert requests[1]["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in requests[1]


def test_provider_error_code_is_surfaced_without_the_body(monkeypatch, tmp_path):
    def post(*args, **kwargs):
        return httpx.Response(400, json={"error": {"code": "1210", "message": "secret-sentinel"}})

    monkeypatch.setattr(httpx, "post", post)
    client = LLMClient("glm-5.3-flash", api_key="test", cache_dir=tmp_path)
    with pytest.raises(RuntimeError, match="HTTP 400, provider code 1210") as excinfo:
        client.complete([{"role": "user", "content": "go"}])
    assert "secret-sentinel" not in str(excinfo.value)


def test_underscored_provider_error_code_is_surfaced(monkeypatch, tmp_path):
    """OpenAI spells codes with underscores; they must survive the redaction filter."""
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded"}})

    monkeypatch.setattr(httpx, "post", post)
    client = LLMClient("gpt-5-nano", api_key="test", cache_dir=tmp_path)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    with pytest.raises(RuntimeError, match="HTTP 429, provider code rate_limit_exceeded"):
        client.complete([{"role": "user", "content": "go"}])
    assert len(calls) == 3


def test_malformed_provider_error_code_is_dropped(monkeypatch, tmp_path):
    def post(*args, **kwargs):
        return httpx.Response(400, json={"error": {"code": "leaked body: " + "x" * 500}})

    monkeypatch.setattr(httpx, "post", post)
    client = LLMClient("model", api_key="test", cache_dir=tmp_path)
    with pytest.raises(RuntimeError, match=r"HTTP 400 \(model\)\.") as excinfo:
        client.complete([{"role": "user", "content": "go"}])
    assert "leaked" not in str(excinfo.value)


def test_balance_failure_is_not_retried(monkeypatch, tmp_path):
    from execbench.llm.client import LLMBalanceError

    requests = []

    def post(*args, **kwargs):
        requests.append(1)
        return httpx.Response(429, json={"error": {"code": "1113", "message": "Insufficient balance"}})

    monkeypatch.setattr(httpx, "post", post)
    client = LLMClient("model", api_key="test", cache_dir=tmp_path)
    with pytest.raises(LLMBalanceError, match="1113"):
        client.complete([{"role": "user", "content": "go"}])
    assert len(requests) == 1


def test_benchmark_stops_queued_work_on_empty_balance(scenario, tmp_path, monkeypatch):
    import importlib

    from execbench.llm.client import LLMBalanceError

    module = importlib.import_module("execbench.runner.run_benchmark")
    source = tmp_path / "scenarios"
    source.mkdir()
    for i in range(20):
        s = scenario.model_copy(update={"scenario_id": f"s{i}"})
        (source / f"{i:02}.json").write_text(s.model_dump_json())

    def fail(*args, **kwargs):
        raise LLMBalanceError("Provider balance exhausted")

    monkeypatch.setattr(module, "run_episode", fail)
    out = tmp_path / "results"
    rows = run_benchmark(source, ["model"], out, workers=1)
    assert len(rows) < 20
    assert all(r["error_kind"] == "account_balance" for r in rows)
    assert json.loads((out / "run_status.json").read_text())["status"] == "blocked_account_balance"


def test_grader_model_default_and_opt_out(monkeypatch):
    from execbench.llm.client import DEFAULT_GRADER_MODEL, build_grader_client, resolve_grader_model

    monkeypatch.delenv("EXECBENCH_GRADER_MODEL", raising=False)
    assert resolve_grader_model(None) == DEFAULT_GRADER_MODEL == "glm-4.7-flash"
    assert resolve_grader_model("glm-4.7") == "glm-4.7"
    assert resolve_grader_model("none") is None
    assert resolve_grader_model("") is None
    monkeypatch.setenv("EXECBENCH_GRADER_MODEL", "glm-5")
    assert resolve_grader_model(None) == "glm-5"
    monkeypatch.setenv("EXECBENCH_GRADER_MODEL", "none")
    assert resolve_grader_model(None) is None
    assert build_grader_client(None) is None
