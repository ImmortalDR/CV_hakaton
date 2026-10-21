export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export const sessionChangedEvent = "fsp:session-changed";
export class SessionChangedError extends ApiError {
  constructor() { super("Аккаунт изменился в другой вкладке. Обновляем кабинет…", 409); }
}
let sessionUserId: string | null = null;
let sessionRevision = 0;
let demoVersion: number | null = null;
export function setApiUser(id: string | null, version: number | null = null) {
  sessionUserId = id;
  demoVersion = version;
  sessionRevision++;
}

export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
  options: { signal?: AbortSignal } = {},
): Promise<T> {
  const revision = sessionRevision;
  const authenticated = !path.startsWith("/auth/") && path !== "/catalog";
  const controller = new AbortController();
  const abort = () => controller.abort();
  options.signal?.addEventListener("abort", abort, { once: true });
  if (options.signal?.aborted) abort();
  const timeout = window.setTimeout(abort, 15000);
  try {
    const res = await fetch("/api" + path, {
      method: method ?? (body === undefined ? "GET" : "POST"),
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "fsp-web",
        ...(authenticated && demoVersion !== null ? { "X-FSP-Demo-Version": String(demoVersion) } : {}),
        ...(authenticated && sessionUserId ? { "X-FSP-User": sessionUserId } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await res.json().catch(() => null);
    if (authenticated && revision !== sessionRevision) throw new SessionChangedError();
    if (authenticated && (res.status === 401 || res.status === 403 || res.headers.has("X-FSP-Session-Changed"))) {
      window.dispatchEvent(new Event(sessionChangedEvent));
      if (res.headers.has("X-FSP-Session-Changed")) throw new SessionChangedError();
    }
    if (!res.ok) throw new ApiError(
      typeof data?.detail === "string" ? data.detail : "Не удалось выполнить запрос. Повторите попытку.", res.status,
    );
    if (data === null) throw new ApiError("Сервер вернул неполный ответ. Повторите попытку.", res.status);
    return data as T;
  } catch (error) {
    if (controller.signal.aborted && !options.signal?.aborted)
      throw new ApiError("Сервер не ответил вовремя. Повторите запрос.", 0);
    throw error;
  } finally {
    window.clearTimeout(timeout);
    options.signal?.removeEventListener("abort", abort);
  }
}
export type User = {
  id: string;
  role: "candidate" | "employer";
  email: string;
  demo: boolean;
  demo_run_id?: string | null;
  demo_candidate_code?: string | null;
  demo_reset_version?: number | null;
};
export type AssessmentRubric = {
  question_count: number;
  minutes: number;
  threshold: number;
  core_min_correct: number;
  core_total: number;
};
export type AssessmentAvailability = {
  checked_at: string;
  bank_version: string;
  specialization: string;
  levels: {
    grade: string;
    available: boolean;
    reasons: { code: string; message: string; until: string | null }[];
    next_available_at: string | null;
    rubric: AssessmentRubric;
  }[];
};
export type Catalog = {
  specializations: Record<string, string>;
  grades: string[];
  skills: Record<string, string>;
  demo: boolean;
  rubric?: AssessmentRubric;
};
export type Evidence = {
  id: string;
  skill: string;
  state: string;
  correct: number;
  total: number;
  date: string;
  version: string;
  attempt_id: string;
};
export type Fact = {
  skill: string;
  state: string;
  source: string;
  evidence: Evidence | null;
  claimed_years?: number | null;
};
export type Match = {
  methodology?: string;
  score: number;
  facts: Fact[];
  breakdown: Record<string, number>;
  required_skills_met?: boolean;
  missing_skills?: string[];
  unmet_skills?: string[];
};
export type Profile = {
  id: string;
  candidate_code: string;
  display_name: string;
  name?: string;
  phone?: string;
  industry?: string;
  specialization: string;
  claimed_grade?: string;
  verified_grade: string | null;
  skills: string[];
  experience_years: number | null;
  roles?: string;
  soft_skills?: string;
  about?: string;
  processing?: boolean;
  published?: boolean;
  show_experience?: boolean;
  fsp_identity?: string | null;
  next_grade_change?: string | null;
  contacts: { email: string; phone: string } | null;
  evidence: Evidence[];
  test_score: number;
  demo: boolean;
  achievements: { title: string; result: string; verification: string }[];
  match?: Match;
  task_last_reviewed_at?: string | null;
};
export type Result = {
  score: number;
  passed: boolean;
  details: {
    id: string;
    correct: boolean;
    expected: string;
    explanation: string;
  }[];
};
export type Attempt = {
  answers: Record<string, string>;
  id: string;
  specialization: string;
  grade: string;
  status: string;
  version: string;
  created_at: string;
  expires_at: string;
  result: Result | null;
  rubric?: AssessmentRubric;
  questions: { id: string; text: string; skill: string }[];
};
export type Company = {
  id: string;
  name: string;
  description: string;
  sector: string;
  contact: string;
};
export type Invitation = {
  id: string;
  created_at: string;
  candidate_id: string;
  candidate_name: string;
  chat_available: boolean;
  company_name: string;
  description: string;
  salary_min: number;
  salary_max: number;
  employer_contact: string;
  status: string;
  contacts: { email: string; phone: string } | null;
};
export type Criteria = {
  title: string;
  description: string;
  specialization: string;
  grades: string[];
  required_skills: string[];
  desired_skills: string[];
  min_years: number | null;
  fsp_only: boolean;
  confirmed: boolean;
};
export type Snapshot = {
  id: string;
  created_at: string;
  criteria: Criteria;
  items: Profile[];
  hidden_count: number;
};
