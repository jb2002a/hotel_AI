
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "mock_hotel.db"

CREATE_MEMBERS_SQL = """
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT
);
"""

CREATE_ROOM_BOOKING_SQL = """
CREATE TABLE IF NOT EXISTS room_booking (
    room_number INTEGER PRIMARY KEY
        CHECK (
            (room_number BETWEEN 101 AND 109)
            OR (room_number BETWEEN 201 AND 209)
            OR (room_number BETWEEN 301 AND 309)
        ),
    member_id INTEGER,
    status TEXT NOT NULL DEFAULT 'vacant' CHECK (status IN ('vacant', 'occupied')),
    check_in DATE,
    check_out DATE,
    FOREIGN KEY (member_id) REFERENCES members (id)
);
"""


def create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(CREATE_MEMBERS_SQL)
    conn.execute(CREATE_ROOM_BOOKING_SQL)
    conn.commit()


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        create_tables(conn)
if __name__ == "__main__":
    # python -m app.database.mock_db
    main()
