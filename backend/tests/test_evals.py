import json
from pathlib import Path

from app.graph.graph import build_graph
from evals.check_judge import agrees
from evals.run_eval import _percentile, run_case, score_case, summarize

_EVALS = Path(__file__).parent.parent / "evals"
_EXPECT_KEYS = {"intent", "budget_vnd", "tools", "product", "new_search_after_reject",
                "budget_below_previous_price", "mentions_previous_product"}
_MULTITURN_KEYS = {"budget_below_previous_price", "mentions_previous_product"}

_STATE = {
    "intent": "shopping",
    "budget": 25_000_000,
    "web_results": [{"url": "https://a.vn/a"}],
    "products": [{"name": "A", "source_url": "https://a.vn/a"}],
    "recommendation": {"product_name": "A", "price": 26_000_000, "url": "https://a.vn/a",
                       "tradeoffs": ["Vượt ngân sách 1 triệu"]},
}
_EVENTS = [
    {"event": "tool_called", "tool": "web_search"},
    {"event": "node_measured", "node": "recommend", "failed": False, "duration_ms": 900, "input_tokens": 1200,
     "output_tokens": 150},
    {"event": "node_measured", "node": "recommend", "failed": False, "duration_ms": 100, "input_tokens": 300,
     "output_tokens": 50},
]


def _case(**expect) -> dict:
    return {"id": "c", "kind": "shopping", "query": "q", "expect": expect}


# --- dataset --------------------------------------------------------------------------------------


def test_eval_cases_are_well_formed():
    cases = json.loads((_EVALS / "cases.json").read_text(encoding="utf-8"))
    assert len({c["id"] for c in cases}) == len(cases), "case ids must be unique"
    for case in cases:
        assert case["kind"] in {"shopping", "knowledge", "general", "followup", "multiturn"}, case["id"]
        assert set(case["expect"]) <= _EXPECT_KEYS, case["id"]
        assert ("reject_with" in case) == ("new_search_after_reject" in case["expect"]), case["id"]
        assert ("then" in case) == bool(_MULTITURN_KEYS & set(case["expect"])), case["id"]


def test_judge_cases_are_labeled_and_balanced():
    cases = json.loads((_EVALS / "judge_cases.json").read_text(encoding="utf-8"))
    labels = [c["label"] for c in cases]
    assert set(labels) == {"good", "bad"} and labels.count("good") == labels.count("bad")


def test_injection_cases_are_well_formed():
    from evals.check_injection import _RUNNERS

    cases = json.loads((_EVALS / "injection_cases.json").read_text(encoding="utf-8"))
    assert len({c["id"] for c in cases}) == len(cases)
    for case in cases:
        assert case["node"] in _RUNNERS, case["id"]
        assert case["vector"] in {"direct", "indirect"}, case["id"]
        assert case.get("must_not_contain") or case.get("must_equal"), case["id"]


def test_injection_violations_check_nested_fields_case_insensitively():
    from evals.check_injection import field_value, violations

    output = {"intent": "general", "recommendation": {"product_name": "hacker laptop x"}}
    case = {"must_not_contain": {"recommendation.product_name": ["Hacker"], "general_reply": ["PWNED"]},
            "must_equal": {"intent": "shopping"}}
    assert field_value(output, "recommendation.product_name") == "hacker laptop x"
    assert field_value(output, "missing.path") is None
    assert violations(case, output) == ["recommendation.product_name contains 'Hacker'",
                                        "intent is 'general', expected 'shopping'"]
    assert violations({"must_not_contain": {"general_reply": ["PWNED"]}}, {"general_reply": "Xin chào"}) == []


# --- scoring --------------------------------------------------------------------------------------


def test_score_case_checks_labels_and_answer_quality():
    row = score_case(_case(intent="shopping", budget_vnd=25_000_000, tools=["web_search"], product=True),
                     _STATE, _EVENTS, latency_s=12.0, error=None, judgement={"purpose_fit": 0.9, "feedback": "ok"})

    assert row["passed"] is True
    assert row["checks"] == {"intent": True, "budget": True, "tools": True, "product": True, "reroute": None,
                             "previous_price": None, "previous_product": None}
    assert row["grounded"] is True and row["price_known"] is True
    assert row["budget_honest"] is True  # over budget, but disclosed in tradeoffs
    assert row["nodes"]["recommend"] == {"ms": 1000, "input_tokens": 1500, "output_tokens": 200}
    assert row["tokens"] == 1700 and row["purpose_fit"] == 0.9 and row["judge_feedback"] == "ok"
    assert row["candidates"] == 1 and row["tradeoffs"] == ["Vượt ngân sách 1 triệu"]


def test_score_case_fails_on_wrong_labels_and_undisclosed_overrun():
    state = {**_STATE, "recommendation": {**_STATE["recommendation"], "tradeoffs": []}}
    row = score_case(_case(budget_vnd=None, tools=["search_knowledge_base"]), state, _EVENTS, 1.0, None)

    assert row["passed"] is False
    assert row["checks"]["budget"] is False and row["checks"]["tools"] is False
    assert row["budget_honest"] is False


def test_score_case_flags_ungrounded_recommendation_and_errors():
    state = {**_STATE, "recommendation": {**_STATE["recommendation"], "url": "https://elsewhere"}}
    row = score_case(_case(), state, [], 1.0, error="ServerError: 503")
    assert row["grounded"] is False
    assert row["passed"] is False


