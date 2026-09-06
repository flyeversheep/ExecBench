import json

import httpx
import pytest

from execbench.llm.client import LLMClient
from execbench.policies.llm_policy import LLMPolicy
from execbench.runner.leaderboard import leaderboard
from execbench.runner.run_benchmark import run_benchmark
from execbench.runner.run_episode import run_episode


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
