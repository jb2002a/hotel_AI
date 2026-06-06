from dotenv import load_dotenv

load_dotenv(override=True)

from app.config.config import LLM
from app.graphs.graphs import graph
from langsmith import evaluate

compiled = graph.compile()


def _actions_for_eval(data: dict) -> set[str]:
    return set(data.get("actions") or [])


def _normalize_extract(data: dict | None) -> dict:
    if not data:
        return {"name": None, "check_in": None, "check_out": None}
    return {
        "name": data.get("name"),
        "check_in": data.get("check_in"),
        "check_out": data.get("check_out"),
    }


def _has_policy_queries(data: dict) -> bool:
    return bool(data.get("policy_queries"))


def target(inputs: dict) -> dict:
    state = compiled.invoke(
        {
            "email_data": {
                "email_subject": inputs["subject"],
                "email_content": inputs["body"],
                "sender_email": inputs["sender_email"],
            }
        }
    )
    clf = state.get("classification") or {}
    business_error = state.get("business_error")

    return {
        "actions": list(state.get("actions") or []),
        "policy_queries": list(state.get("policy_queries") or []),
        "classification": {
            "category": clf.get("category"),
            "urgency": clf.get("urgency"),
        },
        "expected_outcome": {
            "should_succeed": business_error is None,
            "business_error_code": (business_error or {}).get("code"),
        },
        "extract_data": state.get("extract_data"),
    }


def eval_em(outputs: dict, reference_outputs: dict) -> list[dict]:
    clf_p = outputs.get("classification") or {}
    clf_r = reference_outputs.get("classification") or {}
    out_p = outputs.get("expected_outcome") or {}
    out_r = reference_outputs.get("expected_outcome") or {}

    action_score = int(_actions_for_eval(outputs) == _actions_for_eval(reference_outputs))
    extract_score = int(
        _normalize_extract(outputs.get("extract_data"))
        == _normalize_extract(reference_outputs.get("extract_data"))
    )
    classification_score = (
        0.5 * int(clf_p.get("category") == clf_r.get("category"))
        + 0.5 * int(clf_p.get("urgency") == clf_r.get("urgency"))
    )
    outcome_score = (
        0.5 * int(out_p.get("should_succeed") == out_r.get("should_succeed"))
        + 0.5 * int(out_p.get("business_error_code") == out_r.get("business_error_code"))
    )
    policy_queries_presence_score = int(
        _has_policy_queries(outputs) == _has_policy_queries(reference_outputs)
    )

    return [
        {"key": "action_match", "score": action_score},
        {"key": "classification_match", "score": classification_score},
        {"key": "outcome_match", "score": outcome_score},
        {"key": "policy_queries_presence_match", "score": policy_queries_presence_score},
        {"key": "extract_match", "score": extract_score},
    ]


def run_evaluation() -> None:
    """LangSmith 데이터셋으로 EM 평가를 실행한다."""
    print(f"Using LLM: {LLM.model_name}")
    evaluate(
        target,
        data="hotel_ai_email_dataset",
        evaluators=[eval_em],
        experiment_prefix="hotel_ai_em_eval",
        max_concurrency=4,
    )
    print("Evaluation completed")


if __name__ == "__main__":
    # python -m app.evaluation.langsmith_eval.run_em_eval
    run_evaluation()
