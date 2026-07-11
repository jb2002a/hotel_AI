# 호텔 메일 사무자동화 에이전트 — 작업 목록

## 진행 순서 (로드맵)

- [V] **approve_node 비활성화** — 그래프/파이프라인에서 승인 노드 임시 제거 또는 우회해 개발·평가 속도 확보
- [V] **평가체계 구축** — LangSmith 평가 파이프라인 구축 및 목표 metric 상회
    metrics : action, classification(category/urgency), outcome, policy_queries_presence, extract
- [ ] **LLM judge 구축 여부 결정** — draft 품질, RAG retrieve 품질까지 평가할지 판단 후 필요 시 추가
- [ ] **approve_node 재연동** — 평가용 조기 return 제거 후 Human-in-the-loop(`interrupt`/외부 승인) 다시 연결
- [ ] **승인 결과 스키마 정리** — approve/reject/edit, manager_comment, 수정된 draft/action_sqlite 상태 정의
- [ ] **백엔드 API 구현** — 프론트 연동용 요청 실행, 승인 대기 목록, 승인 상세, 승인/반려/수정 resume 엔드포인트 구성
- [ ] **action_node 구현** — 예약 생성·수정·취소 등 DB 반영(쓰기) 액션 노드 구현 및 트랜잭션/검증 처리
- [ ] **send_email_node 그래프 연결** — 매니저 승인 후 고객 응답 메일 발송 단계 연결
- [ ] **read_email 실제 MCP/API 연동** — 모크(`happy_mock_dataset.jsonl`) 대신 메일 수집용 MCP(또는 동등 API)로 `read_email` 경로 교체
- [ ] **프론트 승인 화면 구현** — 승인 큐, 승인 패킷 상세, draft/SQL 수정, 승인/반려 실행 로그 표시
