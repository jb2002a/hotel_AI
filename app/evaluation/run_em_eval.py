from dotenv import load_dotenv

load_dotenv(override=True)

from app.graphs.graphs import graph
from langsmith import evaluate

compiled = graph.compile()


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
    intents: list = clf.get("intents") or []

    return {
        "intent": intents[0] if intents else None,
        "classification": {
            "category": clf.get("category"),
            "urgency": clf.get("urgency"),
        },
        "expected_outcome": {
            "should_succeed": business_error is None,
            "business_error_code": (business_error or {}).get("code"),
        },
        "extract_data": state.get("extract_data"),
        "plan_actions": list(state.get("actions") or []),
    }


def eval_em(outputs: dict, reference_outputs: dict) -> list[dict]:
    clf_p = outputs.get("classification") or {}
    clf_r = reference_outputs.get("classification") or {}
    out_p = outputs.get("expected_outcome") or {}
    out_r = reference_outputs.get("expected_outcome") or {}
    return [
        {"key": "intent_match",   "score": int(outputs.get("intent") == reference_outputs.get("intent"))},
        {"key": "category_match", "score": int(clf_p.get("category") == clf_r.get("category"))},
        {"key": "urgency_match",  "score": int(clf_p.get("urgency")  == clf_r.get("urgency"))},
        {"key": "plan_match",     "score": int(set(outputs.get("plan_actions") or []) == set(reference_outputs.get("plan_actions") or []))},
        {"key": "extract_match",  "score": int(outputs.get("extract_data") == reference_outputs.get("extract_data"))},
        {"key": "outcome_match",  "score": int(out_p.get("should_succeed") == out_r.get("should_succeed"))},
    ]

if __name__ == "__main__":
    # python -m app.evaluation.run_em_eval
    evaluate(
        target,
        data="hotel_ai_eval_dataset_happy_path",
        evaluators=[eval_em],
        experiment_prefix="hotel_ai_em_eval",
        max_concurrency=4,
    )

    print("Evaluation completed")
