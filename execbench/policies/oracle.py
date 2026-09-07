import json

from execbench.schemas import Action, EventKind


class Oracle:
    """Specified greedy reference, with privileged state. This is not an optimal solver."""

    def __init__(self, env):
        self.env = env
        self.reported = False

    def act(self, observation, history):
        e = self.env
        for event in e.scenario.events:
            if (
                event.event_id in e.surfaced
                and event.kind == EventKind.DECISION_POINT
                and event.escalation_worthy
                and event.event_id not in e.resolutions
                and (event.deadline_tick is None or e.tick < event.deadline_tick)
            ):
                return Action(
                    name="escalate", args={"event_id": event.event_id, "framing": event.correct_option or ""}
                )
        free = sorted(
            (ic for ic in e.scenario.ics if not e.current(ic.ic_id)),
            key=lambda ic: (-ic.competence, ic.ic_id),
        )
        if free and e.compute >= e.scenario.config.reassign_cost:
            for w in e.work.values():
                if w.status == "blocked" and w.task_id in e.blockers:
                    return Action(name="reassign", args={"task_id": w.task_id, "new_ic_id": free[0].ic_id})
        ready = [
            t
            for t in e.tasks.values()
            if t.task_id not in e.work
            and all(d in e.work and e.work[d].status == "done_true" for d in t.depends_on)
        ]
        incident_ids = {x.incident_task.task_id for x in e.scenario.events if x.incident_task}
        ready.sort(key=lambda t: (t.task_id not in incident_ids, -e.weights.get(t.task_id, 0), t.task_id))
        ready = [t for t in ready if e.compute >= (
            3 * e.scenario.config.spec_detail_cost
            + len(set(t.required_spec_flags)) * e.scenario.config.spec_flag_cost
        )]
        if free and ready:
            task = ready[0]
            return Action(
                name="assign",
                args={
                    "ic_id": free[0].ic_id,
                    "task_id": task.task_id,
                    "spec_detail": 3,
                    "spec_flags": task.required_spec_flags,
                },
            )
        all_done = all(t in e.work and e.work[t].status == "done_true" for t in e.tasks)
        future = any(x.tick > e.tick for x in e.scenario.events)
        if (all_done and not future) or e.tick >= e.scenario.budgets.max_ticks:
            if not self.reported:
                from execbench.graders.outcome import true_summary

                self.reported = True
                return Action(name="report", args={"text": json.dumps(true_summary(e.hidden(), e.scenario))})
            return Action(name="ship")
        return Action(name="wait")
