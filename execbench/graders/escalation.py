def grade(trace, scenario):
    calls = trace.steps[-1].hidden["escalations"]
    decisions = [
        e for e in scenario.events if e.kind.value == "decision_point" and e.tick <= trace.steps[-1].tick
    ]
    timely = {
        e.event_id
        for e in decisions
        if any(
            c["event_id"] == e.event_id
            and c["tick"] >= e.tick
            and (e.deadline_tick is None or c["tick"] < e.deadline_tick)
            for c in calls
        )
    }
    tp = sum(e.escalation_worthy and e.event_id in timely for e in decisions)
    fp = sum(not e.escalation_worthy and e.event_id in timely for e in decisions)
    fn = sum(e.escalation_worthy and e.event_id not in timely for e in decisions)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"escalation_precision": precision, "escalation_recall": recall, "escalation_f1": f1}, {
        "escalation_f1": f"TP={tp}, FP={fp}, FN={fn}; unique surfaced decision IDs, strictly before deadline."
    }
