"""LangSmith 데이터셋 업로드 후 EM 평가를 순서대로 실행한다."""

from dotenv import load_dotenv

load_dotenv(override=True)

from app.evaluation.run_em_eval import run_evaluation
from app.evaluation.upload_dataset_to_langsmith import upload_dataset


def run_pipeline() -> None:
    print("=== Step 1/2: LangSmith 데이터셋 업로드 ===")
    upload_dataset()

    print("\n=== Step 2/2: EM 평가 실행 ===")
    run_evaluation()

    print("\n=== 파이프라인 완료 ===")


if __name__ == "__main__":
    # python -m app.evaluation.run_eval_pipeline
    run_pipeline()
