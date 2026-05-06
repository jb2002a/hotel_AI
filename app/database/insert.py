# 실서비스에 사용하지 않습니다, mock 데이터 주입용


import json
import sqlite3
from pathlib import Path

from .mock_db import DB_PATH, create_tables

_DATA_JSON = Path(__file__).resolve().parent / "mock_db_data.json"


def _load_json() -> dict:
    with _DATA_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def seed_mock_db(conn: sqlite3.Connection | None = None) -> None:
    """mock_db_data.json 내용을 mock_hotel.db에 반영한다."""
    data = _load_json()
    members = data["members"]
    room_booking = data["room_booking"]

    def _run(c: sqlite3.Connection) -> None:
        create_tables(c)
        c.execute("DELETE FROM room_booking")
        c.execute("DELETE FROM members")
        c.executemany(
            "INSERT INTO members (id, email, name) VALUES (?, ?, ?)",
            [(m["id"], m["email"], m["name"]) for m in members],
        )
        c.executemany(
            """
            INSERT INTO room_booking (
                room_number, member_id, status, check_in, check_out
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    b["room_number"],
                    b["member_id"],
                    b["status"],
                    b["check_in"],
                    b["check_out"],
                )
                for b in room_booking
            ],
        )
        c.commit()

    if conn is not None:
        _run(conn)
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as c:
            _run(c)


def main() -> None:
    seed_mock_db()


if __name__ == "__main__":
    # python -m app.database.service
    main()
