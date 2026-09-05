"""Self-contained, offline trace viewer. All scenario/model text is escaped by Jinja."""

from pathlib import Path

from jinja2 import Environment, select_autoescape

from execbench.graders.outcome import raw_outcome
from execbench.runner.run_episode import read_trace

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ExecBench · {{ trace.scenario_id }} · {{ trace.policy }}</title>
<style>
:root{color-scheme:dark;--bg:#0d1420;--panel:#151f2e;--line:#2c3b50;--muted:#a1b1c6;--red:#ff979b;--green:#84e1bd}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#e4edf7;font:14px/1.5 system-ui,sans-serif}
header{padding:32px 5vw 24px;border-bottom:1px solid var(--line);background:#111c2b}h1{font-size:30px;margin:8px 0}
.kicker{font-size:12px;letter-spacing:.16em;color:var(--green);text-transform:uppercase}.muted{color:var(--muted)}
main{max-width:1500px;margin:auto;padding:24px 4vw}.metrics{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}
.metric{background:var(--panel);padding:12px 18px;border:1px solid var(--line);border-radius:10px;min-width:130px}
.metric strong{display:block;font-size:24px}.toolbar{position:sticky;top:0;background:var(--bg);padding:14px 0;z-index:2;display:flex;gap:20px;align-items:center;border-bottom:1px solid var(--line)}
input[type=search]{background:var(--panel);border:1px solid var(--line);color:inherit;padding:10px;border-radius:6px;width:300px}
.columns,.step{display:grid;grid-template-columns:1fr 1fr;gap:16px}.columns{font-size:12px;letter-spacing:.08em;color:var(--muted);padding:16px 0;text-transform:uppercase}
.step{margin:0 0 16px;scroll-margin-top:70px}.card{border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:16px;min-width:0}
.step.alert .truth{border-color:#aa525a}.step-title{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px}
.pill{display:inline-block;font-size:11px;background:#28384c;border-radius:20px;padding:3px 9px}.danger{color:var(--red)}
.recovery{color:var(--green);padding:8px 0}.notice{border-left:3px solid var(--red);padding:8px 12px;background:#43242d;margin:10px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.55 ui-monospace,monospace;margin:8px 0}
summary{cursor:pointer;color:var(--muted);padding:6px 0}table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;border-bottom:1px solid var(--line);padding:8px 5px}th{color:var(--muted)}
.bar{height:5px;background:#344257;border-radius:4px;min-width:50px}.bar span{display:block;background:var(--green);height:5px;border-radius:4px}
.event{border-left:3px solid #8dadff;padding:6px 10px;margin:8px 0}a{color:#9fcbff}.hidden{display:none}footer{padding:24px;color:var(--muted)}
@media(max-width:760px){.columns{display:none}.step{grid-template-columns:1fr}.toolbar{flex-wrap:wrap}.metrics{gap:6px}.metric{min-width:100px}h1{font-size:23px}main{padding:16px}}
</style></head><body><header><div class="kicker">ExecBench / executive management evaluation</div>
<h1>{{ trace.policy }} <span class="muted">· {{ trace.scenario_id }}</span></h1>
<p>{{ trace.scenario.humans[0].stated_ask }}</p><div class="muted">Difficulty {{ trace.scenario.difficulty.level }} · Seed {{ trace.scenario.seed }} · {{ trace.steps|length }} observations · Ended by {{ trace.termination_reason }}</div>
<div class="metrics">{% for name in ['outcome','escalation_f1','detection_rate','regret','compute_fraction'] %}<div class="metric"><span class="muted">{{ name|replace('_',' ') }}</span><strong>{{ '%.2f'|format(trace.scores[name]) if name in trace.scores else '—' }}</strong></div>{% endfor %}</div>
</header><main><details><summary>How to read this trace</summary><p>Left: the executive's actual observations and actions. Right: simulator truth at the same step. Red notices identify materially misleading reports, defaulted decisions, and undiscovered requirements. Hidden truth was never supplied to the policy. The privileged oracle is labeled separately.</p></details>
<details><summary>Worker identities and hidden profiles</summary><table><tr><th>Worker</th><th>Persona</th><th>Competence</th><th>Speed</th><th>Effective parameters</th></tr>{% for ic in trace.scenario.ics %}<tr><td>{{ ic.display_name }}</td><td>{{ ic.persona.value }}</td><td>{{ '%.2f'|format(ic.competence) }}</td><td>{{ '%.2f'|format(ic.speed) }}</td><td>{{ ic.effective_persona_params }}</td></tr>{% endfor %}</table></details>
<div class="toolbar"><input type="search" id="search" placeholder="Search task, worker, action…" aria-label="Search trace"><label><input type="checkbox" id="alerts"> Show divergences only</label><span class="muted" id="count"></span></div>
<div class="columns"><div>Executive view / observations & decisions</div><div>Hidden truth / what actually happened</div></div>
{% for row in rows %}{% set step = row.step %}<section class="step {{ 'alert' if row.alert else '' }}" id="step-{{ step.index }}">
<div class="card"><div class="step-title"><strong>{{ step.action.name if step.action else 'Project briefing' }}</strong><span class="pill">Day {{ step.tick }} · #{{ step.index }}</span></div>
<div class="muted">Compute {{ '%.1f'|format(step.observation.budgets.compute) }} · Patience {{ step.observation.budgets.patience }}</div>
{% if step.action %}<pre>{{ step.action.args|tojson(indent=2) }}</pre>{% endif %}
{% if step.observation.errors %}<div class="notice">{{ step.observation.errors|join('; ') }}</div>{% endif %}
{% if step.observation.action_result %}<pre>{{ step.observation.action_result|tojson(indent=2) }}</pre>{% endif %}
{% for event in step.observation.new_events %}<div class="event"><strong>{{ event.event_id }}</strong> · {{ event.text }}{% if event.deadline_tick %}<br><span class="muted">Deadline day {{ event.deadline_tick }}</span>{% endif %}</div>{% endfor %}
{% if step.action and step.action.name == 'wait' %}<table><tr><th>Worker / task</th><th>Reported progress</th><th>Proxy metric</th><th>Claim</th></tr>{% for ic in step.observation.roster %}{% if ic.last_status %}<tr><td>{{ ic.ic_id }} / {{ ic.last_status.task_id }}</td><td>{{ '%.0f'|format(ic.last_status.progress*100) }}%</td><td>{{ '%.2f'|format(ic.last_status.metric) }}</td><td>{{ 'Done' if ic.last_status.claims_done else ('Blocked' if ic.last_status.blocked else 'In progress') }}</td></tr>{% endif %}{% endfor %}</table>{% endif %}
{% if step.observation.memory %}<details open><summary>Organizational memory</summary>{% for m in step.observation.memory %}<p>{{ m.text }}</p>{% endfor %}</details>{% endif %}
<details><summary>Full public observation</summary><pre>{{ step.observation.model_dump(mode='json')|tojson(indent=2) }}</pre></details>
{% if step.llm_calls %}<details><summary>Model prompts & responses ({{ step.llm_calls|length }})</summary><pre>{{ step.llm_calls|tojson(indent=2) }}</pre></details>{% endif %}</div>
<div class="card truth"><div class="step-title"><strong>Simulator state</strong><a href="#step-{{ step.index }}">#{{ step.index }}</a></div>
{% for report in row.misleading %}<div class="notice"><strong>{{ report.ic_id }} · {{ report.kind }}</strong><br>Reported {{ '%.0f'|format(report.reported_progress*100) }}% · Actual {{ '%.0f'|format(report.true_progress*100) }}% · Proxy {{ '%.2f'|format(report.reported_metric) }}{% if report.quality is not none %} · Quality {{ '%.2f'|format(report.quality) }}{% endif %}</div>{% endfor %}
{% if row.corrective %}<div class="recovery">Corrective action: {{ step.action.name }} targets an IC with an earlier material misreport.</div>{% endif %}
{% for text in row.notices %}<div class="notice">{{ text }}</div>{% endfor %}
<table><tr><th>Task / worker</th><th>Actual progress</th><th>Quality</th><th>State</th></tr>{% for tid,w in step.hidden.work.items() %}<tr><td>{{ tid }}<br><span class="muted">{{ w.ic_id }}</span></td><td>{{ '%.0f'|format(w.progress*100) }}%<div class="bar"><span style="width:{{ w.progress*100 }}%"></span></div></td><td>{{ '%.2f'|format(w.true_quality) if w.true_quality is not none else '—' }}</td><td>{{ w.status }}</td></tr>{% endfor %}</table>
{% if row.unknown %}<p class="muted">Undiscovered requirements: <span class="danger">{{ row.unknown|join(', ') }}</span></p>{% endif %}
<details><summary>Full hidden snapshot</summary><pre>{{ step.hidden|tojson(indent=2) }}</pre></details></div></section>{% endfor %}
<details><summary>Score explanations & grader evidence</summary><pre>{{ trace.explanations|tojson(indent=2) }}</pre><pre>{{ trace.grading|tojson(indent=2) }}</pre></details>
</main><footer>ExecBench v{{ trace.benchmark_version }} · Standalone, offline trace · Public observations and privileged truth are intentionally separated.</footer>
<script>const steps=[...document.querySelectorAll('.step')];const searchable=new Map(steps.map(s=>[s,s.innerText.toLowerCase()]));function filter(){const q=document.querySelector('#search').value.toLowerCase(),alerts=document.querySelector('#alerts').checked;let n=0;steps.forEach(s=>{const show=(!alerts||s.classList.contains('alert'))&&searchable.get(s).includes(q);s.classList.toggle('hidden',!show);if(show)n++});document.querySelector('#count').textContent=n+' / '+steps.length+' steps'}document.querySelector('#search').addEventListener('input',filter);document.querySelector('#alerts').addEventListener('change',filter);filter();</script></body></html>"""


def render_trace(trace, output):
    if not hasattr(trace, "steps"):
        trace = read_trace(trace)
    rows = []
    constraints = [c for h in trace.scenario.humans for c in h.constraints]
    for step in trace.steps:
        misleading = [r for r in step.hidden["misreports"] if r["material"] and r["step_index"] == step.index]
        notices = []
        for eid, resolution in step.hidden["resolutions"].items():
            if resolution.get("source") == "default" and resolution["tick"] == step.tick:
                e = next(e for e in trace.scenario.events if e.event_id == eid)
                if e.escalation_worthy:
                    notices.append(f"Missed escalation: {eid}; default resolution applied.")
        _, detail = raw_outcome(step.hidden, trace.scenario)
        if detail["violated_constraints"]:
            notices.append(
                "Completed work missing requirement flags: " + ", ".join(detail["violated_constraints"])
            )
        unknown = [c.tag for c in constraints if c.tag not in step.hidden["revealed_constraints"]]
        corrective = False
        if (
            step.action
            and step.action.name in ("audit", "reassign", "cancel", "feed_back")
            and not step.observation.errors
        ):
            target = step.action.args.get("ic_id")
            if step.action.name in ("reassign", "cancel") and step.index:
                target = (
                    trace.steps[step.index - 1]
                    .hidden["work"]
                    .get(step.action.args["task_id"], {})
                    .get("ic_id")
                )
            corrective = any(
                r["material"] and r["ic_id"] == target and r["step_index"] < step.index
                for r in step.hidden["misreports"]
            )
        rows.append(
            {
                "step": step,
                "misleading": misleading,
                "notices": notices,
                "unknown": unknown,
                "alert": bool(misleading or notices or corrective),
                "corrective": corrective,
            }
        )
    html = (
        Environment(autoescape=select_autoescape(default=True))
        .from_string(TEMPLATE)
        .render(trace=trace, rows=rows)
    )
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)
    return path
