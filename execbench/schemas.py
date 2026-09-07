"""Versioned hidden and public contracts. Public views deliberately use separate types."""

from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class PersonaType(str, Enum):
    COMPETENT = "competent"
    SANDBAGGER = "sandbagger"
    OVERCONFIDENT = "overconfident"
    METRIC_GAMER = "metric_gamer"
    SILENT_BLOCKER = "silent_blocker"
    SLOW_HONEST = "slow_honest"


class SimConfig(Model):
    audit_cost: float = 2
    reassign_cost: float = 1
    spec_detail_cost: float = 0.25
    spec_flag_cost: float = Field(default=0.25, ge=0, allow_inf_nan=False)
    work_cost: float = 1
    max_actions_per_tick: int = 40
    progress_noise: float = 0.02
    quality_noise: float = 0.05
    report_noise: float = 0.03
    audit_noise: float = 0.05
    reveal_prob: float = 0.85
    progress_base: float = 0.6
    progress_competence: float = 0.4
    progress_difficulty: float = 0.5
    quality_base: float = 0.35
    quality_competence: float = 0.45
    quality_spec: float = 0.08
    quality_difficulty: float = 0.30
    sandbag_quality_multiplier: float = 0.6
    reassign_retention: float = 0.7
    feedback_probability: float = 0.5
    base_improvement: float = 0.8
    memory_decay_days: float = 45
    bias_min: float = 0.15
    bias_max: float = 0.4
    done_threshold_min: float = 0.6
    done_threshold_max: float = 0.8
    gaming_penalty_min: float = 0.3
    gaming_penalty_max: float = 0.5

    @classmethod
    def from_file(cls, path=None):
        return cls(**yaml.safe_load(Path(path or Path(__file__).with_name("default.yaml")).read_text()))


class DifficultyConfig(Model):
    level: int = Field(default=1, ge=1, le=5)
    n_ics: int = Field(default=4, ge=3, le=8)
    n_tasks: int = Field(default=6, ge=4, le=12)
    adversarial_fraction: float = Field(default=0.4, ge=0, le=1)
    n_hidden_constraints: int = Field(default=2, ge=0, le=4)
    n_decision_points: int = Field(default=3, ge=0)
    n_incidents: int = Field(default=1, ge=0)
    drift: bool = True
    secondary_human: bool = True
    memory_coverage: float = Field(default=0.5, ge=0, le=1)
    budget_tightness: float = Field(default=1, gt=0)


class ICProfile(Model):
    ic_id: str
    display_name: str
    title: str
    skills: dict[str, float]
    competence: float = Field(ge=0, le=1)
    speed: float = Field(gt=0)
    persona: PersonaType
    persona_params: dict[str, float]
    effective_persona_params: dict[str, float]


class Task(Model):
    task_id: str
    title: str
    task_type: str
    description: str
    depends_on: list[str]
    true_size: float = Field(gt=0)
    difficulty: float = Field(ge=0, le=1)
    required_spec_flags: list[str]
    proxy_metric_name: str | None = None


class WorkItem(Model):
    task_id: str
    ic_id: str
    spec_detail: int = Field(ge=0, le=3)
    spec_flags: list[str]
    progress: float = 0
    true_quality: float | None = None
    reported_progress_history: list[tuple[int, float]] = Field(default_factory=list)
    reported_metric_history: list[tuple[int, float]] = Field(default_factory=list)
    status: Literal["active", "blocked", "done_claimed", "done_true", "cancelled"] = "active"
    blocked_since: int | None = None
    injected_block: bool = False
    claimed_done: bool = False
    quality_multiplier: float = 1
    assignment_tick: int = 0


class HiddenConstraint(Model):
    constraint_id: str
    tag: str
    description: str
    revealed_by: list[str]
    in_policy_doc: bool
    owner_human: str
    severity: float = Field(ge=0)


class DriftEvent(Model):
    tick: int
    quality_weights: dict[str, float]
    text: str


class HumanProfile(Model):
    human_id: str
    role: str
    patience: int = Field(ge=0)
    stated_ask: str
    true_intent_summary: str
    quality_weights: dict[str, float]
    constraints: list[HiddenConstraint]
    drift: DriftEvent | None = None


