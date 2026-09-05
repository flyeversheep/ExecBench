import pytest

from execbench.schemas import (
    Budgets,
    DifficultyConfig,
    HiddenConstraint,
    HumanProfile,
    ICProfile,
    PersonaType,
    Scenario,
    SimConfig,
    Task,
)


@pytest.fixture
def scenario():
    c = HiddenConstraint(
        constraint_id="private_constraint",
        tag="mobile_compat",
        description="Require mobile browsers.",
        revealed_by=["platforms"],
        in_policy_doc=True,
        owner_human="pm",
        severity=0.4,
    )
    return Scenario(
        scenario_id="hand",
        seed=42,
        difficulty=DifficultyConfig(),
        ics=[
            ICProfile(
                ic_id=f"ic_{i}",
                display_name=f"Worker {i}",
                title="Specialist",
                skills={"backend": 0.8},
                competence=0.8,
                speed=1,
                persona=PersonaType.COMPETENT,
                persona_params={},
                effective_persona_params={},
            )
            for i in range(3)
        ],
        tasks=[
            Task(
                task_id=f"t{i}",
                title=f"Task {i}",
                task_type="backend",
                description="Deliver the task.",
                depends_on=[],
                true_size=2,
                difficulty=0.2,
                required_spec_flags=["mobile_compat"],
            )
            for i in range(4)
        ],
        humans=[
            HumanProfile(
                human_id="pm",
                role="PM",
                patience=5,
                stated_ask="Build a release.",
                true_intent_summary="Meet the requirements.",
                quality_weights={f"t{i}": 1 for i in range(4)},
                constraints=[c],
            )
        ],
        events=[],
        policy_doc="[mobile_compat] Require mobile browsers.",
        memory_events=[],
        memory_entries=[],
        budgets=Budgets(compute=100, max_ticks=12),
        config=SimConfig(progress_noise=0, quality_noise=0, report_noise=0, audit_noise=0),
    )
