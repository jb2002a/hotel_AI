import json

with open("resources/mail_dataset.jsonl", encoding="utf-8") as f:
    samples = [json.loads(line) for line in f if line.strip()]

import sqlite3

conn = sqlite3.connect("app/database/mock_hotel.db")
existing = {r[0] for r in conn.execute("SELECT email FROM members")}

needs_member = []
for s in samples:
    gt = s["ground_truth"]
    if gt["expected_outcome"]["should_succeed"] and "reservation_search" in gt["actions"]:
        email = s["input"]["sender_email"]
        if email not in existing:
            needs_member.append((s["id"], email, gt["extract_data"].get("name")))

print("Success reservation_search but member missing:")
for item in needs_member:
    print(" ", item)

create_success_missing = []
for s in samples:
    gt = s["ground_truth"]
    if gt["expected_outcome"]["should_succeed"] and "reservation_create" in gt["actions"]:
        email = s["input"]["sender_email"]
        if email not in existing:
            create_success_missing.append((s["id"], email))

print("\nSuccess reservation_create but member missing (OK for create):")
for item in create_success_missing:
    print(" ", item)
