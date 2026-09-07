import json
from datetime import datetime, timezone
from pathlib import Path

import typer

from execbench.gen.scenario_gen import generate_set
from execbench.llm.client import (
    DEFAULT_GRADER_MODEL,
    LLMClient,
    build_grader_client,
    resolve_grader_model,
)
from execbench.runner.leaderboard import leaderboard
from execbench.runner.run_benchmark import run_benchmark, slug
from execbench.runner.run_episode import read_scenario, run_episode, write_trace
from execbench.schemas import SimConfig
from execbench.viewer.trace_viewer import render_trace

app = typer.Typer(
    pretty_exceptions_show_locals=False,
    no_args_is_help=True,
    help="ExecBench: evaluating executive management through controlled simulation.",
)


@app.command("generate")
def generate_cmd(
    out: Path = Path("scenarios/v0"),
    count: int = typer.Option(50, min=1),
    seed: int = 1000,
    memory_model: str | None = typer.Option(
        None, help="Memory rendering model, using the grader API settings; omit for template memory."
    ),
    config: Path | None = None,
):
    paths = generate_set(
        out, count, seed, build_grader_client(memory_model) if memory_model else None, SimConfig.from_file(config)
    )
    typer.echo(f"Generated {len(paths)} scenarios in {out}")


@app.command("run-episode")
def episode_cmd(
    scenario: Path,
    policy: str = "heuristic",
    out: Path = Path("traces"),
    grader_model: str | None = typer.Option(
        None, help=f"Judge model for report/coaching grades (default {DEFAULT_GRADER_MODEL}; 'none' disables)."
    ),
):
    grader_model = resolve_grader_model(grader_model)
    trace = run_episode(read_scenario(scenario), policy, grader_client=build_grader_client(grader_model))
    path = write_trace(trace, out / f"{trace.scenario_id}__{slug(policy)}.json.gz")
    path.with_name(path.name.removesuffix(".json.gz") + ".scores.json").write_text(
        json.dumps(trace.scores, indent=2)
    )
    typer.echo(str(path))
    typer.echo(json.dumps(trace.scores, indent=2))


@app.command("run-benchmark")
def benchmark_cmd(
    scenario_set: Path = Path("scenarios/v0"),
    policies: str = "oracle,heuristic,trust_all,audit_all,random",
    out: Path | None = None,
    workers: int = typer.Option(8, min=1),
    grader_model: str | None = typer.Option(
        None, help=f"Judge model for report/coaching grades (default {DEFAULT_GRADER_MODEL}; 'none' disables)."
    ),
):
    out = out or Path("results") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows = run_benchmark(scenario_set, policies.split(","), out, workers, resolve_grader_model(grader_model))
    leaderboard(out)
    failed = sum(r["status"] != "ok" for r in rows)
    typer.echo(f"{len(rows) - failed} completed, {failed} failed. Results: {out}")
    if failed:
        raise typer.Exit(1)


@app.command("leaderboard")
def leaderboard_cmd(results: Path):
    leaderboard(results)
    typer.echo(str(results / "leaderboard.md"))


@app.command("view")
def view_cmd(trace: Path, out: Path = Path("trace.html")):
    typer.echo(str(render_trace(trace, out)))


@app.command("check-api")
def check_api(model: str = "glm-4.7"):
    result = LLMClient(model).complete(
        [{"role": "user", "content": "Reply with the single word OK."}], max_tokens=32
    )
    typer.echo(json.dumps({k: result[k] for k in ["text", "usage", "cached", "cost_usd"]}))


if __name__ == "__main__":
    app()
