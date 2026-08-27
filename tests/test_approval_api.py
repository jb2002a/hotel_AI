"""Tests for approval web flow API and utilities."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api import mock_loader


client = TestClient(app)


def test_load_mock_emails_returns_list():
    emails = mock_loader.load_mock_emails()
    assert len(emails) > 0
    first = emails[0]
    assert "id" in first
    assert "subject" in first
    assert "sender_email" in first
    assert "preview" in first


def test_build_initial_state_from_mock():
    sample = mock_loader.get_mock_email_by_id("sample_001")
    assert sample is not None
    state = mock_loader.build_initial_state_from_mock(sample)
    assert state["email_data"]["email_subject"] == sample["input"]["subject"]
    assert state["email_data"]["email_content"] == sample["input"]["body"]
    assert state["email_data"]["sender_email"] == sample["input"]["sender_email"]


def test_get_mock_emails_endpoint():
    response = client.get("/mock-emails")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_start_run_unknown_email():
    response = client.post("/runs", json={"email_id": "nonexistent"})
    assert response.status_code == 404


@patch("app.api.main.graph_runner.start_run")
def test_start_run_success(mock_start):
    mock_start.return_value = {
        "thread_id": "test-thread",
        "status": "waiting_approval",
        "approval_payload": {"email_data": {}, "classification": {}, "errors": []},
        "result": None,
    }
    response = client.post("/runs", json={"email_id": "sample_001"})
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "test-thread"
    assert body["status"] == "waiting_approval"


def test_build_initial_state_from_custom():
    state = mock_loader.build_initial_state_from_custom(
        subject="  예약 문의  ",
        body="  내일 체크인 가능할까요?  ",
        sender_email=" guest@example.com ",
    )
    assert state["email_data"]["email_subject"] == "예약 문의"
    assert state["email_data"]["email_content"] == "내일 체크인 가능할까요?"
    assert state["email_data"]["sender_email"] == "guest@example.com"
    assert state["classification"] is None


@patch("app.api.main.graph_runner.start_run")
def test_start_custom_run_success(mock_start):
    mock_start.return_value = {
        "thread_id": "custom-thread",
        "status": "waiting_approval",
        "approval_payload": {"email_data": {}, "classification": {}, "errors": []},
        "result": None,
    }
    response = client.post(
        "/runs/custom",
        json={
            "subject": "직접 작성 메일",
            "body": "2026-08-01 체크인으로 예약 부탁드립니다.",
            "sender_email": "interviewer@example.com",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "custom-thread"
    assert body["status"] == "waiting_approval"
    mock_start.assert_called_once()
    email_id, initial_state = mock_start.call_args.args
    assert email_id == "custom:interviewer@example.com"
    assert initial_state["email_data"]["email_subject"] == "직접 작성 메일"


def test_start_custom_run_validation_error():
    response = client.post(
        "/runs/custom",
        json={"subject": "", "body": "본문", "sender_email": "a@b.com"},
    )
    assert response.status_code == 422


@patch("app.api.main.graph_runner.submit_run")
@patch("app.api.main.graph_runner.get_run")
def test_submit_run_success(mock_get_run, mock_submit):
    mock_get_run.return_value = {"thread_id": "test-thread", "status": "waiting_approval"}
    mock_submit.return_value = {
        "thread_id": "test-thread",
        "status": "completed",
        "result": {"draft_response": "ok"},
    }
    response = client.post(
        "/runs/test-thread/submit",
        json={
            "draft_response": "edited",
            "action_sqlite": {"create_sql": "", "update_sql": "", "delete_sql": ""},
            "manager_comment": "approved",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
