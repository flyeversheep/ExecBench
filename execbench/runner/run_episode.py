import gzip
from pathlib import Path

from execbench.env.env import ExecEnv
from execbench.llm.client import LLMClient
from execbench.policies.baselines import AuditAll, Heuristic, Random, TrustAll
from execbench.policies.llm_policy import LLMPolicy, ParseFailure
from execbench.policies.oracle import Oracle
from execbench.schemas import EpisodeTrace, Scenario

BASELINES = {"trust_all": TrustAll, "audit_all": AuditAll, "heuristic": Heuristic, "random": Random}


def read_scenario(path):
    return Scenario.model_validate_json(Path(path).read_text())


def run_episode(scenario, policy="heuristic", grade=True, client=None, grader_client=None):
    env = ExecEnv(scenario, grader_client=grader_client)
    if isinstance(policy, str):
        name = policy
        if policy == "oracle":
            instance = Oracle(env)
        elif policy in BASELINES:
            instance = BASELINES[policy](scenario.seed)
        else:
            informed = policy.endswith(":informed")
            model = policy.removesuffix(":informed")
            instance = LLMPolicy(client or LLMClient(model), informed=informed)
    else:
        instance, name = policy, type(policy).__name__
    obs = env.steps[0].observation
    history = []
    while not env.terminated:
        try:
            action = instance.act(obs, history)
            obs = env.step(action, getattr(instance, "calls", []))
        except ParseFailure:
            obs = env.parse_failure(instance.calls)
            action = env.steps[-1].action
        history.append({"action": action.model_dump(mode="json"), "observation": obs.model_dump(mode="json")})
    trace = env.trace(name)
    if grade:
        from execbench.graders.scorecard import score

        score(trace, scenario, grader_client)
    return trace


def write_trace(trace, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = trace.model_dump_json().encode()
    if path.suffix == ".gz":
        data = gzip.compress(data, mtime=0)
    path.write_bytes(data)
    return path


def read_trace(path):
    path = Path(path)
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return EpisodeTrace.model_validate_json(data)
