import json
import os
from copy import deepcopy

from execbench.llm.client import prompt
from execbench.schemas import Action, tool_schemas, validate_args


class ParseFailure(Exception):
    pass


class LLMPolicy:
    def __init__(self, client, informed=False, history_chars=None):
        self.client = client
        self.history_chars = history_chars or int(os.getenv("EXECBENCH_HISTORY_CHARS", "60000"))
        self.system = prompt("exec_system.md") + ("\n" + prompt("exec_informed.md") if informed else "")
        self.initial = None
        self.calls = []
        self.turns = []
        self.pending = []
        self.pending_tool_call_id = None

    def act(self, observation, history):
        if self.initial is None:
            self.initial = observation.model_dump(mode="json")
        elif self.pending:
            # Complete the previous turn only after the environment has executed it.
            # Store new messages rather than modifying any previously sent request.
            if self.pending_tool_call_id:
                result_message = {
                    "role": "tool",
                    "tool_call_id": self.pending_tool_call_id,
                    "content": json.dumps(observation.model_dump(mode="json")),
                }
            else:
                # Parse failures produce a harness-forced wait, not an executed model tool call.
                # Text-only custom clients also use this explicit action/observation record.
                result_message = {"role": "user", "content": json.dumps(history[-1])}
            self.turns.append([*self.pending, result_message])
            self.pending = []
            self.pending_tool_call_id = None
        recent = list(history)
        # Deterministic compact journal preserves earlier decisions and observations; no hidden-state summary.
        discarded = []
        while recent and len(json.dumps(recent)) > self.history_chars:
            item = recent.pop(0)
            discarded.append(
                {
                    "tick": item["observation"]["tick"],
                    "action": item["action"],
                    "result": item["observation"]["action_result"],
                    "events": item["observation"]["new_events"],
                    "errors": item["observation"]["errors"],
                }
            )
        messages = [
            {"role": "system", "content": self.system},
            {"role": "user", "content": json.dumps({"initial": self.initial})},
        ]
        if discarded:
            messages.append({"role": "user", "content": json.dumps({"earlier_journal": discarded})})
        messages.extend(m for turn in self.turns[len(discarded):] for m in turn)
        if history and not recent:
            # An unusually small window can discard even the newest observation.
            messages.append({"role": "user", "content": json.dumps({
                "current": observation.model_dump(mode="json"),
            })})
        prefix_length = len(messages)
        start = len(self.client.calls)
        for attempt in range(3):
            result = self.client.complete(messages, tools=tool_schemas(), max_tokens=2048)
            try:
                if len(result["tool_calls"]) != 1:
                    raise ValueError(
                        f"You returned {len(result['tool_calls'])} tool calls; exactly one is required"
                    )
                action = Action.model_validate(result["tool_calls"][0])
                validate_args(action)
                ids = result.get("tool_call_ids", [])
                if ids and ids[0]:
                    assistant = deepcopy(result["assistant_message"])
                    self.pending_tool_call_id = ids[0]
                else:
                    assistant = {"role": "assistant", "content": json.dumps(result["tool_calls"])}
                self.pending = [*messages[prefix_length:], assistant]
                self.calls = self.client.calls[start:]
                return action
            except (ValueError, TypeError) as exc:
                # Use a fresh list so saved request records retain the messages actually sent.
                # Rejected proposals are text, not executed tool turns with fabricated results.
                messages = [*messages,
                    {
                        "role": "assistant",
                        "content": json.dumps(result["tool_calls"]) if result["tool_calls"] else result["text"],
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Invalid response: {exc}. No tool calls were executed; "
                            "the simulation has not advanced. "
                            "Return exactly one valid tool call matching its argument schema. "
                            "Wait for its result before proposing another action."
                        ),
                    },
                ]
        self.pending = messages[prefix_length:]
        self.calls = self.client.calls[start:]
        raise ParseFailure()
