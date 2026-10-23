# Evaluation

Offline evaluation of the pipeline against live Gemini and Tavily. Scripts are in `backend/evals/`; reports are written to `backend/evals/results/` (gitignored).

## Running

Run from `backend/` with the API server stopped (embedded Qdrant allows one process). Cases run sequentially; concurrent runs on the same keys raise Gemini 503/429 rates and distort latency.

| Command | Scope | Cost |
|---|---|---|
| `python -m evals.run_eval` | 20 labeled queries, end to end | ~110–130 Gemini calls, 20–30 searches, ~20 min |
| `python -m evals.run_eval --kind shopping` | One group: `shopping`, `knowledge`, `general`, `followup` | proportional |
| `python -m evals.run_eval --case usd-budget` | One case | ~7 calls |
| `python -m evals.run_eval --repeat 3` | Every case 3 times; reports unstable cases | 3× |
| `python -m evals.check_judge` | LLM judge vs. hand labels | 8 calls |

## Dataset

`evals/cases.json`: 11 shopping, 4 knowledge, 3 general-chat and 2 rejection-followup cases. Shopping cases cover budget formats (`20tr`, USD, none), a brand constraint, an impossible budget and an injected instruction; general chat includes a prompt-leak attempt.

Each case lists the checks it is labeled for; unlabeled aspects are not checked.

| Label | Passes when |
|---|---|
| `intent` | Classified as `shopping` or `general` as labeled |
| `budget_vnd` | Extracted budget within 1% of the label; `null` requires no budget |
| `tools` | The agent called at least these tools |
| `product` | A product was recommended (`true`) or the answer is `N/A` (`false`) |
| `new_search_after_reject` | After rejection with `reject_with`, the router chose a new search (`true`) or a re-pick (`false`) |

A run passes when it completes without error and no labeled check fails.

## Metrics

`errors` and `passed` count all runs; every other rate counts completed runs only, so provider outages are reported as errors, not as wrong answers.

| Metric | Definition |
|---|---|
| `accuracy.*` | Completed runs passing each labeled check |
| `grounded` | All products and the recommended URL come from retrieved pages |
| `price_known` | The recommended product has a price verified on its source page |
| `budget_honest` | Price within budget, or the overrun stated in the trade-offs |
| `fallback_used` | Researched queries where the agent returned nothing and the fixed search ran |
| `price_filter.recovered_by_lookup` | Products extracted without a price that the second search found one for |
| `price_filter.dropped_no_price` | Products removed because no price was found |
| `price_filter.answers_emptied` | Researched queries that ended with no candidate only because every product lacked a price; their cost shows in `accuracy.product` |
| `failed_attempts` | Node attempts that failed and were retried |
| `latency_s` | p50 / p95 of the first turn of researched queries |
| `per_node_mean`, `mean_tokens_per_query` | From the `node_measured` events emitted by every LLM node (`app/core/metrics.py`), including calls inside the agent loop |

**Judge check.** `evals/judge_cases.json` holds 8 fixed recommendations, 4 labeled good and 4 bad. The judge agrees when it scores good ≥ 0.7 and bad ≤ 0.4. The cases are clear-cut: agreement shows the judge separates good from bad, not that it is reliable on borderline cases.

## Baseline

2026-10-23, `gemini-3.5-flash`. Report `eval-20261023-172209.json`.

| Metric | Result |
|---|---|
| Passed | 17/20 (3 errors, all Gemini 503) |
| Labeled checks | intent 17/17, budget 10/10, tools 14/14, product 7/7, reroute 2/2 |
| Grounded | 14/14 |
| Budget honest | 3/3 |
| Price known | 4/9 |
| Fallback used | 0/14 |
| Failed attempts | 30 |
| Latency | p50 60 s, p95 83 s |
| Tokens per query | 22.7k |
| Judge agreement | 8/8 |

| Node | Duration | Input tokens | Output tokens |
|---|---|---|---|
| `research_agent` | 19.1 s | 6,971 | 496 |
| `extract_products` | 13.7 s | 5,985 | 2,411 |
| `evaluator` | 13.0 s | 1,942 | 338 |
| `recommend` | 10.2 s | 2,405 | 1,396 |
| `understand` | 3.8 s | 328 | 332 |
| `feedback_router` | 2.8 s | 591 | 280 |

## Findings

| Issue | Evidence | Status |
|---|---|---|
| Gemini 503 errors outlast node retries (~3 s, ~6 s) | All 3 failed cases; 30 retried attempts. An interleaved A/B (12 calls each) gave equal error rates for `json_schema` and `function_calling`, and errors came in bursts | Open |
| Page price lines never reached extraction | They were appended after the ~2,000-character snippet; extraction reads 1,500 characters | Fixed (separate `price_listing` field, covered by a unit test); not yet re-measured live |
| Few prices in search results | Most results are editorial listicles that write prices as "19,4 triệu", which the price-line pattern does not match; some retailer pages return a ~150-character snippet | Mitigated: a product without a price is searched once more by name and kept only if a price is found next to its model code. Not yet measured; expect `price_known` near 100% and more `N/A` answers |
| `extract_products` output is mostly reasoning | On saved states, 2,698 of 3,275 output tokens were thoughts at the default thinking level; at `low`/`minimal` output was 600–1,100 tokens, with identical products in the one case where both completed | Changed to `thinking_level="low"`; inputs capped at 12 results, priced pages first. Latency effect not yet measured |
| A missing price costs little in the quality score | It lowers the score by 0.14 (budget fit 0.5, spec completeness 4/5), so priceless recommendations still score ~0.86 | Superseded: products without a price are no longer recommended |
| Rejection with an unavailable requirement ("AMD Radeon") | Re-search ran as labeled, but results contained no AMD GPU laptop. One run picked integrated graphics (purpose fit 0.2); a re-run stated the gap in the trade-offs | Data limitation |
| Injected instruction in the query | Errored in the baseline; on re-run the recommendation stayed in budget and ignored the instruction | Passed on re-run |

## Caveats

- One case is 5 points of a 20-case rate; differences of one or two cases are noise unless `--repeat` confirms them.
- Search results change daily; compare runs made close together.
- Open a failed case's row (`checks`, `tools_called`, `warnings`, `product`) before changing a prompt.
