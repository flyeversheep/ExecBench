import json
import os

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

    def act(self, observation, history):
        if self.initial is None:
            self.initial = observation.model_dump(mode="json")
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
        payload = {
            "initial": self.initial,
            "earlier_journal": discarded,
            "recent_history": recent,
            "current": observation.model_dump(mode="json"),
        }
        messages = [
            {"role": "system", "content": self.system},
            {"role": "user", "content": json.dumps(payload)},
        ]
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
                self.calls = self.client.calls[start:]
                return action
            except (ValueError, TypeError) as exc:
                # Use a fresh list so saved request records retain the messages actually sent.
                # Rejected proposals are text, not executed tool turns with fabricated results.
                if attempt == 2:
                    break
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
        self.calls = self.client.calls[start:]
        raise ParseFailure()