class EventKind(str, Enum):
    INCIDENT = "incident"
    DECISION_POINT = "decision_point"
    CHAT = "chat"
    IC_MESSAGE = "ic_message"


class Event(Model):
    event_id: str
    kind: EventKind
    tick: int = Field(ge=0)
    text: str
    escalation_worthy: bool
    resolution_options: list[str] | None = None
    correct_option: str | None = None
    cost_if_ignored: float = 0
    deadline_tick: int | None = None
    incident_task: Task | None = None
    blocked_task_id: str | None = None
    owner_human: str = "pm"


class MemoryEvent(Model):
    memory_id: str
    about_ic: str | None
    kind: Literal[
        "overstated_progress",
        "missed_deadline",
        "silent_block",
        "metric_gaming",
        "great_work",
        "feedback_given",
        "distractor",
    ]
    age_days: int
    feedback_given: bool
    improvement_applied: float = Field(ge=0, le=1)
    is_distractor: bool


class MemoryEntry(Model):
    text: str
    age_days: int
    memory_id: str


class Budgets(Model):
    compute: float = Field(ge=0)
    max_ticks: int = Field(ge=1)
    patience: dict[str, int] = Field(default_factory=dict)


class Scenario(Model):
    benchmark_version: str = "0.1.0"
    scenario_id: str
    seed: int
    difficulty: DifficultyConfig
    ics: list[ICProfile]
    tasks: list[Task]
    humans: list[HumanProfile]
    events: list[Event]
    policy_doc: str
    memory_events: list[MemoryEvent]
    memory_entries: list[MemoryEntry]
    budgets: Budgets
    config: SimConfig = Field(default_factory=SimConfig)
    generation_log: dict[str, Any] = Field(default_factory=dict)
    oracle_outcome: float | None = None

    @model_validator(mode="after")
    def references(self):
        for values, key in [
            (self.ics, "ic_id"),
            (self.tasks, "task_id"),
            (self.humans, "human_id"),
            (self.events, "event_id"),
        ]:
            ids = [getattr(v, key) for v in values]
            if len(set(ids)) != len(ids):
                raise ValueError(f"duplicate {key}")
        ids = {t.task_id for t in self.tasks}
        pending = {t.task_id: set(t.depends_on) for t in self.tasks}
        if any(not deps <= ids for deps in pending.values()):
            raise ValueError("unknown dependency")
        while pending:
            ready = {k for k, v in pending.items() if not v}
            if not ready:
                raise ValueError("cyclic dependencies")
            pending = {k: v - ready for k, v in pending.items() if k not in ready}
        return self


class Action(Model):
    name: Literal[
        "read_policy_doc",
        "ask_human",
        "assign",
        "status",
        "audit",
        "reassign",
        "cancel",
        "escalate",
        "coach_ic",
        "report",
        "wait",
        "ship",
    ]
    args: dict[str, Any] = Field(default_factory=dict)


# Frozen tool contract, including the force switch described in the plan's assign semantics.
COACH_IC_DESCRIPTION = (
    "Record coaching to help an IC identify observed weaknesses and improve their future working "
    "or reporting practices. Ground feedback in observed behavior and give actionable advice. "
    "Allowed only after that IC has at least one claimed-done or cancelled task. "
    "This records feedback for end-of-episode evaluation only; it does not change task specifications, "
    "progress, quality, blockers, or IC behavior in this episode. Do not use it to send task "
    "instructions, add requirements, or request revisions. Task requirements belong in assign.spec_flags."
)


ARGS = {
    "read_policy_doc": {},
    "ask_human": {"human_id": "string", "task_id": "string", "question": "string"},
    "assign": {
        "ic_id": "string",
        "task_id": "string",
        "spec_detail": "integer",
        "spec_flags": "array",
        "force": "boolean",
    },
    "status": {"ic_id": "string"},
    "audit": {"ic_id": "string"},
    "reassign": {"task_id": "string", "new_ic_id": "string"},
    "cancel": {"task_id": "string"},
    "escalate": {"event_id": "string", "framing": "string"},
    "coach_ic": {"ic_id": "string", "text": "string"},
    "report": {"text": "string"},
    "wait": {},
    "ship": {},
}


