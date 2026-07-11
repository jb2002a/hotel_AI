"""Integration test for interrupt/resume using a mocked compiled graph."""

from unittest.mock import MagicMock, patch

from langgraph.types import Command

from app.api import graph_runner


def _fake_interrupt_result(payload: dict) -> dict:
    return {
        "__interrupt__": [
            MagicMock(
                value={
                    "message": "approval needed",
                    "payload": payload,
                }
            )
        ],
        "draft_response": payload.get("draft_response"),
        "action_sqlite": payload.get("action_sqlite"),
    }


def test_interrupt_and_resume_flow():
    payload = {
        "email_data": {
            "email_subject": "test",
            "email_content": "body",
            "sender_email": "a@b.com",
        },
        "classification": {"category": "normal", "urgency": "normal", "actions": []},
        "extract_data": None,
        "draft_response": "draft",
        "action_sqlite": {"create_sql": "", "update_sql": "", "delete_sql": ""},
        "errors": [],
    }

    mock_graph = MagicMock()
    mock_graph.invoke.side_effect = [
        _fake_interrupt_result(payload),
        {
            "draft_response": "edited draft",
            "action_sqlite": payload["action_sqlite"],
            "manager_comment": "ok",
        },
    ]

    with patch.object(graph_runner, "_compiled_graph", mock_graph):
        start = graph_runner.start_run("sample_001", {"email_data": payload["email_data"]})
        assert start["status"] == "waiting_approval"
        assert start["approval_payload"] == payload

        submit = graph_runner.submit_run(
            start["thread_id"],
            email_data=payload["email_data"],
            classification=payload["classification"],
            extract_data=payload["extract_data"],
            draft_response="edited draft",
            action_sqlite=payload["action_sqlite"],
            manager_comment="ok",
        )
        assert submit["status"] == "completed"
        assert submit["result"]["draft_response"] == "edited draft"

        mock_graph.invoke.assert_any_call(
            Command(
                resume={
                    "email_data": payload["email_data"],
                    "classification": payload["classification"],
                    "extract_data": payload["extract_data"],
                    "draft_response": "edited draft",
                    "action_sqlite": payload["action_sqlite"],
                    "manager_comment": "ok",
                }
            ),
            config={"configurable": {"thread_id": start["thread_id"]}},
        )
