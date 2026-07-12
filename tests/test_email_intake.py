"""Tests for Gmail IMAP intake service and API."""

from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.services import email_service

client = TestClient(app)


def _make_message(
    *,
    subject: str = "[hotel] 예약 문의",
    body: str = "2025-12-24 체크인 예약 부탁드립니다.",
    sender: str = "guest@example.com",
    message_id: str = "<test@example.com>",
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = "hotel@example.com"
    msg["Message-ID"] = message_id
    msg["Date"] = "Mon, 13 Jul 2026 00:00:00 +0900"
    msg.set_content(body)
    return msg


def test_matches_subject_tag_case_insensitive(monkeypatch):
    monkeypatch.setenv("GMAIL_INBOX_SUBJECT_TAG", "[hotel]")
    assert email_service._matches_subject_tag("[HOTEL] 예약 문의")
    assert not email_service._matches_subject_tag("일반 메일")


def test_extract_body_plain_text():
    msg = _make_message(body="plain body text")
    assert email_service._extract_body(msg) == "plain body text"


def test_extract_body_html_fallback():
    msg = EmailMessage()
    msg.set_content("<p>hello</p>", subtype="html")
    assert email_service._extract_body(msg) == "hello"


def test_build_initial_state_from_email():
    record = {
        "subject": "[hotel] 예약 문의",
        "body": "예약 본문",
        "sender_email": "guest@example.com",
        "preview": "예약 본문",
    }
    state = email_service.build_initial_state_from_email(record)
    assert state["email_data"]["email_subject"] == "[hotel] 예약 문의"
    assert state["email_data"]["email_content"] == "예약 본문"
    assert state["email_data"]["sender_email"] == "guest@example.com"
    assert state["classification"] is None


@patch("app.services.email_service._imap_connection")
def test_list_inbox_emails_filters_by_subject_tag(mock_conn, monkeypatch):
    monkeypatch.setenv("GMAIL_INBOX_SUBJECT_TAG", "[hotel]")

    imap = MagicMock()
    mock_conn.return_value.__enter__.return_value = imap

    hotel_msg = _make_message(subject="[hotel] reservation", body="hotel body")
    normal_msg = _make_message(subject="general mail", body="normal body")
    messages = {
        "1": hotel_msg,
        "2": normal_msg,
    }

    def uid_side_effect(command, *args):
        if command == "search":
            return ("OK", [b"1 2"])
        if command == "fetch":
            uid = args[0]
            msg = messages[uid]
            return ("OK", [(uid.encode(), msg.as_bytes())])
        return ("NO", [None])

    imap.uid.side_effect = uid_side_effect

    emails = email_service.list_inbox_emails(limit=10)
    assert len(emails) == 1
    assert emails[0]["uid"] == "1"
    assert emails[0]["subject"] == "[hotel] reservation"
    assert emails[0]["sender_email"] == "guest@example.com"


@patch("app.api.main.email_service.list_inbox_emails")
def test_get_inbox_emails_endpoint(mock_list_emails):
    mock_list_emails.return_value = [
        {
            "uid": "42",
            "message_id": "<abc@example.com>",
            "subject": "[hotel] 예약 문의",
            "sender_email": "guest@example.com",
            "preview": "preview",
            "received_at": "2026-07-13T00:00:00+09:00",
        }
    ]
    response = client.get("/inbox-emails")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["uid"] == "42"
    assert data[0]["subject"] == "[hotel] 예약 문의"


@patch("app.api.main.email_service.get_email_by_uid")
def test_start_run_from_email_not_found(mock_get_email):
    mock_get_email.return_value = None
    response = client.post("/runs/from-email", json={"uid": "999"})
    assert response.status_code == 404


@patch("app.api.main.graph_runner.start_run")
@patch("app.api.main.email_service.get_email_by_uid")
def test_start_run_from_email_success(mock_get_email, mock_start):
    mock_get_email.return_value = {
        "uid": "42",
        "message_id": "<abc@example.com>",
        "subject": "[hotel] 예약 문의",
        "sender_email": "guest@example.com",
        "preview": "preview",
        "body": "full body",
        "received_at": "2026-07-13T00:00:00+09:00",
    }
    mock_start.return_value = {
        "thread_id": "test-thread",
        "status": "waiting_approval",
        "approval_payload": {"email_data": {}, "classification": {}, "errors": []},
        "result": None,
    }

    response = client.post("/runs/from-email", json={"uid": "42"})
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "test-thread"
    assert body["status"] == "waiting_approval"
    mock_start.assert_called_once()
    _, initial_state = mock_start.call_args[0]
    assert initial_state["email_data"]["email_subject"] == "[hotel] 예약 문의"
    assert initial_state["email_data"]["email_content"] == "full body"
