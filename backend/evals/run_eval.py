"""Run the graph on the labeled query set and report accuracy, grounding, latency and token usage.

Usage (from backend/):
    python -m evals.run_eval [--kind shopping|knowledge|general|followup] [--case ID] [--limit N] [--repeat N]

Calls the real Gemini API and Tavily. Each run stops at the human-approval pause; a "followup" case
first rejects the recommendation with its `reject_with` feedback. Labels live in cases.json and
the metrics are described in docs/eval.md.
"""

import argparse
import json
import math
import statistics
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from langgraph.types import Command

from app.core.config import settings
from app.graph.graph import build_graph
from app.schemas.recommendation import NO_PRODUCT

_HERE = Path(__file__).parent
_BUDGET_WORDS = ("budget", "ngân sách")


# --- running --------------------------------------------------------------------------------------


def _stream(graph, graph_input, config) -> tuple[list[dict], float, str | None]:
    """Run one graph turn, collecting its progress events; returns (events, seconds, error)."""
    events: list[dict] = []
    started = time.perf_counter()
    try:
        events.extend(graph.stream(graph_input, config, stream_mode="custom"))
        error = None
    except Exception as exc:  # noqa: BLE001 - recorded as a failed case, the run continues
        error = f"{type(exc).__name__}: {exc}"
    return events, round(time.perf_counter() - started, 1), error


def run_case(graph, case: dict) -> dict:
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    events, latency, error = _stream(graph, {"query": case["query"]}, config)

    followup = None
    if case.get("reject_with") and not error and graph.get_state(config).interrupts:
        resume = Command(resume={"approved": False, "feedback": case["reject_with"]})
        followup_events, followup_latency, error = _stream(graph, resume, config)
        events += followup_events
        followup = {
            "latency_s": followup_latency,
            "new_search": graph.get_state(config).values.get("research_hint") is not None,
        }

    return score_case(case, graph.get_state(config).values, events, latency, error, followup)


# --- scoring (pure, unit-tested offline) ----------------------------------------------------------


def _node_usage(events: list[dict]) -> dict[str, dict]:
    nodes: dict[str, dict] = defaultdict(lambda: {"ms": 0, "input_tokens": 0, "output_tokens": 0})
    for event in events:
        if event["event"] == "node_measured":
            for key, field in (("ms", "duration_ms"), ("input_tokens", "input_tokens"), ("output_tokens", "output_tokens")):
                nodes[event["node"]][key] += event[field]
    return dict(nodes)


def _price_filter(events: list[dict]) -> dict[str, int | bool]:
    """What the verified-price filter did, summed over extractions (a followup can extract twice)."""
    extractions = [e for e in events if e["event"] == "products_extracted"]
    dropped = sum(e.get("dropped_no_price", 0) for e in extractions)
    return {
        "priced_by_lookup": sum(e.get("priced_by_lookup", 0) for e in extractions),
        "dropped_no_price": dropped,
        # Products were found, but none had a price, so the answer became N/A because of the filter
        "emptied_by_price_filter": bool(extractions) and extractions[-1]["products"] == 0
        and extractions[-1].get("dropped_no_price", 0) > 0,
    }


def _checks(expect: dict, state: dict, tools_called: set[str], followup: dict | None) -> dict[str, bool | None]:
    """Compare the run with the case's labels; None means the case does not label that aspect."""
    recommendation = state.get("recommendation") or {}
    checks: dict[str, bool | None] = {"intent": None, "budget": None, "tools": None, "product": None, "reroute": None}

    if "intent" in expect:
        checks["intent"] = state.get("intent") == expect["intent"]
    if "budget_vnd" in expect:
        expected, actual = expect["budget_vnd"], state.get("budget")
        checks["budget"] = actual is None if expected is None else actual is not None and math.isclose(
            actual, expected, rel_tol=0.01)
    if "tools" in expect:
        checks["tools"] = set(expect["tools"]) <= tools_called
    if "product" in expect:
        recommended = recommendation.get("product_name") not in (None, NO_PRODUCT)
        checks["product"] = recommended == expect["product"]
    if "new_search_after_reject" in expect:
        checks["reroute"] = followup is not None and followup["new_search"] == expect["new_search_after_reject"]
    return checks


