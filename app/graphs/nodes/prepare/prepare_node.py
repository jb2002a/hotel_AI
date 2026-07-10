from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from langsmith import traceable

from app.schemas.graph_state import EmailAgentState
from app.graphs.nodes.retrieval import (
    member_booking_retrieve,
    policy_retrieve,
    vacancy_retrieve,
)
from app.graphs.nodes.prepare.reservation_sql import (
    validate_booking_context_before_retrieve,
)

_ACTION_RETRIEVERS: dict[str, Callable[[EmailAgentState], dict]] = {
    "reservation_search": member_booking_retrieve,
    "reservation_create": vacancy_retrieve,
    "reservation_update": member_booking_retrieve,
    "reservation_delete": member_booking_retrieve,
}


def _collect_retrievers(
    state: EmailAgentState,
    actions: set[str],
) -> list[Callable[[EmailAgentState], dict]]:
    seen: set[Callable[[EmailAgentState], dict]] = set()
    fns: list[Callable[[EmailAgentState], dict]] = []

    if state.get("policy_queries"):
        seen.add(policy_retrieve)
        fns.append(policy_retrieve)

    for action in actions:
        fn = _ACTION_RETRIEVERS.get(action)
        if fn and fn not in seen:
            seen.add(fn)
            fns.append(fn)
    return fns


@traceable(name="prepare_node")
def prepare_node(state: EmailAgentState) -> dict:
    """actions에 따라 필요한 retriever를 병렬 실행"""

    if state.get("business_error"):
        return {}

    actions_raw = state.get("actions")
    actions = set(actions_raw) if isinstance(actions_raw, list) else set()

    validate_booking_context_before_retrieve(state, actions)

    tasks = _collect_retrievers(state, actions)
    if not tasks:
        return {}

    if len(tasks) == 1:
        return tasks[0](state)

    merged: dict = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = [executor.submit(fn, state) for fn in tasks]
        for future in futures:
            merged.update(future.result())
    return merged
