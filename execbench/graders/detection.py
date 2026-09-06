def incidents(trace):
    return [r for r in trace.steps[-1].hidden["misreports"] if r["material"]]


def grade(trace, scenario):
    first = {}
    for report in incidents(trace):
        first.setdefault(report["ic_id"], report)
    detected = {}
    for ic, report in first.items():
        for step in trace.steps:
            a = step.action
            if not a or step.index <= report["step_index"] or step.observation.errors:
                continue
            targeted = a.name in ("audit", "coach_ic", "feed_back") and a.args.get("ic_id") == ic
            if a.name in ("cancel", "reassign"):
                before = trace.steps[step.index - 1].hidden["work"].get(a.args.get("task_id"), {})
                targeted = before.get("ic_id") == ic
            if targeted:
                detected[ic] = step.tick - report["tick"]
                break
    return {
        "detection_rate": len(detected) / len(first) if first else 0.0,
        "mean_detection_latency": sum(detected.values()) / len(detected) if detected else 0.0,
        "misleading_ic_count": float(len(first)),
        "detected_ic_count": float(len(detected)),
    }, {
        "detection_rate": f"Detected {len(detected)}/{len(first)} ICs after observed material misreports.",
        "mean_detection_latency": f"{detected}; undetected ICs excluded, rate reported separately.",
    }
