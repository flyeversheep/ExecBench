def raw_outcome(hidden, scenario):
    work = hidden["work"]
    delivered = sum(
        weight
        * (work.get(task, {}).get("true_quality") or 0)
        * (work.get(task, {}).get("status") == "done_true")
        for task, weight in hidden["weights"].items()
    )
    violated = []
    for human in scenario.humans:
        for c in human.constraints:
            if any(
                c.tag in task["required_spec_flags"]
                and work.get(tid, {}).get("status") == "done_true"
                and c.tag not in work[tid]["spec_flags"]
                for tid, task in hidden["tasks"].items()
            ):
                violated.append(c)
    # An incident that has not surfaced before shipping still must not be preemptively penalized.
    incident_cost = sum(
        e.cost_if_ignored
        for e in scenario.events
        if e.kind.value == "incident"
        and e.event_id not in hidden["handled_incidents"]
        and e.tick <= hidden.get("final_tick", 10**9)
    )
    penalties = sum(c.severity for c in violated)
    return delivered - penalties - incident_cost, {
        "delivered": delivered,
        "constraint_penalty": penalties,
        "incident_cost": incident_cost,
        "violated_constraints": [c.tag for c in violated],
    }


def true_summary(hidden, scenario):
    _, detail = raw_outcome(hidden, scenario)
    tasks = []
    for tid, task in hidden["tasks"].items():
        w = hidden["work"].get(tid, {})
        q = w.get("true_quality")
        tasks.append(
            {
                "task_id": tid,
                "done": w.get("status") == "done_true",
                "quality_bucket": None
                if q is None
                else ("high" if q >= 0.8 else "medium" if q >= 0.5 else "low"),
                "missing_flags": [f for f in task["required_spec_flags"] if f not in w.get("spec_flags", [])],
            }
        )
    return {
        "tasks": tasks,
        "constraint_violations": detail["violated_constraints"],
        "incidents": [
            {"event_id": e.event_id, "handled": e.event_id in hidden["handled_incidents"]}
            for e in scenario.events
            if e.kind.value == "incident" and e.tick <= hidden.get("final_tick", 10**9)
        ],
    }


def grade(trace, scenario):
    raw, details = raw_outcome(trace.steps[-1].hidden, scenario)
    reference = scenario.oracle_outcome
    if reference is None:
        from execbench.runner.run_episode import run_episode

        oracle = run_episode(scenario, "oracle", grade=False)
        reference = raw_outcome(oracle.steps[-1].hidden, scenario)[0]
    denominator = reference if reference > 1e-9 else 1.0
    return {
        "outcome_raw": raw,
        "outcome": raw / denominator,
        "regret": (reference - raw) / denominator,
        "oracle_outcome": reference,
    }, {"outcome": str(details), "regret": "Relative to the greedy reference; negative values are permitted."}
