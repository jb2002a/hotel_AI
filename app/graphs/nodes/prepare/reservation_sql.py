from app.errors import BusinessError
from app.schemas.graph_state import ActionSQLite, EmailAgentState


def _require_email(state: EmailAgentState) -> str:
    email_data = state.get("email_data")
    if not email_data:
        raise BusinessError("state.email_data가 없습니다.")

    email = email_data.get("sender_email")
    if not email:
        raise BusinessError("sender_email이 없습니다.")
    return email


def _require_create_dates(state: EmailAgentState) -> tuple[str, str]:
    extract_data = state.get("extract_data")
    if not extract_data:
        raise BusinessError(
            "state.extract_data가 없습니다.",
            code="BOOKING_CONTEXT_REQUIRED",
        )

    check_in = extract_data.get("check_in")
    check_out = extract_data.get("check_out")
    if not check_in or not check_out:
        raise BusinessError(
            "신규 예약에는 check_in과 check_out이 모두 필요합니다.",
            code="BOOKING_CONTEXT_REQUIRED",
        )
    return check_in, check_out


def _get_occupied_booking(state: EmailAgentState) -> dict:
    db_results = state.get("db_retrieve_results")
    if db_results is None:
        raise BusinessError(
            "예약 변경/취소에는 회원 및 예약 DB 조회가 필요합니다.",
            code="BOOKING_CONTEXT_REQUIRED",
        )
    bookings = db_results.get("bookings")
    if bookings is None or not isinstance(bookings, list):
        raise BusinessError(
            "예약 DB 조회 결과(bookings)가 없거나 형식이 올바르지 않습니다.",
            code="BOOKING_CONTEXT_REQUIRED",
        )
    occupied = [
        b for b in bookings if isinstance(b, dict) and b.get("status") == "occupied"
    ]
    if not occupied:
        raise BusinessError(
            "변경/취소할 상태의 예약(status=occupied)이 없습니다.",
            code="BOOKING_NOT_FOUND",
        )
    return occupied[0]


def _resolve_update_dates(state: EmailAgentState) -> tuple[str, str]:
    """extract 목표값 + DB 기존값 merge로 update용 날짜를 확정한다."""
    extract_data = state.get("extract_data") or {}
    extract_in = extract_data.get("check_in")
    extract_out = extract_data.get("check_out")

    if not extract_in and not extract_out:
        raise BusinessError(
            "예약 일정 변경에는 변경할 check_in 또는 check_out이 필요합니다.",
            code="BOOKING_CONTEXT_REQUIRED",
        )

    booking = _get_occupied_booking(state)
    check_in = extract_in or booking.get("check_in")
    check_out = extract_out or booking.get("check_out")

    if not check_in or not check_out:
        raise BusinessError(
            "예약 일정 변경에 필요한 날짜 정보가 부족합니다.",
            code="BOOKING_CONTEXT_REQUIRED",
        )
    return check_in, check_out


def _build_create_sql(
    email: str,
    check_in: str,
    check_out: str,
    name: str | None = None,
) -> str:
    email_escaped = email.replace("'", "''")
    if name and str(name).strip():
        name_escaped = str(name).strip().replace("'", "''")
        name_sql = f"'{name_escaped}'"
    else:
        name_sql = "NULL"
    return f"""
    INSERT OR IGNORE INTO members (email, name)
    VALUES ('{email_escaped}', {name_sql});

    UPDATE room_booking
    SET
    member_id = (SELECT id FROM members WHERE email = '{email_escaped}'),
    status = 'occupied',
    check_in = '{check_in}',
    check_out = '{check_out}'
    WHERE room_number = (
    SELECT room_number
    FROM room_booking
    WHERE status = 'vacant'
    ORDER BY room_number
    LIMIT 1
    );
    """.strip()


def _build_update_sql(email: str, check_in: str, check_out: str) -> str:
    return f"""
    UPDATE room_booking
    SET
    check_in = '{check_in}',
    check_out = '{check_out}'
    WHERE member_id = (SELECT id FROM members WHERE email = '{email}')
    AND status = 'occupied';
    """.strip()


def _build_delete_sql(email: str) -> str:
    return (
        "UPDATE room_booking "
        "SET member_id = NULL, status = 'vacant', check_in = NULL, check_out = NULL "
        f"WHERE member_id = (SELECT id FROM members WHERE email = '{email}') "
        "AND status = 'occupied';"
    )


def build_action_sqlite(state: EmailAgentState, actions: set[str]) -> dict | None:
    """예약 액션에 따라 SQL 생성"""

    has_booking = actions & {"reservation_create", "reservation_update", "reservation_delete"}
    if not has_booking:
        return None

    email = _require_email(state)

    action_sqlite: ActionSQLite = {
        "create_sql": "",
        "update_sql": "",
        "delete_sql": "",
    }

    if "reservation_create" in actions:
        check_in, check_out = _require_create_dates(state)
        rest = state.get("rest_room_retrieve_results") or {}
        room_count = rest.get("vacant_room_count")
        if not room_count or room_count < 1:
            raise BusinessError("현재 예약 가능한 객실이 없습니다.", code="NO_VACANCY")
        extract_data = state.get("extract_data") or {}
        guest_name = extract_data.get("name")
        action_sqlite["create_sql"] = _build_create_sql(
            email, check_in, check_out, guest_name
        )

    if "reservation_update" in actions or "reservation_delete" in actions:
        if state.get("db_retrieve_results") is None:
            raise BusinessError(
                "예약 변경/취소에는 회원 및 예약 DB 조회가 필요합니다.",
                code="BOOKING_CONTEXT_REQUIRED",
            )

    if "reservation_update" in actions:
        check_in, check_out = _resolve_update_dates(state)
        action_sqlite["update_sql"] = _build_update_sql(email, check_in, check_out)

    if "reservation_delete" in actions:
        _get_occupied_booking(state)
        action_sqlite["delete_sql"] = _build_delete_sql(email)

    return {"action_sqlite": action_sqlite}
