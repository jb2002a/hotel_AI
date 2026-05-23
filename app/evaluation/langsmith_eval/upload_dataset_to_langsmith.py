import json

from dotenv import load_dotenv
from langsmith import Client
from langsmith.utils import LangSmithConflictError

load_dotenv(override=True)

DATASET_NAME = "hotel_ai_email_dataset"
DATASET_DESCRIPTION = "호텔 AI 메일 데이터셋"
JSONL_PATH = "resoruces/mail_dataset.jsonl"

def upload_dataset() -> int:
    """JSONL을 LangSmith 데이터셋에 업로드한다. 업로드한 예제 수를 반환한다."""
    client = Client()

    try:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=DATASET_DESCRIPTION,
        )
    except LangSmithConflictError:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        old_ids = [ex.id for ex in client.list_examples(dataset_id=dataset.id)]
        if old_ids:
            client.delete_examples(old_ids)
            print(f"기존 예제 {len(old_ids)}개 삭제")

    examples = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line.strip())
            examples.append({
                "inputs": record["input"],
                "outputs": record["ground_truth"],
            })

    client.create_examples(
        inputs=[e["inputs"] for e in examples],
        outputs=[e["outputs"] for e in examples],
        dataset_id=dataset.id,
    )

    print(f"✅ {len(examples)}개 예제 업로드 완료 (dataset: {DATASET_NAME})")
    return len(examples)


if __name__ == "__main__":
    # python -m app.evaluation.langsmith_eval.upload_dataset_to_langsmith
    upload_dataset()
