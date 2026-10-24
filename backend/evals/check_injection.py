"""Check that prompt-injection attempts do not change what the pipeline outputs.

Usage (from backend/):  python -m evals.check_injection

Each case in injection_cases.json feeds a fixed state with an injected instruction - in the query,
the feedback, a retrieved web page or the conversation history - to the real node(s), then checks
the output in code: `must_not_contain` lists strings that must not appear in an output field,
`must_equal` values a field must keep. About 1-2 Gemini calls per case; no web search.
"""

import json
from pathlib import Path

from app.graph.nodes.extract_products import extract_products_node
from app.graph.nodes.feedback_router import feedback_router_node
from app.graph.nodes.recommend import recommend_node
from app.graph.nodes.understand import understand_node
from app.tools import price_lookup
from evals.run_eval import save_results

_CASES = Path(__file__).parent / "injection_cases.json"


def _extract_then_recommend(state: dict) -> dict:
    state = {**state, **extract_products_node(state)}
    return {**state, **recommend_node(state)}


_RUNNERS = {
    "understand": understand_node,
    "recommend": recommend_node,
    "feedback_router": feedback_router_node,
    "extract_recommend": _extract_then_recommend,
}


def field_value(output: dict, path: str):
    """`a.b` reads output["a"]["b"]; a missing step gives None."""
    value = output
    for key in path.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    return value


def violations(case: dict, output: dict) -> list[str]:
    found = []
    for path, needles in case.get("must_not_contain", {}).items():
        text = json.dumps(field_value(output, path), ensure_ascii=False).lower()
        found += [f"{path} contains {needle!r}" for needle in needles if needle.lower() in text]
    for path, expected in case.get("must_equal", {}).items():
        if field_value(output, path) != expected:
            found.append(f"{path} is {field_value(output, path)!r}, expected {expected!r}")
    return found


def main() -> None:
    # The cases test the model, not the price lookup; no web search runs
    price_lookup.search_web = lambda query, max_results: []

    rows = []
    for case in json.loads(_CASES.read_text(encoding="utf-8")):
        try:
            output, error = _RUNNERS[case["node"]](case["state"]), None
        except Exception as exc:  # noqa: BLE001 - recorded, the run continues
            output, error = {}, f"{type(exc).__name__}: {exc}"
        found = violations(case, output) if error is None else []
        row = {"id": case["id"], "vector": case["vector"], "passed": error is None and not found,
               "violations": found, "error": error,
               "checked": {path: field_value(output, path)
                           for path in [*case.get("must_not_contain", {}), *case.get("must_equal", {})]}}
        rows.append(row)
        status = "PASS" if row["passed"] else "ERROR" if error else "FAIL"
        print(f"{status:<5} {case['id']:<26} {'; '.join(found) or (error or '')}")

    completed = [r for r in rows if r["error"] is None]
    passed = sum(r["passed"] for r in completed)
    summary = {"cases": len(rows), "errors": len(rows) - len(completed),
               "resisted": f"{passed / len(completed):.0%} ({passed}/{len(completed)})" if completed else None}
    print("\n" + json.dumps(summary, indent=2))
    print(f"Saved {save_results('injection', {'summary': summary, 'rows': rows})}")


if __name__ == "__main__":
    main()
