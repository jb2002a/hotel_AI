import json
from langsmith import Client
from dotenv import load_dotenv

load_dotenv(override=True)
client = Client()

dataset = client.create_dataset(
    dataset_name="hotel_ai_eval_dataset_happy_path",
    description="호텔 AI 이메일 처리 평가 데이터셋"
)

examples = []
with open("resoruces/happy_mock_dataset.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line.strip())
        examples.append({
            "inputs": record["input"],       # subject, body, sender_email
            "outputs": record["ground_truth"] # intent, classification, etc.
        })

# 3. 배치로 업로드
client.create_examples(
    inputs=[e["inputs"] for e in examples],
    outputs=[e["outputs"] for e in examples],
    dataset_id=dataset.id
)


#python -m app.evaluation.upload_dataset_to_langsmith
print(f"✅ {len(examples)}개 예제 업로드 완료")