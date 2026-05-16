from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from langsmith import traceable

from app.schemas.graph_state import EmailAgentState
from app.graphs.nodes.prepare.reservation_sql import build_action_sqlite
from app.graphs.nodes.retrieval import (
    member_booking_retrieve,
    policy_retrieve,
    vacancy_retrieve,
)

_RETRIEVE_FNS: list[tuple[str, Callable[[EmailAgentState], dict]]] = [
    ("vector_retrieve", policy_retrieve),
    ("db_retrieve", member_booking_retrieve),
    ("retrieve_rest_rooms", vacancy_retrieve),
]


def _run_retrieves(state: EmailAgentState, actions: set[str]) -> dict:
    tasks = [fn for action, fn in _RETRIEVE_FNS if action in actions]
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


@traceable(name="prepare_node")
def prepare_node(state: EmailAgentState) -> dict:
    if state.get("business_error"):
        return {}

    actions_raw = state.get("actions")
    actions_list = actions_raw if isinstance(actions_raw, list) else []
    actions = set(actions_list)

    retrieve_results = _run_retrieves(state, actions)
    result = dict(retrieve_results)

    effective_state: EmailAgentState = {**state, **retrieve_results}
    sql_result = build_action_sqlite(effective_state, actions)
    if sql_result:
        result.update(sql_result)

    return result