def _answer_quality(state: dict) -> dict[str, bool | None]:
    """Properties every shopping answer should have, whatever the case; None when not applicable."""
    if state.get("intent") != "shopping":
        return {"grounded": None, "price_known": None, "budget_honest": None}

    recommendation = state.get("recommendation") or {}
    web_urls = {r["url"] for r in state.get("web_results", [])}
    url = recommendation.get("url")
    grounded = all(p["source_url"] in web_urls for p in state.get("products", [])) and (not url or url in web_urls)

    has_product = recommendation.get("product_name") not in (None, NO_PRODUCT)
    price, budget = recommendation.get("price"), state.get("budget")
    budget_honest = None
    if has_product and price is not None and budget:
        disclosed = any(word in t.lower() for t in recommendation.get("tradeoffs", []) for word in _BUDGET_WORDS)
        budget_honest = price <= budget or disclosed

    return {"grounded": grounded, "price_known": (price is not None) if has_product else None,
            "budget_honest": budget_honest}


def score_case(case: dict, state: dict, events: list[dict], latency_s: float, error: str | None,
               followup: dict | None = None) -> dict:
    tools_called = {e["tool"] for e in events if e["event"] == "tool_called"}
    checks = _checks(case.get("expect", {}), state, tools_called, followup)
    nodes = _node_usage(events)
    purpose_fit = next((e["purpose_fit"] for e in reversed(events) if e["event"] == "evaluator_done"), None)
    recommendation = state.get("recommendation") or {}

    return {
        "id": case["id"],
        "kind": case["kind"],
        "query": case["query"],
        "error": error,
        "passed": error is None and all(v is not False for v in checks.values()),
        "checks": checks,
        **_answer_quality(state),
        "intent": state.get("intent"),
        "tools_called": sorted(tools_called),
        "fallback_used": any(e["event"] == "research_fallback" for e in events),
        **_price_filter(events),
        # Why a run degraded: warning events (e.g. research_agent_failed) and node attempts that failed and were retried
        "warnings": sorted({e["event"] for e in events if e.get("status") == "warning" and e["event"] != "node_measured"}),
        "failed_attempts": sum(1 for e in events if e["event"] == "node_measured" and e["failed"]),
        "product": recommendation.get("product_name"),
        "candidates": len(state.get("products", [])),
        # The model's own reasoning, so a surprising answer (e.g. N/A despite candidates) can be explained
        "why_it_fits": recommendation.get("why_it_fits"),
        "tradeoffs": recommendation.get("tradeoffs"),
        "quality_score": state.get("quality_score"),
        "purpose_fit": purpose_fit,
        "evaluation_feedback": state.get("evaluation_feedback"),
        "latency_s": latency_s,
        "followup_latency_s": followup["latency_s"] if followup else None,
        "tokens": sum(n["input_tokens"] + n["output_tokens"] for n in nodes.values()),
        "nodes": nodes,
    }


# --- summary --------------------------------------------------------------------------------------


def _rate(values) -> str | None:
    known = [v for v in values if v is not None]
    return f"{sum(known) / len(known):.0%} ({sum(known)}/{len(known)})" if known else None


def _mean(values) -> float | None:
    known = [v for v in values if v is not None]
    return round(statistics.mean(known), 2) if known else None


