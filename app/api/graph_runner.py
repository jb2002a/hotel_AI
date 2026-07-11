import uuid
from typing import Any

from langgraph.types import Command

try:
    from langgraph.checkpoint.memory import InMemorySaver as _MemorySaver
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver as _MemorySaver

from app.graphs.graphs import graph
from app.schemas.graph_state import build_approval_payload

_checkpointer = _MemorySaver()
_compiled_graph = graph.compile(checkpointer=_checkpointer)

# thread_id -> run metadata
_runs: dict[str, dict[str, Any]] = {}


def _extract_interrupt_payload(result: dict) -> dict | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None

    first_interrupt = interrupts[0]
    payload_wrapper = getattr(first_interrupt, "value", first_interrupt)
    if isinstance(payload_wrapper, dict):
        payload = payload_wrapper.get("payload")
        if isinstance(payload, dict):
            return payload
    return None


def _serialize_state(result: dict) -> dict:
    """Return JSON-serializable graph state (exclude interrupt handles)."""
    out: dict[str, Any] = {}
    for key, value in result.items():
        if key == "__interrupt__":
            continue
        if key == "vector_retrieve_results" and value:
            out[key] = [
                {"page_content": doc.page_content, "metadata": getattr(doc, "metadata", {})}
                for doc in value
            ]
            continue
        out[key] = value
    return out


def start_run(email_id: str, initial_state: dict) -> dict:
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = _compiled_graph.invoke(initial_state, config=config)
    approval_payload = _extract_interrupt_payload(result)
    if approval_payload is None:
        approval_payload = build_approval_payload(result)

    status = "waiting_approval" if result.get("__interrupt__") else "completed"
    _runs[thread_id] = {
        "thread_id": thread_id,
        "email_id": email_id,
        "status": status,
        "approval_payload": approval_payload,
        "result": _serialize_state(result) if status == "completed" else None,
    }

    return {
        "thread_id": thread_id,
        "status": status,
        "approval_payload": approval_payload,
        "result": _runs[thread_id]["result"],
    }


def submit_run(
    thread_id: str,
    email_data: dict[str, str] | None,
    classification: dict[str, Any] | None,
    extract_data: dict[str, str | None] | None,
    draft_response: str,
    action_sqlite: dict[str, str],
    manager_comment: str,
) -> dict:
    if thread_id not in _runs:
        raise KeyError(f"Unknown thread_id: {thread_id}")

    run = _runs[thread_id]
    if run["status"] != "waiting_approval":
        raise ValueError(f"Run is not waiting for approval: {run['status']}")

    config = {"configurable": {"thread_id": thread_id}}
    resume_payload = {
        "email_data": email_data,
        "classification": classification,
        "extract_data": extract_data,
        "draft_response": draft_response,
        "action_sqlite": action_sqlite,
        "manager_comment": manager_comment,
    }

    result = _compiled_graph.invoke(Command(resume=resume_payload), config=config)
    final_state = _serialize_state(result)

    run["status"] = "completed"
    run["result"] = final_state
    run["approval_payload"] = build_approval_payload(result)

    return {
        "thread_id": thread_id,
        "status": "completed",
        "result": final_state,
    }


def get_run(thread_id: str) -> dict | None:
    return _runs.get(thread_id)
