import numpy as np


def ranks(values):
    return np.array([sum(x < v for x in values) + (sum(x == v for x in values) + 1) / 2 for v in values])


def grade(trace, scenario):
    counts = {ic.ic_id: 0 for ic in scenario.ics}
    divergence = dict.fromkeys(counts, 0.0)
    for step in trace.steps:
        if step.action and step.action.name == "audit" and not step.observation.errors:
            counts[step.action.args["ic_id"]] += 1
    for r in trace.steps[-1].hidden["misreports"]:
        divergence[r["ic_id"]] += r["divergence"]
    a, b = ranks(list(counts.values())), ranks(list(divergence.values()))
    defined = np.std(a) > 0 and np.std(b) > 0
    corr = float(np.corrcoef(a, b)[0, 1]) if defined else 0.0
    return {
        "verification_calibration": corr,
        "verification_defined": float(defined),
        "audit_spend_fraction": trace.steps[-1].hidden["audit_spend"] / max(scenario.budgets.compute, 1e-9),
    }, {
        "verification_calibration": f"Spearman with average tie ranks; defined={defined}. Audits={counts}; divergence={divergence}"
    }
