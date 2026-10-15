import json
import sys
import uuid

from langgraph.types import Command

from app.core.config import settings
from app.core.errors import to_app_error
from app.graph.graph import build_graph
from app.guards.input_guard import InvalidQueryError


def _invoke(graph, graph_input, config: dict) -> dict:
    """Run the graph; a failure ends the CLI with the same message the API would show, not a traceback."""
    try:
        return graph.invoke(graph_input, config)
    except InvalidQueryError as exc:
        sys.exit(f"Invalid query: {exc}")
    except Exception as exc:  # noqa: BLE001 - classified and logged by to_app_error
        sys.exit(f"\n{to_app_error(exc, config['configurable']['thread_id']).message}")


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
    result = _invoke(graph, {"query": query}, config)

    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("\nRecommendation pending approval:")
        print(json.dumps(payload.get("recommendation", {}), ensure_ascii=False, indent=2))
        if payload.get("quality_score") is not None:
            print(f"Quality score: {payload['quality_score']:.2f} (threshold {settings.quality_threshold:.2f})")
        result = _invoke(graph, _prompt_for_approval(), config)

    if result.get("general_reply"):
        print(f"\n{result['general_reply']}")
        return

    if result.get("human_approval") is False:
        print("\nRejection limit reached - the last recommendation below was NOT approved.")
    print("\nFinal recommendation:")
    print(json.dumps(result.get("recommendation", {}), ensure_ascii=False, indent=2))

    quality_score = result.get("quality_score")

    if quality_score is not None:
        print(f"\nQuality score: {quality_score:.2f} (threshold {settings.quality_threshold:.2f})")
        if quality_score < settings.quality_threshold:
            print("Note: quality bar not met - treat as unverified:")
            print(f"  - {result.get('evaluation_feedback', '')}")


if __name__ == "__main__":
    main()
