from typing import Protocol

from execbench.schemas import Action, Observation


class Policy(Protocol):
    def act(self, observation: Observation, history: list[dict]) -> Action: ...
