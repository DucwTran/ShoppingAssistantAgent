import json
import sys
import uuid

from app.graph.graph import build_graph


def main() -> None:
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


if __name__ == "__main__":
    main()
