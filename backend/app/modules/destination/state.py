"""目的地研究子图 State — DestinationState (共享+私有 key)"""

from typing import Annotated, TypedDict

from app.modules.planner.state import merge_dicts


class DestinationState(TypedDict):
    """目的地研究子图状态

    共享 key (与主图同步):
    - destination, research_result

    私有 key (仅子图内部):
    - city_details, cities_to_research
    """

    # ── 共享 key ──
    destination: str
    research_result: Annotated[dict, merge_dicts]

    # ── 私有 key ──
    city_details: dict
    cities_to_research: list[str]
