"""Tests for send_email_node."""

from email import message_from_string
from unittest.mock import MagicMock, patch

import pytest

from app.errors import BusinessError
from app.graphs.nodes.response.execution_node import (
    _format_email_body,
    send_email_node,
)


def test_format_email_body_without_sql():
    body = _format_email_body("안녕하세요.", None)
    assert body == "안녕하세요."


def test_format_email_body_with_sql_footer():
    body = _format_email_body(
        "답변 본문입니다.",
        {
            "create_sql": "INSERT INTO bookings ...",
            "update_sql": "",
            "delete_sql": "DELETE FROM bookings ...",
        },
    )
    assert "답변 본문입니다." in body
    assert "[참고용 예약 SQL]" in body
    assert "CREATE: INSERT INTO bookings ..." in body
    assert "DELETE: DELETE FROM bookings ..." in body
    assert "UPDATE:" not in body


def test_send_email_node_requires_draft():
    with pytest.raises(BusinessError, match="draft_response"):
        send_email_node(
            {
                "email_data": {
                    "email_subject": "test",
                    "email_content": "body",
                    "sender_email": "guest@example.com",
                },
                "draft_response": None,
            }
        )


@patch("app.graphs.nodes.response.execution_node.smtplib.SMTP")
def test_send_email_node_sends_formatted_body(mock_smtp_cls):
    mock_smtp = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_smtp

    state = {
        "email_data": {
            "email_subject": "[hotel] 예약 문의",
            "email_content": "본문",
            "sender_email": "guest@example.com",
        },
        "draft_response": "Hello customer.",
        "action_sqlite": {
            "create_sql": "INSERT INTO bookings VALUES (...);",
            "update_sql": "",
            "delete_sql": "",
        },
    }

    with patch.dict(
        "os.environ",
        {"GMAIL_SENDER": "hotel@example.com", "GMAIL_APP_PASSWORD": "secret"},
    ):
        result = send_email_node(state)

    assert result == {"email_sent": True}
    mock_smtp.login.assert_called_once_with("hotel@example.com", "secret")
    mock_smtp.sendmail.assert_called_once()
    _, receiver, raw_message = mock_smtp.sendmail.call_args[0]
    assert receiver == "guest@example.com"
    body = message_from_string(raw_message).get_payload(decode=True).decode("utf-8")
    assert "Hello customer." in body
    assert "[참고용 예약 SQL]" in body
    assert "INSERT INTO bookings" in body
