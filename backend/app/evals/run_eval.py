import sys

from app.evals.golden_queries import GOLDEN_QUERIES
from app.graph.graph import build_graph


def run() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    graph = build_graph()

    for query in GOLDEN_QUERIES:
        result = graph.invoke({"query": query}, config={"recursion_limit": 40})
        recommendation = result.get("recommendation", {})
        print(
            f"[{result.get('quality_score', 0):.2f}] "
            f"reflections={result.get('reflection_count', 0)} "
            f"product={recommendation.get('product_name', 'N/A')!r} "
            f"| {query}"
        )


if __name__ == "__main__":
    run()
