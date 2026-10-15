"""Run the graph on a fixed query set and report accuracy/latency metrics.

Usage (from backend/):  python -m evals.run_eval [--limit N] [--kind shopping|knowledge|general]
Calls the real Gemini API and Tavily. Each run stops at the human-approval pause.
"""

import argparse
import json
import statistics
import time
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.graph.graph import build_graph

_HERE = Path(__file__).parent


def _evaluate_case(graph, case: dict) -> dict:
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    started = time.perf_counter()
    try:
        graph.invoke({"query": case["query"]}, config)
        error = None
    except Exception as exc:  # noqa: BLE001 - recorded as a failed case, the run continues
        error = f"{type(exc).__name__}: {exc}"
    latency = time.perf_counter() - started

    state = graph.get_state(config).values
    recommendation = state.get("recommendation") or {}
    products = state.get("products", [])
    web_urls = {r["url"] for r in state.get("web_results", [])}
    budget, price = state.get("budget"), recommendation.get("price")

    return {
        "query": case["query"],
        "kind": case["kind"],
        "error": error,
        "latency_s": round(latency, 1),
        "intent": state.get("intent"),
        "intent_correct": state.get("intent") == ("general" if case["kind"] == "general" else "shopping"),
        "products": len(products),
        "retrieved_docs": len(state.get("retrieved_docs", [])),
        "product": recommendation.get("product_name"),
        "grounded": all(p["source_url"] in web_urls for p in products)
        and (recommendation.get("url") in web_urls if recommendation.get("url") else True),
        "within_budget": None if not (budget and price) else price <= budget,
        "quality_score": state.get("quality_score"),
    }


def _rate(rows: list[dict], key: str) -> str:
    values = [row[key] for row in rows if row[key] is not None]
    return f"{sum(values) / len(values):.0%} ({sum(values)}/{len(values)})" if values else "n/a"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--kind", choices=["shopping", "knowledge", "general"])
    args = parser.parse_args()

    cases = json.loads((_HERE / "cases.json").read_text(encoding="utf-8"))
    cases = [c for c in cases if not args.kind or c["kind"] == args.kind][: args.limit]

    graph = build_graph()
    rows = []
    for index, case in enumerate(cases, 1):
        row = _evaluate_case(graph, case)
        rows.append(row)
        print(f"[{index}/{len(cases)}] {row['latency_s']:>6}s products={row['products']} "
              f"product={row['product']!r} score={row['quality_score']} err={row['error']} | {case['query']}")

    shopping = [r for r in rows if r["kind"] == "shopping"]
    latencies = sorted(r["latency_s"] for r in rows if r["intent"] == "shopping")
    summary = {
        "model": settings.gemini_model,
        "cases": len(rows),
        "errors": sum(r["error"] is not None for r in rows),
        "intent_accuracy": _rate(rows, "intent_correct"),
        "shopping_with_products": _rate([{"v": r["products"] > 0} for r in shopping], "v"),
        "grounded": _rate([r for r in rows if r["intent"] == "shopping"], "grounded"),
        "within_budget": _rate(shopping, "within_budget"),
        "mean_quality_score": round(statistics.mean(s for r in rows if (s := r["quality_score"]) is not None), 2)
        if any(r["quality_score"] is not None for r in rows) else None,
        "latency_p50_s": statistics.median(latencies) if latencies else None,
        "latency_p95_s": latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))] if latencies else None,
    }

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    out_dir = _HERE / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out_file.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {out_file}")


if __name__ == "__main__":
    main()
