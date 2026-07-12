import { useCallback, useEffect, useState } from "react";
import { fetchInboxEmails, startRunFromEmail, submitApproval } from "./api";
import type {
  ApprovalPayload,
  EmailData,
  ExtractData,
  InboxEmailSummary,
  ManagerClassification,
  StartRunResponse,
} from "./types";
import "./App.css";

type View = "list" | "review" | "result";

const emptySql = () => ({ create_sql: "", update_sql: "", delete_sql: "" });
const emptyEmailData = (): EmailData => ({
  email_subject: "",
  email_content: "",
  sender_email: "",
});
const emptyClassification = (): ManagerClassification => ({
  category: null,
  urgency: null,
  actions: [],
});
const emptyExtractData = (): ExtractData => ({
  name: null,
  check_in: null,
  check_out: null,
});
const nullable = (value: string) => {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};
const parseActions = (value: string) =>
  value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);

function App() {
  const [view, setView] = useState<View>("list");
  const [emails, setEmails] = useState<InboxEmailSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<StartRunResponse | null>(null);
  const [finalResult, setFinalResult] = useState<Record<string, unknown> | null>(null);

  const [emailData, setEmailData] = useState<EmailData>(emptyEmailData);
  const [classification, setClassification] =
    useState<ManagerClassification>(emptyClassification);
  const [actionsText, setActionsText] = useState("");
  const [extractData, setExtractData] = useState<ExtractData>(emptyExtractData);
  const [draftResponse, setDraftResponse] = useState("");
  const [actionSqlite, setActionSqlite] = useState(emptySql);
  const [managerComment, setManagerComment] = useState("");

  const loadEmails = useCallback(async () => {
    setError(null);
    try {
      const data = await fetchInboxEmails();
      setEmails(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "목록 로드 실패");
    }
  }, []);

  useEffect(() => {
    void loadEmails();
  }, [loadEmails]);

  const hydrateEditors = (payload: ApprovalPayload) => {
    setEmailData(payload.email_data);
    setClassification(payload.classification);
    setActionsText(payload.classification.actions.join("\n"));
    setExtractData(payload.extract_data ?? emptyExtractData());
    setDraftResponse(payload.draft_response ?? "");
    setActionSqlite({
      create_sql: payload.action_sqlite?.create_sql ?? "",
      update_sql: payload.action_sqlite?.update_sql ?? "",
      delete_sql: payload.action_sqlite?.delete_sql ?? "",
    });
    setManagerComment("");
  };

  const handleRun = async (uid: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await startRunFromEmail(uid);
      setRun(response);
      hydrateEditors(response.approval_payload);
      setView("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "파이프라인 실행 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!run) return;
    setLoading(true);
    setError(null);
    try {
      const response = await submitApproval(run.thread_id, {
        email_data: emailData,
        classification: {
          ...classification,
          actions: parseActions(actionsText),
        },
        extract_data: {
          name: nullable(extractData.name ?? ""),
          check_in: nullable(extractData.check_in ?? ""),
          check_out: nullable(extractData.check_out ?? ""),
        },
        draft_response: draftResponse,
        action_sqlite: actionSqlite,
        manager_comment: managerComment,
      });
      setFinalResult(response.result);
      setView("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleBackToList = () => {
    setRun(null);
    setFinalResult(null);
    setView("list");
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <span className="eyebrow">Human-in-the-loop Demo</span>
          <h1>Hotel AI Manager Approval</h1>
          <p>실제 Gmail 수신 메일([hotel]) → LLM 파이프라인 → 승인 검토 → 답변 메일 발송</p>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {view === "list" && (
        <section className="panel">
          <div className="panel-header">
            <h2>실제 수신 메일 ([hotel])</h2>
            <button type="button" onClick={() => void loadEmails()} disabled={loading}>
              새로고침
            </button>
          </div>
          <ul className="email-list">
            {emails.map((email) => (
              <li key={email.uid} className="email-card">
                <div className="email-meta">
                  <span className="email-id">uid: {email.uid}</span>
                  <strong>{email.subject}</strong>
                  <span>{email.sender_email}</span>
                </div>
                <p className="preview">{email.preview}</p>
                <button
                  type="button"
                  className="primary"
                  disabled={loading}
                  onClick={() => void handleRun(email.uid)}
                >
                  파이프라인 실행
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {view === "review" && run && (
        <section className="panel">
          <div className="review-hero">
            <div>
              <span className="eyebrow">Waiting Approval</span>
              <h2>승인 검토 및 수정</h2>
              <p>LLM이 만든 승인 패킷을 항목별로 확인하고 필요한 값을 바로 수정하세요.</p>
            </div>
            <span className="thread-id">thread_id: {run.thread_id}</span>
          </div>

          {run.approval_payload.errors.length > 0 && (
            <div className="alert-card">
              <h3>검토 필요 알림</h3>
              <ul className="error-list">
                {run.approval_payload.errors.map((e) => (
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
                <h3>이메일 정보</h3>
              </div>
              <label className="field">
                <span>제목</span>
                <input
                  value={emailData.email_subject}
                  onChange={(e) =>
                    setEmailData((prev) => ({ ...prev, email_subject: e.target.value }))
                  }
                />
              </label>
              <label className="field">
                <span>발신자</span>
                <input
                  value={emailData.sender_email}
                  onChange={(e) =>
                    setEmailData((prev) => ({ ...prev, sender_email: e.target.value }))
                  }
                />
              </label>
              <label className="field">
                <span>본문</span>
                <textarea
                  rows={8}
                  value={emailData.email_content}
                  onChange={(e) =>
                    setEmailData((prev) => ({ ...prev, email_content: e.target.value }))
                  }
                />
              </label>
            </section>

            <section className="card">
              <div className="card-title">
                <span>02</span>
                <h3>분류 결과</h3>
              </div>
              <div className="inline-fields">
                <label className="field">
                  <span>category</span>
                  <select
                    value={classification.category ?? ""}
                    onChange={(e) =>
                      setClassification((prev) => ({
                        ...prev,
                        category: e.target.value || null,
                      }))
                    }
                  >
                    <option value="">미지정</option>
                    <option value="normal">normal</option>
                    <option value="spam">spam</option>
                  </select>
                </label>
                <label className="field">
                  <span>urgency</span>
                  <select
                    value={classification.urgency ?? ""}
                    onChange={(e) =>
                      setClassification((prev) => ({
                        ...prev,
                        urgency: e.target.value || null,
                      }))
                    }
                  >
                    <option value="">미지정</option>
                    <option value="normal">normal</option>
                    <option value="high">high</option>
                  </select>
                </label>
              </div>
              <label className="field">
                <span>actions (줄바꿈 또는 콤마로 구분)</span>
                <textarea
                  rows={5}
                  value={actionsText}
                  onChange={(e) => setActionsText(e.target.value)}
                  placeholder="reservation_create"
                />
              </label>
            </section>

            <section className="card">
              <div className="card-title">
                <span>03</span>
                <h3>추출값</h3>
              </div>
              <div className="inline-fields">
                <label className="field">
                  <span>name</span>
                  <input
                    value={extractData.name ?? ""}
                    onChange={(e) =>
                      setExtractData((prev) => ({ ...prev, name: e.target.value }))
                    }
                    placeholder="null"
                  />
                </label>
                <label className="field">
                  <span>check_in</span>
                  <input
                    value={extractData.check_in ?? ""}
                    onChange={(e) =>
                      setExtractData((prev) => ({ ...prev, check_in: e.target.value }))
                    }
                    placeholder="YYYY-MM-DD"
                  />
                </label>
                <label className="field">
                  <span>check_out</span>
                  <input
                    value={extractData.check_out ?? ""}
                    onChange={(e) =>
                      setExtractData((prev) => ({ ...prev, check_out: e.target.value }))
                    }
                    placeholder="YYYY-MM-DD"
                  />
                </label>
              </div>
            </section>
          </div>

          <section className="card full-card">
            <div className="card-title">
              <span>04</span>
              <h3>고객 응답 초안</h3>
            </div>
            <label className="field">
              <span>draft_response</span>
              <textarea
                rows={11}
                value={draftResponse}
                onChange={(e) => setDraftResponse(e.target.value)}
              />
            </label>
          </section>

          <section className="card full-card">
            <div className="card-title">
              <span>05</span>
              <h3>예약 액션 SQL</h3>
            </div>
            <div className="sql-grid">
              {(["create_sql", "update_sql", "delete_sql"] as const).map((key) => (
                <label key={key} className="field">
                  <span>{key}</span>
                  <textarea
                    rows={6}
                    value={actionSqlite[key]}
                    onChange={(e) =>
                      setActionSqlite((prev) => ({ ...prev, [key]: e.target.value }))
                    }
                  />
                </label>
              ))}
            </div>
          </section>

          <section className="card full-card">
            <div className="card-title">
              <span>06</span>
              <h3>매니저 코멘트</h3>
            </div>
            <label className="field">
              <span>manager_comment</span>
              <input
                type="text"
                value={managerComment}
                onChange={(e) => setManagerComment(e.target.value)}
                placeholder="수정/승인 사유를 남겨주세요."
              />
            </label>
          </section>

          <div className="actions">
            <button type="button" onClick={handleBackToList} disabled={loading}>
              목록으로
            </button>
            <button type="button" className="primary" disabled={loading} onClick={() => void handleSubmit()}>
              Submit (Resume)
            </button>
          </div>
        </section>
      )}

      {view === "result" && finalResult && (
        <section className="panel">
          <div className="panel-header">
            <h2>검토 반영 완료</h2>
          </div>
          <p className="success">승인 내용이 반영되었고, 답변 메일 발송까지 완료되었습니다.</p>
          <pre className="readonly">{JSON.stringify(finalResult, null, 2)}</pre>
          <div className="actions">
            <button type="button" className="primary" onClick={handleBackToList}>
              새 요청 시작
            </button>
          </div>
        </section>
      )}
    </div>
  );
}

export default App;
