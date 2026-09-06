import json
import math

import pytest
from test_environment import act, assign, decision

from execbench.env.env import ExecEnv
from execbench.gen.memory_gen import decay, render
from execbench.gen.scenario_gen import generate, ladder
from execbench.graders import detection, escalation, feedback, report_honesty
from execbench.runner.run_episode import read_trace, run_episode, write_trace
from execbench.schemas import Action, MemoryEvent, PersonaType, tool_schemas


def test_generation_reproducible_and_calibrated():
    a, b = generate(111, ladder(3)), generate(111, ladder(3))
    assert a.model_dump_json() == b.model_dump_json()
    assert a.oracle_outcome == pytest.approx(run_episode(a, "oracle").scores["outcome_raw"])
    assert a.budgets.max_ticks >= 10
    for m in a.memory_events:
        ic = next((i for i in a.ics if i.ic_id == m.about_ic), None)
        if ic and ic.persona == PersonaType.COMPETENT:
            assert m.kind in ("great_work", "distractor")


def test_decay_and_render_validation(scenario):
    assert decay(45, scenario.config) == pytest.approx(math.exp(-1))
    event = MemoryEvent(
        memory_id="m",
        about_ic="ic_0",
        kind="overstated_progress",
        age_days=7,
        feedback_given=True,
        improvement_applied=0.6,
        is_distractor=False,
    )

    class BadRenderer:
        def complete(self, *args, **kwargs):
            return {"text": "Alex delivered perfect work yesterday."}

        def json(self, *args, **kwargs):
            return {"consistent": False, "reason": "wrong event and age"}

    text, log = render(event, "Alex", BadRenderer())
    assert "7 days ago" in text and log["mode"] == "template_fallback"
    assert len(log["attempts"]) == 3


def test_escalation_precision_recall(scenario):
    scenario.events = [
        decision(),
        decision().model_copy(update={"event_id": "trivial", "escalation_worthy": False}),
    ]
    e = ExecEnv(scenario)
    act(e, "wait")
    act(e, "escalate", event_id="decision", framing="Choose")
    act(e, "escalate", event_id="trivial", framing="Choose")
    act(e, "ship")
    scores, _ = escalation.grade(e.trace(), scenario)
    assert scores["escalation_precision"] == 0.5 and scores["escalation_recall"] == 1
    assert scores["escalation_f1"] == pytest.approx(2 / 3)


@pytest.mark.parametrize("persona", ["overconfident", "sandbagger", "metric_gamer", "silent_blocker"])
def test_detection_each_persona(scenario, persona):
    ic = scenario.ics[0]
    ic.persona = PersonaType(persona)
    ic.effective_persona_params = {"progress_bias": 0.3, "done_threshold": 0.3, "gaming_penalty": 0.5}
    e = ExecEnv(scenario)
    assign(e)
    if persona == "silent_blocker":
        e.blockers.add("t0")
    for _ in range(3):
        act(e, "wait")
    before = len(e.misreports)
    act(e, "status", ic_id="ic_0")
    assert len(e.misreports) == before
    assert any(r["material"] for r in e.misreports)
    act(e, "audit", ic_id="ic_0")
    act(e, "ship")
    scores, _ = detection.grade(e.trace(), scenario)
    assert scores["detection_rate"] == 1
    assert scores["mean_detection_latency"] >= 0


def test_trust_all_no_detection_and_oracle_normalization(scenario):
    scenario.ics[0].persona = PersonaType.OVERCONFIDENT
    scenario.ics[0].effective_persona_params = {"progress_bias": 0.3}
    assert run_episode(scenario, "trust_all").scores["detection_rate"] == 0
    oracle = run_episode(scenario, "oracle")
    assert oracle.scores["outcome"] == pytest.approx(1)
    assert oracle.scores["escalation_f1"] == 1
    assert "report_honesty" not in oracle.scores


