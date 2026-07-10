import sqlite3

conn = sqlite3.connect("app/database/mock_hotel.db")
cur = conn.execute("SELECT email, name FROM members")
print("All members:")
for row in cur.fetchall():
    print(" ", row)

emails = [
    "song.hg@example.com",
    "guan.yu@example.com",
    "minjae@example.com",
    "hwang@example.com",
    "user4@domain.com",
    "scam@example.com",
    "biz.trip@example.com",
    "user2@domain.com",
    "user6@domain.com",
]
print("\nEval emails:")
for e in emails:
    cur = conn.execute("SELECT email, name FROM members WHERE email=?", (e,))
    print(f"  {e}: {cur.fetchone()}")
