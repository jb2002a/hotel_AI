import os
import smtplib
from email.mime.text import MIMEText
from typing import Any

from langsmith import traceable

from app.errors import BusinessError
from app.schemas.graph_state import EmailAgentState


def _format_email_body(draft_response: str, action_sqlite: dict[str, Any] | None) -> str:
    parts = [draft_response.strip()]
    if not action_sqlite:
        return parts[0]

    sql_lines: list[str] = []
    for label, key in (
        ("CREATE", "create_sql"),
        ("UPDATE", "update_sql"),
        ("DELETE", "delete_sql"),
    ):
        sql = str(action_sqlite.get(key) or "").strip()
        if sql:
            sql_lines.append(f"{label}: {sql}")

    if sql_lines:
        parts.append("\n---\n[참고용 예약 SQL]\n" + "\n".join(sql_lines))

    return "\n".join(parts)


@traceable(name="send_email_node")
def send_email_node(state: EmailAgentState) -> dict:
    email_data = state["email_data"]
    draft_response = state.get("draft_response")

    if not draft_response:
        raise BusinessError("draft_response가 비어 있어 메일을 발송할 수 없습니다.")

    sender_email = os.getenv("GMAIL_SENDER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if not sender_email or not app_password:
        raise BusinessError("GMAIL_SENDER, GMAIL_APP_PASSWORD 환경변수가 필요합니다.")

    receiver_email = email_data["sender_email"]
    if not receiver_email:
        raise BusinessError("수신자 이메일이 비어 있어 메일을 발송할 수 없습니다.")

    subject = f"Re: {email_data['email_subject']}"
    body = _format_email_body(draft_response, state.get("action_sqlite"))

    message = MIMEText(body, _charset="utf-8")
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(sender_email, app_password)
        smtp.sendmail(sender_email, receiver_email, message.as_string())

    return {"email_sent": True}
