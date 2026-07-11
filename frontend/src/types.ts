export interface MockEmailSummary {
  id: string;
  subject: string;
  sender_email: string;
  preview: string;
}

export interface EmailData {
  email_subject: string;
  email_content: string;
  sender_email: string;
}

export interface ManagerClassification {
  category: string | null;
  urgency: string | null;
  actions: string[];
}

export interface ExtractData {
  name: string | null;
  check_in: string | null;
  check_out: string | null;
}

export interface ActionSQLite {
  create_sql: string;
  update_sql: string;
  delete_sql: string;
}

export interface ManagerError {
  type: string;
  code: string;
  message: string;
}

export interface ApprovalPayload {
  email_data: EmailData;
  classification: ManagerClassification;
  extract_data: ExtractData | null;
  draft_response: string | null;
  action_sqlite: ActionSQLite | null;
  errors: ManagerError[];
}

export interface StartRunResponse {
  thread_id: string;
  status: string;
  approval_payload: ApprovalPayload;
  result: Record<string, unknown> | null;
}

export interface SubmitResponse {
  thread_id: string;
  status: string;
  result: Record<string, unknown>;
}
