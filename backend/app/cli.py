import json
import sys
import uuid

from app.core.config import settings
from app.graph.graph import build_graph


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        print('Usage: python -m app.cli "<your shopping question>"')
        sys.exit(1)

    query = sys.argv[1]
    thread_id = str(uuid.uuid4())

    graph = build_graph()
    result = graph.invoke({"query": query, "thread_id": thread_id})

    print(f"\nthread_id: {thread_id}")
    print("\nRecommendation:")
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
