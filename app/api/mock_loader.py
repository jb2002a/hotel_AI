import json
from pathlib import Path

_DATASET_PATH = Path(__file__).resolve().parents[2] / "resoruces" / "mail_dataset.jsonl"


def _preview(body: str, max_len: int = 120) -> str:
    text = body.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def load_mock_emails() -> list[dict]:
    emails: list[dict] = []
    with _DATASET_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            inp = row["input"]
            emails.append(
                {
                    "id": row["id"],
                    "subject": inp["subject"],
                    "sender_email": inp["sender_email"],
                    "preview": _preview(inp["body"]),
                }
            )
    return emails


def get_mock_email_by_id(email_id: str) -> dict | None:
    with _DATASET_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row["id"] == email_id:
                return row
    return None


def build_initial_state_from_mock(sample: dict) -> dict:
    inp = sample["input"]
    return {
        "email_data": {
            "email_subject": inp["subject"],
            "email_content": inp["body"],
            "sender_email": inp["sender_email"],
        },
        "extract_data": None,
        "classification": None,
        "actions": None,
        "policy_queries": None,
        "vector_retrieve_results": None,
        "db_retrieve_results": None,
        "rest_room_retrieve_results": None,
        "action_sqlite": None,
        "draft_response": None,
        "manager_comment": None,
        "business_error": None,
        "manager_errors": None,
    }
