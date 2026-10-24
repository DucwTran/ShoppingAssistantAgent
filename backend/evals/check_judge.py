"""Check the LLM judge (purpose_fit, evals/judge.py) against hand-labeled recommendations.

Usage (from backend/):  python -m evals.check_judge

Each case in judge_cases.json is a fixed state that a person labeled "good" or "bad" for the user's
purpose. The judge agrees when it scores a good case at least GOOD_MIN and a bad one at most BAD_MAX;
a score in between counts as a disagreement, since an undecided judge cannot separate the two.
One Gemini call per case.
"""

import json
from pathlib import Path

from evals.judge import judge_purpose
from evals.run_eval import save_results

_CASES = Path(__file__).parent / "judge_cases.json"
GOOD_MIN = 0.7
BAD_MAX = 0.4


def agrees(label: str, purpose_fit: float) -> bool:
    return purpose_fit >= GOOD_MIN if label == "good" else purpose_fit <= BAD_MAX


def main() -> None:
    cases = json.loads(_CASES.read_text(encoding="utf-8"))
    rows = []
    for case in cases:
        judgement = judge_purpose(case["state"])
        row = {"id": case["id"], "label": case["label"], "purpose_fit": judgement.purpose_fit,
               "agrees": agrees(case["label"], judgement.purpose_fit), "feedback": judgement.feedback}
        rows.append(row)
        print(f"{'OK  ' if row['agrees'] else 'MISS'} {row['id']:<28} label={row['label']:<4} "
              f"purpose_fit={row['purpose_fit']:.2f} | {row['feedback']}")

    agreed = sum(r["agrees"] for r in rows)
    summary = {"cases": len(rows), "agreement": f"{agreed / len(rows):.0%} ({agreed}/{len(rows)})",
               "good_min": GOOD_MIN, "bad_max": BAD_MAX}
    print("\n" + json.dumps(summary, indent=2))
    print(f"Saved {save_results('judge', {'summary': summary, 'rows': rows})}")


if __name__ == "__main__":
    main()
