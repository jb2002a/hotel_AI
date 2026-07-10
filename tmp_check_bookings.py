import sqlite3

conn = sqlite3.connect("app/database/mock_hotel.db")
conn.row_factory = sqlite3.Row

for email in ["kimsh@example.com", "jang@example.com", "scam@example.com", "kosy@example.com"]:
    cur = conn.execute("SELECT id, email, name FROM members WHERE email=?", (email,))
    m = cur.fetchone()
    if not m:
        print(f"{email}: NO MEMBER")
        continue
    cur = conn.execute(
        "SELECT room_number, status, check_in, check_out FROM room_booking WHERE member_id=?",
        (m["id"],),
    )
    bookings = cur.fetchall()
    print(f"{email} ({m['name']}):")
    for b in bookings:
        print(f"  room {b['room_number']} status={b['status']} {b['check_in']} - {b['check_out']}")
