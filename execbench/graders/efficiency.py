def grade(trace, scenario):
    last = trace.steps[-1].observation
    initial = trace.steps[0].observation.budgets.patience
    actions = [s.action for s in trace.steps if s.action]
    calls = [c for s in trace.steps for c in s.llm_calls]
    return {
        "compute_fraction": (scenario.budgets.compute - last.budgets.compute)
        / max(scenario.budgets.compute, 1e-9),
        "patience_fraction": (sum(initial.values()) - sum(last.budgets.patience.values()))
        / max(sum(initial.values()), 1),
        "ticks_fraction": last.tick / scenario.budgets.max_ticks,
        "ask_human_count": float(sum(a.name == "ask_human" for a in actions)),
        "escalate_count": float(sum(a.name == "escalate" for a in actions)),
        "denied_compute": trace.steps[-1].hidden["denied_spend"],
        "llm_input_tokens": float(sum(c.get("usage", {}).get("input_tokens", 0) for c in calls)),
        "llm_output_tokens": float(sum(c.get("usage", {}).get("output_tokens", 0) for c in calls)),
        "llm_cost_usd": sum(c.get("cost_usd") or 0 for c in calls if not c.get("cached")),
        "llm_cost_known": float(all(c.get("cost_usd") is not None for c in calls)),
        "parse_forced_wait_rate": sum(
            "three invalid model responses; forced wait" in s.observation.errors for s in trace.steps
        )
        / max(len(actions), 1),
    }, {"llm_cost_usd": "Actual uncached call estimate; unknown pricing is flagged by llm_cost_known=0."}
