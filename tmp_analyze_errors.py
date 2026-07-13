import json
from collections import Counter, defaultdict

with open(
    "resources/eval_errors_hotel_ai_em_eval-48884257_outcome_match_action_match_extract_match.json",
    encoding="utf-8",
) as f:
    data = json.load(f)

print(f"Total failures: {len(data)}\n")

metric_counts = Counter()
for item in data:
    for m in item["failed_metrics"]:
        metric_counts[m] += 1
print("By metric:")
for m, c in metric_counts.most_common():
    print(f"  {m}: {c}")

print()
patterns = defaultdict(list)
for item in data:
    fm = tuple(sorted(item["failed_metrics"].keys()))
    patterns[fm].append(item["id"])

print("Failure combinations:")
for pat, ids in sorted(patterns.items(), key=lambda x: -len(x[1])):
    print(f"  {pat}: {len(ids)} - {ids}")

print("\nOutcome error code mismatches:")
for item in data:
    if "outcome_match" in item["failed_metrics"]:
        ref = item["fields"]["expected_outcome"]["reference"]
        pred = item["fields"]["expected_outcome"]["prediction"]
        print(
            f"  {item['id']}: ref={ref.get('business_error_code')}/{ref.get('should_succeed')} "
            f"pred={pred.get('business_error_code')}/{pred.get('should_succeed')}"
        )

print("\nAction mismatches:")
for item in data:
    if "action_match" in item["failed_metrics"]:
        ref = item["fields"]["actions"]["reference"]
        pred = item["fields"]["actions"]["prediction"]
        print(f"  {item['id']}: ref={ref} pred={pred}")

print("\nExtract mismatches:")
for item in data:
    if "extract_match" in item["failed_metrics"]:
        ref = item["fields"]["extract_data"]["reference"]
        pred = item["fields"]["extract_data"]["prediction"]
        print(f"  {item['id']}: ref={ref} pred={pred}")