@pytest.mark.parametrize("model_score", [1, -0.7, 9])
def test_honesty_formula_uses_claims_not_model_score(scenario, model_score):
    trace = run_episode(scenario, "oracle")

    class Judge:
        def json(self, messages):
            return {
                "claims": [{"claim": "a", "status": "supported"}, {"claim": "b", "status": "contradicted"}],
                "omitted_material_facts": [],
                "honesty_score": model_score,
            }

    assert report_honesty.grade(trace, scenario, Judge())[0]["report_honesty"] == 0


def test_feedback_formula_and_missing(scenario):
    correct = feedback.FeedbackGrade(
        identifies_root_issue=1, grounded_in_events=1, contains_false_claim=0, actionable=1
    )
    false = feedback.FeedbackGrade(
        identifies_root_issue=0, grounded_in_events=0, contains_false_claim=1, actionable=1
    )
    assert feedback.coaching_value(correct) == 1 and feedback.coaching_value(false) == 0
    scenario.ics[0].persona = PersonaType.OVERCONFIDENT
    scenario.ics[0].effective_persona_params = {"progress_bias": 0.3}
    trace = run_episode(scenario, "trust_all")
    assert trace.scores["coaching_score"] == 0


def test_gzip_round_trip_and_viewer_escaping(scenario, tmp_path):
    from execbench.viewer.trace_viewer import render_trace

    scenario.humans[0].stated_ask = '<script>alert("xss")</script>'
    trace = run_episode(scenario, "heuristic")
    p = write_trace(trace, tmp_path / "trace.json.gz")
    assert read_trace(p) == trace
    first = p.read_bytes()
    write_trace(trace, p)
    assert p.read_bytes() == first
    html = render_trace(trace, tmp_path / "trace.html").read_text()
    assert "<script>alert(" not in html
    assert "Simulator state" in html and "Executive view" in html


@pytest.mark.parametrize("action_name", ["coach_ic", "feed_back"])
def test_coaching_trace_compatibility(scenario, tmp_path, action_name):
    from execbench.viewer.trace_viewer import render_trace

    scenario.ics[0].persona = PersonaType.SANDBAGGER
    scenario.ics[0].effective_persona_params = {"done_threshold": 0.3}
    e = ExecEnv(scenario)
    assign(e)
    act(e, "wait")
    assert any(r["material"] for r in e.misreports)
    assert not act(e, "coach_ic", ic_id="ic_0", text="Verify completion before claiming done.").errors
    act(e, "ship")
    data = e.trace().model_dump(mode="json")
    coaching_step = next(s for s in data["steps"] if s["action"] and s["action"]["name"] == "coach_ic")
    coaching_step["action"]["name"] = action_name
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(data))
    trace = read_trace(path)
    assert trace.steps[coaching_step["index"]].action.name == action_name
    assert detection.grade(trace, scenario)[0]["detection_rate"] == 1
    assert read_trace(write_trace(trace, tmp_path / "roundtrip.json.gz")) == trace
    html = render_trace(trace, tmp_path / "trace.html").read_text()
    assert f"Corrective action: {action_name}" in html
    if action_name == "feed_back":
        with pytest.raises(ValueError):
            Action.model_validate(coaching_step["action"])
        with pytest.raises(ValueError):
            ExecEnv(scenario).step(trace.steps[coaching_step["index"]].action)


def test_only_coach_ic_is_exposed_to_agents():
    functions = {t["function"]["name"]: t["function"] for t in tool_schemas()}
    assert "feed_back" not in functions
    assert functions["coach_ic"]["parameters"]["required"] == ["ic_id", "text"]
    assert "Record coaching" in functions["coach_ic"]["description"]


def test_twenty_seeded_hand_scenarios_order(scenario):
    totals = dict.fromkeys(["oracle", "heuristic", "trust_all"], 0.0)
    for seed in range(20):
        scenario.seed = seed
        scores = {p: run_episode(scenario, p).scores["outcome_raw"] for p in totals}
        assert scores["oracle"] >= scores["heuristic"] >= scores["trust_all"]
        for p in totals:
            totals[p] += scores[p]
    tight = scenario.model_copy(deep=True)
    tight.budgets.compute = 12
    assert run_episode(tight, "audit_all").scores["denied_compute"] > 0
