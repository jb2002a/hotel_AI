

from __future__ import annotations

import json
import pathlib
import traceback
from typing import Any

from app.config.config import EM_EVAL_INDICES, EM_EVAL_OUT_DIR, USER_MOCK_DATA_PATH

EM_METRIC_KEYS = (
    "intent_em",
    "category_em",
    "urgency_em",
    "plan_em",
    "name_em",
    "check_in_em",
    "check_out_em",
    "extract_all_em",
    "should_succeed_em",
    "business_error_code_em",
)


def _norm_str(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _ground_truth_intent_list(gt: dict[str, Any]) -> list[str]:
    if "intents" in gt and isinstance(gt["intents"], list):
        return [str(x) for x in gt["intents"]]
    raw = gt.get("intent")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    return [str(raw)]


def _normalize_ground_truth(gt: dict[str, Any]) -> dict[str, Any]:
    """JSONL ground_truth -> comparable dict."""
    cls = gt.get("classification") or {}
    ext = gt.get("extract_data") or {}
    out = gt.get("expected_outcome") or {}
    return {
        "intents": _ground_truth_intent_list(gt),
        "category": cls.get("category"),
        "urgency": cls.get("urgency"),
        "plan_actions": list(gt.get("plan_actions") or []),
        "name": _norm_str(ext.get("name")),
        "check_in": _norm_str(ext.get("check_in")),
        "check_out": _norm_str(ext.get("check_out")),
        "should_succeed": bool(out.get("should_succeed")),
        "business_error_code": out.get("business_error_code"),
    }


def _extract_pred_from_state(state: dict[str, Any]) -> dict[str, Any]:
    clf = state.get("classification") or {}
    intents = clf.get("intents")
    if not isinstance(intents, list):
        intents = []

    plan = state.get("plan") or {}
    actions = plan.get("actions")
    if not isinstance(actions, list):
        actions = []

    ext = state.get("extract_data") or {}
    be = state.get("business_error")
    should_succeed = be is None
    code: str | None = None
    if isinstance(be, dict):
        code = be.get("code")

    return {
        "intents": [str(x) for x in intents],
        "category": clf.get("category"),
        "urgency": clf.get("urgency"),
        "plan_actions": [str(x) for x in actions],
        "name": _norm_str(ext.get("name") if isinstance(ext, dict) else None),
        "check_in": _norm_str(ext.get("check_in") if isinstance(ext, dict) else None),
        "check_out": _norm_str(ext.get("check_out") if isinstance(ext, dict) else None),
        "should_succeed": should_succeed,
        "business_error_code": code,
    }


def _set_equal(a: list[str], b: list[str]) -> bool:
    return set(a) == set(b)


def compute_sample_em(gt_n: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    """Per-field 0/1 exact match flags plus mismatch field names."""
    intent_em = 1 if _set_equal(pred["intents"], gt_n["intents"]) else 0
    category_em = 1 if pred["category"] == gt_n["category"] else 0
    urgency_em = 1 if pred["urgency"] == gt_n["urgency"] else 0
    plan_em = 1 if _set_equal(pred["plan_actions"], [str(x) for x in gt_n["plan_actions"]]) else 0

    name_em = 1 if pred["name"] == gt_n["name"] else 0
    check_in_em = 1 if pred["check_in"] == gt_n["check_in"] else 0
    check_out_em = 1 if pred["check_out"] == gt_n["check_out"] else 0
    extract_all_em = 1 if (name_em and check_in_em and check_out_em) else 0

    gt_code = gt_n["business_error_code"]
    pred_code = pred["business_error_code"]
    should_succeed_em = 1 if pred["should_succeed"] == gt_n["should_succeed"] else 0

    gt_code_norm = gt_code if gt_code is None else str(gt_code)
    pred_code_norm = pred_code if pred_code is None else str(pred_code)
    business_error_code_em = 1 if gt_code_norm == pred_code_norm else 0

    mismatch: list[str] = []
    if not intent_em:
        mismatch.append("intent")
    if not category_em:
        mismatch.append("category")
    if not urgency_em:
        mismatch.append("urgency")
    if not plan_em:
        mismatch.append("plan")
    if not name_em:
        mismatch.append("extract.name")
    if not check_in_em:
        mismatch.append("extract.check_in")
    if not check_out_em:
        mismatch.append("extract.check_out")
    if not extract_all_em:
        mismatch.append("extract_all")
    if not should_succeed_em:
        mismatch.append("should_succeed")
    if not business_error_code_em:
        mismatch.append("business_error_code")

    return {
        "intent_em": intent_em,
        "category_em": category_em,
        "urgency_em": urgency_em,
        "plan_em": plan_em,
        "name_em": name_em,
        "check_in_em": check_in_em,
        "check_out_em": check_out_em,
        "extract_all_em": extract_all_em,
        "should_succeed_em": should_succeed_em,
        "business_error_code_em": business_error_code_em,
        "mismatch_fields": mismatch,
    }


def default_initial_state(mock_email_idx: int) -> dict[str, Any]:
    return {
        "email_data": {
            "email_subject": "",
            "email_content": "",
            "sender_email": "",
        },
        "extract_data": None,
        "classification": None,
        "plan": None,
        "vector_retrieve_results": None,
        "db_retrieve_results": None,
        "rest_room_retrieve_results": None,
        "action_sqlite": None,
        "draft_response": None,
        "approval_packet": None,
        "manager_comment": None,
        "business_error": None,
        "mock_email_idx": mock_email_idx,
    }


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON") from exc
    return rows


def aggregate_metrics(per_sample_scores: list[dict[str, int]]) -> dict[str, float]:
    if not per_sample_scores:
        return {k: 0.0 for k in EM_METRIC_KEYS}
    n = len(per_sample_scores)
    totals = {k: 0 for k in EM_METRIC_KEYS}
    for row in per_sample_scores:
        for k in EM_METRIC_KEYS:
            totals[k] += row.get(k, 0)
    return {k: totals[k] / n for k in EM_METRIC_KEYS}


def run_eval(
    dataset_path: pathlib.Path,
    out_dir: pathlib.Path,
    indices: list[int],
) -> dict[str, Any]:
    from app.graphs.graphs import graph as email_graph
    from app.services.vector_store_service import get_vector_store_from_chroma

    dataset = load_jsonl(dataset_path)

    compiled = email_graph.compile()
    # retrieve 경로에서 첫 호출 지연/재로딩 비용을 줄이기 위해 사전 초기화
    get_vector_store_from_chroma()

    per_sample_written: list[dict[str, Any]] = []

    score_rows_only: list[dict[str, int]] = []

    for idx in indices:
        row = dataset[idx]
        sid = row.get("id", f"idx_{idx}")
        gt_raw = row.get("ground_truth")
        if not isinstance(gt_raw, dict):
            raise ValueError(f"sample {sid}: missing ground_truth object")

        gt_n = _normalize_ground_truth(gt_raw)

        run_error: str | None = None
        final_state: dict[str, Any] = {}

        try:
            final_state = compiled.invoke(default_initial_state(idx))
            assert isinstance(final_state, dict)
        except Exception:
            run_error = traceback.format_exc()
            final_state = {}

        if run_error:
            pred = {
                "intents": [],
                "category": None,
                "urgency": None,
                "plan_actions": [],
                "name": None,
                "check_in": None,
                "check_out": None,
                "should_succeed": True,
                "business_error_code": None,
            }
            em_flags = {k: 0 for k in EM_METRIC_KEYS}
            mismatch = ["run_error"]
        else:
            pred = _extract_pred_from_state(final_state)
            em = compute_sample_em(gt_n, pred)
            em_flags = {k: int(em[k]) for k in EM_METRIC_KEYS}
            mismatch = em["mismatch_fields"]

        record: dict[str, Any] = {
            "id": sid,
            "idx": idx,
            "run_error": run_error,
            **em_flags,
            "mismatch_fields": mismatch,
            "pred": pred,
            "ground_truth_normalized": gt_n,
        }
        per_sample_written.append(record)
        score_rows_only.append({k: em_flags[k] for k in EM_METRIC_KEYS})

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "em_summary.json"
    per_sample_path = out_dir / "em_per_sample.jsonl"

    metrics = aggregate_metrics(score_rows_only)

    five_axes = {
        "intent": metrics["intent_em"],
        "classification": (metrics["category_em"] + metrics["urgency_em"]) / 2.0,
        "plan": metrics["plan_em"],
        "extract": metrics["extract_all_em"],
        "outcome": (metrics["should_succeed_em"] + metrics["business_error_code_em"]) / 2.0,
    }

    summary = {
        "dataset": str(dataset_path.resolve()),
        "n_samples": len(indices),
        "indices": indices,
        "metrics": metrics,
        "five_axes_mean": five_axes,
    }

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with per_sample_path.open("w", encoding="utf-8") as f:
        for rec in per_sample_written:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    return summary


def main() -> None:
    dataset_path: pathlib.Path = USER_MOCK_DATA_PATH
    out_dir: pathlib.Path = EM_EVAL_OUT_DIR

    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    rows = load_jsonl(dataset_path)
    if not rows:
        raise ValueError("Dataset empty")

    if EM_EVAL_INDICES is None:
        indices = list(range(len(rows)))
    else:
        for idx in EM_EVAL_INDICES:
            if idx < 0 or idx >= len(rows):
                raise ValueError(f"index {idx} out of range [0,{len(rows) - 1}]")
        indices = list(EM_EVAL_INDICES)

    summary = run_eval(dataset_path, out_dir, indices)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # python -m app.evaluation.run_em_eval
    main()
