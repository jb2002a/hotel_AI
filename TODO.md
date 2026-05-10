# 호텔 메일 사무자동화 에이전트 — 작업 목록

## 진행 순서 (로드맵)

- [V] **approve_node 비활성화** — 그래프/파이프라인에서 승인 노드 임시 제거 또는 우회해 개발·평가 속도 확보
- [ ] **평가체계 구축** — langsmith로 평가체계 구축
    metrics : intent,category,urgency,plan,extract,business_error
- [ ] **llm judge 구축** — draft, rag retrieve


- [ ] **approve_node 재연동** — 평가·플로우 안정 후 Human-in-the-loop(`interrupt`/외부 승인) 다시 연결
- [ ] **action_node 구현** — 예약 생성·수정·취소 등 DB 반영(쓰기) 액션 노드 (`booking_action_node` 등과 정합)
- [ ] **read_email 실제 MCP 연동** — 모크(`happy_mock_dataset.json`) 대신 메일 수집용 MCP(또는 동등 API)로 `read_email` 경로 교체
