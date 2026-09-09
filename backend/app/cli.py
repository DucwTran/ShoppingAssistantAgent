import json
import sys
import uuid

from langgraph.types import Command

from app.core.config import settings
from app.graph.graph import build_graph


def _prompt_for_approval() -> Command:
    answer = input("\nApprove this recommendation? [y/n]: ").strip().lower()
    approved = answer in ("y", "yes")
    feedback = None
    if not approved:
        feedback = input("What should change? ").strip() or None
    return Command(resume={"approved": approved, "feedback": feedback})


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        print('Usage: python -m app.cli "<your shopping question>"')
        sys.exit(1)

    query = sys.argv[1]
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"thread_id: {thread_id}")

    graph = build_graph()
    result = graph.invoke({"query": query}, config)

    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("\nRecommendation pending approval:")
        print(json.dumps(payload.get("recommendation", {}), ensure_ascii=False, indent=2))
        if payload.get("quality_score") is not None:
            print(f"Quality score: {payload['quality_score']:.2f} (threshold {settings.quality_threshold:.2f})")
        result = graph.invoke(_prompt_for_approval(), config)

    print("\nFinal recommendation:")
    print(json.dumps(result.get("recommendation", {}), ensure_ascii=False, indent=2))

    quality_score = result.get("quality_score")
    reflection_count = result.get("reflection_count", 0)

    if quality_score is not None:
        print(f"\nQuality score: {quality_score:.2f} (threshold {settings.quality_threshold:.2f})")
        if reflection_count:
            print(f"Reflections performed: {reflection_count}")
        if quality_score < settings.quality_threshold:
            print("Note: quality bar not fully met after reflection - treat as unverified:")
            print(f"  - {result.get('evaluation_feedback', '')}")


if __name__ == "__main__":
    main()
