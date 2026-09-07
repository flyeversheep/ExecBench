import copy
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


@pytest.mark.parametrize("documented", [True, False])
def test_policy_constraints_are_public_and_usable_in_assignments(scenario, documented):
    constraint = scenario.humans[0].constraints[0]
    constraint.in_policy_doc = documented
    if not documented:
        scenario.policy_doc = "Project policy\n"
    scenario.humans[0].constraints.append(constraint.model_copy(update={
        "constraint_id": "undocumented", "tag": "private_tag", "in_policy_doc": False,
        "description": "Undocumented requirement.",
    }))
    e = ExecEnv(scenario)
    before = (e.tick, e.compute, dict(e.patience))
    result = act(e, "read_policy_doc").action_result
    expected = [{"tag": constraint.tag, "description": constraint.description}] if documented else []
    assert result == {"policy_doc": scenario.policy_doc, "constraints": expected}
    assert (e.tick, e.compute, e.patience) == before
    assert e.revealed == ({constraint.tag} if documented else set())
    assert act(e, "read_policy_doc").action_result == result
    flags = [c["tag"] for c in result["constraints"]]
    assert not act(e, "assign", ic_id="ic_0", task_id="t0", spec_detail=3, spec_flags=flags).errors
    for _ in range(3):
        act(e, "wait")
    assert e.work["t0"].status == "done_true"
    _, details = raw_outcome(e.hidden(), scenario)
    assert details["violated_constraints"] == ([] if documented else [constraint.tag])


def test_human_repeated_questions_use_word_cost(scenario):
    e = ExecEnv(scenario)
    for remaining in range(4, -1, -1):
        result = act(e, "ask_human", human_id="pm", task_id="t0", question="Which mobile platforms?")
        assert result.action_result["constraints"][0]["tag"] == "mobile_compat"
        assert e.patience["pm"] == remaining
    result = act(e, "ask_human", human_id="pm", task_id="t0", question="Which mobile platforms?")
    assert result.action_result["constraints"] == []


@pytest.mark.parametrize("words,cost", [(0, 1), (1, 1), (20, 1), (21, 2), (40, 2), (41, 3)])
def test_human_word_cost(scenario, words, cost):
    e = ExecEnv(scenario)
    question = " \n\t".join(["mobile"] * words)
    act(e, "ask_human", human_id="pm", task_id="t0", question=question)
    assert e.patience["pm"] == 5 - cost
    assert e.tick == 0
    assert e.compute == 100


def test_human_insufficient_patience(scenario):
    scenario.humans[0].patience = 1
    e = ExecEnv(scenario)
    result = act(e, "ask_human", human_id="pm", task_id="t0", question="mobile " * 21)
    assert result.action_result["constraints"] == []
    assert e.patience["pm"] == 0
    assert not e.revealed


def test_human_task_scope_and_question_matching(scenario):
    scenario.tasks[1].required_spec_flags = ["retention_limit"]
    scenario.humans[0].constraints.append(scenario.humans[0].constraints[0].model_copy(update={
        "constraint_id": "retention", "tag": "retention_limit", "description": "Retain for 30 days.",
        "revealed_by": ["risks"],
    }))
    e = ExecEnv(scenario)
    question = "What mobile and retention requirements apply?"
    for task_id, expected in [("t0", "mobile_compat"), ("t1", "retention_limit")]:
        result = act(e, "ask_human", human_id="pm", task_id=task_id, question=question)
        assert [c["tag"] for c in result.action_result["constraints"]] == [expected]
    result = act(e, "ask_human", human_id="pm", task_id="t0", question="When is the deadline?")
    assert result.action_result["constraints"] == []
    # A discovered tag can still be used on another applicable task without asking again.
    assign(e, task="t2")
    assert e.work["t2"].spec_flags == ["mobile_compat"]


@pytest.mark.parametrize("args", [
    {"human_id": "pm", "question": "mobile"},
    {"human_id": "pm", "task_id": "unknown", "question": "mobile"},
    {"human_id": "unknown", "task_id": "t0", "question": "mobile"},
])
def test_human_invalid_target_does_not_spend_patience(scenario, args):
    e = ExecEnv(scenario)
    result = act(e, "ask_human", **args)
    assert result.errors
    assert e.patience["pm"] == 5
    assert e.questions["pm"] == []


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
    assert act(e, "coach_ic", ic_id="ic_0", text="Improve").errors
    act(e, "reassign", task_id="t0", new_ic_id="ic_1")
    assert e.work["t0"].progress == pytest.approx(old * 0.7)
    act(e, "cancel", task_id="t0")
    assert not act(e, "coach_ic", ic_id="ic_1", text="Improve").errors
    assert e.feedback


@pytest.mark.parametrize("eligible", [False, True])
def test_feedback_cannot_update_work_or_adapt_ic(scenario, eligible):
    e = ExecEnv(scenario)
    assign(e)
    if eligible:
        for _ in range(3):
            act(e, "wait")
        assert "ic_0" in e.feedback_eligible
    control = copy.deepcopy(e)
    text = "Incorporate explicit consent and retention_limit into the deliverable."
    result = act(e, "coach_ic", ic_id="ic_0", text=text)
    if eligible:
        assert result.action_result == {
            "recorded": True, "effect": "coaching_recorded_only", "task_state_changed": False,
        }
        assert e.feedback[-1]["text"] == text
    else:
        assert "coach_ic records IC coaching only" in result.errors[0]
        assert not e.feedback
    assert e.work == control.work
    assert e.ics == control.ics
    assert e.tick == control.tick
    # Recorded prose must not affect subsequent simulated work either.
    act(e, "wait")
    act(control, "wait")
    assert e.work == control.work
    assert e.ics == control.ics


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
