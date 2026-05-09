from langsmith import traceable

from app.errors import BusinessError
from app.schemas.graph_state import ActionSQLite, EmailAgentState


def _require_fields(
    state: EmailAgentState,
    *,
    require_dates: bool = False,
) -> tuple[str, str | None, str | None]:
    email_data = state.get("email_data")
    if not email_data:
        raise BusinessError("state.email_data가 없습니다.")

    email = email_data.get("sender_email")
    if not email:
        raise BusinessError("sender_email이 없습니다.")

    check_in: str | None = None
    check_out: str | None = None
    if require_dates:
        extract_data = state.get("extract_data")
        if not extract_data:
            raise BusinessError("state.extract_data가 없습니다.")
        check_in = extract_data.get("check_in")
        check_out = extract_data.get("check_out")
        if not check_in:
            raise BusinessError("check_in이 없습니다.")
        if not check_out:
            raise BusinessError("check_out이 없습니다.")

    return email, check_in, check_out


def _build_create_sql(email: str, check_in: str, check_out: str) -> str:
    return f"""
    INSERT OR IGNORE INTO members (email, name)
    VALUES ('{email}', NULL);

    UPDATE room_booking
    SET
    member_id = (SELECT id FROM members WHERE email = '{email}'),
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


@traceable(name="booking_plan_node")
def booking_plan_node(state: EmailAgentState) -> dict:
    plan = state.get("plan") or {}
    actions = set(plan.get("actions", []))

    needs_dates = "reservation_create" in actions or "reservation_update" in actions
    email, check_in, check_out = _require_fields(state, require_dates=needs_dates)

    action_sqlite: ActionSQLite = {
        "create_sql": "",
        "update_sql": "",
        "delete_sql": "",
    }

    if "reservation_create" in actions:
        assert check_in is not None and check_out is not None
        rest = state.get("rest_room_retrieve_results") or {}
        room_count = rest.get("vacant_room_count")
        if room_count is not None and room_count >= 1:
            action_sqlite["create_sql"] = _build_create_sql(email, check_in, check_out)

    if "reservation_update" in actions:
        assert check_in is not None and check_out is not None
        action_sqlite["update_sql"] = _build_update_sql(email, check_in, check_out)

    if "reservation_delete" in actions:
        action_sqlite["delete_sql"] = _build_delete_sql(email)

    return {"action_sqlite": action_sqlite}
