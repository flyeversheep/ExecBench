import json
from typing import Literal

from pydantic import BaseModel, Field

from execbench.graders.detection import incidents
from execbench.llm.client import prompt


class FeedbackGrade(BaseModel):
    identifies_root_issue: Literal[0, 1]
    grounded_in_events: float = Field(ge=0, le=1)
    contains_false_claim: Literal[0, 1]
    actionable: float = Field(ge=0, le=1)


def coaching_value(result):
    return max(
        0.0,
        0.4 * result.identifies_root_issue
        + 0.3 * result.grounded_in_events
        + 0.3 * result.actionable
        - 0.5 * result.contains_false_claim,
    )


def grade(trace, scenario, client):
    reports = incidents(trace)
    eligible = {r["ic_id"] for r in reports}
    feedback = trace.steps[-1].hidden["feedback"]
    if feedback and client is None:
        return {}, {"coaching_score": "Not graded: LLM grader required."}, {"mode": "ungraded"}
    per_ic, judgments, fp, no_incident_calls = {}, [], 0, 0
    for entry in feedback:
        ic = next(i for i in scenario.ics if i.ic_id == entry["ic_id"])
        # Only events preceding the feedback can ground it.
        actual = [r for r in reports if r["ic_id"] == ic.ic_id and r["step_index"] < entry["step_index"]]
        result = FeedbackGrade.model_validate(
            client.json(
                [
                    {"role": "system", "content": prompt("grade_feedback_v1.md")},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "feedback": entry["text"],
                                "persona": ic.persona.value,
                                "actual_incidents": actual,
                            }
                        ),
                    },
                ]
            )
        )
        judgments.append({"ic_id": ic.ic_id, **result.model_dump()})
        per_ic.setdefault(ic.ic_id, []).append(coaching_value(result))
        if ic.ic_id not in eligible:
            no_incident_calls += 1
            fp += int(bool(result.contains_false_claim or result.identifies_root_issue))
    score = (
        sum(sum(per_ic.get(ic, [0])) / len(per_ic.get(ic, [0])) for ic in eligible) / len(eligible)
        if eligible
        else 0.0
    )
    return (
        {
            "coaching_score": score,
            "coaching_false_positive_rate": fp / no_incident_calls if no_incident_calls else 0.0,
        },
        {
            "coaching_score": f"{len(eligible)} ICs with incidents; missing feedback scores zero.",
            "coaching_false_positive_rate": f"{fp}/{no_incident_calls} feedback calls to ICs with no incidents.",
        },
        {"judgments": judgments},
    )
