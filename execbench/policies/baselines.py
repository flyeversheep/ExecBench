"""Baselines consume public observations only. No environment reference is accepted."""

import re

import numpy as np

from execbench.schemas import Action


class TrustAll:
    def __init__(self, seed=0):
        self.attempted = set()
        self.reported = False
        self.flags = set()
        self.events = {}

    def preprocess(self, obs):
        self.events.update({e.event_id: e for e in obs.new_events})
        for c in obs.action_result.get("constraints", []):
            self.flags.add(c["tag"])
        self.flags.update(re.findall(r"\[([a-z_]+)\]", obs.action_result.get("policy_doc", "")))

    def finish(self, obs):
        if obs.tick < obs.budgets.max_ticks:
            return None
        if not self.reported:
            self.reported = True
            claimed = [t.task_id for t in obs.tasks if t.status == "done_claimed"]
            return Action(
                name="report",
                args={
                    "text": f"Workers claim completion of: {claimed}. "
                    "Other tasks are not confirmed complete. I have not independently verified overall quality or requirements."
                },
            )
        return Action(name="ship")

    def assign(self, obs):
        done = {t.task_id for t in obs.tasks if t.status == "done_claimed"}
        for task in sorted(obs.tasks, key=lambda t: (not t.task_id.startswith("incident"), t.task_id)):
            if task.status != "unassigned" or not set(task.depends_on) <= done:
                continue
            free = sorted(
                (ic for ic in obs.roster if ic.current_task is None),
                key=lambda ic: (-ic.skills.get(task.task_type, 0), ic.ic_id),
            )
            for ic in free:
                key = (obs.tick, task.task_id, ic.ic_id)
                if key not in self.attempted and obs.budgets.compute >= 3 * obs.costs.get(
                    "per_spec_level", 0.25
                ):
                    self.attempted.add(key)
                    return Action(
                        name="assign",
                        args={
                            "ic_id": ic.ic_id,
                            "task_id": task.task_id,
                            "spec_detail": 3 if self.flags else 1,
                            "spec_flags": sorted(self.flags),
                        },
                    )
        return None

    def act(self, observation, history):
        self.preprocess(observation)
        return self.finish(observation) or self.assign(observation) or Action(name="wait")


class AuditAll(TrustAll):
    def __init__(self, seed=0):
        super().__init__(seed)
        self.asked, self.audited = set(), set()

    def act(self, observation, history):
        obs = observation
        self.preprocess(obs)
        finished = self.finish(obs)
        if finished:
            return finished
        questions = [
            "Who are the users and platforms?",
            "What risks and requirements matter?",
            "What is the deadline, priority and success metric?",
        ]
        for h in obs.humans:
            for idx, question in enumerate(questions):
                key = (h["human_id"], idx)
                if key not in self.asked:
                    self.asked.add(key)
                    return Action(name="ask_human", args={"human_id": h["human_id"], "question": question})
        for ic in obs.roster:
            key = (obs.tick, ic.ic_id)
            if key not in self.audited and (ic.current_task or ic.last_status):
                self.audited.add(key)
                return Action(name="audit", args={"ic_id": ic.ic_id})
        return self.assign(obs) or Action(name="wait")


