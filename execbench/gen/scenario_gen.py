import math
from pathlib import Path

import numpy as np
import yaml

from execbench.gen.memory_gen import generate_memory
from execbench.schemas import (
    Budgets,
    DifficultyConfig,
    DriftEvent,
    Event,
    EventKind,
    HiddenConstraint,
    HumanProfile,
    ICProfile,
    PersonaType,
    Scenario,
    SimConfig,
    Task,
)


def ladder(level):
    return DifficultyConfig(
        level=level,
        n_ics=3 + (level >= 3),
        n_tasks=4 + level,
        adversarial_fraction=0.15 * level,
        n_hidden_constraints=min(4, level),
        n_decision_points=level,
        n_incidents=int(level >= 2),
        drift=level >= 3,
        secondary_human=level >= 2,
        memory_coverage=0.6,
        budget_tightness=1.15 - 0.05 * level,
    )


def generate(seed, difficulty=None, config=None, memory_client=None):
    d, cfg = difficulty or DifficultyConfig(), config or SimConfig.from_file()
    rng = np.random.default_rng(seed)
    paths = sorted(Path(__file__).with_name("templates").glob("*.yaml"))
    template = yaml.safe_load(paths[int(rng.integers(len(paths)))].read_text())
    types = ["backend", "frontend", "docs", "data", "infra"]
    bad = [
        PersonaType.SANDBAGGER,
        PersonaType.OVERCONFIDENT,
        PersonaType.METRIC_GAMER,
        PersonaType.SILENT_BLOCKER,
    ]
    adversarial = set(
        rng.choice(d.n_ics, int(round(d.n_ics * d.adversarial_fraction)), replace=False).tolist()
    )
    ics = []
    for i in range(d.n_ics):
        persona = (
            bad[int(rng.integers(len(bad)))]
            if i in adversarial
            else (PersonaType.SLOW_HONEST if rng.random() < 0.15 else PersonaType.COMPETENT)
        )
        competence = float(rng.beta(4, 2))
        params = {}
        if persona == PersonaType.OVERCONFIDENT:
            params["progress_bias"] = float(rng.uniform(cfg.bias_min, cfg.bias_max))
        if persona == PersonaType.SANDBAGGER:
            params["done_threshold"] = float(rng.uniform(cfg.done_threshold_min, cfg.done_threshold_max))
        if persona == PersonaType.METRIC_GAMER:
            params["gaming_penalty"] = float(rng.uniform(cfg.gaming_penalty_min, cfg.gaming_penalty_max))
        speed = float(rng.uniform(0.6, 1.6))
        if persona == PersonaType.SLOW_HONEST:
            speed *= 0.6
        ics.append(
            ICProfile(
                ic_id=f"ic_{chr(97 + i)}",
                display_name=f"{['Alex', 'Blair', 'Casey', 'Devon', 'Emery', 'Fran', 'Gray', 'Harper'][i]} ({types[i % 5]})",
                title=types[i % 5].title() + " specialist",
                skills={t: float(np.clip(competence + rng.normal(0, 0.15), 0, 1)) for t in types},
                competence=competence,
                speed=speed,
                persona=persona,
                persona_params=params,
                effective_persona_params=params,
            )
        )
    tasks = []
    for i in range(d.n_tasks):
        skeleton = template["tasks"][i % len(template["tasks"])]
        tasks.append(
            Task(
                task_id=f"task_{i}",
                title=skeleton["title"] + (f" phase {i // 6 + 1}" if i >= 6 else ""),
                task_type=skeleton["type"],
                description=f"{skeleton['title']} for this project. Coordinate acceptance requirements with stakeholders.",
                depends_on=[f"task_{j}" for j in skeleton["deps"] if j < i],
                true_size=float(rng.uniform(1.5, 3.5)),
                difficulty=float(rng.uniform(0.1, 0.2 + d.level * 0.1)),
                required_spec_flags=[],
                proxy_metric_name="checks_passing",
            )
        )
    constraints = []
    for idx in rng.choice(len(template["constraints"]), d.n_hidden_constraints, replace=False).tolist():
        c = template["constraints"][idx]
        owner = c["owner"] if d.secondary_human else "pm"
        constraints.append(
            HiddenConstraint(
                constraint_id=f"constraint_{idx}",
                tag=c["tag"],
                description=c["description"],
                revealed_by=c["intents"],
                in_policy_doc=bool(rng.random() < 0.5),
                owner_human=owner,
                severity=float(rng.uniform(0.15, 0.4)),
            )
        )
        for task in tasks:
            if task.task_type in c["task_types"]:
                task.required_spec_flags.append(c["tag"])
    weights = {t.task_id: 1.0 for t in tasks}
    drift = None
    if d.drift:
        docs = next(t for t in tasks if t.task_type == "docs")
        drift = DriftEvent(
            tick=4,
            quality_weights={**weights, docs.task_id: 3.0},
            text=f"Priority update: {docs.task_id} now carries three times its previous importance.",
        )
    humans = [
        HumanProfile(
            human_id="pm",
            role="Product manager",
            patience=8,
            stated_ask=template["ask"] + ". Deliver by the deadline and provide a final status report.",
            true_intent_summary="A usable, compliant release with reliable documentation.",
            quality_weights=weights,
            constraints=[c for c in constraints if c.owner_human == "pm"],
            drift=drift,
        )
    ]
    if d.secondary_human:
        humans.append(
            HumanProfile(
                human_id="legal",
                role="Legal reviewer",
                patience=5,
                stated_ask="",
                true_intent_summary="Customer data handling must meet all applicable requirements.",
                quality_weights=weights,
                constraints=[c for c in constraints if c.owner_human == "legal"],
            )
        )
    events = []
    for i in range(d.n_decision_points):
        x = template["decisions"][i % len(template["decisions"])]
        tick = 1 + i
        events.append(
            Event(
                event_id=f"decision_{i}",
                kind=EventKind.DECISION_POINT,
                tick=tick,
                text=x["text"],
                escalation_worthy=x["worthy"],
                resolution_options=x["options"],
                correct_option=x["correct"],
                cost_if_ignored=0,
                deadline_tick=tick + 3,
            )
        )
    for i in range(d.n_incidents):
        task = Task(
            task_id=f"incident_task_{i}",
            title="Mitigate rollout incident",
            task_type="infra",
            description=template["incident"],
            depends_on=[],
            true_size=1.5,
            difficulty=0.25,
            required_spec_flags=[],
        )
        events.append(
            Event(
                event_id=f"incident_{i}",
                kind=EventKind.INCIDENT,
                tick=2 + i,
                text=template["incident"],
                escalation_worthy=False,
                incident_task=task,
                cost_if_ignored=0.6,
                deadline_tick=5 + i,
            )
        )
    if drift:
        events.append(
            Event(
                event_id="priority_drift",
                kind=EventKind.CHAT,
                tick=drift.tick,
                text=drift.text,
                escalation_worthy=False,
            )
        )
    # An external blocker has visible context; whether a worker discloses its effect is persona-dependent.
    if any(ic.persona == PersonaType.SILENT_BLOCKER for ic in ics):
        events.append(
            Event(
                event_id="access_blocker",
                kind=EventKind.IC_MESSAGE,
                tick=2,
                text="Access to the initial project dataset has changed. A different owner can request renewed access.",
                escalation_worthy=False,
                blocked_task_id="task_0",
            )
        )
    memories, entries, logs = generate_memory(ics, d.memory_coverage, rng, cfg, memory_client)
    scenario = Scenario(
        scenario_id=f"l{d.level}_{seed:05d}",
        seed=seed,
        difficulty=d,
        ics=ics,
        tasks=tasks,
        humans=humans,
        events=events,
        policy_doc="Project policy\n"
        + "\n".join(f"[{c.tag}] {c.description}" for c in constraints if c.in_policy_doc),
        memory_events=memories,
        memory_entries=entries,
        budgets=Budgets(compute=10000, max_ticks=100),
        config=cfg,
        generation_log={
            "template": template["name"],
            "memory": logs,
            "rng": "numpy.PCG64",
            "calibration": "greedy oracle; empirical reference, not optimal ceiling",
        },
    )
    from execbench.graders.outcome import raw_outcome
    from execbench.runner.run_episode import run_episode

    reference = run_episode(scenario, "oracle", grade=False)
    used = scenario.budgets.compute - reference.steps[-1].observation.budgets.compute
    ticks = reference.steps[-1].tick
    scenario.budgets = Budgets(
        compute=round(used / 0.7 * d.budget_tightness, 6), max_ticks=max(10, math.ceil(ticks * 1.3))
    )
    calibrated = run_episode(scenario, "oracle", grade=False)
    scenario.oracle_outcome = raw_outcome(calibrated.steps[-1].hidden, scenario)[0]
    scenario.generation_log["oracle_compute_used"] = used
    scenario.generation_log["oracle_ticks"] = ticks
    return scenario


def generate_set(out, count=50, start_seed=1000, memory_client=None, config=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        level = min(5, i * 5 // count + 1)
        s = generate(start_seed + i, ladder(level), config, memory_client)
        path = out / f"{s.scenario_id}.json"
        path.write_text(s.model_dump_json(indent=2) + "\n")
        paths.append(path)
    return paths
