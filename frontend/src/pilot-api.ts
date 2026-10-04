import type { Complaint, Evaluation, Health } from "./types";
export type Event = {
  seq: number;
  case_id: string;
  at: string;
  kind: string;
  actor: string;
  detail: {
    note?: string;
    reason?: string;
    from?: string;
    to?: string;
    changes?: Record<string, { from: string; to: string }>;
  };
};
export type Case = Complaint & {
  confirmed: number;
  review_flag: number;
  revision: number;
  updated_at: string;
  original: Complaint;
  events?: Event[];
};
export type Page = {
  items: Case[];
  total: number;
  page: number;
  page_size: number;
};
export type Config = {
  taxonomy: Record<string, string[]>;
  departments: string[];
  routing: Record<string, string>;
  outside: string;
};
export type Overview = {
  total: number;
  by_status: Record<string, number>;
  by_product: Record<string, number>;
  high_open: number;
  unreviewed: number;
  activity: Event[];
};
export type Job = {
  id: string;
  created_at: string;
  source: string;
  status: string;
  total: number;
  counts: Record<string, number>;
  rows: {
    position: number;
    text: string;
    state: string;
    case_id: string;
    error: string | null;
  }[];
};
export type System = {
  database_bytes: number;
  schema_version: number;
  backups: { name: string; bytes: number }[];
  pending_rows: number;
  running_rows: number;
  failed_rows: number;
  mode: string;
};
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  method = "GET",
  body?: object,
): Promise<T> {
  const r = await fetch(
    "/api/" + path,
    method === "GET"
      ? undefined
      : {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body ?? {}),
        },
  );
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new ApiError(
      e.error?.message ?? "The request failed. Please try again.",
      r.status,
    );
  }
  return r.json();
}
export const pilot = {
  config: () => request<Config>("config"),
  health: () => request<Health>("health"),
  overview: () => request<Overview>("overview"),
  cases: (query = "") => request<Page>("cases?" + query),
  case: (id: string) => request<Case>("cases/" + encodeURIComponent(id)),
  review: (id: string, body: object) =>
    request<Case>(`cases/${encodeURIComponent(id)}/review`, "PATCH", body),
  note: (id: string, body: object) =>
    request<Case>(`cases/${encodeURIComponent(id)}/notes`, "POST", body),
  transition: (id: string, body: object) =>
    request<Case>(`cases/${encodeURIComponent(id)}/transition`, "POST", body),
  jobs: () => request<{ items: Job[] }>("jobs"),
  job: (id: string) => request<Job>("jobs/" + encodeURIComponent(id)),
  submit: (texts: string[], request_key: string, source: string) =>
    request<Job>("jobs", "POST", { texts, request_key, source }),
  control: (id: string, action: string) =>
    request<Job>(`jobs/${encodeURIComponent(id)}/${action}`, "POST"),
  system: () => request<System>("system"),
  backup: () => request<{ name: string }>("backups", "POST"),
  evaluation: () => request<Evaluation>("evaluation"),
};
