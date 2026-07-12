# 호텔 메일 사무자동화 에이전트 — 작업 목록

## 진행 순서 (로드맵)

- [V] **approve_node 비활성화** — 그래프/파이프라인에서 승인 노드 임시 제거 또는 우회해 개발·평가 속도 확보
- [V] **평가체계 구축** — LangSmith 평가 파이프라인 구축 및 목표 metric 상회
    metrics : action, classification(category/urgency), outcome, policy_queries_presence, extract
- [V]  **LLM judge 구축 여부 결정** — draft 품질, RAG retrieve 품질까지 평가할지 판단 후 필요 시 추가
- [V]  **approve_node 재연동** — 평가용 조기 return 제거 후 Human-in-the-loop(`interrupt`/외부 승인) 다시 연결
- [V]  **승인 결과 스키마 정리** — approve/reject/edit, manager_comment, 수정된 draft/action_sqlite 상태 정의
- [V]  **백엔드 API 구현** — 프론트 연동용 요청 실행, 승인 대기 목록, 승인 상세, 승인/반려/수정 resume 엔드포인트 구성
- [ ] **action_node 구현 보류** — 면접 시연에서는 예약 생성·수정·취소 등 실제 DB 쓰기 액션은 실행하지 않고, 생성된 `action_sqlite`는 참고용 SQL로만 활용
- [ ] **read_email 실제 MCP/API 연동** — 모크(`happy_mock_dataset.jsonl`) 대신 실제 수신 메일을 읽어 `email_data` 초기 상태를 구성하는 `read_email` 경로 연결
- [ ] **send_email_node 구현 및 그래프 연결** — 실제 메일이 수신되면 그래프 처리와 매니저 승인/수정 후 발신자에게 답변 메일 전송
- [ ] **응답 메일 하단 참고 SQL 첨부** — 면접관에게 에이전트의 예약 처리 의도를 보여주기 위해 발송 본문 아래에 `action_sqlite`의 create/update/delete SQL을 참고용으로 포함
- [ ] **프론트 승인 화면 구현** — 승인 큐, 승인 패킷 상세, draft/SQL 수정, 승인/반려 실행 로그 표시
