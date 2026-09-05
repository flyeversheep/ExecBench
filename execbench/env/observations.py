from execbench.schemas import (
    Budgets,
    EventPublicView,
    ICPublicView,
    Observation,
    PublicMemory,
    TaskPublicView,
)


def observe(env, result=None, errors=None, reset=False):
    roster = []
    for ic in env.scenario.ics:
        current = env.current(ic.ic_id)
        roster.append(
            ICPublicView(
                ic_id=ic.ic_id,
                display_name=ic.display_name,
                title=ic.title,
                skills=dict(ic.skills),
                current_task=current.task_id if current else None,
                last_status=env.last_status.get(ic.ic_id),
            )
        )
    tasks = []
    for task in env.tasks.values():
        w = env.work.get(task.task_id)
        # Do not expose done_true vs done_claimed. Completion is an IC claim until audited.
        status = "unassigned" if w is None else ("cancelled" if w.status == "cancelled" else "assigned")
        last = env.task_reports.get(task.task_id, {}) if w else {}
        if w and last.get("task_id") == task.task_id:
            status = (
                "done_claimed" if last.get("claims_done") else ("blocked" if last.get("blocked") else status)
            )
        tasks.append(
            TaskPublicView(
                task_id=task.task_id,
                title=task.title,
                task_type=task.task_type,
                description=task.description,
                depends_on=list(task.depends_on),
                status=status,
            )
        )
    events = [
        EventPublicView(
            event_id=e.event_id,
            kind=e.kind,
            tick=e.tick,
            text=e.text,
            resolution_options=e.resolution_options,
            deadline_tick=e.deadline_tick,
            task_id=e.incident_task.task_id if e.incident_task else None,
        )
        for e in env.new_events
    ]
    return Observation(
        tick=env.tick,
        budgets=Budgets(
            compute=env.compute, max_ticks=env.scenario.budgets.max_ticks, patience=dict(env.patience)
        ),
        costs={
            "audit": env.scenario.config.audit_cost,
            "reassign": env.scenario.config.reassign_cost,
            "per_spec_level": env.scenario.config.spec_detail_cost,
            "max_actions_per_tick": env.scenario.config.max_actions_per_tick,
        },
        roster=roster,
        tasks=tasks,
        new_events=events,
        action_result=result or {},
        errors=errors or [],
        terminated=env.terminated,
        memory=[PublicMemory(text=m.text, age_days=m.age_days) for m in env.scenario.memory_entries]
        if reset
        else None,
        stated_ask=env.scenario.humans[0].stated_ask if reset else None,
        humans=[{"human_id": h.human_id, "role": h.role} for h in env.scenario.humans],
    )
