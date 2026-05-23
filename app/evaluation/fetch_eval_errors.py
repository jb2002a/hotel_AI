"""LangSmith 실험 조회 및 특정 메트릭 실패 케이스 추출 스크립트.

사용법:
    # 1) 실험 이름 목록 확인
    python -m app.evaluation.fetch_eval_errors --list

    # 2) 특정 메트릭 실패 케이스 조회
    python -m app.evaluation.fetch_eval_errors \
        --experiment "attempt 1" \
        --metrics intent_match plan_match \
        --threshold 1.0
"""

import argparse
import json
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv(override=True)

from langsmith import Client

client = Client()

DATASET_NAME = "hotel_ai_email_dataset"
ALL_METRICS = [
    "intent_match",
    "category_match",
    "urgency_match",
    "plan_match",
    "extract_match",
    "outcome_match",
]


# ──────────────────────────────────────────────
# 1. 실험 목록 출력
# ──────────────────────────────────────────────

def list_experiments() -> None:
    """LangSmith에서 조회 가능한 실험(프로젝트) 목록을 출력한다."""
    projects = list(client.list_projects(name_contains="attempt"))

    print(f"\n{'No':<4} {'실험 이름':<45} {'생성일'}")
    print("-" * 75)
    for i, p in enumerate(sorted(projects, key=lambda x: x.start_time, reverse=True), 1):
        created = p.start_time.strftime("%Y-%m-%d %H:%M") if p.start_time else "-"
        print(f"{i:<4} {p.name:<45} {created}")


# ──────────────────────────────────────────────
# 2. 실패 케이스 조회
# ──────────────────────────────────────────────

def fetch_errors(
    experiment_name: str,
    metrics: list[str],
    threshold: float = 1.0,
) -> list[dict]:
    """
    실험에서 지정한 메트릭 중 하나라도 threshold 미만인 run을 반환한다.

    Args:
        experiment_name: LangSmith 실험(프로젝트) 이름
        metrics: 확인할 메트릭 키 리스트 (예: ["intent_match", "plan_match"])
        threshold: 이 값 미만이면 실패로 간주 (기본 1.0 = 완벽 일치만 통과)

    Returns:
        실패 케이스 딕셔너리 리스트
    """
    # 실험 존재 여부 확인
    matched = [p for p in client.list_projects() if p.name == experiment_name]
    if not matched:
        raise ValueError(
            f"실험 '{experiment_name}'을 찾을 수 없습니다.\n"
            "--list 옵션으로 사용 가능한 실험 목록을 확인하세요."
        )

    experiment = matched[0]
    print(f"\n실험: {experiment.name}")

    # 최상위 run 전체 조회 (execution_order=1 이 최상위)
    runs = list(client.list_runs(
        project_name=experiment_name,
        is_root=True,
    ))
    print(f"총 {len(runs)}개 run 조회됨 → 피드백 수집 중...")

    # run_id → {metric: score} 매핑
    score_map: dict[str, dict[str, float]] = defaultdict(dict)
    for run in runs:
        for fb in client.list_feedback(run_ids=[str(run.id)]):
            if fb.key in metrics and fb.score is not None:
                score_map[str(run.id)][fb.key] = fb.score

    # reference example 캐시 (API 호출 최소화): ex_id -> {outputs, id}
    example_cache: dict[str, dict] = {}

    errors = []
    for run in runs:
        run_id = str(run.id)
        scores = score_map.get(run_id, {})

        # 지정 메트릭 중 하나라도 threshold 미만이면 포함
        failed_metrics = {k: v for k, v in scores.items() if v < threshold}
        if not failed_metrics:
            continue

        # reference 데이터 가져오기
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

        row = {
            "run_id": run_id[:8],
            "id": sample_id,
            "failed_metrics": failed_metrics,
            "subject": inputs.get("subject", ""),
            "body": inputs.get("body", "")[:80],
        }

        # 실패한 메트릭별 ref vs pred 비교값 추가
        for metric in failed_metrics:
            field = _metric_to_field(metric)
            if field:
                row[f"ref_{field}"] = ref_outputs.get(field)
                row[f"pred_{field}"] = outputs.get(field)

        errors.append(row)

    return errors


def _metric_to_field(metric: str) -> str | None:
    """메트릭 이름을 outputs 필드명으로 변환한다."""
    return {
        "intent_match": "intents",
        "plan_match": "plan_actions",
        "category_match": "classification",
        "urgency_match": "classification",
        "extract_match": "extract_data",
        "outcome_match": "expected_outcome",
    }.get(metric)


# ──────────────────────────────────────────────
# 3. 결과 출력
# ──────────────────────────────────────────────

def print_report(errors: list[dict], metrics: list[str]) -> None:
    print(f"\n{'='*65}")
    print(f"실패 케이스: 총 {len(errors)}건  (대상 메트릭: {', '.join(metrics)})")
    print(f"{'='*65}\n")

    # 메트릭별 집계
    counter: dict[str, int] = defaultdict(int)
    for e in errors:
        for k in e["failed_metrics"]:
            counter[k] += 1
    print("[ 메트릭별 실패 건수 ]")
    for k, v in sorted(counter.items(), key=lambda x: -x[1]):
        print(f"  {k:<20} {v}건")
    print()

    # 케이스별 상세
    for i, e in enumerate(errors, 1):
        scores_str = ", ".join(f"{k}={v}" for k, v in e["failed_metrics"].items())
        print(f"[{i:>3}] {scores_str}")
        if e.get("id"):
            print(f"      id      : {e['id']}")
        print(f"      subject : {e['subject']}")
        print(f"      body    : {e['body']}")
        for metric in e["failed_metrics"]:
            field = _metric_to_field(metric)
            if field:
                print(f"      ref_{field:<12}: {e.get(f'ref_{field}')}")
                print(f"      pred_{field:<11}: {e.get(f'pred_{field}')}")
        print()


# ──────────────────────────────────────────────
# 4. CLI 진입점
# ──────────────────────────────────────────────

def main() -> None:
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
        "--metrics", "-m", nargs="+", default=["intent_match"],
        choices=ALL_METRICS,
        help=f"확인할 메트릭 (기본: intent_match). 선택지: {ALL_METRICS}",
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

    # ── JSON 파일 저장 ──────────────────────────────
    save_path = _resolve_output_path(args.output, args.experiment, args.metrics)
    _save_json(errors, save_path)

    # ── stdout 출력 ────────────────────────────────
    if args.json:
        print(json.dumps(errors, ensure_ascii=False, indent=2))
    else:
        print_report(errors, args.metrics)


def _resolve_output_path(output: str | None, experiment: str, metrics: list[str]) -> str:
    """저장 경로를 결정한다. output이 None이면 자동 생성."""
    import os
    if output:
        return output
    safe_exp = experiment.replace(" ", "_").replace("/", "-")
    safe_metrics = "_".join(metrics)
    filename = f"eval_errors_{safe_exp}_{safe_metrics}.json"
    return os.path.join("resoruces", filename)


def _save_json(data: list[dict], path: str) -> None:
    """data를 path에 JSON으로 저장한다."""
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 결과 저장: {path}  ({len(data)}건)")


if __name__ == "__main__":
    # python -m app.evaluation.fetch_eval_errors --list
    # python -m app.evaluation.fetch_eval_errors -e "attempt 1" -m intent_match 
    main()
