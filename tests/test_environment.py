import json

import pytest

from execbench.env import dynamics
from execbench.env.env import ExecEnv
from execbench.graders.outcome import raw_outcome
from execbench.runner.run_episode import run_episode
from execbench.schemas import Action, DriftEvent, Event, EventKind, PersonaType, WorkItem


def act(env, name, **args):
    return env.step(Action(name=name, args=args))


def assign(env, task="t0", ic="ic_0", **extra):
    return act(env, "assign", ic_id=ic, task_id=task, spec_detail=3, spec_flags=["mobile_compat"], **extra)


def test_progress_quality_formula(scenario):
    e = ExecEnv(scenario)
    assign(e)
    act(e, "wait")
    assert e.work["t0"].progress == pytest.approx(1 * (0.6 + 0.4 * 0.8) * (1 - 0.5 * 0.2) / 2)
    act(e, "wait")
    act(e, "wait")
    assert e.work["t0"].true_quality == pytest.approx(0.35 + 0.45 * 0.8 + 0.08 * 3 - 0.30 * 0.2)
    assert e.work["t0"].status == "done_true"


@pytest.mark.parametrize("persona", list(PersonaType))
def test_persona_distortion(scenario, persona):
    ic = scenario.ics[0]
    ic.persona = persona
    ic.effective_persona_params = {"progress_bias": 0.3, "done_threshold": 0.6, "gaming_penalty": 0.4}
    w = WorkItem(task_id="t0", ic_id=ic.ic_id, spec_detail=3, spec_flags=[], progress=0.7)
    r = dynamics.report(ic, scenario.tasks[0], w, 2, scenario.config, dynamics.rng_for(1))
    if persona == PersonaType.OVERCONFIDENT:
        assert r["progress"] == 1 and r["claims_done"]
    elif persona == PersonaType.SANDBAGGER:
        assert r["claims_done"] and w.quality_multiplier == 0.6
    elif persona == PersonaType.METRIC_GAMER:
        assert r["metric"] > r["progress"]
        assert dynamics.quality(
            ic, scenario.tasks[0], w, scenario.config, dynamics.rng_for(1)
        ) == pytest.approx(0.49)
    else:
        assert r["progress"] == 0.7
    if persona == PersonaType.SILENT_BLOCKER:
        w.status, w.blocked_since, w.progress = "blocked", 2, 0.8
        assert (
            dynamics.report(ic, scenario.tasks[0], w, 4, scenario.config, dynamics.rng_for(1))["progress"]
            == 0.7
        )


def test_dependency_force_and_tick_snapshot(scenario):
    scenario.tasks[1].depends_on = ["t0"]
    e = ExecEnv(scenario)
    assert assign(e, "t1", "ic_1").errors
    assign(e, "t1", "ic_1", force=True)
    act(e, "wait")
    assert e.work["t1"].progress == 0
    assign(e)
    for _ in range(3):
        act(e, "wait")
    assert e.work["t0"].status == "done_true"
    assert e.work["t1"].progress == 0
    act(e, "wait")
    assert e.work["t1"].progress > 0


def test_budget_exhaustion_and_invalid_action(scenario):
    scenario.budgets.compute = 1
    e = ExecEnv(scenario)
    assign(e)
    assert act(e, "audit", ic_id="ic_0").errors
    assert e.compute == 0.25
    act(e, "wait")
    assert e.work["t0"].progress == 0 and e.compute >= 0
    assert act(e, "assign", ic_id="ic_1", task_id="t1", spec_detail=True, spec_flags=[]).errors


def test_human_duplicate_patience(scenario):
    e = ExecEnv(scenario)
    q = "Which mobile platforms are required?"
    result = act(e, "ask_human", human_id="pm", question=q)
    assert result.action_result["constraints"][0]["tag"] == "mobile_compat"
    assert e.patience["pm"] == 4
    act(e, "ask_human", human_id="pm", question=q)
    assert e.patience["pm"] == 2
    act(e, "ask_human", human_id="pm", question=q)
    assert not act(e, "ask_human", human_id="pm", question=q).action_result["constraints"]


def decision(**kwargs):
    return Event(
        event_id="decision",
        kind=EventKind.DECISION_POINT,
        tick=1,
        text="Choose scope.",
        escalation_worthy=True,
        resolution_options=["good", "wrong"],
        correct_option="good",
        deadline_tick=3,
        **kwargs,
    )


