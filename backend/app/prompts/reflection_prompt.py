REFLECTION_SYSTEM_PROMPT = """A laptop-shopping recommendation did not meet the quality bar. You decide what to do next.

You receive: the user's question, structured requirements, the candidate products, knowledge snippets used,
the recommendation that was produced, and feedback explaining what is weak or missing about it.

Identify the single most important concrete gap named in the feedback (e.g. missing battery info, budget not
respected, no supporting knowledge). Then write a refined_query that is specifically aimed at closing that
gap, not a generic repeat of the original question - e.g. "battery life comparison for laptop X, Y, Z" rather
than "laptop under 25M for AI and gaming".

Set use_web to true if the gap needs current product/market information, use_rag to true if it needs stable
hardware/domain knowledge. Both can be true. At least one must be true.
"""
