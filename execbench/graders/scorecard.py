from execbench.graders import (
    detection,
    efficiency,
    escalation,
    feedback,
    memory_use,
    outcome,
    report_honesty,
    specification,
    verification,
)


def score(trace, scenario=None, grader_client=None):
    scenario = scenario or trace.scenario
    for module in (outcome, escalation, detection, verification, memory_use, efficiency, specification):
        values, explanations = module.grade(trace, scenario)
        trace.scores.update(values)
        trace.explanations.update(explanations)
    trace.grading["mode"] = "llm" if grader_client else "deterministic_only"
    if grader_client:
        trace.grading["model"] = grader_client.model
        start = len(grader_client.calls)
    for module in (report_honesty, feedback):
        values, explanations, evidence = module.grade(trace, scenario, grader_client)
        trace.scores.update(values)
        trace.explanations.update(explanations)
        trace.grading[module.__name__.split(".")[-1]] = evidence
    if grader_client:
        calls = trace.grading.get("question_readability", {}).get("calls", []) + grader_client.calls[start:]
        trace.grading["calls"] = calls
        trace.scores["grader_input_tokens"] = float(
            sum(c.get("usage", {}).get("input_tokens", 0) for c in calls)
        )
        trace.scores["grader_output_tokens"] = float(
            sum(c.get("usage", {}).get("output_tokens", 0) for c in calls)
        )
        trace.scores["grader_cost_usd"] = sum(c.get("cost_usd") or 0 for c in calls if not c.get("cached"))
        trace.scores["grader_cost_known"] = float(all(c.get("cost_usd") is not None for c in calls))
    return trace
