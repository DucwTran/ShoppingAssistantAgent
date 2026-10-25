# Evaluation

Offline evaluation of the pipeline against live Gemini and Tavily, on eight metrics. Scripts are in `backend/evals/`; reports are written to `backend/evals/results/` (gitignored).

## Running

Run from `backend/` with the API server stopped (embedded Qdrant allows one process). Cases run sequentially; concurrent runs on the same keys raise Gemini 503/429 rates and distort latency.

| Command | Scope | Cost |
|---|---|---|
| `python -m evals.run_eval` | 18 labeled queries | ~80 Gemini calls, ~25 searches, ~15 min |
| `python -m evals.run_eval --kind shopping` | One group: `shopping`, `knowledge` or `general` | proportional |
| `python -m evals.run_eval --case usd-budget` | One case | ~6 calls |
| `python -m evals.check_judge` | The judge behind metric 6, against hand labels | 8 calls |

## Dataset

`evals/cases.json`: 11 shopping, 4 knowledge and 3 general-chat queries. Shopping cases cover budget formats (`20tr`, USD, none), a brand constraint, an impossible budget and an injected instruction; general chat includes a prompt-leak attempt. Each case labels the intent, and where relevant the budget and the tools the agent must call.

## Metrics

| # | Metric | Passes when | Counted over |
|---|---|---|---|
| 1 | `intent_accuracy` | Classified as `shopping` or `general` as labeled | All completed cases |
| 2 | `budget_accuracy` | Extracted budget within 1% of the label; a `null` label requires no budget | Cases labeled with a budget |
| 3 | `tool_accuracy` | The agent called at least the labeled tools | Cases labeled with tools |
| 4 | `grounded_rate` | Every extracted product and the recommended URL come from a retrieved page | Shopping answers |
| 5 | `budget_compliance` | The recommended price is within budget, or the overrun is stated in the trade-offs | Answers with a product, a price and a budget |
| 6 | `answer_quality` | Mean LLM-judge score (0–1) for how well the answer serves the stated purpose (`evals/judge.py`); `judged` gives how many answers the judge scored | Shopping answers the judge scored |
| 7 | `latency_s` | p50 / p95 of the time to the recommendation | Shopping answers |
| 8 | `error_rate` | Runs that ended in an error (provider 503, timeout) | All runs |

Metrics 1–7 count completed runs only, so a provider outage shows up in the error rate, not as a wrong answer. A case passes when it completes and none of checks 1–5 fails; `failed_cases` lists the others, and each row keeps the tools called, product, price, trade-offs and judge feedback needed to see why.

**Judge check.** Metric 6 is only as good as the judge. `evals/judge_cases.json` holds 8 fixed recommendations, 4 labeled good and 4 bad by hand; the judge agrees when it scores good ≥ 0.7 and bad ≤ 0.4. The cases are clear-cut: agreement shows the judge separates good from bad, not that it is reliable on borderline answers. Re-run `check_judge` after changing the judge prompt or the model.

## Baseline

2026-10-25, `gemini-3.5-flash`, Tavily; reports `eval-20261025-130421.json` and `judge-20261025-130513.json`. The previous run (2026-10-23, 20 cases on the earlier set) is shown for reference; it predates the price filter, the leaner extraction and the removal of the in-graph quality-scoring node.

| # | Metric | 2026-10-25 | 2026-10-23 |
|---|---|---|---|
| 1 | Intent accuracy | 100% (18/18) | 100% (17/17) |
| 2 | Budget accuracy | 100% (11/11) | 100% (10/10) |
| 3 | Tool accuracy | 100% (15/15) | 100% (14/14) |
| 4 | Grounded rate | 100% (15/15) | 100% (14/14) |
| 5 | Budget compliance | 100% (8/8) | 100% (3/3) |
| 6 | Answer quality | 0.97 over 9 of 15 answers; judge agreement 8/8 | 0.93; judge agreement 8/8 |
| 7 | Latency | p50 53 s, p95 103 s (product searches alone: p50 62 s) | p50 60 s, p95 83 s |
| 8 | Error rate | 0% (0/18) | 15% (3/20) |

All 18 cases passed. Ten node attempts failed and were retried (one Gemini 503 in the agent, which fell back to the fixed search), and 12 keys were rotated out for quota during the run.

## Findings

| Issue | Evidence | Status |
|---|---|---|
| Latency did not improve | Removing the quality-scoring node saved ~13 s, but the second price search adds ~15–20 s to `extract_products` when it runs (7 of 11 product searches), the agent takes 11–49 s at 4–10 s per Tavily call, and each retried attempt adds 3–15 s | Open; the price search is the cost of `budget_compliance` rising from 3 to 8 qualifying answers |
| The judge scored 9 of 15 answers | Judge calls failed while keys were being rotated for quota; the failures were not reported until this run | The summary now gives `judged` and the script prints each judge failure; re-run on fresh quota |
| Gemini 503 and 429 | No case failed this run (0/18, against 3/20 before); retries, key rotation and the agent fallback absorbed them | Monitored through the error rate |
| Rejected requirement not in the data ("AMD Radeon") | Search returned no AMD-GPU laptop; one run picked integrated graphics (judge 0.2) | Data limitation; the rejection flow is outside this eval's cases |

## Caveats

- One case is about 5 points of a rate over 18 cases; a difference of one or two cases is noise.
- Search results change daily; compare runs made close together.
- Open a failed case's row before changing a prompt.
