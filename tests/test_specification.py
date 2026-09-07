import pytest
from test_environment import act

from execbench.env.env import ExecEnv
from execbench.graders.specification import grade


def assign_flags(e, flags):
    return act(e, "assign", ic_id="ic_0", task_id="t0", spec_detail=2, spec_flags=flags)


def test_distinct_flag_cost_and_storage(scenario):
    scenario.config.spec_flag_cost = 0.5
    e = ExecEnv(scenario)
    assert e.steps[0].observation.costs["per_spec_flag"] == 0.5
    assert not assign_flags(e, ["mobile_compat", "extra", "extra"]).errors
    assert e.compute == 98.5
    assert e.work["t0"].spec_flags == ["mobile_compat", "extra"]


def test_assignment_cost_is_atomic(scenario):
    scenario.budgets.compute = 0.75
    e = ExecEnv(scenario)
    assert assign_flags(e, ["mobile_compat", "extra"]).errors
    assert e.compute == 0.75
    assert not e.work
    assert not e.assignments
    assert not assign_flags(e, ["mobile_compat"]).errors
    assert e.compute == 0


def test_cost_does_not_reveal_relevance_and_can_be_disabled(scenario):
    for flag in ["mobile_compat", "irrelevant"]:
        e = ExecEnv(scenario)
        assign_flags(e, [flag])
        assert e.compute == 99.25
    scenario.config.spec_flag_cost = 0
    e = ExecEnv(scenario)
    assign_flags(e, ["irrelevant"])
    assert e.compute == 99.5


def test_precision_includes_cancelled_assignments_excludes_rejected(scenario):
    e = ExecEnv(scenario)
    assign_flags(e, ["mobile_compat", "extra", "extra"])
    assert assign_flags(e, ["other"]).errors
    act(e, "cancel", task_id="t0")
    assign_flags(e, ["mobile_compat"])
    act(e, "ship")
    scores, _ = grade(e.trace(), scenario)
    assert scores["specification_flag_count"] == 3
    assert scores["specification_relevant_flag_count"] == 2
    assert scores["specification_precision"] == pytest.approx(2 / 3)


def test_empty_flags_do_not_earn_precision(scenario):
    e = ExecEnv(scenario)
    assign_flags(e, [])
    act(e, "ship")
    scores, _ = grade(e.trace(), scenario)
    assert scores["specification_flag_count"] == 0
    assert "specification_precision" not in scores
