import json

from pydantic import BaseModel, ConfigDict, StrictBool

from execbench.llm.client import prompt


class QuestionVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    readable: StrictBool
    reason: str


def judge(client, question):
    # No hidden state or trigger vocabulary is exposed to the judge.
    try:
        result = client.json([
            {"role": "system", "content": prompt("grade_question_v1.md")},
            {"role": "user", "content": json.dumps({"question": question})},
        ])
        return QuestionVerdict.model_validate(result).model_dump()
    except ValueError as exc:
        # An infrastructure failure must not become a free action or an accepted question.
        raise RuntimeError("Invalid question-readability judge response") from exc