def test_event_deadline_default_and_drift(scenario):
    scenario.events = [decision()]
    scenario.humans[0].drift = DriftEvent(tick=2, quality_weights={"t0": 3}, text="Priorities changed.")
    e = ExecEnv(scenario)
    assert act(e, "escalate", event_id="decision", framing="Choose").errors
    assert act(e, "wait").new_events[0].event_id == "decision"
    act(e, "wait")
    assert e.weights["t0"] == 3
    act(e, "wait")
    assert e.resolutions["decision"]["option"] == "wrong"
    assert act(e, "escalate", event_id="decision", framing="Choose").errors


def test_incident_assignment_before_deadline(scenario):
    scenario.events = [
        Event(
            event_id="incident",
            kind=EventKind.INCIDENT,
            tick=1,
            text="Mitigate.",
            escalation_worthy=False,
            incident_task=scenario.tasks[0].model_copy(update={"task_id": "fix"}),
            deadline_tick=3,
            cost_if_ignored=0.8,
        )
    ]
    e = ExecEnv(scenario)
    assert "fix" not in e.tasks
    act(e, "wait")
    assign(e, "fix")
    assert "incident" in e.handled_incidents
    e2 = ExecEnv(scenario)
    for _ in range(3):
        act(e2, "wait")
    assign(e2, "fix")
    assert "incident" not in e2.handled_incidents


def test_reassign_cancel_feedback(scenario):
    e = ExecEnv(scenario)
    assign(e)
    act(e, "wait")
    old = e.work["t0"].progress
    assert act(e, "feed_back", ic_id="ic_0", text="Improve").errors
    act(e, "reassign", task_id="t0", new_ic_id="ic_1")
    assert e.work["t0"].progress == pytest.approx(old * 0.7)
    act(e, "cancel", task_id="t0")
    assert not act(e, "feed_back", ic_id="ic_1", text="Improve").errors
    assert e.feedback


def test_spam_guard_and_deadline(scenario):
    scenario.config.max_actions_per_tick = 2
    scenario.budgets.max_ticks = 1
    e = ExecEnv(scenario)
    act(e, "read_policy_doc")
    act(e, "read_policy_doc")
    result = act(e, "read_policy_doc")
    assert result.tick == 1 and result.errors
    act(e, "wait")
    assert e.terminated and e.termination_reason == "deadline"
    with pytest.raises(RuntimeError):
        act(e, "wait")


def test_no_hidden_fields_or_sentinels(scenario):
    scenario.ics[0].persona_params = {"secret_persona_sentinel": 0.34}
    scenario.ics[0].effective_persona_params = {"secret_effective_sentinel": 0.2}
    scenario.generation_log = {"secret_generation_sentinel": "never public"}
    trace = run_episode(scenario, "heuristic")
    forbidden = {
        "competence",
        "speed",
        "persona",
        "persona_params",
        "effective_persona_params",
        "true_size",
        "difficulty",
        "required_spec_flags",
        "true_quality",
        "escalation_worthy",
        "correct_option",
        "quality_weights",
        "generation_log",
        "memory_id",
        "improvement_applied",
    }

    def walk(obj):
        if isinstance(obj, dict):
            assert not forbidden.intersection(obj)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    for step in trace.steps:
        data = step.observation.model_dump(mode="json")
        walk(data)
        assert "sentinel" not in json.dumps(data)
    # All observations are isolated copies, including reset memory and mutable roster reports.
    assert trace.steps[0].observation.budgets.compute == 100


def test_seed_reproducibility_and_read_independence(scenario):
    assert (
        run_episode(scenario, "heuristic").model_dump_json()
        == run_episode(scenario, "heuristic").model_dump_json()
    )
    a, b = ExecEnv(scenario), ExecEnv(scenario)
    assign(a)
    assign(b)
    act(a, "status", ic_id="ic_0")
    act(a, "audit", ic_id="ic_0")
    act(a, "wait")
    act(b, "wait")
    assert a.work["t0"].progress == b.work["t0"].progress


def test_quality_and_constraint_separated(scenario):
    a, b = ExecEnv(scenario), ExecEnv(scenario)
    assign(a)
    act(b, "assign", ic_id="ic_0", task_id="t0", spec_detail=3, spec_flags=[])
    for e in (a, b):
        for _ in range(3):
            act(e, "wait")
        act(e, "ship")
    assert a.work["t0"].true_quality == b.work["t0"].true_quality
    assert raw_outcome(a.hidden(), scenario)[0] - raw_outcome(b.hidden(), scenario)[0] == pytest.approx(0.4)


def test_completion_claim_persists_when_worker_takes_new_task(scenario):
    e = ExecEnv(scenario)
    assign(e)
    for _ in range(3):
        act(e, "wait")
    result = assign(e, "t1")
    assert next(t for t in result.tasks if t.task_id == "t0").status == "done_claimed"
    assert next(t for t in result.tasks if t.task_id == "t1").status == "assigned"
