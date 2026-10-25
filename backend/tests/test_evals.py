import json
from pathlib import Path

from app.graph.graph import build_graph
from evals.check_judge import agrees
from evals.run_eval import _KINDS, _percentile, run_case, score_case, summarize

_EVALS = Path(__file__).parent.parent / "evals"

_STATE = {
    "intent": "shopping",
    "budget": 25_000_000,
    "web_results": [{"url": "https://a.vn/a"}],
    "products": [{"name": "A", "source_url": "https://a.vn/a"}],
    "recommendation": {"product_name": "A", "price": 26_000_000, "url": "https://a.vn/a",
                       "tradeoffs": ["Vượt ngân sách 1 triệu"]},
}
_EVENTS = [{"event": "tool_called", "tool": "web_search"}]


def _case(**expect) -> dict:
    return {"id": "c", "kind": "shopping", "query": "q", "expect": expect}


# --- dataset --------------------------------------------------------------------------------------


def test_eval_cases_are_well_formed():
    cases = json.loads((_EVALS / "cases.json").read_text(encoding="utf-8"))
    assert len({c["id"] for c in cases}) == len(cases), "case ids must be unique"
    for case in cases:
        assert case["kind"] in _KINDS, case["id"]
        assert set(case["expect"]) <= {"intent", "budget_vnd", "tools"}, case["id"]


def test_judge_cases_are_labeled_and_balanced():
    cases = json.loads((_EVALS / "judge_cases.json").read_text(encoding="utf-8"))
    labels = [c["label"] for c in cases]
    assert set(labels) == {"good", "bad"} and labels.count("good") == labels.count("bad")


# --- scoring --------------------------------------------------------------------------------------


def test_score_case_passes_labels_and_answer_checks():
    row = score_case(_case(intent="shopping", budget_vnd=25_000_000, tools=["web_search"]),
                     _STATE, _EVENTS, latency_s=12.0, error=None, judgement={"purpose_fit": 0.9, "feedback": "ok"})

    assert row["passed"] is True
    # Over budget, but disclosed in the trade-offs
    assert row["checks"] == {"intent": True, "budget": True, "tools": True, "grounded": True, "budget_compliant": True}
    assert row["purpose_fit"] == 0.9 and row["judge_feedback"] == "ok"
    assert row["price"] == 26_000_000 and row["tradeoffs"] == ["Vượt ngân sách 1 triệu"]


def test_score_case_fails_on_wrong_labels_and_undisclosed_overrun():
    state = {**_STATE, "recommendation": {**_STATE["recommendation"], "tradeoffs": []}}
    row = score_case(_case(budget_vnd=None, tools=["search_knowledge_base"]), state, _EVENTS, 1.0, None)

    assert row["passed"] is False
    assert row["checks"]["budget"] is False and row["checks"]["tools"] is False
    assert row["checks"]["budget_compliant"] is False


def test_score_case_flags_ungrounded_recommendation():
    state = {**_STATE, "recommendation": {**_STATE["recommendation"], "url": "https://elsewhere"}}
    row = score_case(_case(), state, [], 1.0, None)
    assert row["checks"]["grounded"] is False and row["passed"] is False


def test_unlabeled_and_not_applicable_checks_are_none():
    no_answer = {**_STATE, "recommendation": {"product_name": "N/A", "price": None, "tradeoffs": []}}
    row = score_case(_case(), no_answer, [], 1.0, None)
    assert row["checks"] == {"intent": None, "budget": None, "tools": None, "grounded": True, "budget_compliant": None}
    assert row["passed"] is True

    chat = score_case({"id": "g", "kind": "general", "query": "hi", "expect": {"intent": "general"}},
                      {"intent": "general", "general_reply": "Xin chào"}, [], 2.0, None)
    assert chat["passed"] is True
    assert chat["checks"]["grounded"] is None and chat["checks"]["budget_compliant"] is None


def test_summarize_reports_the_eight_metrics():
    passing = score_case(_case(intent="shopping"), _STATE, _EVENTS, 10.0, None, {"purpose_fit": 0.8, "feedback": ""})
    failing = score_case(_case(intent="general"), _STATE, _EVENTS, 30.0, None, {"purpose_fit": 0.4, "feedback": ""})
    outage = score_case(_case(intent="general"), {}, [], 50.0, error="ServerError: 503")
    summary = summarize([passing, failing, outage])

    assert summary["intent_accuracy"] == "50% (1/2)"  # the errored run does not count as a wrong answer
    assert summary["budget_accuracy"] is None  # no case labels it
    assert summary["grounded_rate"] == "100% (2/2)"
    assert summary["answer_quality"] == {"mean": 0.6, "judged": "2/2"}
    assert summary["latency_s"] == {"p50": 10.0, "p95": 30.0}
    assert summary["error_rate"] == "33% (1/3)"
    assert summary["failed_cases"] == ["c", "c"]


def test_percentile_uses_nearest_rank():
    assert _percentile([], 0.5) is None
    assert _percentile([3.0, 1.0, 2.0], 0.5) == 2.0
    assert _percentile([float(v) for v in range(1, 21)], 0.95) == 19.0


def test_judge_agreement_needs_a_decisive_score():
    assert agrees("good", 0.8) and not agrees("good", 0.6)
    assert agrees("bad", 0.3) and not agrees("bad", 0.5)


# --- harness, offline -----------------------------------------------------------------------------


def test_run_case_offline_scores_and_judges_the_answer(fake_pipeline):
    row = run_case(build_graph(), _case(intent="shopping", budget_vnd=25_000_000))
    assert row["passed"] is True, row
    assert row["checks"]["grounded"] is True
    assert row["purpose_fit"] == 0.9  # from the eval's own judge call, not from the graph


def test_judge_reads_the_specs_of_the_named_product_when_a_page_lists_several(fake_pipeline):
    from evals.judge import judge_purpose

    page = "https://shop.vn/gaming"
    state = {"query": "laptop gaming", "products": [{"name": "Cheap", "gpu": "unknown", "source_url": page},
                                                    {"name": "B", "gpu": "RTX 4050", "source_url": page}],
             "recommendation": {"product_name": "B", "url": page}}
    judge_purpose(state)
    assert fake_pipeline.payloads["PurposeJudgement"]["recommended_product_specs"]["gpu"] == "RTX 4050"


def test_general_chat_is_not_judged(fake_pipeline):
    fake_pipeline.is_shopping = False
    row = run_case(build_graph(), {"id": "g", "kind": "general", "query": "hi", "expect": {"intent": "general"}})
    assert row["purpose_fit"] is None and "PurposeJudgement" not in fake_pipeline.calls
