FEEDBACK_ROUTER_SYSTEM_PROMPT = """A person rejected a laptop recommendation with feedback. Decide whether satisfying the
feedback needs a new product search, or whether the current candidates can satisfy it.

needs_new_products = true when the feedback asks for something none of the current candidates offers (a cheaper
price range, a different brand/GPU/size, a different use case). Then set research_hint to a short search
description combining the original need with the feedback, e.g. "laptop gaming GPU AMD dưới 25 triệu".

needs_new_products = false when the feedback can be met by picking another current candidate or rewording
(e.g. "prefer the cheaper one", "explain the battery tradeoff"). research_hint is then null.
"""
