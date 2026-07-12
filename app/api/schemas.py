from pydantic import BaseModel, Field


class MockEmailSummary(BaseModel):
    id: str
    subject: str
    sender_email: str
    preview: str


class StartRunRequest(BaseModel):
    email_id: str


class InboxEmailSummary(BaseModel):
    uid: str
    message_id: str
    subject: str
    sender_email: str
    preview: str
    received_at: str | None = None


class StartEmailRunRequest(BaseModel):
    uid: str


class ActionSQLitePayload(BaseModel):
    create_sql: str = ""
    update_sql: str = ""
    delete_sql: str = ""


class EmailDataPayload(BaseModel):
    email_subject: str = ""
    email_content: str = ""
    sender_email: str = ""


class ClassificationPayload(BaseModel):
    category: str | None = None
    urgency: str | None = None
    actions: list[str] = Field(default_factory=list)


class ExtractDataPayload(BaseModel):
    name: str | None = None
    check_in: str | None = None
    check_out: str | None = None


class SubmitApprovalRequest(BaseModel):
    email_data: EmailDataPayload | None = None
    classification: ClassificationPayload | None = None
    extract_data: ExtractDataPayload | None = None
    draft_response: str = ""
    action_sqlite: ActionSQLitePayload = Field(default_factory=ActionSQLitePayload)
    manager_comment: str = ""
