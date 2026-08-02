// Thin fetch wrapper for the CB Nest backend.
// Keeps the JWT in localStorage and attaches it to every request.

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("cb_nest_token");
}

export function setToken(token: string) {
  window.localStorage.setItem("cb_nest_token", token);
}

export function clearToken() {
  window.localStorage.removeItem("cb_nest_token");
  window.localStorage.removeItem("cb_nest_role");
}

export function getRole(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("cb_nest_role");
}

export function setRole(role: string) {
  window.localStorage.setItem("cb_nest_role", role);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Request failed (${res.status})`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: "EMPLOYEE" | "MANAGER" | "ADMIN";
}

export function login(email: string, password: string) {
  return request<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export interface ChatEnvelope<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}

export interface PolicySource {
  title: string;
  category: string;
  filename: string | null;
}

export interface PolicyChatData {
  answer: string;
  sources: PolicySource[];
}

export function askPolicy(message: string) {
  return request<ChatEnvelope<PolicyChatData>>("/api/v1/chat/policy", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export interface SQLChatData {
  answer: string;
  sql: string | null;
  rows: Record<string, unknown>[];
}

export function askSql(message: string) {
  return request<ChatEnvelope<SQLChatData>>("/api/v1/chat/sql", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export interface ActionChatData {
  answer: string;
  intent: string | null;
  status: "SUCCESS" | "DENIED" | "ERROR" | "NEEDS_CONFIRMATION";
  needs_confirmation: boolean;
  pending_action: Record<string, unknown> | null;
}

export function askAction(message: string, confirm = false, pendingAction: Record<string, unknown> | null = null) {
  return request<ChatEnvelope<ActionChatData>>("/api/v1/chat/actions", {
    method: "POST",
    body: JSON.stringify({ message, confirm, pending_action: pendingAction }),
  });
}

export interface RouterChatData {
  intent: string;
  confidence: number;
  reason: string;
}

export function askRouter(message: string) {
  return request<ChatEnvelope<RouterChatData>>("/api/v1/chat/router", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export interface AIAuditLogRow {
  id: number;
  message: string;
  intent: string | null;
  tool_name: string | null;
  action_status: string | null;
  created_at: string;
}

export function getRecentAiActions(limit = 10) {
  return request<ChatEnvelope<{ logs: AIAuditLogRow[] }>>(`/api/v1/chat/audit/recent?limit=${limit}`);
}

export interface AIUsageStats {
  total_requests: number;
  requests_by_intent: Record<string, number>;
  requests_by_tool: Record<string, number>;
  failed_permission_attempts: number;
  avg_latency_ms: number | null;
  rag_no_answer_count: number;
  rag_no_answer_rate_pct: number | null;
  sql_blocked_count: number;
}

export function getAiUsageStats() {
  return request<ChatEnvelope<AIUsageStats>>("/api/v1/chat/audit/usage");
}

export interface EmployeeDirectoryRow {
  id: number;
  name: string;
  job_title: string | null;
  role: string;
  department: string | null;
}

export function listEmployees() {
  return request<EmployeeDirectoryRow[]>("/api/v1/employees");
}

export interface DepartmentRow {
  id: number;
  name: string;
}

export function listDepartments() {
  return request<DepartmentRow[]>("/api/v1/employees/departments");
}

export interface EmployeeCreatePayload {
  name: string;
  email: string;
  password: string;
  role: string;
  department_id?: number | null;
  manager_id?: number | null;
  job_title?: string | null;
}

export function createEmployee(payload: EmployeeCreatePayload) {
  return request<EmployeeDirectoryRow>("/api/v1/employees", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface MyProjectRow {
  id: number;
  name: string;
  status: string;
}

export function getMyProjects() {
  return request<MyProjectRow[]>("/api/v1/employees/me/projects");
}

export interface AnnouncementRow {
  id: number;
  title: string;
  body: string;
  created_by_name: string;
  created_at: string;
}

export function listAnnouncements() {
  return request<AnnouncementRow[]>("/api/v1/announcements");
}

export interface PolicyRow {
  id: number;
  title: string;
  category: string;
  filename: string | null;
  content: string;
}

export function listPolicies() {
  return request<PolicyRow[]>("/api/v1/policies");
}

export interface TicketRow {
  id: number;
  title: string;
  category: string;
  priority: string;
  status: string;
  sla_due_at: string | null;
  is_breached: boolean;
  created_at: string;
}

export function listMyTickets() {
  return request<TicketRow[]>("/api/v1/tickets/mine");
}

export interface TicketDetail {
  id: number;
  title: string;
  description: string | null;
  category: string;
  status: string;
  priority: string;
  created_by: number;
  created_by_name: string;
  assigned_to: number | null;
  assigned_to_name: string | null;
  sla_due_at: string | null;
  is_breached: boolean;
  created_at: string;
}

export function listAllTickets(filters?: { category?: string; status?: string; breachedOnly?: boolean }) {
  const params = new URLSearchParams();
  if (filters?.category) params.set("category", filters.category);
  if (filters?.status) params.set("status", filters.status);
  if (filters?.breachedOnly) params.set("breached_only", "true");
  const qs = params.toString();
  return request<TicketDetail[]>(`/api/v1/tickets${qs ? `?${qs}` : ""}`);
}

export function getTicket(ticketId: number) {
  return request<TicketDetail>(`/api/v1/tickets/${ticketId}`);
}

export function createTicket(payload: { title: string; description?: string; category?: string; priority?: string }) {
  return request<TicketDetail>("/api/v1/tickets", { method: "POST", body: JSON.stringify(payload) });
}

export function updateTicket(ticketId: number, updates: Partial<{
  status: string; assigned_to: number; priority: string; category: string;
}>) {
  return request<TicketDetail>(`/api/v1/tickets/${ticketId}`, { method: "PATCH", body: JSON.stringify(updates) });
}

export interface TicketCommentRow {
  id: number;
  ticket_id: number;
  employee_id: number;
  employee_name: string;
  body: string;
  created_at: string;
}

export function listTicketComments(ticketId: number) {
  return request<TicketCommentRow[]>(`/api/v1/tickets/${ticketId}/comments`);
}

export function addTicketComment(ticketId: number, body: string) {
  return request<TicketCommentRow>(`/api/v1/tickets/${ticketId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export interface LeaveBalanceRow {
  leave_type: string;
  balance_days: number;
  year: number;
}

export function getLeaveBalance() {
  return request<LeaveBalanceRow[]>("/api/v1/leaves/balance");
}

export interface TodayAttendanceStatus {
  checked_in: boolean;
  checked_out: boolean;
  check_in_at: string | null;
  check_out_at: string | null;
  status: string | null;
}

export function getTodayAttendance() {
  return request<TodayAttendanceStatus>("/api/v1/attendance/today");
}

export function checkIn() {
  return request<unknown>("/api/v1/attendance/check-in", { method: "POST" });
}

export function checkOut() {
  return request<unknown>("/api/v1/attendance/check-out", { method: "POST" });
}

export interface AttendanceHistoryRow {
  id: number;
  work_date: string;
  check_in_at: string | null;
  check_out_at: string | null;
  status: string;
}

export function getMyAttendanceHistory() {
  return request<AttendanceHistoryRow[]>("/api/v1/attendance/me");
}

export interface TeamAttendanceRow {
  employee_id: number;
  employee_name: string;
  work_date: string;
  check_in_at: string | null;
  check_out_at: string | null;
  status: string;
}

export function getTeamAttendance(forDate?: string) {
  const qs = forDate ? `?for_date=${forDate}` : "";
  return request<TeamAttendanceRow[]>(`/api/v1/attendance/team${qs}`);
}

export interface HeadcountReport {
  total_active: number;
  total_inactive: number;
  by_department: { department: string; headcount: number }[];
  by_role: Record<string, number>;
}

export function getHeadcountReport() {
  return request<HeadcountReport>("/api/v1/reports/headcount");
}

export interface LeaveTrendsReport {
  by_type: { leave_type: string; approved: number; pending: number; rejected: number }[];
  total_requests_last_90_days: number;
}

export function getLeaveTrendsReport() {
  return request<LeaveTrendsReport>("/api/v1/reports/leave-trends");
}

export interface AttendanceTrendsReport {
  last_14_days: { work_date: string; present: number; late: number; absent: number }[];
  late_rate_pct: number;
}

export function getAttendanceTrendsReport() {
  return request<AttendanceTrendsReport>("/api/v1/reports/attendance-trends");
}

export interface TicketsReport {
  by_status: { status: string; count: number }[];
  by_priority: { priority: string; count: number }[];
  by_category: { category: string; count: number }[];
  total_open: number;
  total_breached: number;
}

export function getTicketsReport() {
  return request<TicketsReport>("/api/v1/reports/tickets");
}

export interface AssetWithHolder {
  id: number;
  asset_tag: string;
  category: string;
  name: string;
  serial_number: string | null;
  status: string;
  purchase_date: string | null;
  warranty_expiry: string | null;
  current_holder_name: string | null;
}

export function listAssets() {
  return request<AssetWithHolder[]>("/api/v1/assets");
}

export function getMyAssets() {
  return request<AssetWithHolder[]>("/api/v1/assets/me");
}

export function createAsset(payload: { asset_tag: string; category: string; name: string; serial_number?: string }) {
  return request<AssetWithHolder>("/api/v1/assets", { method: "POST", body: JSON.stringify(payload) });
}

export function issueAsset(assetId: number, employeeId: number, conditionOnIssue = "GOOD") {
  return request<AssetWithHolder>(`/api/v1/assets/${assetId}/issue`, {
    method: "POST",
    body: JSON.stringify({ employee_id: employeeId, condition_on_issue: conditionOnIssue }),
  });
}

export function returnAsset(assetId: number, conditionOnReturn = "GOOD") {
  return request<AssetWithHolder>(`/api/v1/assets/${assetId}/return`, {
    method: "POST",
    body: JSON.stringify({ condition_on_return: conditionOnReturn }),
  });
}

export interface ExitRequestRow {
  id: number;
  employee_id: number;
  employee_name: string;
  last_working_day: string;
  reason: string | null;
  status: string;
  decided_by: number | null;
  decided_at: string | null;
  knowledge_transfer_done: boolean;
  exit_interview_done: boolean;
  fnf_settled: boolean;
  assets_returned: boolean;
  completed_at: string | null;
  created_at: string;
}

export function submitResignation(lastWorkingDay: string, reason?: string) {
  return request<ExitRequestRow>("/api/v1/exits", {
    method: "POST",
    body: JSON.stringify({ last_working_day: lastWorkingDay, reason }),
  });
}

export function getMyExitRequests() {
  return request<ExitRequestRow[]>("/api/v1/exits/me");
}

export function listExitRequests() {
  return request<ExitRequestRow[]>("/api/v1/exits");
}

export function decideExitRequest(exitId: number, decision: "APPROVED" | "REJECTED") {
  return request<ExitRequestRow>(`/api/v1/exits/${exitId}/decision`, {
    method: "PATCH",
    body: JSON.stringify({ status: decision }),
  });
}

export function updateExitChecklist(exitId: number, updates: Partial<{
  knowledge_transfer_done: boolean; exit_interview_done: boolean; fnf_settled: boolean;
}>) {
  return request<ExitRequestRow>(`/api/v1/exits/${exitId}/checklist`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export function completeExit(exitId: number) {
  return request<ExitRequestRow>(`/api/v1/exits/${exitId}/complete`, { method: "POST" });
}

export interface PollOptionResult {
  id: number;
  option_text: string;
  vote_count: number;
}

export interface PollRow {
  id: number;
  question: string;
  status: string;
  created_by_name: string;
  created_at: string;
  options: PollOptionResult[];
  total_votes: number;
  my_vote_option_id: number | null;
}

export function listPolls() {
  return request<PollRow[]>("/api/v1/polls");
}

export function createPoll(question: string, options: string[]) {
  return request<PollRow>("/api/v1/polls", { method: "POST", body: JSON.stringify({ question, options }) });
}

export function voteInPoll(pollId: number, optionId: number) {
  return request<PollRow>(`/api/v1/polls/${pollId}/vote`, { method: "POST", body: JSON.stringify({ option_id: optionId }) });
}

export function closePoll(pollId: number) {
  return request<PollRow>(`/api/v1/polls/${pollId}/close`, { method: "POST" });
}

export interface KudosRow {
  id: number;
  from_employee_name: string;
  to_employee_name: string;
  category: string;
  message: string;
  created_at: string;
}

export function listKudos() {
  return request<KudosRow[]>("/api/v1/kudos");
}

export function giveKudos(toEmployeeId: number, category: string, message: string) {
  return request<KudosRow>("/api/v1/kudos", {
    method: "POST",
    body: JSON.stringify({ to_employee_id: toEmployeeId, category, message }),
  });
}

export interface TimeEntryRow {
  id: number;
  project_id: number;
  project_name: string;
  work_date: string;
  hours: number;
  billable: boolean;
  description: string | null;
}

export function logTime(projectId: number, workDate: string, hours: number, billable: boolean, description?: string) {
  return request<TimeEntryRow>("/api/v1/time-entries", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, work_date: workDate, hours, billable, description }),
  });
}

export function getMyTimeEntries() {
  return request<TimeEntryRow[]>("/api/v1/time-entries/me");
}

export function deleteTimeEntry(entryId: number) {
  return request<void>(`/api/v1/time-entries/${entryId}`, { method: "DELETE" });
}

export interface TeamTimeEntryRow extends TimeEntryRow {
  employee_id: number;
  employee_name: string;
}

export function getTeamTimeEntries() {
  return request<TeamTimeEntryRow[]>("/api/v1/time-entries/team");
}
