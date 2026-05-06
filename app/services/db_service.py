import sqlite3
from typing import Any

from app.config.config import DB_PATH
from langsmith import traceable


@traceable(name="get_member_and_booking_by_name_email")
def get_member_and_booking_by_name_email(name: str, email: str) -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        cur = conn.execute(
            "SELECT id, email, name FROM members WHERE name = ? AND email = ?",
            (name, email),
        )
        member_row = cur.fetchone()

        if member_row is None:
            raise ValueError(
                f"회원을 찾을 수 없습니다: name={name!r}, email={email!r}"
            )

        member_id = member_row["id"]
        member_wrapper: dict[str, Any] = {
            "member": {
                "id": member_row["id"],
                "email": member_row["email"],
                "name": member_row["name"],
            }
        }

        cur = conn.execute(
            """
            SELECT room_number, member_id, status, check_in, check_out
            FROM room_booking
            WHERE member_id = ?
            ORDER BY room_number
            """,
            (member_id,),
        )
        booking_rows = cur.fetchall()
        bookings = [
            {
                "room_number": r["room_number"],
                "member_id": r["member_id"],
                "status": r["status"],
                "check_in": r["check_in"],
                "check_out": r["check_out"],
            }
            for r in booking_rows
        ]
        bookings_wrapper: dict[str, Any] = {"bookings": bookings}

    return [member_wrapper, bookings_wrapper]
