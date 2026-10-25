"""Run the graph on the labeled query set and report the eight eval metrics.

Usage (from backend/):
    python -m evals.run_eval [--kind shopping|knowledge|general] [--case ID] [--limit N]

Calls the real Gemini API and Tavily. Each run stops at the human-approval pause. Labels live in
cases.json and the metrics are described in docs/eval.md.
"""

import argparse
import json
import math
import statistics
import time
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.graph.graph import build_graph
from app.schemas.recommendation import NO_PRODUCT
from evals.judge import judge_purpose

_HERE = Path(__file__).parent
_KINDS = ("shopping", "knowledge", "general")
_BUDGET_WORDS = ("budget", "ngân sách")
# Summary metric -> the per-run check it is the rate of
_RATES = {"intent_accuracy": "intent", "budget_accuracy": "budget", "tool_accuracy": "tools",
          "grounded_rate": "grounded", "budget_compliance": "budget_compliant"}


# --- running --------------------------------------------------------------------------------------


def run_case(graph, case: dict) -> dict:
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    events: list[dict] = []
    started = time.perf_counter()
    try:
        events.extend(graph.stream({"query": case["query"]}, config, stream_mode="custom"))
        error = None
    except Exception as exc:  # noqa: BLE001 - recorded as a failed case, the run continues
        error = f"{type(exc).__name__}: {exc}"
    latency = round(time.perf_counter() - started, 1)

    state = graph.get_state(config).values
    judgement = _judge(state) if error is None and state.get("intent") == "shopping" else None
    return score_case(case, state, events, latency, error, judgement)


def _judge(state: dict) -> dict | None:
    """The LLM judge's view of the final answer; None if the judge call itself fails, which is not the case's fault."""
    try:
        return judge_purpose(state).model_dump()
    except Exception as exc:  # noqa: BLE001 - a judge outage leaves purpose_fit unknown for this case
        print(f"judge failed: {type(exc).__name__}: {str(exc)[:200]}")
        return None


# --- scoring (pure, unit-tested offline) ----------------------------------------------------------


def _checks(expect: dict, state: dict, tools_called: set[str]) -> dict[str, bool | None]:
    """Pass/fail per check; None means it does not apply to this run.

    intent, budget and tools compare with the case's labels; grounded and budget_compliant hold for
    every shopping answer.
    """
    checks: dict[str, bool | None] = dict.fromkeys(_RATES.values())
    if "intent" in expect:
        checks["intent"] = state.get("intent") == expect["intent"]
    if "budget_vnd" in expect:
        expected, actual = expect["budget_vnd"], state.get("budget")
        checks["budget"] = actual is None if expected is None else actual is not None and math.isclose(
            actual, expected, rel_tol=0.01)
    if "tools" in expect:
        checks["tools"] = set(expect["tools"]) <= tools_called

    if state.get("intent") != "shopping":
        return checks
    recommendation = state.get("recommendation") or {}
    web_urls = {r["url"] for r in state.get("web_results", [])}
    url = recommendation.get("url")
    checks["grounded"] = all(p["source_url"] in web_urls for p in state.get("products", [])) and (
        not url or url in web_urls)

    price, budget = recommendation.get("price"), state.get("budget")
    if recommendation.get("product_name") not in (None, NO_PRODUCT) and price is not None and budget:
        disclosed = any(word in t.lower() for t in recommendation.get("tradeoffs", []) for word in _BUDGET_WORDS)
        checks["budget_compliant"] = price <= budget or disclosed
    return checks


def score_case(case: dict, state: dict, events: list[dict], latency_s: float, error: str | None,
               judgement: dict | None = None) -> dict:
    tools_called = {e["tool"] for e in events if e["event"] == "tool_called"}
    checks = _checks(case.get("expect", {}), state, tools_called)
    recommendation = state.get("recommendation") or {}
    return {
        "id": case["id"],
        "kind": case["kind"],
        "query": case["query"],
        "error": error,
        "passed": error is None and all(v is not False for v in checks.values()),
        "checks": checks,
        "purpose_fit": judgement["purpose_fit"] if judgement else None,
        "latency_s": latency_s,
        # What to open when a check fails
        "intent": state.get("intent"),
        "tools_called": sorted(tools_called),
        "product": recommendation.get("product_name"),
        "price": recommendation.get("price"),
        "tradeoffs": recommendation.get("tradeoffs"),
        "judge_feedback": judgement["feedback"] if judgement else None,
    }


# --- summary --------------------------------------------------------------------------------------


def _rate(values) -> str | None:
    known = [v for v in values if v is not None]
    return f"{sum(known) / len(known):.0%} ({sum(known)}/{len(known)})" if known else None


def _percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile: with few runs it reports an observed value instead of interpolating."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def summarize(rows: list[dict]) -> dict:
    # A provider outage says nothing about answer quality: the error rate counts every run, every
    # other metric counts completed runs only.
    completed = [r for r in rows if r["error"] is None]
    researched = [r for r in completed if r["intent"] == "shopping"]
    fits = [r["purpose_fit"] for r in researched if r["purpose_fit"] is not None]
    latencies = [r["latency_s"] for r in researched]
    return {
        "model": settings.gemini_model,
        "runs": len(rows),
        **{metric: _rate(r["checks"][check] for r in completed) for metric, check in _RATES.items()},
        # Answers the judge failed to score are left out, so the mean says how many it covers
        "answer_quality": {"mean": round(statistics.mean(fits), 2) if fits else None,
                           "judged": f"{len(fits)}/{len(researched)}"},
        "latency_s": {"p50": _percentile(latencies, 0.5), "p95": _percentile(latencies, 0.95)},
        "error_rate": _rate(r["error"] is not None for r in rows),
        "failed_cases": sorted(r["id"] for r in rows if not r["passed"]),
    }


# --- entry point ----------------------------------------------------------------------------------


def save_results(prefix: str, payload: dict) -> Path:
    out_dir = _HERE / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{prefix}-{datetime.now():%Y%m%d-%H%M%S}.json"
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=_KINDS)
    parser.add_argument("--case", help="run only the case with this id")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    cases = json.loads((_HERE / "cases.json").read_text(encoding="utf-8"))
    cases = [c for c in cases if (not args.kind or c["kind"] == args.kind) and (not args.case or c["id"] == args.case)]
    cases = cases[: args.limit]

    graph = build_graph()
    rows = []
    for index, case in enumerate(cases, 1):
        row = run_case(graph, case)
        rows.append(row)
        failed = [name for name, ok in row["checks"].items() if ok is False]
        print(f"[{index}/{len(cases)}] {'PASS' if row['passed'] else 'FAIL'} {row['id']:<22} {row['latency_s']:>6}s "
              f"product={row['product']!r}{' failed=' + ','.join(failed) if failed else ''}"
              f"{' err=' + row['error'] if row['error'] else ''}")

    summary = summarize(rows)
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved {save_results('eval', {'summary': summary, 'rows': rows})}")


if __name__ == "__main__":
    main()
