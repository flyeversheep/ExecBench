from execbench.schemas import EventKind


def surface(env):
    for event in env.scenario.events:
        if event.tick == env.tick and event.event_id not in env.surfaced:
            env.surfaced.add(event.event_id)
            env.new_events.append(event)
            if event.incident_task:
                env.tasks[event.incident_task.task_id] = event.incident_task.model_copy(deep=True)
            if event.blocked_task_id:
                env.blockers.add(event.blocked_task_id)
    for human in env.scenario.humans:
        if human.drift and human.drift.tick == env.tick:
            env.weights.update(human.drift.quality_weights)
    for event in env.scenario.events:
        if event.event_id not in env.surfaced or event.deadline_tick is None:
            continue
        if env.tick >= event.deadline_tick and event.event_id not in env.resolutions:
            if event.kind == EventKind.DECISION_POINT:
                alternatives = [o for o in event.resolution_options or [] if o != event.correct_option]
                env.resolutions[event.event_id] = {
                    "option": alternatives[0] if alternatives else None,
                    "source": "default",
                    "tick": env.tick,
                }
            elif event.kind == EventKind.INCIDENT:
                env.resolutions[event.event_id] = {
                    "handled": event.event_id in env.handled_incidents,
                    "tick": env.tick,
                }
