import os
import smtplib
from email.mime.text import MIMEText

from langsmith import traceable

from app.errors import BusinessError
from app.schemas.graph_state import EmailAgentState


@traceable(name="send_email_node")
def send_email_node(state: EmailAgentState) -> dict:
    email_data = state["email_data"]
    draft_response = state["draft_response"]

    if not draft_response:
        raise BusinessError("draft_response가 비어 있어 메일을 발송할 수 없습니다.")

    sender_email = os.getenv("GMAIL_SENDER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if not sender_email or not app_password:
        raise BusinessError("GMAIL_SENDER, GMAIL_APP_PASSWORD 환경변수가 필요합니다.")

    receiver_email = email_data["sender_email"]
    subject = f"Re: {email_data['email_subject']}"

    message = MIMEText(draft_response, _charset="utf-8")
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(sender_email, app_password)
        smtp.sendmail(sender_email, receiver_email, message.as_string())

    return {}
