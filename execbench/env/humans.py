import re

KEYWORDS = {
    "users": ["user", "customer", "audience", "accessib"],
    "platforms": ["platform", "mobile", "browser", "device", "compat"],
    "risks": ["risk", "constraint", "privacy", "security", "legal", "consent", "retention", "policy"],
    "timeline": ["timeline", "deadline", "when", "schedule"],
    "priority": ["priorit", "important", "tradeoff", "focus"],
    "success_metric": ["success", "metric", "quality", "acceptance", "requirement"],
    "stakeholders": ["stakeholder", "owner", "approve", "team"],
}


def classify(question):
    lower = question.lower()
    return {intent for intent, words in KEYWORDS.items() if any(w in lower for w in words)} or {"other"}


def duplicate(question, previous):
    words = set(re.findall(r"\w+", question.lower()))
    return any(len(words & old) / max(1, len(words | old)) >= 0.7 for old in previous)


def answer(human, question, remaining, previous, config, rng, weights):
    cost = 2 if duplicate(question, previous) else 1
    previous.append(set(re.findall(r"\w+", question.lower())))
    if remaining <= 0:
        return {"answer": "Use your judgment.", "constraints": []}, cost
    intents = classify(question)
    revealed = []
    for c in human.constraints:
        specific = any(part in question.lower() for part in c.tag.split("_") if len(part) > 3)
        if (intents.intersection(c.revealed_by) or specific) and rng.random() < (
            1 if specific else config.reveal_prob
        ):
            revealed.append({"tag": c.tag, "description": c.description})
    details = [f"[{c['tag']}] {c['description']}" for c in revealed]
    if "priority" in intents or "success_metric" in intents:
        details.append("Current task priorities: " + ", ".join(f"{k}: {v:g}" for k, v in weights.items()))
        details.append(human.true_intent_summary)
    if "stakeholders" in intents:
        details.append("Consult the stakeholders in your roster for requirements they own.")
    return {
        "answer": " ".join(details) or "Deliver the requested project within the stated budgets.",
        "constraints": revealed,
    }, cost
