import json
import uuid
import tkinter as tk
from tkinter import messagebox, scrolledtext

from langgraph.types import Command

try:
    from langgraph.checkpoint.memory import InMemorySaver as _MemorySaver
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver as _MemorySaver

from app.config.config import USER_MOCK_DATA_PATH
from app.graphs.graphs import graph


class ApprovalUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Hotel AI Manager Approval")
        self.root.geometry("1200x900")

        self.thread_id = str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.compiled_graph = graph.compile(checkpointer=_MemorySaver())

        self.last_packet: dict | None = None
        self._mock_email_max_idx = self._load_mock_email_max_idx()
        self._build_widgets()

    def _load_mock_email_max_idx(self) -> int:
        try:
            with open(USER_MOCK_DATA_PATH, "r", encoding="utf-8") as f:
                data = [json.loads(line) for line in f if line.strip()]
            return max(0, len(data) - 1)
        except (OSError, json.JSONDecodeError, TypeError):
            return 0

    def _build_widgets(self) -> None:
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=12, pady=8)

        self.thread_label = tk.Label(top_frame, text=f"thread_id: {self.thread_id}")
        self.thread_label.pack(side="left")

        mock_frame = tk.Frame(top_frame)
        mock_frame.pack(side="left", padx=(16, 0))
        tk.Label(mock_frame, text="mock 이메일 인덱스:").pack(side="left")
        default_idx = "1" if self._mock_email_max_idx >= 1 else "0"
        self.mock_email_spin = tk.Spinbox(
            mock_frame,
            from_=0,
            to=self._mock_email_max_idx,
            width=5,
            justify="center",
        )
        self.mock_email_spin.delete(0, tk.END)
        self.mock_email_spin.insert(0, default_idx)
        self.mock_email_spin.pack(side="left", padx=(4, 0))

        start_button = tk.Button(
            top_frame,
            text="새 요청 실행",
            command=self.start_request,
            bg="#2d6cdf",
            fg="white",
        )
        start_button.pack(side="right", padx=4)

        resume_button = tk.Button(
            top_frame,
            text="수정 후 Resume(종료)",
            command=self.resume_with_edits,
            bg="#1f8b4c",
            fg="white",
        )
        resume_button.pack(side="right", padx=4)

        plan_frame = tk.Frame(self.root)
        plan_frame.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(
            plan_frame,
            text="플랜 액션 (state.plan.actions)",
            anchor="w",
        ).pack(anchor="w")
        self.plan_actions_text = scrolledtext.ScrolledText(
            plan_frame, height=3, wrap=tk.WORD, state=tk.DISABLED
        )
        self.plan_actions_text.pack(fill="x")

        packet_label = tk.Label(self.root, text="승인 패킷(JSON, 읽기 전용)")
        packet_label.pack(anchor="w", padx=12)
        self.packet_text = scrolledtext.ScrolledText(self.root, height=16, wrap=tk.WORD)
        self.packet_text.pack(fill="both", expand=False, padx=12, pady=(0, 8))

        edit_frame = tk.Frame(self.root)
        edit_frame.pack(fill="both", expand=True, padx=12, pady=8)

        tk.Label(edit_frame, text="Draft Response (수정 가능)").pack(anchor="w")
        self.draft_text = scrolledtext.ScrolledText(edit_frame, height=10, wrap=tk.WORD)
        self.draft_text.pack(fill="both", expand=False, pady=(0, 8))

        sql_frame = tk.Frame(edit_frame)
        sql_frame.pack(fill="both", expand=True)

        self.create_sql_text = self._build_sql_editor(sql_frame, "create_sql")
        self.update_sql_text = self._build_sql_editor(sql_frame, "update_sql")
        self.delete_sql_text = self._build_sql_editor(sql_frame, "delete_sql")

        comment_frame = tk.Frame(self.root)
        comment_frame.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(comment_frame, text="manager_comment").pack(anchor="w")
        self.manager_comment_entry = tk.Entry(comment_frame)
        self.manager_comment_entry.pack(fill="x")

        result_label = tk.Label(self.root, text="그래프 실행 결과")
        result_label.pack(anchor="w", padx=12)
        self.result_text = scrolledtext.ScrolledText(self.root, height=8, wrap=tk.WORD)
        self.result_text.pack(fill="both", expand=False, padx=12, pady=(0, 12))

    def _build_sql_editor(self, parent: tk.Frame, title: str) -> scrolledtext.ScrolledText:
        frame = tk.LabelFrame(parent, text=title)
        frame.pack(fill="both", expand=True, pady=4)
        text_widget = scrolledtext.ScrolledText(frame, height=6, wrap=tk.WORD)
        text_widget.pack(fill="both", expand=True, padx=4, pady=4)
        return text_widget

    def _set_text(self, widget: scrolledtext.ScrolledText, value: str) -> None:
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)

    def _set_plan_actions_text(self, value: str) -> None:
        self.plan_actions_text.configure(state=tk.NORMAL)
        self.plan_actions_text.delete("1.0", tk.END)
        self.plan_actions_text.insert("1.0", value)
        self.plan_actions_text.configure(state=tk.DISABLED)

    def _format_plan_for_ui(self, plan: dict | None) -> str:
        if not plan:
            return "(plan 없음)"
        actions = plan.get("actions")
        if not actions:
            return "(액션 목록 비어 있음)"
        return "\n".join(f"- {a}" for a in actions)

    def _extract_interrupt_payload(self, result: dict) -> dict | None:
        interrupts = result.get("__interrupt__")
        if not interrupts:
            return None

        first_interrupt = interrupts[0]
        payload_wrapper = getattr(first_interrupt, "value", first_interrupt)
        if isinstance(payload_wrapper, dict):
            payload = payload_wrapper.get("payload")
            if isinstance(payload, dict):
                return payload
        return None

    def _default_initial_state(self) -> dict:
        return {
            "email_data": {
                "email_subject": "",
                "email_content": "",
                "sender_email": "",
            },
            "extract_data": None,
            "classification": None,
            "plan": None,
            "vector_retrieve_results": None,
            "db_retrieve_results": None,
            "rest_room_retrieve_results": None,
            "action_sqlite": None,
            "draft_response": None,
            "approval_packet": None,
            "manager_comment": None,
            "business_error": None,
            "mock_email_idx": self._read_mock_email_idx(),
        }

    def _read_mock_email_idx(self) -> int:
        raw = self.mock_email_spin.get().strip()
        try:
            return int(raw)
        except ValueError:
            return 1

    def start_request(self) -> None:
        self.thread_id = str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.thread_label.config(text=f"thread_id: {self.thread_id}")

        try:
            result = self.compiled_graph.invoke(self._default_initial_state(), config=self.config)
        except Exception as exc:
            messagebox.showerror("실행 실패", str(exc))
            return

        self._render_result(result)

    def _render_result(self, result: dict) -> None:
        self._set_text(
            self.result_text, json.dumps(result, ensure_ascii=False, indent=2, default=str)
        )

        packet = self._extract_interrupt_payload(result)
        plan = None
        if isinstance(packet, dict):
            plan = packet.get("plan")
        if plan is None and isinstance(result, dict):
            plan = result.get("plan")
        self._set_plan_actions_text(self._format_plan_for_ui(plan))

        if packet is None:
            self.last_packet = None
            self._set_text(self.packet_text, "(interrupt 없음)")
            return

        self.last_packet = packet
        self._set_text(self.packet_text, json.dumps(packet, ensure_ascii=False, indent=2, default=str))
        self._hydrate_editors(packet)

    def _hydrate_editors(self, packet: dict) -> None:
        self._set_text(self.draft_text, str(packet.get("draft_response") or ""))
        action_sqlite = packet.get("action_sqlite") or {}
        self._set_text(self.create_sql_text, str(action_sqlite.get("create_sql") or ""))
        self._set_text(self.update_sql_text, str(action_sqlite.get("update_sql") or ""))
        self._set_text(self.delete_sql_text, str(action_sqlite.get("delete_sql") or ""))

    def resume_with_edits(self) -> None:
        if self.last_packet is None:
            messagebox.showwarning("알림", "먼저 '새 요청 실행'으로 interrupt 패킷을 받아주세요.")
            return

        resume_payload = {
            "draft_response": self.draft_text.get("1.0", tk.END).strip(),
            "action_sqlite": {
                "create_sql": self.create_sql_text.get("1.0", tk.END).strip(),
                "update_sql": self.update_sql_text.get("1.0", tk.END).strip(),
                "delete_sql": self.delete_sql_text.get("1.0", tk.END).strip(),
            },
            "manager_comment": self.manager_comment_entry.get().strip(),
        }

        try:
            result = self.compiled_graph.invoke(Command(resume=resume_payload), config=self.config)
        except Exception as exc:
            messagebox.showerror("Resume 실패", str(exc))
            return

        self._render_result(result)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    # python -m app.ui.approval_ui
    ApprovalUI().run()
