# 평가 계획 (Evaluation Plan)

현재 `run_em_eval.py`는 **분류/계획/추출** 레이어의 구조적 정확성만 평가하며, 아래 영역들이 누락되어 있습니다.

---

## 현재 평가 항목 (EM)

| 키 | 설명 |
|----|------|
| `intent_match` | 첫 번째 인텐트 정확도 |
| `category_match` | 스팸/정상 분류 정확도 |
| `urgency_match` | 긴급도 분류 정확도 |
| `plan_match` | 플랜 액션 집합 일치 여부 |
| `extract_match` | ExtractData (name, check_in, check_out) 일치 여부 |
| `outcome_match` | business_error 발생 여부 일치 |

---

## 추가 필요 평가

### 1. `draft_response` 품질 평가 (가장 중요)

`target()`이 `draft_response`를 반환하지도 않고, 평가 항목에도 없습니다.  
최종 고객 응답 품질이 서비스 핵심임에도 전혀 측정되지 않는 상태입니다.

EM으로는 측정 불가능하므로 **LLM-as-a-Judge** 방식이 적합합니다.

```python
# 평가해야 할 항목들
- 템플릿 준수 여부 (서두/말미 고정 문구 포함 여부)
- 검색 근거 반영도 (vector_retrieve 내용이 답변에 사용됐는가)
- 거짓 정보 단언 여부 (근거 없는 사실 단정)
- 정중함 / 비즈니스 톤 유지
- 고객 질문 해소 완결성
```

---

### 2. `action_sqlite` SQL 평가

`booking_plan_node`에서 생성하는 SQL이 올바른지 전혀 평가하지 않습니다.  
`target()`에서 `action_sqlite` 자체를 반환하지 않고 있습니다.

예약 생성/수정/삭제는 DB에 직접 영향을 주는 행동이므로 정확성이 중요합니다.

```python
# 추가해야 할 평가 항목 (예시)
{"key": "create_sql_match", "score": int(outputs["action_sqlite"]["create_sql"] == ref["action_sqlite"]["create_sql"])}
# 또는 SQL 실행 결과 기반 평가 (행 변화 비교)
```

---

### 3. `business_error_code` 세분화

현재 `outcome_match`는 `should_succeed` (성공/실패 여부)만 체크합니다.  
`target()`이 `business_error_code`를 반환하고 있음에도 `eval_em`에서 사용하지 않고 있습니다.

`BOOKING_NOT_FOUND`, `BOOKING_CONTEXT_REQUIRED` 등 에러 코드를 잘못 반환하는 케이스도 포착해야 합니다.

```python
# 추가
{"key": "error_code_match", "score": int(out_p.get("business_error_code") == out_r.get("business_error_code"))}
```

---

### 4. 멀티 인텐트 평가

현재는 `intents[0]`만 비교합니다.  
이메일에 여러 인텐트가 포함된 경우(예: `policy_qna` + `reservation_create`) 나머지 인텐트는 평가되지 않습니다.

```python
# 현재
int(outputs.get("intent") == reference_outputs.get("intent"))  # 첫 번째만

# 권장: Jaccard similarity
predicted = set(state["classification"]["intents"])
expected  = set(ref["classification"]["intents"])
score = len(predicted & expected) / len(predicted | expected)
```

---

### 5. Error Path 데이터셋 평가

현재 데이터셋이 `hotel_ai_eval_dataset_happy_path`로 정상 케이스만 포함됩니다.  
비정상 케이스를 별도 데이터셋으로 만들어 평가해야 합니다.

```
# 필요한 에러 케이스
- 존재하지 않는 예약 변경/삭제 시도 → BOOKING_NOT_FOUND
- sender_email 없는 이메일 → 조기 종료
- spam 이메일 → approval_node 라우팅 확인
- out_of_scope 인텐트 → 적절한 거절 답변
```

---

## 우선순위 요약

| 순위 | 평가 항목 | 방식 | 이유 |
|------|-----------|------|------|
| 1 | `draft_response` 품질 | LLM-as-a-Judge | 최종 고객 접점, 미측정 상태 |
| 2 | `action_sqlite` 정확성 | EM 또는 실행 비교 | DB 직접 영향, 오류 시 치명적 |
| 3 | Error Path 데이터셋 | EM | 현재 happy_path만 존재 |
| 4 | `error_code` 세분화 | EM | 이미 `target()`에서 반환 중이나 미사용 |
| 5 | 멀티 인텐트 Jaccard | 유사도 점수 | 현재 단일 인텐트만 평가 |
