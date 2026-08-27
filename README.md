# 호텔 메일 사무자동화 에이전트

호텔 고객 메일을 **분류 · 정보 추출 · 규정 RAG · 예약 SQL 초안 생성 · 답변 초안**까지 처리하고, 매니저 승인 후에만 회신을 보내는 LangGraph 기반 LLM 에이전트입니다.

코로나19 이후 호텔·숙박 업계의 인력 공백이 충분히 회복되지 않으며 구인난이 이어지고 있습니다. 반복적인 메일 응대·예약 문의 처리는 현장의 분명한 페인 포인트이고, 그 부담을 줄일 수 있다고 판단해 이 프로젝트를 선정·구현했습니다.

---

## Demo

> 시연 기간 동안 관리자 승인 사이트를 공개 운영할 예정입니다. URL은 아래에 업데이트합니다.

- **Live Demo**: `[데모 URL — 추후 기입]`
- **시연 흐름**: 수신 메일 선택 → 에이전트 실행 → 승인 화면에서 draft/SQL 검토·수정 → 승인/반려 → 답변 메일 발송

### 스크린샷

<!-- 이미지 경로를 채운 뒤 주석을 해제하세요 -->

```text
[스크린샷 1] 수신 메일 목록 / 실행
[스크린샷 2] 매니저 승인 화면 (분류 · draft · SQL)
[스크린샷 3] 승인 후 발송 결과
```

<!--
![수신 메일 목록](docs/images/01-inbox.png)
![매니저 승인](docs/images/02-approval.png)
![발송 결과](docs/images/03-result.png)
-->

---

## Features

- **메일 분류**: spam / high urgency / normal, 필요 시 즉시 매니저 승인으로 라우팅
- **의도·슬롯 추출**: 예약 create/update/delete/search 액션, 투숙객·일정 등 `extract_data`
- **정책 RAG**: 호텔 규정 문서(Chroma + BGE-M3)에서 `policy_queries` 기반 검색
- **예약 SQL 초안**: 조회·공실·기존 예약 컨텍스트를 반영한 create/update/delete SQL 생성
- **답변 초안 + HITL**: LangGraph `interrupt`로 승인·반려·수정 후 resume
- **실메일 연동**: Gmail IMAP 수신 · SMTP 발송 (제목 태그 `[hotel]` 필터)
- **관리자 UI**: FastAPI + React로 승인 큐·상세·수정·실행 결과 확인
- **정량 평가**: LangSmith Exact Match 파이프라인 (`mail_dataset.jsonl` 108건)

---

## Architecture

```mermaid
flowchart TD
    START([START]) --> CLASSIFY[email_classification]
    CLASSIFY --> INGEST{normal?}
    INGEST -->|yes| EXTRACT[email_ingest]
    INGEST -->|spam / high urgency| APPROVAL[manager_approval]
    EXTRACT --> PREPARE[prepare]
    PREPARE --> SQL[sql_build]
    SQL --> DRAFT[reply_draft]
    DRAFT --> APPROVAL
    APPROVAL -->|approve / edit| ACTION[sql_action]
    ACTION --> SEND[send_email]
    APPROVAL -->|reject| END([END])
    SEND --> END
```

분류 → (정상 메일만) 추출·RAG·SQL·초안 → **모든 케이스가 매니저 승인(`interrupt`)** → 승인 시 발송.  
spam/긴급·오류는 자동 처리하지 않고 승인으로 넘깁니다. 매니저가 UI에서 draft/SQL을 검토·수정하면 FastAPI가 LangGraph를 `resume`합니다.

### 디렉터리

```text
app/
  graphs/          # LangGraph 노드 · 엣지
  api/             # FastAPI (실행 · 승인 resume)
  rag/             # 규정 파싱 · 벡터 적재
  evaluation/      # LangSmith 업로드 · EM 평가
  services/        # 메일 · DB · 벡터스토어
frontend/          # React 매니저 승인 UI
resources/         # 평가 데이터셋 · 규정 문서 · mock
tests/             # interrupt / API / 발송 등
```

### 기술 블로그 (왜 이렇게 설계했는가)

- `[라우터 구조 선택 이유 추후 기입]`

---

## Tech Stack

| 영역 | 기술 |
|------|------|
| Agent | LangGraph, LangChain, OpenAI (`gpt-4o-mini`) |
| Observability / Eval | LangSmith |
| RAG | LlamaCloud 파싱, Chroma, `BAAI/bge-m3` |
| Backend | FastAPI, Uvicorn |
| Frontend | React, TypeScript, Vite |
| Data | SQLite (예약 mock DB), JSONL 평가셋 |
| Mail | Gmail IMAP / SMTP (앱 비밀번호) |

---

## Evaluation

최대한 다양한 호텔 고객 메일 시나리오를 반영한 **golden dataset 108건**을 직접 구성했습니다.  
spam / high urgency / normal 분류, 예약 생성·변경·취소·조회, 규정 문의, 복합 의도, 성공/실패 케이스 등 다양한 타입의 데이터를 준비해 특정 패턴에 과적합되는 것을 최대한 방지했습니다.

LangSmith 평가를 총 **11회 반복**하며 실패 케이스를 분석하고 프롬프트·라우팅·상태 처리 기준을 개선했습니다.  
최종적으로 전체 metric에서 목표 기준 **0.90**을 상회했습니다.

| Metric | AVG |
|--------|-----|
| `action_match` | **0.94** |
| `classification_match` | **0.98** |
| `extract_match` | **0.92** |
| `outcome_match` | **0.92** |
| `policy_queries_presence_match` | **0.93** |

