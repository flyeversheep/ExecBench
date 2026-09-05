"""Parametric workers. Named RNG streams keep policy-dependent reads from changing work."""

import hashlib

import numpy as np

from execbench.schemas import PersonaType as P


def rng_for(seed, *parts):
    digest = hashlib.sha256((":".join(map(str, (seed, *parts)))).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


def clamp(value):
    return float(np.clip(value, 0, 1))


def quality(ic, task, work, config, rng):
    q = clamp(
        config.quality_base
        + config.quality_competence * ic.competence
        + config.quality_spec * work.spec_detail
        - config.quality_difficulty * task.difficulty
        + rng.normal(0, config.quality_noise)
    )
    if ic.persona == P.METRIC_GAMER:
        q = max(0, q - ic.effective_persona_params.get("gaming_penalty", 0.4))
    return q * work.quality_multiplier


def advance(ic, task, work, config, rng):
    rate = ic.speed * (config.progress_base + config.progress_competence * ic.competence)
    rate *= 1 - config.progress_difficulty * task.difficulty
    work.progress = clamp(work.progress + rate / task.true_size + rng.normal(0, config.progress_noise))
    if work.progress >= 1:
        work.true_quality = quality(ic, task, work, config, rng)
        work.status = "done_true"


def report(ic, task, work, tick, config, rng):
    true = work.progress
    params = ic.effective_persona_params
    blocked = work.status == "blocked"
    claimed = true >= 1
    if ic.persona in (P.COMPETENT, P.SLOW_HONEST):
        progress = clamp(true + rng.normal(0, config.report_noise)) if true < 1 else 1.0
    elif ic.persona == P.OVERCONFIDENT:
        progress = clamp(true + params.get("progress_bias", 0.3))
        claimed = progress >= 1
    else:
        progress = true
    if ic.persona == P.SANDBAGGER:
        claimed = true >= params.get("done_threshold", 0.7)
        if claimed and not work.claimed_done:
            work.quality_multiplier *= config.sandbag_quality_multiplier
            if work.true_quality is not None:
                work.true_quality *= config.sandbag_quality_multiplier
    metric = progress
    if ic.persona == P.METRIC_GAMER:
        previous = work.reported_metric_history[-1][1] if work.reported_metric_history else 0
        metric = max(previous, clamp(true * 1.4 + 0.2))
    if ic.persona == P.SILENT_BLOCKER and blocked:
        progress = work.reported_progress_history[-1][1] if work.reported_progress_history else 0
        metric = work.reported_metric_history[-1][1] if work.reported_metric_history else 0
    if claimed:
        work.claimed_done = True
        if work.status == "active":
            work.status = "done_claimed"
    work.reported_progress_history.append((tick, progress))
    work.reported_metric_history.append((tick, metric))
    return {
        "task_id": task.task_id,
        "progress": progress,
        "claims_done": claimed,
        "blocked": blocked and ic.persona != P.SILENT_BLOCKER,
        "metric_name": task.proxy_metric_name or "completion",
        "metric": metric,
    }
