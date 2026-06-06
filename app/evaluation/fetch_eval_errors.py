"""LangSmith 실험 조회 및 특정 메트릭 실패 케이스 추출 스크립트.

AI에 주입하기 위해 전처리 데이터를 가져오는 스크립트입니다. 

사용법:
    # 1) 실험 이름 목록 확인
    python -m app.evaluation.fetch_eval_errors --list

    # 2) 특정 메트릭 실패 케이스 조회
    python -m app.evaluation.fetch_eval_errors \
        --experiment "attempt 1" \
        --metrics action_match outcome_match \
        --threshold 1.0
"""

import argparse
import json
import sys
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv(override=True)

from langsmith import Client

client = Client()

DATASET_NAME = "hotel_ai_email_dataset"
ALL_METRICS = [
    "action_match",
    "classification_match",
    "outcome_match",
    "policy_queries_presence_match",
    "extract_match",
]

# run_em_eval target / dataset outputs와 동일한 필드
OUTPUT_FIELDS = [
    "actions",
    "policy_queries",
    "classification",
    "expected_outcome",
    "extract_data",
]


def list_experiments() -> None:
    """LangSmith에서 조회 가능한 실험(프로젝트) 목록을 출력한다."""
    projects = list(client.list_projects(name_contains="attempt"))

    print(f"\n{'No':<4} {'실험 이름':<45} {'생성일'}")
    print("-" * 75)
    for i, p in enumerate(sorted(projects, key=lambda x: x.start_time, reverse=True), 1):
        created = p.start_time.strftime("%Y-%m-%d %H:%M") if p.start_time else "-"
        print(f"{i:<4} {p.name:<45} {created}")


def _build_field_pairs(ref_outputs: dict, outputs: dict) -> dict:
    """outputs의 모든 필드를 reference / prediction 쌍으로 묶는다."""
    pairs = {}
    for field in OUTPUT_FIELDS:
        pairs[field] = {
            "reference": ref_outputs.get(field),
            "prediction": outputs.get(field),
        }
    return pairs


def fetch_errors(
    experiment_name: str,
    metrics: list[str],
    threshold: float = 1.0,
) -> list[dict]:
    """
    실험에서 지정한 메트릭 중 하나라도 threshold 미만인 run을 반환한다.

    Returns:
        실패 케이스 딕셔너리 리스트 (id, run_id, input, failed_metrics, fields)
    """
    matched = [p for p in client.list_projects() if p.name == experiment_name]
    if not matched:
        raise ValueError(
            f"실험 '{experiment_name}'을 찾을 수 없습니다.\n"
            "--list 옵션으로 사용 가능한 실험 목록을 확인하세요."
        )

    experiment = matched[0]
    print(f"\n실험: {experiment.name}")

    runs = list(client.list_runs(
        project_name=experiment_name,
        is_root=True,
    ))
    print(f"총 {len(runs)}개 run 조회됨 -> 피드백 수집 중...")

    score_map: dict[str, dict[str, float]] = defaultdict(dict)
    for run in runs:
        for fb in client.list_feedback(run_ids=[str(run.id)]):
            if fb.key in metrics and fb.score is not None:
                score_map[str(run.id)][fb.key] = fb.score

    example_cache: dict[str, dict] = {}

    errors = []
    for run in runs:
        run_id = str(run.id)
        scores = score_map.get(run_id, {})

        failed_metrics = {k: v for k, v in scores.items() if v < threshold}
        if not failed_metrics:
            continue

        ref_outputs = {}
        sample_id = ""
        if run.reference_example_id:
            ex_id = str(run.reference_example_id)
            if ex_id not in example_cache:
                try:
                    ex = client.read_example(ex_id)
                    meta = ex.metadata or {}
                    example_cache[ex_id] = {
                        "outputs": ex.outputs or {},
                        "id": meta.get("id", ""),
                    }
                except Exception:
                    example_cache[ex_id] = {"outputs": {}, "id": ""}
            cached = example_cache[ex_id]
            ref_outputs = cached["outputs"]
            sample_id = cached["id"]

        inputs = run.inputs or {}
        outputs = run.outputs or {}

        errors.append({
            "id": sample_id,
            "run_id": run_id[:8],
            "input": {
                "subject": inputs.get("subject", ""),
                "body": inputs.get("body", ""),
                "sender_email": inputs.get("sender_email", ""),
            },
            "failed_metrics": failed_metrics,
            "fields": _build_field_pairs(ref_outputs, outputs),
        })

    return errors


def print_report(errors: list[dict], metrics: list[str]) -> None:
    print(f"\n{'='*65}")
    print(f"실패 케이스: 총 {len(errors)}건  (대상 메트릭: {', '.join(metrics)})")
    print(f"{'='*65}\n")

    counter: dict[str, int] = defaultdict(int)
    for e in errors:
        for k in e["failed_metrics"]:
            counter[k] += 1
    print("[ 메트릭별 실패 건수 ]")
    for k, v in sorted(counter.items(), key=lambda x: -x[1]):
        print(f"  {k:<20} {v}건")
    print()

    for i, e in enumerate(errors, 1):
        scores_str = ", ".join(f"{k}={v}" for k, v in e["failed_metrics"].items())
        print(f"[{i:>3}] {scores_str}")
        if e.get("id"):
            print(f"      id      : {e['id']}")
        inp = e["input"]
        print(f"      subject : {inp.get('subject', '')}")
        body = inp.get("body", "")
        print(f"      body    : {body[:80]}{'...' if len(body) > 80 else ''}")
        for field, pair in e["fields"].items():
            print(f"      [{field}]")
            print(f"        reference : {pair['reference']}")
            print(f"        prediction: {pair['prediction']}")
        print()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="LangSmith 실험에서 메트릭 실패 케이스를 조회합니다."
    )
    parser.add_argument(
        "--list", action="store_true",
        help="사용 가능한 실험 목록을 출력한다.",
    )
    parser.add_argument(
        "--experiment", "-e", type=str, default=None,
        help="조회할 실험 이름",
    )
    parser.add_argument(
        "--metrics", "-m", nargs="+", default=["action_match"],
        choices=ALL_METRICS,
        help=f"확인할 메트릭 (기본: action_match). 선택지: {ALL_METRICS}",
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=1.0,
        help="이 값 미만을 실패로 간주 (기본: 1.0)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="결과를 JSON으로 stdout에 출력한다 (AI에게 붙여넣기용).",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="결과를 저장할 JSON 파일 경로 (미지정 시 자동 생성).",
    )
    args = parser.parse_args()

    if args.list:
        list_experiments()
        return

    if not args.experiment:
        parser.print_help()
        return

    errors = fetch_errors(
        experiment_name=args.experiment,
        metrics=args.metrics,
        threshold=args.threshold,
    )

    save_path = _resolve_output_path(args.output, args.experiment, args.metrics)
    _save_json(errors, save_path)

    if args.json:
        print(json.dumps(errors, ensure_ascii=False, indent=2))
    else:
        print_report(errors, args.metrics)


def _resolve_output_path(output: str | None, experiment: str, metrics: list[str]) -> str:
    import os
    if output:
        return output
    safe_exp = experiment.replace(" ", "_").replace("/", "-")
    safe_metrics = "_".join(metrics)
    filename = f"eval_errors_{safe_exp}_{safe_metrics}.json"
    return os.path.join("resoruces", filename)


def _save_json(data: list[dict], path: str) -> None:
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[저장] {path}  ({len(data)}건)")


if __name__ == "__main__":
    # python -m app.evaluation.fetch_eval_errors --list
    # python -m app.evaluation.fetch_eval_errors -e attempt1 -m action_match
    main()
