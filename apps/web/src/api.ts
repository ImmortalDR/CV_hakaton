export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const res = await fetch("/api" + path, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "fsp-web",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? "Не удалось выполнить запрос");
  return data as T;
}
export type User = {
  id: string;
  role: "candidate" | "employer";
  email: string;
  demo: boolean;
};
export type Catalog = {
  specializations: Record<string, string>;
  grades: string[];
  skills: Record<string, string>;
  demo: boolean;
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
  score: number;
  facts: Fact[];
  breakdown: Record<string, number>;
  required_skills_met?: boolean;
  missing_skills?: string[];
  unmet_skills?: string[];
};
export type Profile = {
  id: string;
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
  id: string;
  grade: string;
  status: string;
  version: string;
  created_at: string;
  expires_at: string;
  result: Result | null;
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
  candidate_id: string;
  candidate_name: string;
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
