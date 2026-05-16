import json
from typing import Literal

from app.config.config import LLM, USER_MOCK_DATA_PATH
from app.errors import BusinessError
from app.schemas.graph_state import EmailAgentState, EmailData, ExtractData
from langgraph.types import Command
from langsmith import traceable


def _resolve_mock_email_idx(state: EmailAgentState, list_len: int) -> int:
    raw = state.get("mock_email_idx", 1)
    try:
        idx = int(raw)
    except (TypeError, ValueError):
        idx = 1
    return max(0, min(idx, list_len - 1))


@traceable(name="email_ingest")
def email_ingest(
    state: EmailAgentState,
) -> Command[Literal["intent_classifier_node", "manager_approval_node"]]:
    try:
        # TODO: 현재는 mock 데이터와 임시적으로 연결, 실제 이메일 서비스와 연동 필요
        # json은 emails내에 subject,body,sender_email,category 필드가 있음 (카테고리는 평가용으로 적어둠, 사용x)

        # 평가용 파이프라인의 경우(state에 email_data가 있음)
        if state.get("email_data"):
            email_data = state["email_data"]
        # 일반적인 파이프라인
        else:
            with open(USER_MOCK_DATA_PATH, "r", encoding="utf-8") as f:
                mock_list = [json.loads(line) for line in f if line.strip()]

            idx = _resolve_mock_email_idx(state, len(mock_list))
            mock_row = mock_list[idx]["input"]

            email_data = EmailData(
                email_subject=mock_row["subject"],
                email_content=mock_row["body"],
                sender_email=mock_row["sender_email"],
            )

        extract_llm = LLM.with_structured_output(ExtractData)
        extract_prompt = f"""
        Extract reservation-related fields from this customer email context.

        Return JSON with exactly these keys:
        - name: The full name of the person who sent this email, as they identify themselves.
        Extract it regardless of context (even if they mention wanting to change or correct their name).
        Use null only if no personal name can be found anywhere in the email.
        - check_in (YYYY-MM-DD if inferable, else null)
        - check_out (YYYY-MM-DD if inferable, else null)

        Subject: {email_data["email_subject"]}
        Body: {email_data["email_content"]}
        """
        extract_data = extract_llm.invoke(extract_prompt)

        return Command(
            update={"email_data": email_data, "extract_data": extract_data},
            goto="intent_classifier_node",
        )
    except BusinessError as exc:
        return Command(
            update={
                "business_error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
            goto="manager_approval_node",
        )
