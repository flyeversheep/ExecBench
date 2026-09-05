def grade(trace, scenario):
    final = trace.steps[-1].hidden
    assignments = {}
    for x in final["assignments"]:
        assignments.setdefault(x["ic_id"], x["tick"])
    audited = {}
    for step in trace.steps:
        if step.action and step.action.name == "audit" and not step.observation.errors:
            audited.setdefault(step.action.args["ic_id"], []).append(step.tick)
    has_memory = {m.about_ic for m in scenario.memory_events if m.about_ic and not m.is_distractor}
    issue = {
        m.about_ic
        for m in scenario.memory_events
        if m.kind not in ("great_work", "distractor")
        and m.improvement_applied < 0.5
        and m.about_ic in assignments
    }
    no_memory = set(assignments) - has_memory
    stale = {
        m.about_ic
        for m in scenario.memory_events
        if m.feedback_given and m.age_days >= 60 and m.improvement_applied < 0.3 and m.about_ic in assignments
    }

    def rate(group):
        return (
            sum(any(assignments[ic] <= t <= assignments[ic] + 3 for t in audited.get(ic, [])) for ic in group)
            / len(group)
            if group
            else 0.0
        )

    return {
        "prior_utilization": rate(issue),
        "no_memory_audit_rate": rate(no_memory),
        "stale_trust": sum(ic not in audited for ic in stale) / len(stale) if stale else 0.0,
        "prior_eligible_count": float(len(issue)),
        "stale_eligible_count": float(len(stale)),
    }, {
        "prior_utilization": f"{len(issue)} assigned ICs with issue memories; {len(no_memory)} without memory.",
        "stale_trust": f"{len(stale)} assigned ICs with feedback aged >=60 days and improvement <0.3.",
    }
