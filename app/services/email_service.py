"""Gmail IMAP intake: fetch emails whose subject contains a configured tag."""

from __future__ import annotations

import email
import imaplib
import os
import re
from contextlib import contextmanager
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any, Iterator

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
_DEFAULT_SUBJECT_TAG = "[hotel]"
_DEFAULT_MAILBOX = "INBOX"
_DEFAULT_LIST_LIMIT = 50


def _preview(body: str, max_len: int = 120) -> str:
    text = body.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _get_credentials() -> tuple[str, str]:
    sender = os.getenv("GMAIL_SENDER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if not sender or not app_password:
        raise ValueError("GMAIL_SENDER, GMAIL_APP_PASSWORD 환경변수가 필요합니다.")
    return sender, app_password


def _get_subject_tag() -> str:
    return os.getenv("GMAIL_INBOX_SUBJECT_TAG", _DEFAULT_SUBJECT_TAG)


def _get_mailbox() -> str:
    return os.getenv("GMAIL_INBOX_MAILBOX", _DEFAULT_MAILBOX)


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for chunk, charset in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts).strip()


def _extract_email_address(from_header: str) -> str:
    _, addr = parseaddr(from_header)
    return addr


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_body(msg: Message) -> str:
    if msg.is_multipart():
        plain_parts: list[str] = []
        html_parts: list[str] = []
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if content_type == "text/plain":
                plain_parts.append(decoded)
            elif content_type == "text/html":
                html_parts.append(decoded)
        if plain_parts:
            return "\n".join(plain_parts).strip()
        if html_parts:
            return _html_to_text("\n".join(html_parts))
        return ""

    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    decoded = payload.decode(charset, errors="replace")
    if msg.get_content_type() == "text/html":
        return _html_to_text(decoded)
    return decoded.strip()


def _matches_subject_tag(subject: str) -> bool:
    tag = _get_subject_tag()
    return tag.lower() in subject.lower()


def _parse_received_at(msg: Message) -> str | None:
    date_header = msg.get("Date")
    if not date_header:
        return None
    try:
        return parsedate_to_datetime(date_header).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _message_to_summary(uid: bytes | str, msg: Message) -> dict[str, Any]:
    uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
    subject = _decode_header_value(msg.get("Subject"))
    from_header = _decode_header_value(msg.get("From"))
    sender_email = _extract_email_address(from_header)
    body = _extract_body(msg)
    return {
        "uid": uid_str,
        "message_id": (msg.get("Message-ID") or "").strip(),
        "subject": subject,
        "sender_email": sender_email,
        "preview": _preview(body),
        "received_at": _parse_received_at(msg),
    }


def _message_to_email_data(msg: Message) -> dict[str, str]:
    subject = _decode_header_value(msg.get("Subject"))
    from_header = _decode_header_value(msg.get("From"))
    return {
        "email_subject": subject,
        "email_content": _extract_body(msg),
        "sender_email": _extract_email_address(from_header),
    }


@contextmanager
def _imap_connection() -> Iterator[imaplib.IMAP4_SSL]:
    sender, app_password = _get_credentials()
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        imap.login(sender, app_password)
        status, _ = imap.select(_get_mailbox(), readonly=True)
        if status != "OK":
            raise ValueError(f"메일함을 열 수 없습니다: {_get_mailbox()}")
        yield imap
    finally:
        try:
            imap.close()
        except imaplib.IMAP4.error:
            pass
        imap.logout()


def _fetch_message_by_uid(imap: imaplib.IMAP4_SSL, uid: bytes | str) -> Message | None:
    uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
    status, data = imap.uid("fetch", uid_str, "(BODY.PEEK[])")
    if status != "OK" or not data or data[0] is None:
        return None
    raw = data[0][1]
    if not isinstance(raw, (bytes, bytearray)):
        return None
    return email.message_from_bytes(raw)


def list_inbox_emails(*, limit: int = _DEFAULT_LIST_LIMIT) -> list[dict[str, Any]]:
    """Return recent inbox emails whose subject contains the configured tag."""
    with _imap_connection() as imap:
        status, data = imap.uid("search", None, "ALL")
        if status != "OK" or not data or not data[0]:
            return []

        uids = data[0].split()
        if len(uids) > limit:
            uids = uids[-limit:]
        uids = list(reversed(uids))

        results: list[dict[str, Any]] = []
        for uid in uids:
            msg = _fetch_message_by_uid(imap, uid)
            if msg is None:
                continue
            subject = _decode_header_value(msg.get("Subject"))
            if not _matches_subject_tag(subject):
                continue
            results.append(_message_to_summary(uid, msg))
        return results


def get_email_by_uid(uid: str) -> dict[str, Any] | None:
    """Fetch one inbox email by IMAP UID."""
    with _imap_connection() as imap:
        msg = _fetch_message_by_uid(imap, uid)
        if msg is None:
            return None
        subject = _decode_header_value(msg.get("Subject"))
        if not _matches_subject_tag(subject):
            return None
        summary = _message_to_summary(uid, msg)
        summary["body"] = _extract_body(msg)
        return summary


def build_initial_state_from_email(email_record: dict[str, Any]) -> dict[str, Any]:
    """Convert a fetched inbox email into graph initial state."""
    return {
        "email_data": {
            "email_subject": email_record["subject"],
            "email_content": email_record.get("body") or email_record.get("preview", ""),
            "sender_email": email_record["sender_email"],
        },
        "extract_data": None,
        "classification": None,
        "actions": None,
        "policy_queries": None,
        "vector_retrieve_results": None,
        "db_retrieve_results": None,
        "rest_room_retrieve_results": None,
        "action_sqlite": None,
        "draft_response": None,
        "manager_comment": None,
        "business_error": None,
        "manager_errors": None,
    }
