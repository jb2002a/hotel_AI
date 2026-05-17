from langsmith import traceable

from app.errors import BusinessError
from app.schemas.graph_state import EmailAgentState
from app.services.db_service import get_member_and_booking_by_email, get_vacant_room_count
from app.services.vector_store_service import get_vector_store_from_chroma


@traceable(name="policy_retrieve")
def policy_retrieve(state: EmailAgentState) -> dict:
    email_data = state["email_data"]
    query = f"{email_data['email_subject']}\n{email_data['email_content']}"
    try:
        vector_store = get_vector_store_from_chroma()
        search_results = vector_store.similarity_search(query, k=3)
    except Exception as exc:
        raise BusinessError("정책 벡터 스토어 조회에 실패했습니다.", code="VECTOR_STORE_ERROR") from exc
    if not search_results:
        raise BusinessError("관련 정책 문서를 찾을 수 없습니다.", code="POLICY_NOT_FOUND")
    return {"vector_retrieve_results": search_results}


@traceable(name="member_booking_retrieve")
def member_booking_retrieve(state: EmailAgentState) -> dict:
    email_data = state["email_data"]
    email = email_data["sender_email"]
    try:
        member_and_bookings = get_member_and_booking_by_email(email)
    except ValueError as exc:
        raise BusinessError(str(exc), code="MEMBER_NOT_FOUND") from exc
    return {"db_retrieve_results": member_and_bookings}


@traceable(name="vacancy_retrieve")
def vacancy_retrieve(state: EmailAgentState) -> dict:
    try:
        vacant_room_count = get_vacant_room_count()
    except Exception as exc:
        raise BusinessError("객실 현황 조회에 실패했습니다.", code="ROOM_QUERY_ERROR") from exc
    return {"rest_room_retrieve_results": {"vacant_room_count": vacant_room_count}}