class Heuristic(TrustAll):
    def __init__(self, seed=0):
        super().__init__(seed)
        self.asked, self.audited, self.escalated, self.corrected = set(), set(), set(), set()
        self.read = False
        self.progress = {}
        self.audit_results = {}

    def act(self, observation, history):
        obs = observation
        self.preprocess(obs)
        result = obs.action_result
        if "quality_estimate" in result:
            self.audit_results[result["ic_id"]] = result
        finished = self.finish(obs)
        if finished:
            return finished
        if not self.read:
            self.read = True
            return Action(name="read_policy_doc")
        for h in obs.humans:
            for idx, question in enumerate(
                [
                    "Who are the users, platforms and stakeholders? What risks, constraints and requirements apply?",
                    "What are the timeline, priorities and success metrics?",
                ]
            ):
                key = (h["human_id"], idx)
                if key not in self.asked:
                    self.asked.add(key)
                    return Action(name="ask_human", args={"human_id": h["human_id"], "question": question})
        for event in self.events.values():
            if event.kind.value == "decision_point" and event.event_id not in self.escalated:
                if event.deadline_tick is None or obs.tick < event.deadline_tick:
                    self.escalated.add(event.event_id)
                    return Action(
                        name="escalate",
                        args={
                            "event_id": event.event_id,
                            "framing": "Please resolve this decision and confirm the preferred option.",
                        },
                    )
        for ic in obs.roster:
            last = ic.last_status or {}
            task = last.get("task_id")
            progress = last.get("progress", 0)
            previous = self.progress.get((ic.ic_id, task), (obs.tick, 0))
            jump = progress - previous[1]
            if previous[0] < obs.tick:
                self.progress[(ic.ic_id, task)] = (obs.tick, progress)
            elif (ic.ic_id, task) not in self.progress:
                self.progress[(ic.ic_id, task)] = (obs.tick, progress)
            key = (obs.tick, ic.ic_id)
            if (
                (last.get("claims_done") or jump > 0.3)
                and key not in self.audited
                and obs.budgets.compute >= obs.costs.get("audit", 2)
            ):
                self.audited.add(key)
                return Action(name="audit", args={"ic_id": ic.ic_id})
            audit = self.audit_results.get(ic.ic_id, {})
            if audit.get("blocked") and task not in self.corrected:
                free = next((x for x in obs.roster if x.current_task is None and x.ic_id != ic.ic_id), None)
                if free and obs.budgets.compute >= obs.costs.get("reassign", 1):
                    self.corrected.add(task)
                    return Action(name="reassign", args={"task_id": task, "new_ic_id": free.ic_id})
        return self.assign(obs) or Action(name="wait")


class Random(TrustAll):
    """Uniform over a finite catalog of legal actions with templated string arguments."""

    def __init__(self, seed=0):
        super().__init__(seed)
        self.rng = np.random.default_rng(seed)

    def act(self, observation, history):
        obs = observation
        self.preprocess(obs)
        free = [ic for ic in obs.roster if ic.current_task is None]
        actions = [
            Action(name="wait"),
            Action(name="ship"),
            Action(name="read_policy_doc"),
            Action(name="report", args={"text": "Work status is not independently verified."}),
        ]
        for ic in obs.roster:
            actions.append(Action(name="status", args={"ic_id": ic.ic_id}))
            if (ic.current_task or ic.last_status) and obs.budgets.compute >= obs.costs.get("audit", 2):
                actions.append(Action(name="audit", args={"ic_id": ic.ic_id}))
            if (ic.last_status or {}).get("claims_done"):
                actions.append(
                    Action(
                        name="coach_ic",
                        args={"ic_id": ic.ic_id, "text": "Please verify completion before reporting."},
                    )
                )
        for task in obs.tasks:
            if task.status in ("assigned", "blocked", "done_claimed"):
                actions.append(Action(name="cancel", args={"task_id": task.task_id}))
                owner = next(
                    (
                        ic.ic_id
                        for ic in obs.roster
                        if ic.current_task == task.task_id
                        or (ic.last_status or {}).get("task_id") == task.task_id
                    ),
                    None,
                )
                if owner and obs.budgets.compute >= obs.costs.get("reassign", 1):
                    for ic in free:
                        if ic.ic_id != owner:
                            actions.append(
                                Action(name="reassign", args={"task_id": task.task_id, "new_ic_id": ic.ic_id})
                            )
            if task.status in ("unassigned", "cancelled"):
                for ic in free:
                    for detail in range(4):
                        if obs.budgets.compute >= detail * obs.costs.get("per_spec_level", 0.25):
                            actions.append(
                                Action(
                                    name="assign",
                                    args={
                                        "ic_id": ic.ic_id,
                                        "task_id": task.task_id,
                                        "spec_detail": detail,
                                        "spec_flags": sorted(self.flags),
                                        "force": True,
                                    },
                                )
                            )
        for h in obs.humans:
            actions.append(
                Action(name="ask_human", args={"human_id": h["human_id"], "question": "What are the risks?"})
            )
        for event in self.events.values():
            if event.deadline_tick is not None and obs.tick >= event.deadline_tick:
                continue
            if not any(
                h["action"]["name"] == "escalate" and h["action"]["args"].get("event_id") == event.event_id
                for h in history
            ):
                actions.append(
                    Action(name="escalate", args={"event_id": event.event_id, "framing": "Please decide."})
                )
        return actions[int(self.rng.integers(len(actions)))]
