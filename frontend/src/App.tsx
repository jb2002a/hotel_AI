import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchMockEmails, startRunFromCustom, startRunFromSample } from "./api";
import type {
  ApprovalPayload,
  CustomEmailInput,
  MockEmailSummary,
  StartRunResponse,
} from "./types";
import "./App.css";

type InputMode = "samples" | "custom";

const CURATED_SAMPLE_IDS = [
  "sample_001",
  "sample_002",
  "sample_003",
  "sample_006",
  "sample_007",
  "sample_016",
  "sample_020",
  "sample_031",
] as const;

const emptyCustomInput = (): CustomEmailInput => ({
  subject: "",
  body: "",
  sender_email: "interviewer@example.com",
});

function App() {
  const [mode, setMode] = useState<InputMode>("samples");
  const [emails, setEmails] = useState<MockEmailSummary[]>([]);
  const [customInput, setCustomInput] = useState<CustomEmailInput>(emptyCustomInput);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);
  const [run, setRun] = useState<StartRunResponse | null>(null);

  const loadEmails = useCallback(async () => {
    setListError(null);
    try {
      const data = await fetchMockEmails();
      const curated = new Set<string>(CURATED_SAMPLE_IDS);
      setEmails(data.filter((email) => curated.has(email.id)));
    } catch (err) {
      setListError(err instanceof Error ? err.message : "샘플 목록 로드 실패");
    }
  }, []);

  useEffect(() => {
    void loadEmails();
  }, [loadEmails]);

  useEffect(() => {
    if (!drawerOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !loading) {
        setDrawerOpen(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [drawerOpen, loading]);

  const payload: ApprovalPayload | null = useMemo(
    () => run?.approval_payload ?? null,
    [run],
  );

  const beginRun = () => {
    setDrawerError(null);
    setRun(null);
    setLoading(true);
  };

  const handleSampleRun = async (emailId: string) => {
    beginRun();
    try {
      const response = await startRunFromSample(emailId);
      setRun(response);
      setDrawerOpen(true);
    } catch (err) {
      setDrawerError(err instanceof Error ? err.message : "파이프라인 실행 실패");
      setDrawerOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomRun = async () => {
    const subject = customInput.subject.trim();
    const body = customInput.body.trim();
    const senderEmail = customInput.sender_email.trim();
    if (!subject || !body || !senderEmail) {
      setListError("제목, 본문, 발신자 이메일을 모두 입력해 주세요.");
      return;
    }

    beginRun();
    try {
      const response = await startRunFromCustom({
        subject,
        body,
        sender_email: senderEmail,
      });
      setRun(response);
      setDrawerOpen(true);
    } catch (err) {
      setDrawerError(err instanceof Error ? err.message : "파이프라인 실행 실패");
      setDrawerOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const handleCloseDrawer = () => {
    if (loading) {
      return;
    }
    setDrawerOpen(false);
  };

  const handleClearAndClose = () => {
    if (loading) {
      return;
    }
    setRun(null);
    setDrawerError(null);
    setDrawerOpen(false);
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <span className="eyebrow">Hotel AI</span>
          <h1>고객 메일 처리 데모</h1>
          <p>
            샘플 메일 또는 직접 작성한 메일을 실행하고, 분류·추출·SQL·답변 초안을
            확인합니다. 실제 메일은 발송하지 않습니다.
          </p>
        </div>
      </header>

      {listError && <div className="error-banner">{listError}</div>}

      <section className="panel">
        <div className="panel-header">
          <h2>메일 입력</h2>
          <div className="mode-tabs">
            <button
              type="button"
              className={mode === "samples" ? "primary" : undefined}
              disabled={loading}
              onClick={() => setMode("samples")}
            >
              대표 샘플
            </button>
            <button
              type="button"
              className={mode === "custom" ? "primary" : undefined}
              disabled={loading}
              onClick={() => setMode("custom")}
            >
              직접 작성
            </button>
          </div>
        </div>

        {mode === "samples" && (
          <>
            <div className="panel-subheader">
              <p>시연용 대표 시나리오 {emails.length}건</p>
              <button type="button" onClick={() => void loadEmails()} disabled={loading}>
                새로고침
              </button>
            </div>
            <ul className="email-list">
              {emails.map((email) => (
                <li key={email.id} className="email-card">
                  <div className="email-meta">
                    <span className="email-id">{email.id}</span>
                    <strong>{email.subject}</strong>
                    <span>{email.sender_email}</span>
                  </div>
                  <p className="preview">{email.preview}</p>
                  <button
                    type="button"
                    className="primary"
                    disabled={loading}
                    onClick={() => void handleSampleRun(email.id)}
                  >
                    {loading ? "실행 중..." : "파이프라인 실행"}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        {mode === "custom" && (
          <section className="card full-card">
            <div className="card-title">
              <span>입력</span>
              <h3>메일 작성</h3>
            </div>
            <label className="field">
              <span>제목</span>
              <input
                value={customInput.subject}
                onChange={(e) =>
                  setCustomInput((prev) => ({ ...prev, subject: e.target.value }))
                }
                placeholder="예: 체크인 일정 변경 문의"
                disabled={loading}
              />
            </label>
            <label className="field">
              <span>발신자 이메일</span>
              <input
                value={customInput.sender_email}
                onChange={(e) =>
                  setCustomInput((prev) => ({ ...prev, sender_email: e.target.value }))
                }
                placeholder="interviewer@example.com"
                disabled={loading}
              />
            </label>
            <label className="field">
              <span>본문</span>
              <textarea
                rows={10}
                value={customInput.body}
                onChange={(e) =>
                  setCustomInput((prev) => ({ ...prev, body: e.target.value }))
                }
                placeholder="예약 생성/변경/취소/조회 또는 규정 문의 내용을 작성해 주세요."
                disabled={loading}
              />
            </label>
            <div className="actions">
              <button
                type="button"
                className="primary"
                disabled={loading}
                onClick={() => void handleCustomRun()}
              >
                {loading ? "실행 중..." : "API 실행"}
              </button>
            </div>
          </section>
        )}
      </section>

      {drawerOpen && (
        <>
          <button
            type="button"
            className="drawer-backdrop"
            aria-label="결과 패널 닫기"
            onClick={handleCloseDrawer}
            disabled={loading}
          />
          <aside
            className="drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="drawer-title"
          >
            <div className="drawer-header">
              <div>
                <span className="eyebrow">실행 결과</span>
                <h2 id="drawer-title">파이프라인 응답</h2>
              </div>
              <button
                type="button"
                className="drawer-close"
                onClick={handleCloseDrawer}
                disabled={loading}
                aria-label="닫기"
              >
                닫기
              </button>
            </div>

            <div className="drawer-body">
              {drawerError && (
                <div className="drawer-error">
                  <div className="alert-card">
                    <h3>실행 실패</h3>
                    <p>{drawerError}</p>
                  </div>
                  <p className="drawer-hint">닫은 뒤 다시 시도해 주세요.</p>
                  <div className="actions">
                    <button type="button" className="primary" onClick={handleClearAndClose}>
                      닫기
                    </button>
                  </div>
                </div>
              )}

              {!drawerError && run && payload && (
                <>
                  <div className="review-hero">
                    <div>
                      <p>
                        승인 중단 시점의 분류·추출·SQL·답변 초안입니다. 실제 메일은
                        발송되지 않습니다.
                      </p>
                    </div>
                    <span className="thread-id">
                      {run.status} · {run.thread_id}
                    </span>
                  </div>

                  {payload.errors.length > 0 && (
                    <div className="alert-card">
                      <h3>검토 필요 알림</h3>
                      <ul className="error-list">
                        {payload.errors.map((e) => (
                          <li key={`${e.type}-${e.code}`}>
                            <strong>[{e.code}]</strong> {e.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="review-layout">
                    <section className="card">
                      <div className="card-title">
                        <span>01</span>
                        <h3>입력 메일</h3>
                      </div>
                      <div className="readonly-block">
                        <strong>{payload.email_data.email_subject}</strong>
                        <span>{payload.email_data.sender_email}</span>
                        <p>{payload.email_data.email_content}</p>
                      </div>
                    </section>

                    <section className="card">
                      <div className="card-title">
                        <span>02</span>
                        <h3>분류 결과</h3>
                      </div>
                      <dl className="kv-list">
                        <div>
                          <dt>category</dt>
                          <dd>{payload.classification.category ?? "null"}</dd>
                        </div>
                        <div>
                          <dt>urgency</dt>
                          <dd>{payload.classification.urgency ?? "null"}</dd>
                        </div>
                        <div>
                          <dt>actions</dt>
                          <dd>
                            {payload.classification.actions.length > 0
                              ? payload.classification.actions.join(", ")
                              : "없음"}
                          </dd>
                        </div>
                      </dl>
                    </section>

                    <section className="card">
                      <div className="card-title">
                        <span>03</span>
                        <h3>추출값</h3>
                      </div>
                      <dl className="kv-list">
                        <div>
                          <dt>name</dt>
                          <dd>{payload.extract_data?.name ?? "null"}</dd>
                        </div>
                        <div>
                          <dt>check_in</dt>
                          <dd>{payload.extract_data?.check_in ?? "null"}</dd>
                        </div>
                        <div>
                          <dt>check_out</dt>
                          <dd>{payload.extract_data?.check_out ?? "null"}</dd>
                        </div>
                      </dl>
                    </section>
                  </div>

                  <section className="card full-card draft-card">
                    <div className="card-title">
                      <span>04</span>
                      <h3>고객 응답 초안</h3>
                    </div>
                    <pre className="readonly draft-readonly">
                      {payload.draft_response || "(초안 없음)"}
                    </pre>
                  </section>

                  <section className="card full-card">
                    <div className="card-title">
                      <span>05</span>
                      <h3>예약 액션 SQL</h3>
                    </div>
                    <div className="sql-grid">
                      {(["create_sql", "update_sql", "delete_sql"] as const).map((key) => (
                        <div key={key} className="field">
                          <span>{key}</span>
                          <pre className="readonly">
                            {payload.action_sqlite?.[key]?.trim() || "(없음)"}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </section>

                  <div className="actions">
                    <button type="button" className="primary" onClick={handleClearAndClose}>
                      닫기
                    </button>
                  </div>
                </>
              )}
            </div>
          </aside>
        </>
      )}
    </div>
  );
}

export default App;
