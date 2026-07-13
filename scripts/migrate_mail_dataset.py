"""mail_dataset.jsonl: intents/plan_actions → actions + policy_queries 마이그레이션."""

import json
import re
from pathlib import Path

JSONL_PATH = Path(__file__).resolve().parents[1] / "resources" / "mail_dataset.jsonl"

_QUESTION_MARKERS = (
    "?",
    "인가",
    "궁금",
    "알려",
    "안내",
    "어떻",
    "가능",
    "문의",
    "되나",
    "있나",
    "할까",
    "알고 싶",
    "설명",
)


def _derive_policy_queries(inp: dict) -> list[str]:
    subject = (inp.get("subject") or "").strip()
    body = (inp.get("body") or "").strip()
    for sent in re.split(r"[.!?\n]+", body):
        s = sent.strip()
        if not s:
            continue
        if any(marker in s for marker in _QUESTION_MARKERS):
            return [s]
    if subject:
        return [subject]
    return [body[:120]] if body else []


def migrate_record(record: dict) -> dict:
    gt = dict(record["ground_truth"])
    intents = gt.pop("intents", [])
    plan_actions = gt.pop("plan_actions", [])
    actions = [a for a in plan_actions if a != "vector_retrieve"]
    if "policy_qna" in intents:
        policy_queries = _derive_policy_queries(record["input"])
    else:
        policy_queries = []
    gt["actions"] = actions
    gt["policy_queries"] = policy_queries
    record["ground_truth"] = gt
    return record


def main() -> None:
    lines = JSONL_PATH.read_text(encoding="utf-8").strip().splitlines()
    migrated = [migrate_record(json.loads(line)) for line in lines]
    JSONL_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in migrated) + "\n",
        encoding="utf-8",
    )
    with_policy = sum(1 for r in migrated if r["ground_truth"]["policy_queries"])
    print(f"Migrated {len(migrated)} records ({with_policy} with policy_queries)")


if __name__ == "__main__":
    main()