def test_general_chat_has_no_shopping_quality_checks():
    row = score_case({"id": "g", "kind": "general", "query": "hi", "expect": {"intent": "general"}},
                     {"intent": "general", "general_reply": "Xin chào"}, [], 2.0, None)
    assert row["passed"] is True
    assert row["grounded"] is None and row["budget_honest"] is None


def test_score_case_records_why_a_run_degraded():
    events = [*_EVENTS,
              {"event": "research_agent_failed", "status": "warning"},
              {"event": "node_measured", "node": "recommend", "status": "warning", "failed": True,
               "duration_ms": 10, "input_tokens": 0, "output_tokens": 0}]
    row = score_case(_case(), _STATE, events, 1.0, None)
    assert row["warnings"] == ["research_agent_failed"]
    assert row["failed_attempts"] == 1


def test_price_filter_metrics_sum_extractions_and_flag_emptied_answers():
    first = {"event": "products_extracted", "products": 3, "priced_by_lookup": 2, "dropped_no_price": 1}
    last = {"event": "products_extracted", "products": 0, "priced_by_lookup": 0, "dropped_no_price": 4}
    row = score_case(_case(), _STATE, [*_EVENTS, first, last], 1.0, None)
    assert (row["priced_by_lookup"], row["dropped_no_price"]) == (2, 5)
    assert row["emptied_by_price_filter"] is True

    kept = score_case(_case(), _STATE, [*_EVENTS, first], 1.0, None)
    assert kept["emptied_by_price_filter"] is False
    summary = summarize([row, kept])["price_filter"]
    assert summary == {"recovered_by_lookup": "40% (4/10)", "dropped_no_price": 6, "answers_emptied": "50% (1/2)"}


def test_summarize_reports_rates_and_unstable_cases():
    passing = score_case(_case(intent="shopping"), _STATE, _EVENTS, 10.0, None)
    failing = score_case(_case(intent="general"), _STATE, _EVENTS, 30.0, None)
    outage = score_case(_case(intent="general"), {}, [], 50.0, error="ServerError: 503")
    summary = summarize([passing, failing, outage])

    assert summary["errors"] == 1
    assert summary["passed"] == "33% (1/3)"
    assert summary["accuracy"]["intent"] == "50% (1/2)"  # the errored run does not count as a wrong answer
    assert summary["accuracy"]["reroute"] is None
    assert summary["unstable_cases"] == ["c"]  # same id passed once and failed once
    assert summary["per_node_mean"]["recommend"]["input_tokens"] == 1500


def test_percentile_uses_nearest_rank():
    assert _percentile([], 0.5) is None
    assert _percentile([3.0, 1.0, 2.0], 0.5) == 2.0
    assert _percentile([float(v) for v in range(1, 21)], 0.95) == 19.0


def test_judge_agreement_needs_a_decisive_score():
    assert agrees("good", 0.8) and not agrees("good", 0.6)
    assert agrees("bad", 0.3) and not agrees("bad", 0.5)


# --- harness, offline -----------------------------------------------------------------------------


def test_run_case_offline_collects_node_measurements_and_judges_the_answer(fake_pipeline):
    row = run_case(build_graph(), _case(intent="shopping", budget_vnd=25_000_000, product=True))
    assert row["passed"] is True, row
    assert {"understand", "research_agent", "extract_products", "recommend"} <= set(row["nodes"])
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


def test_run_case_offline_reports_an_answer_emptied_by_the_price_filter(fake_pipeline):
    from app.schemas.product import Product
    from tests.conftest import WEB_RESULTS

    fake_pipeline.extracted = [Product(name="Acer Nitro V 15", source_url=WEB_RESULTS[0]["url"])]  # priceless
    fake_pipeline.product_id = None

    row = run_case(build_graph(), _case(product=True))
    assert row["emptied_by_price_filter"] is True and row["dropped_no_price"] == 1
    assert row["checks"]["product"] is False  # the cost of the filter shows up as a failed product check


def test_run_case_offline_multiturn_checks_the_follow_up(fake_pipeline):
    case = {"id": "m", "kind": "multiturn", "query": "laptop gaming dưới 25 triệu", "then": "còn máy nào rẻ hơn không?",
            "expect": {"budget_below_previous_price": True, "mentions_previous_product": True}}
    # The fake keeps a 25M budget, above the first answer's 22.99M: "cheaper" was not applied
    fake_pipeline.standalone_query = "laptop gaming rẻ hơn Acer Nitro V 15"
    row = run_case(build_graph(), case)

    assert row["checks"]["previous_product"] is True
    assert row["checks"]["previous_price"] is False
    assert row["followup_latency_s"] is not None


def test_run_case_offline_followup_checks_the_reroute(fake_pipeline):
    fake_pipeline.needs_new_products = True
    case = {"id": "f", "kind": "followup", "query": "laptop gaming dưới 25 triệu", "reject_with": "prefer AMD GPU",
            "expect": {"new_search_after_reject": True}}
    row = run_case(build_graph(), case)
    assert row["checks"]["reroute"] is True
    assert row["followup_latency_s"] is not None
    assert "feedback_router" in row["nodes"]