### Metric 기준

- `action_match`: 예측한 예약/정책 처리 액션 집합이 golden actions와 정확히 일치하는지 평가
- `classification_match`: 메일 category와 urgency가 golden classification과 일치하는지 평가
- `extract_match`: 이름, 체크인, 체크아웃 등 핵심 예약 슬롯이 golden extract data와 일치하는지 평가
- `outcome_match`: 처리 성공 여부와 business error code가 golden expected outcome과 일치하는지 평가
- `policy_queries_presence_match`: 규정 RAG 검색이 필요한 메일에서 policy query 생성 여부가 golden 기준과 일치하는지 평가

- 데이터셋: `resources/mail_dataset.jsonl` (108 samples)
- 실행: `python -m app.evaluation.run_eval_pipeline`

### 기술 블로그

평가 목표 설정, 실패 케이스 분석, 11회 개선 과정은 작성 후 아래에 링크합니다.

- `[평가 개선 과정 — 추후 기입]`

---

## Quick Start

### 요구 사항

- Python 3.11+ 권장
- Node.js 20+ 권장
- OpenAI API Key, LangSmith API Key
- (실메일 데모 시) Gmail 계정 + 앱 비밀번호
- (규정 인덱싱 시) LlamaCloud API Key

### 환경 변수

루트 [`.env.example`](.env.example) · 프론트 [`frontend/.env.example`](frontend/.env.example) 를 복사해 `.env` 를 만듭니다.

```env
OPENAI_API_KEY=
EMBEDDING_PROVIDER=openai
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

LANGSMITH_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=hotel-ai
```

프론트엔드 API 주소:

```env
# frontend/.env
VITE_API_BASE=http://127.0.0.1:8000
```

로컬 BGE-M3 평가를 쓰려면 `EMBEDDING_PROVIDER=huggingface` 와 `pip install -r requirements-dev.txt` 가 필요합니다.  
실메일·LlamaCloud 키는 로컬 전용이며 공개 데모 범위 밖입니다.

### 설치 · 실행

```bash
# 백엔드
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

# (최초 1회) 예약 mock DB
python -m app.database.mock_db

# 정책 Chroma는 최초 RAG 조회 시 docx에서 자동 부트스트랩됩니다.
# (선택) LlamaCloud 기반 재인덱싱: pip install -r requirements-dev.txt
# python -m app.rag.split_vector

uvicorn app.api.main:app --reload --port 8000
```

```bash
# 프론트엔드 (다른 터미널)
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 으로 관리자 승인 UI에 접속합니다.

### 평가 · 테스트

```bash
pip install -r requirements-dev.txt
EMBEDDING_PROVIDER=huggingface python -m app.evaluation.run_eval_pipeline
pytest
```

---

## Deploy (Vercel + Railway)

포트폴리오 데모: **프론트=Vercel**, **백엔드=Railway**. Mock/직접 입력만 공개하며, 실제 Gmail 발송과 영구 승인 상태 저장은 포함하지 않습니다.

### Railway (백엔드)

1. GitHub 저장소 연결 후 **Root Directory = 저장소 루트**
2. 시작 명령은 [`railway.json`](railway.json) 에 정의됨 (`uvicorn ... --port $PORT`)
3. Variables 예시:

```env
OPENAI_API_KEY=...
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
FRONTEND_ORIGINS=http://localhost:5173,https://YOUR-FRONTEND.vercel.app
LANGSMITH_API_KEY=...          # 선택
LANGCHAIN_TRACING_V2=true      # 선택
LANGCHAIN_PROJECT=hotel-ai     # 선택
```

4. Public Domain 생성 후 `https://YOUR-BACKEND.up.railway.app/health` 확인
5. Vercel URL이 나온 뒤 `FRONTEND_ORIGINS` 를 갱신하고 재배포

### Vercel (프론트)

1. 같은 GitHub 저장소 Import
2. **Root Directory = `frontend`**
3. Framework: Vite · Build: `npm run build` · Output: `dist`
4. Environment Variable:

```env
VITE_API_BASE=https://YOUR-BACKEND.up.railway.app
```

5. 배포 후 Railway `FRONTEND_ORIGINS` 에 Vercel URL 추가

### 배포 한계 (데모)

- LangGraph 체크포인트·`_runs` 는 **프로세스 메모리**입니다. Railway 재시작 시 `thread_id` 는 사라집니다. 현재 UI는 실행 결과 조회만 하므로 시연에는 충분합니다.
- Chroma 인덱스는 디스크에 캐시되며, 재배포 시 비어 있으면 규정 docx에서 다시 생성됩니다.
- `/inbox-emails`, `/runs/from-email`, 승인 submit·실발송은 공개 데모 UI에서 사용하지 않습니다.

---

## Limitations

- **예약 DB 실쓰기(`action_node`)는 의도적으로 미구현**입니다. 실행 시마다 DB 상태가 바뀌면 평가·시연 재현이 어려워지기 때문입니다. 생성된 SQL을 실행하는 단계는 상대적으로 단순하며, 필요 시 바로 연결할 수 있습니다.
- 데모/면접에서는 생성된 `action_sqlite`를 **참고용 SQL**로 답변 메일에 포함해, 에이전트의 예약 처리 의도를 보여 줍니다.
- 프로덕션급 인증·권한·멀티테넌시·대규모 동시성은 범위 밖입니다.

---

## Author

LeeJaeBin · [GitHub](https://github.com/jb2002a)
