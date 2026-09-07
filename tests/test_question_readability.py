import json

import pytest
from test_environment import act

from execbench.env.env import ExecEnv
from execbench.graders.scorecard import score
from execbench.runner.run_episode import run_episode


class Judge:
    model = "test-grader"

    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = []

    def json(self, messages):
        self.calls.append({"request": messages, "usage": {"input_tokens": 10, "output_tokens": 5},
                           "cost_usd": 0.01, "cached": False})
        return self.verdict


@pytest.mark.parametrize("readable", [True, False])
def test_readability_gates_information_and_charges_patience(scenario, readable):
    client = Judge({"readable": readable, "reason": "test verdict"})
    e = ExecEnv(scenario, grader_client=client)
    question = "Which mobile platforms must we support?"
    result = act(e, "ask_human", human_id="pm", task_id="t0", question=question)
    assert bool(result.action_result["constraints"]) is readable
    assert bool(e.revealed) is readable
    assert e.patience["pm"] == 4
    assert json.loads(client.calls[0]["request"][1]["content"]) == {"question": question}
    act(e, "ship")
    trace = e.trace()
    assert trace.grading["question_readability"]["judgments"][0]["readable"] is readable
    score(trace, scenario, client)
    assert trace.scores["grader_input_tokens"] == 10
    assert trace.scores["grader_cost_usd"] == 0.01


def test_rejected_question_does_not_reveal_priorities(scenario):
    client = Judge({"readable": False, "reason": "keyword stuffing"})
    e = ExecEnv(scenario, grader_client=client)
    result = act(e, "ask_human", human_id="pm", task_id="t0",
                 question="mobile users risks priority success metric")
    assert result.action_result["question_rejected"]
    assert "Current task priorities" not in result.action_result["answer"]


def test_no_judge_calls_for_invalid_target_or_insufficient_patience(scenario):
    client = Judge({"readable": True, "reason": "readable"})
    e = ExecEnv(scenario, grader_client=client)
    act(e, "ask_human", human_id="pm", task_id="bad", question="mobile")
    e.patience["pm"] = 0
    act(e, "ask_human", human_id="pm", task_id="t0", question="mobile")
    assert not client.calls


@pytest.mark.parametrize("verdict", [{}, {"readable": "false", "reason": "bad boolean"}])
def test_invalid_judge_response_stops_episode(scenario, verdict):
    e = ExecEnv(scenario, grader_client=Judge(verdict))
    with pytest.raises(RuntimeError, match="Invalid question-readability"):
        act(e, "ask_human", human_id="pm", task_id="t0", question="mobile")
    assert not e.revealed


def test_runner_uses_grader_for_online_check_even_without_final_grading(scenario):
    client = Judge({"readable": True, "reason": "readable"})
    trace = run_episode(scenario, "heuristic", grade=False, grader_client=client)
    assert client.calls
    assert trace.grading["question_readability"]["mode"] == "llm"
    unchecked = run_episode(scenario, "heuristic", grade=False)
    assert unchecked.grading["question_readability"]["mode"] == "unchecked"
