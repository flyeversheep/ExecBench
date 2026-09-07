def grade(trace, scenario):
    relevant = total = 0
    for step in trace.steps:
        action = step.action
        if action is None or action.name != "assign" or step.observation.errors:
            continue
        task_id = action.args["task_id"]
        if step.observation.action_result.get("assigned") != task_id:
            continue
        flags = set(action.args["spec_flags"])
        required = set(step.hidden["tasks"][task_id]["required_spec_flags"])
        total += len(flags)
        relevant += len(flags & required)
    scores = {
        "specification_flag_count": float(total),
        "specification_relevant_flag_count": float(relevant),
    }
    if total:
        scores["specification_precision"] = relevant / total
    return scores, {
        "specification_precision": (
            f"{relevant}/{total} distinct flags were applicable across accepted assignments, "
            "including subsequently cancelled or replaced work."
            if total else "Undefined: no flags in accepted assignments; precision omitted."
        ),
    }
