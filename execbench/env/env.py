"""Gym-style L0 environment. Invalid actions are recorded and count against the spam guard."""

from execbench.env import dynamics, events, humans
from execbench.env.observations import observe
from execbench.schemas import Action, EpisodeTrace, TraceStep, WorkItem, validate_args


class ExecEnv:
    def __init__(self, scenario):
        self.scenario = scenario.model_copy(deep=True)
        self.reset()

    def reset(self):
        s = self.scenario
        self.tick = 0
        self.compute = s.budgets.compute
        self.patience = {h.human_id: s.budgets.patience.get(h.human_id, h.patience) for h in s.humans}
        self.initial_patience = dict(self.patience)
        self.tasks = {t.task_id: t.model_copy(deep=True) for t in s.tasks}
        self.ics = {i.ic_id: i for i in s.ics}
        self.work = {}
        self.last_status = {}
        self.task_reports = {}
        self.questions = {h.human_id: [] for h in s.humans}
        self.weights = dict(s.humans[0].quality_weights)
        self.surfaced, self.blockers, self.handled_incidents = set(), set(), set()
        self.new_events, self.feedback, self.escalations, self.misreports, self.assignments = (
            [],
            [],
            [],
            [],
            [],
        )
        self.revealed, self.resolutions = set(), {}
        self.feedback_eligible = set()
        self.final_report = ""
        self.actions_this_tick = 0
        self.terminated = False
        self.termination_reason = ""
        self.audit_spend = 0.0
        self.denied_spend = 0.0
        self.steps = []
        events.surface(self)
        obs = observe(self, reset=True)
        self.record(None, obs)
        return obs

    def current(self, ic_id):
        return next(
            (
                w
                for w in self.work.values()
                if w.ic_id == ic_id and w.status not in ("done_true", "cancelled")
            ),
            None,
        )

    def target(self, ic_id):
        if ic_id not in self.ics:
            raise ValueError("unknown IC")
        return self.current(ic_id) or next(
            (w for w in reversed(list(self.work.values())) if w.ic_id == ic_id), None
        )

    def spend(self, cost):
        if self.compute + 1e-9 < cost:
            self.denied_spend += cost
            raise ValueError("insufficient compute budget")
        self.compute = max(0.0, self.compute - cost)

    def hidden(self):
        return {
            "final_tick": self.tick,
            "work": {k: v.model_dump(mode="json") for k, v in self.work.items()},
            "tasks": {k: v.model_dump(mode="json") for k, v in self.tasks.items()},
            "weights": dict(self.weights),
            "revealed_constraints": sorted(self.revealed),
            "resolutions": dict(self.resolutions),
            "handled_incidents": sorted(self.handled_incidents),
            "escalations": list(self.escalations),
            "misreports": list(self.misreports),
            "feedback": list(self.feedback),
            "assignments": list(self.assignments),
            "report": self.final_report,
            "audit_spend": self.audit_spend,
            "denied_spend": self.denied_spend,
        }

    def record(self, action, obs, llm_calls=None):
        self.steps.append(
            TraceStep(
                index=len(self.steps),
                tick=self.tick,
                action=action,
                observation=obs.model_copy(deep=True),
                hidden=self.hidden(),
                llm_calls=llm_calls or [],
            )
        )

    def step(self, action, llm_calls=None):
        if self.terminated:
            raise RuntimeError("episode already terminated")
        if not isinstance(action, Action):
            action = Action.model_validate(action)
        self.new_events = []
        self.actions_this_tick += 1
        errors = []
        try:
            if self.actions_this_tick > self.scenario.config.max_actions_per_tick:
                result = self._wait()
                errors.append("action limit reached; forced wait")
            else:
                validate_args(action)
                result = getattr(self, "_" + action.name)(**action.args)
        except (ValueError, KeyError) as exc:
            result = {}
            errors.append(str(exc))
        obs = observe(self, result, errors)
        self.record(action, obs, llm_calls)
        return obs

    def parse_failure(self, calls):
        obs = self.step(Action(name="wait"), calls)
        obs.errors.append("three invalid model responses; forced wait")
        self.steps[-1].observation = obs.model_copy(deep=True)
        return obs

    def _read_policy_doc(self):
        constraints = [
            {"tag": c.tag, "description": c.description}
            for h in self.scenario.humans
            for c in h.constraints
            if c.in_policy_doc
        ]
        self.revealed.update(c["tag"] for c in constraints)
        return {"policy_doc": self.scenario.policy_doc, "constraints": constraints}

    def _ask_human(self, human_id, question):
        h = next((h for h in self.scenario.humans if h.human_id == human_id), None)
        if h is None:
            raise ValueError("unknown human")
        result, cost = humans.answer(
            h,
            question,
            self.patience[human_id],
            self.questions[human_id],
            self.scenario.config,
            dynamics.rng_for(self.scenario.seed, "human", human_id, len(self.questions[human_id])),
            self.weights,
        )
        self.patience[human_id] = max(0, self.patience[human_id] - cost)
        self.revealed.update(c["tag"] for c in result["constraints"])
        return result

    def _assign(self, ic_id, task_id, spec_detail, spec_flags, force=False):
        if ic_id not in self.ics or task_id not in self.tasks:
            raise ValueError("unknown IC or task")
        if self.current(ic_id):
            raise ValueError("IC busy")
        if task_id in self.work and self.work[task_id].status != "cancelled":
            raise ValueError("task already assigned")
        deps_met = all(
            d in self.work and self.work[d].status == "done_true" for d in self.tasks[task_id].depends_on
        )
        if not deps_met and not force:
            raise ValueError("dependencies incomplete")
        self.spend(spec_detail * self.scenario.config.spec_detail_cost)
        self.work[task_id] = WorkItem(
            task_id=task_id,
            ic_id=ic_id,
            spec_detail=spec_detail,
            spec_flags=spec_flags,
            assignment_tick=self.tick,
            status="active" if deps_met else "blocked",
            blocked_since=None if deps_met else self.tick,
        )
        self.last_status.pop(ic_id, None)
        self.task_reports.pop(task_id, None)
        self.assignments.append({"ic_id": ic_id, "task_id": task_id, "tick": self.tick})
        for event in self.scenario.events:
            if (
                event.incident_task
                and event.incident_task.task_id == task_id
                and event.event_id in self.surfaced
            ):
                if event.deadline_tick is None or self.tick < event.deadline_tick:
                    self.handled_incidents.add(event.event_id)
        return {"assigned": task_id, "ic_id": ic_id}

    def _status(self, ic_id):
        w = self.target(ic_id)
        if w is None:
            return {"ic_id": ic_id, "idle": True}
        return self.make_report(w)

    def make_report(self, w):
        ic, task, cfg = self.ics[w.ic_id], self.tasks[w.task_id], self.scenario.config
        result = dynamics.report(
            ic,
            task,
            w,
            self.tick,
            cfg,
            dynamics.rng_for(self.scenario.seed, "status", w.task_id, w.ic_id, self.tick),
        )
        self.last_status[w.ic_id] = result
        self.task_reports[w.task_id] = result
        if w.claimed_done:
            self.feedback_eligible.add(w.ic_id)
        p = ic.persona.value
        material = (
            (p == "overconfident" and result["progress"] - w.progress >= 0.1 - 1e-9)
            or (p == "sandbagger" and result["claims_done"] and w.progress < 1)
            or (
                p == "metric_gamer"
                and w.true_quality is not None
                and result["metric"] - w.true_quality >= 0.2
            )
            or (p == "silent_blocker" and w.blocked_since is not None and self.tick - w.blocked_since >= 2)
        )
        divergence = abs(result["progress"] - w.progress)
        if p == "metric_gamer" and w.true_quality is not None:
            divergence = max(divergence, abs(result["metric"] - w.true_quality))
        if p == "silent_blocker" and material:
            divergence = max(divergence, 0.2)
        entry = {
            "ic_id": w.ic_id,
            "task_id": w.task_id,
            "tick": self.tick,
            "step_index": len(self.steps),
            "true_progress": w.progress,
            "reported_progress": result["progress"],
            "reported_metric": result["metric"],
            "quality": w.true_quality,
            "material": material,
            "divergence": divergence,
            "kind": p,
        }
        # One sample per IC/task/tick: free polling cannot inflate misleadingness.
        if not any(
            x["ic_id"] == w.ic_id and x["task_id"] == w.task_id and x["tick"] == self.tick
            for x in self.misreports
        ):
            self.misreports.append(entry)
        return result

    def _audit(self, ic_id):
        w = self.target(ic_id)
        if w is None:
            raise ValueError("IC has no assigned work")
        self.spend(self.scenario.config.audit_cost)
        self.audit_spend += self.scenario.config.audit_cost
        estimate = w.true_quality
        if estimate is not None:
            estimate = dynamics.clamp(
                estimate
                + dynamics.rng_for(self.scenario.seed, "audit", w.task_id, self.tick).normal(
                    0, self.scenario.config.audit_noise
                )
            )
        return {
            "ic_id": ic_id,
            "task_id": w.task_id,
            "progress": w.progress,
            "quality_estimate": estimate,
            "blocked": w.status == "blocked",
            "complete": w.progress >= 1,
        }

    def _reassign(self, task_id, new_ic_id):
        if task_id not in self.work or new_ic_id not in self.ics:
            raise ValueError("unknown task or IC")
        w = self.work[task_id]
        if w.status == "cancelled" or new_ic_id == w.ic_id or self.current(new_ic_id):
            raise ValueError("invalid reassignment or IC busy")
        self.spend(self.scenario.config.reassign_cost)
        old_ic = w.ic_id
        w.ic_id = new_ic_id
        w.progress *= self.scenario.config.reassign_retention
        w.true_quality, w.blocked_since = None, None
        w.status, w.claimed_done, w.injected_block = "active", False, False
        w.quality_multiplier = 1
        w.reported_progress_history, w.reported_metric_history = [], []
        self.blockers.discard(task_id)
        self.task_reports.pop(task_id, None)
        self.last_status.pop(old_ic, None)
        self.last_status.pop(new_ic_id, None)
        self.assignments.append({"ic_id": new_ic_id, "task_id": task_id, "tick": self.tick})
        return {"reassigned": task_id, "ic_id": new_ic_id}

    def _cancel(self, task_id):
        if task_id not in self.work or self.work[task_id].status == "cancelled":
            raise ValueError("task is not assigned")
        self.work[task_id].status = "cancelled"
        self.feedback_eligible.add(self.work[task_id].ic_id)
        return {"cancelled": task_id}

    def _escalate(self, event_id, framing):
        event = next((e for e in self.scenario.events if e.event_id == event_id), None)
        if event is None or event_id not in self.surfaced:
            raise ValueError("event not visible")
        if event_id in self.resolutions:
            raise ValueError("event already resolved or deadline passed")
        h = event.owner_human
        available = self.patience.get(h, 0) > 0
        self.patience[h] = max(0, self.patience.get(h, 0) - 1)
        self.escalations.append({"event_id": event_id, "tick": self.tick, "framing": framing})
        if not available:
            return {"answer": "Use your judgment."}
        option = event.correct_option or (event.resolution_options or ["acknowledged"])[0]
        self.resolutions[event_id] = {"option": option, "source": "human", "tick": self.tick}
        return {"event_id": event_id, "option": option}

    def _coach_ic(self, ic_id, text):
        if ic_id not in self.feedback_eligible:
            raise ValueError(
                "feedback requires a claimed-done or cancelled task; coach_ic records IC coaching "
                "only and cannot send task instructions or change requirements"
            )
        self.feedback.append({"ic_id": ic_id, "text": text, "tick": self.tick, "step_index": len(self.steps)})
        return {"recorded": True, "effect": "coaching_recorded_only", "task_state_changed": False}

    def _report(self, text):
        self.final_report = text
        return {"recorded": True}

    def _wait(self):
        self.tick += 1
        self.actions_this_tick = 0
        if self.tick > self.scenario.budgets.max_ticks:
            self.terminated, self.termination_reason = True, "deadline"
            return {"terminated": "deadline"}
        events.surface(self)
        # Dependency state is sampled at tick start, so dict order cannot speed up a chain.
        done = {k for k, w in self.work.items() if w.status == "done_true"}
        for task_id, w in sorted(self.work.items()):
            if w.status in ("done_true", "cancelled"):
                continue
            deps_met = all(d in done for d in self.tasks[task_id].depends_on)
            blocked = not deps_met or task_id in self.blockers
            if blocked:
                w.status = "blocked"
                if w.blocked_since is None:
                    w.blocked_since = self.tick
            else:
                w.status = "done_claimed" if w.claimed_done else "active"
                w.blocked_since = None
            cost = self.scenario.config.work_cost * self.ics[w.ic_id].speed
            if self.compute + 1e-9 < cost:
                self.denied_spend += cost
            else:
                self.spend(cost)
                if not blocked:
                    dynamics.advance(
                        self.ics[w.ic_id],
                        self.tasks[task_id],
                        w,
                        self.scenario.config,
                        dynamics.rng_for(self.scenario.seed, "work", task_id, w.ic_id, self.tick),
                    )
            self.make_report(w)
        return {"advanced": True}

    def _ship(self):
        self.terminated, self.termination_reason = True, "ship"
        return {"terminated": "ship"}

    def trace(self, policy="unknown"):
        if not self.terminated:
            raise RuntimeError("cannot finalize an active episode")
        return EpisodeTrace(
            scenario_id=self.scenario.scenario_id,
            policy=policy,
            scenario=self.scenario,
            steps=self.steps,
            termination_reason=self.termination_reason,
        )