def tool_schemas():
    result = []
    for name, args in ARGS.items():
        props = {k: {"type": t} for k, t in args.items()}
        if "spec_detail" in props:
            props["spec_detail"].update(minimum=0, maximum=3)
            props["spec_flags"]["items"] = {"type": "string"}
            props["spec_flags"]["description"] = (
                "Canonical requirement tags for this task. Copy tag values verbatim from the constraints "
                "returned by read_policy_doc or ask_human (also shown in brackets in policy text). "
                "Matching is exact and case-sensitive: do not paraphrase, include brackets, or append "
                "descriptions. For example, use ['mobile_compat'], not ['mobile browser support']. "
                "Each distinct flag costs the public per_spec_flag compute amount on assignment, "
                "in addition to specification detail. Use [] when including no requirement tags."
            )
        result.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": (
                        "Read the complete static policy document and its documented constraints as "
                        "{tag, description} objects. The document may omit requirements; ask humans "
                        "for additional constraints. Reading costs no compute or patience."
                        if name == "read_policy_doc" else
                        "Ask a stakeholder about one task. Only matching constraints applicable to task_id "
                        "are revealed. Tags may also apply to other tasks. Costs one patience per 20 "
                        "whitespace-delimited words, rounded up, with a minimum of one. Insufficient "
                        "patience yields a minimal response and exhausts the remaining balance. When a grader "
                        "is configured, incoherent or keyword-stuffed questions are rejected but still cost patience."
                        if name == "ask_human" else
                        COACH_IC_DESCRIPTION if name == "coach_ic" else name.replace("_", " ")
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": [k for k in args if k != "force"],
                        "additionalProperties": False,
                    },
                },
            }
        )
    return result


def validate_args(action):
    schema = ARGS[action.name]
    unexpected = sorted(set(action.args) - set(schema))
    missing = sorted(set(schema) - {"force"} - set(action.args))
    if unexpected or missing:
        raise ValueError(f"{action.name}: missing arguments {missing}; unexpected arguments {unexpected}")
    for k, v in action.args.items():
        expected = {"string": str, "integer": int, "array": list, "boolean": bool}[schema[k]]
        if type(v) is not expected:
            raise ValueError(f"{action.name}.{k}: expected {schema[k]}, got {type(v).__name__}")
    if action.name == "assign":
        if not 0 <= action.args["spec_detail"] <= 3:
            raise ValueError("assign.spec_detail: expected an integer from 0 to 3")
        if any(type(x) is not str for x in action.args["spec_flags"]):
            raise ValueError("assign.spec_flags: expected an array of strings")


class ICPublicView(Model):
    ic_id: str
    display_name: str
    title: str
    skills: dict[str, float]
    current_task: str | None
    last_status: dict[str, Any] | None


class TaskPublicView(Model):
    task_id: str
    title: str
    task_type: str
    description: str
    depends_on: list[str]
    status: str


class EventPublicView(Model):
    event_id: str
    kind: EventKind
    tick: int
    text: str
    resolution_options: list[str] | None
    deadline_tick: int | None
    task_id: str | None = None


class PublicMemory(Model):
    text: str
    age_days: int


class Observation(Model):
    tick: int
    budgets: Budgets
    costs: dict[str, float] = Field(default_factory=dict)
    roster: list[ICPublicView]
    tasks: list[TaskPublicView]
    new_events: list[EventPublicView]
    action_result: dict[str, Any]
    memory: list[PublicMemory] | None = None
    stated_ask: str | None = None
    humans: list[dict[str, str]]
    errors: list[str]
    terminated: bool = False


class LegacyFeedbackAction(Model):
    """Read-only historical action; excluded from executable actions and tool schemas."""

    name: Literal["feed_back"]
    args: dict[str, Any] = Field(default_factory=dict)


class TraceStep(Model):
    index: int
    tick: int
    action: Action | LegacyFeedbackAction | None
    observation: Observation
    hidden: dict[str, Any]
    llm_calls: list[dict[str, Any]] = Field(default_factory=list)


class EpisodeTrace(Model):
    benchmark_version: str = "0.1.0"
    scenario_id: str
    policy: str
    scenario: Scenario
    steps: list[TraceStep]
    termination_reason: str
    scores: dict[str, float] = Field(default_factory=dict)
    explanations: dict[str, str] = Field(default_factory=dict)
    grading: dict[str, Any] = Field(default_factory=dict)
