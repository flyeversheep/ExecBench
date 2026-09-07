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


def question_cost(question):
    # Words are whitespace-delimited; even an empty question costs one patience.
    return max(1, (len(question.split()) + 19) // 20)


def answer(human, question, task, remaining, config, rng, weights):
    cost = question_cost(question)
    if remaining < cost:
        return {"answer": "Use your judgment.", "constraints": []}, cost
    intents = classify(question)
    revealed = []
    for c in human.constraints:
        if c.tag not in task.required_spec_flags:
            continue
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
