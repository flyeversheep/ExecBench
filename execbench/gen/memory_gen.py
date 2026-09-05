import json
import math

from execbench.schemas import MemoryEntry, MemoryEvent

KINDS = {
    "competent": "great_work",
    "slow_honest": "missed_deadline",
    "overconfident": "overstated_progress",
    "sandbagger": "overstated_progress",
    "metric_gamer": "metric_gaming",
    "silent_blocker": "silent_block",
}
TEXT = {
    "great_work": "delivered strong work with accurate updates",
    "missed_deadline": "missed a deadline",
    "overstated_progress": "reported more completion than was independently confirmed",
    "metric_gaming": "improved a dashboard metric without improving the deliverable",
    "silent_block": "remained blocked without mentioning it in updates",
    "distractor": "preferred written meeting notes",
    "feedback_given": "received feedback",
}


def decay(days, config):
    return math.exp(-days / config.memory_decay_days)


def template(event, name):
    text = f"{event.age_days} days ago, {name} {TEXT[event.kind]}."
    if event.feedback_given:
        text += " They received feedback and showed improvement at the time."
    return text


def render(event, name, client=None):
    fallback = template(event, name)
    if client is None:
        return fallback, {"mode": "template"}
    from execbench.llm.client import prompt

    attempts = []
    payload = {"event": event.model_dump(), "display_name": name}
    for attempt in range(3):
        try:
            response = client.complete(
                [
                    {"role": "system", "content": prompt("memory_render_v1.md")},
                    {"role": "user", "content": json.dumps({**payload, "attempt": attempt})},
                ],
                temperature=0.7,
            )
            text = response["text"].strip()
            check = client.json(
                [
                    {"role": "system", "content": prompt("memory_validate_v1.md")},
                    {"role": "user", "content": json.dumps({**payload, "text": text})},
                ]
            )
            attempts.append({"text": text, "validation": check})
            if check.get("consistent") is True and text:
                return text, {"mode": "llm", "attempts": attempts}
        except (ValueError, RuntimeError) as exc:
            attempts.append({"error": str(exc)})
    return fallback, {"mode": "template_fallback", "attempts": attempts}


def generate_memory(ics, coverage, rng, config, client=None):
    events, entries, logs = [], [], []
    count = int(round(len(ics) * coverage))
    covered = set(rng.choice(len(ics), size=count, replace=False).tolist())
    for idx, ic in enumerate(ics):
        ic.effective_persona_params = dict(ic.persona_params)
        if idx not in covered:
            continue
        for _ in range(int(rng.integers(1, 4))):
            age = int(rng.choice([3, 7, 14, 30, 60, 120]))
            kind = KINDS[ic.persona.value]
            feedback = kind != "great_work" and rng.random() < config.feedback_probability
            improvement = config.base_improvement * decay(age, config) if feedback else 0
            event = MemoryEvent(
                memory_id=f"mem_{len(events)}",
                about_ic=ic.ic_id,
                kind=kind,
                age_days=age,
                feedback_given=feedback,
                improvement_applied=improvement,
                is_distractor=False,
            )
            events.append(event)
        # Most recent feedback supersedes older notes; do not compound improvements.
        feedbacks = [e for e in events if e.about_ic == ic.ic_id and e.feedback_given]
        improvement = max((e.improvement_applied for e in feedbacks), default=0)
        for key in ("progress_bias", "gaming_penalty"):
            if key in ic.effective_persona_params:
                ic.effective_persona_params[key] *= 1 - improvement
        if "done_threshold" in ic.effective_persona_params:
            ic.effective_persona_params["done_threshold"] += (
                1 - ic.effective_persona_params["done_threshold"]
            ) * improvement
    for _ in range(int(rng.integers(1, 4))):
        events.append(
            MemoryEvent(
                memory_id=f"mem_{len(events)}",
                about_ic=None,
                kind="distractor",
                age_days=int(rng.choice([7, 30, 120])),
                feedback_given=False,
                improvement_applied=0,
                is_distractor=True,
            )
        )
    for event in events:
        name = next((ic.display_name for ic in ics if ic.ic_id == event.about_ic), "the organization")
        text, log = render(event, name, client)
        entries.append(MemoryEntry(text=text, age_days=event.age_days, memory_id=event.memory_id))
        logs.append(log)
    rng.shuffle(entries)
    return events, entries, logs