def _percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile: with few runs it reports an observed value instead of interpolating."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def summarize(rows: list[dict]) -> dict:
    # A provider outage says nothing about answer quality: quality metrics use completed runs only,
    # while `errors` and `passed` still count every run.
    completed = [r for r in rows if r["error"] is None]
    researched = [r for r in completed if r["intent"] == "shopping"]

    per_node: dict[str, dict] = {}
    for node in sorted({n for r in researched for n in r["nodes"]}):
        usages = [r["nodes"][node] for r in researched if node in r["nodes"]]
        per_node[node] = {key: round(statistics.mean(u[key] for u in usages)) for key in ("ms", "input_tokens", "output_tokens")}

    recovered = sum(r["priced_by_lookup"] for r in researched)
    priceless = recovered + sum(r["dropped_no_price"] for r in researched)

    outcomes: dict[str, set[bool]] = defaultdict(set)
    for row in rows:
        outcomes[row["id"]].add(row["passed"])

    return {
        "model": settings.gemini_model,
        "runs": len(rows),
        "cases": len(outcomes),
        "errors": sum(r["error"] is not None for r in rows),
        "failed_attempts": sum(r["failed_attempts"] for r in rows),
        "passed": _rate(r["passed"] for r in rows),
        "accuracy": {check: _rate(r["checks"][check] for r in completed)
                     for check in ("intent", "budget", "tools", "product", "reroute")},
        "answer_quality": {
            "grounded": _rate(r["grounded"] for r in completed),
            "price_known": _rate(r["price_known"] for r in completed),
            "budget_honest": _rate(r["budget_honest"] for r in completed),
            "fallback_used": _rate(r["fallback_used"] for r in researched),
            "mean_quality_score": _mean(r["quality_score"] for r in researched),
            "mean_purpose_fit": _mean(r["purpose_fit"] for r in researched),
        },
        "price_filter": {
            # Of the products extracted without a price, the share the second search found one for
            "recovered_by_lookup": f"{recovered / priceless:.0%} ({recovered}/{priceless})" if priceless else None,
            "dropped_no_price": priceless - recovered,
            "answers_emptied": _rate(r["emptied_by_price_filter"] for r in researched),
        },
        "latency_s": {"p50": _percentile([r["latency_s"] for r in researched], 0.5),
                      "p95": _percentile([r["latency_s"] for r in researched], 0.95)},
        "mean_tokens_per_query": _mean(r["tokens"] for r in researched),
        "per_node_mean": per_node,
        "failed_cases": sorted({r["id"] for r in rows if not r["passed"]}),
        # With --repeat: cases that passed in some runs and failed in others
        "unstable_cases": sorted(case_id for case_id, seen in outcomes.items() if len(seen) > 1),
    }


# --- entry point ----------------------------------------------------------------------------------


def save_results(prefix: str, payload: dict) -> Path:
    out_dir = _HERE / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{prefix}-{datetime.now():%Y%m%d-%H%M%S}.json"
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file


def _failed_checks(row: dict) -> str:
    failed = [name for name, ok in row["checks"].items() if ok is False]
    return f" failed={','.join(failed)}" if failed else ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["shopping", "knowledge", "general", "followup"])
    parser.add_argument("--case", help="run only the case with this id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeat", type=int, default=1, help="run every case N times to expose unstable results")
    args = parser.parse_args()

    cases = json.loads((_HERE / "cases.json").read_text(encoding="utf-8"))
    cases = [c for c in cases if (not args.kind or c["kind"] == args.kind) and (not args.case or c["id"] == args.case)]
    cases = cases[: args.limit]

    graph = build_graph()
    rows = []
    total = len(cases) * args.repeat
    for index, case in enumerate([c for _ in range(args.repeat) for c in cases], 1):
        row = run_case(graph, case)
        rows.append(row)
        print(f"[{index}/{total}] {'PASS' if row['passed'] else 'FAIL'} {row['id']:<22} {row['latency_s']:>6}s "
              f"{row['tokens']:>6} tok product={row['product']!r}{_failed_checks(row)}"
              f"{' err=' + row['error'] if row['error'] else ''}")

    summary = summarize(rows)
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved {save_results('eval', {'summary': summary, 'rows': rows})}")


if __name__ == "__main__":
    main()
