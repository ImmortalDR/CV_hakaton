import { useEffect, useState, type ReactNode } from "react";
import { api, type Invitation, type User } from "./api";
import { date, EmptyState, Loading } from "./ui";
type Act = (fn: () => Promise<void>) => Promise<void>;
type Assignment = {
  id: string;
  sequence: number;
  version: number;
  prompt: string;
  status: string;
  due_at: string;
  answer: string | null;
  score: number | null;
  feedback: string | null;
  reviewed_at: string | null;
};
type Plan = {
  id: string;
  candidate_name: string;
  company_name: string;
  title: string;
  prompt: string;
  rubric: string;
  interval_days: number;
  response_days: number;
  status: string;
  next_issue_at: string | null;
  access_available: boolean;
  assignments: Assignment[];
};
export type TaskInbox = {
  plans: Plan[];
  pending: number;
  last_reviewed_at: string | null;
};
const states: Record<string, string> = {
  awaiting: "Ожидает согласия",
  active: "Выдача включена",
  paused: "Выдача приостановлена",
  closed: "План закрыт",
  issued: "Ожидает ответа",
  viewed: "Просмотрено",
  submitted: "На проверке",
  reviewed: "Оценено работодателем",
  expired: "Срок ответа истёк",
  cancelled: "Отменено",
};
function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
export function Tasks({
  user,
  act,
  busy,
  refresh,
}: {
  user: User;
  act: Act;
  busy: boolean;
  refresh: () => void;
}) {
  const [inbox, setInbox] = useState<TaskInbox | null>(null),
    [invitations, setInvitations] = useState<Invitation[]>([]);
  const [requestId, setRequestId] = useState(() => crypto.randomUUID()),
    [candidateId, setCandidateId] = useState("");
  const [title, setTitle] = useState(""),
    [prompt, setPrompt] = useState(""),
    [rubric, setRubric] = useState("");
  const [interval, setIntervalDays] = useState(7),
    [responseDays, setResponseDays] = useState(3);
  const load = async () => {
    setInbox(await api<TaskInbox>("/tasks"));
  };
  useEffect(() => {
    void act(async () => {
      await load();
      if (user.role === "employer")
        setInvitations(await api<Invitation[]>("/invitations"));
    });
    const timer = window.setInterval(() => {
      void load().catch(() => {});
    }, 30000);
    return () => window.clearInterval(timer);
  }, [user.id]);
  const update = async (fn: () => Promise<unknown>) => {
    await fn();
    await load();
    refresh();
  };
  const recipients = [
    ...new Map(
      invitations
        .filter((i) => i.status === "accepted" && i.contacts)
        .map((i) => [i.candidate_id, i]),
    ).values(),
  ];
  if (!inbox) return <Loading />;
  return (
    <>
      <div className="page-title">
        <h1>Задания от компаний</h1>
        <p>
          Короткие адресные задания по отдельному согласию. Оценка работодателя
          не меняет подтверждённый грейд.
        </p>
      </div>
      <div className="notice" role="status">
        Требуют внимания: {inbox.pending}. Последняя оценка задания:{" "}
        {inbox.last_reviewed_at ? date(inbox.last_reviewed_at) : "пока нет"}.
        Это отдельный сигнал актуальности профиля.
      </div>
      <button
        className="text-button"
        disabled={busy}
        onClick={() => void act(load)}
      >
        Обновить задания
      </button>
      {user.role === "employer" && (
        <section className="panel task-create">
          <h2>Предложить регулярные задания</h2>
          <p>
            Для кандидатов, принявших приглашение. Кандидат сам включает выдачу.
            Содержание и критерии фиксируются для повторов плана.
          </p>
          {!recipients.length ? (
            <p>Сначала дождитесь принятия приглашения кандидатом.</p>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void act(() =>
                  update(async () => {
                    await api("/tasks/plans", {
                      candidate_id: candidateId,
                      request_id: requestId,
                      title,
                      prompt,
                      rubric,
                      interval_days: interval,
                      response_days: responseDays,
                    });
                    setRequestId(crypto.randomUUID());
                    setTitle("");
                    setPrompt("");
                    setRubric("");
                  }),
                );
              }}
            >
              <Field label="Получатель задания">
                <select
                  required
                  value={candidateId}
                  onChange={(e) => setCandidateId(e.target.value)}
                >
                  <option value="">Выберите кандидата</option>
                  {recipients.map((i) => (
                    <option key={i.candidate_id} value={i.candidate_id}>
                      {i.candidate_name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Название задания">
                <input
                  required
                  minLength={3}
                  maxLength={160}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </Field>
              <Field label="Задача и ожидаемый ответ">
                <textarea
                  required
                  minLength={20}
                  maxLength={4000}
                  rows={4}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                />
              </Field>
              <Field label="Критерии оценки">
                <textarea
                  required
                  minLength={10}
                  maxLength={2000}
                  rows={3}
                  value={rubric}
                  onChange={(e) => setRubric(e.target.value)}
                />
              </Field>
              <div className="form-grid">
                <Field label="Период выдачи, дней">
                  <input
                    type="number"
                    required
                    min={1}
                    max={365}
                    value={interval}
                    onChange={(e) => setIntervalDays(Number(e.target.value))}
                  />
                </Field>
                <Field label="Срок ответа, дней">
                  <input
                    type="number"
                    required
                    min={1}
                    max={interval}
                    value={responseDays}
                    onChange={(e) => setResponseDays(Number(e.target.value))}
                  />
                </Field>
              </div>
              <p className="muted">
                Не более одного задания за период. Новая выдача ждёт завершения
                предыдущего задания и проверки отправленного ответа.
              </p>
              <button disabled={busy}>Предложить план кандидату</button>
            </form>
          )}
        </section>
      )}
      {!inbox.plans.length && (
        <EmptyState
          title="Заданий пока нет"
          description="Планы появятся после предложения компании. Участие добровольное."
        />
      )}
      {inbox.plans.map((p) => (
        <section className="panel task-plan" key={p.id}>
          <div className="section-heading">
            <h2>{p.title}</h2>
            <span className="badge">{states[p.status]}</span>
          </div>
          <p>{user.role === "candidate" ? p.company_name : p.candidate_name}</p>
          <p className="task-text">{p.prompt}</p>
          <p className="task-text">
            <strong>Критерии оценки: </strong>
            {p.rubric}
          </p>
          <p>
            Период: {p.interval_days} дн. · Срок ответа: {p.response_days} дн.
          </p>
          {p.next_issue_at && (
            <p>
              Следующая выдача не ранее {date(p.next_issue_at)} — после
              завершения предыдущего задания.
            </p>
          )}
          {!p.access_available && (
            <p className="notice">
              Выдача и обмен ответами недоступны: нужно действующее согласие на
              контакты и публикация профиля.
            </p>
          )}
          <div className="actions">
            {user.role === "candidate" &&
              p.access_available &&
              ["awaiting", "paused"].includes(p.status) && (
                <button
                  disabled={busy}
                  onClick={() =>
                    void act(() =>
                      update(() =>
                        api(
                          `/tasks/plans/${p.id}`,
                          { status: "active" },
                          "PATCH",
                        ),
                      ),
                    )
                  }
                >
                  Согласиться и включить выдачу
                </button>
              )}
            {user.role === "candidate" &&
              p.access_available &&
              p.status === "active" && (
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    void act(() =>
                      update(() =>
                        api(
                          `/tasks/plans/${p.id}`,
                          { status: "paused" },
                          "PATCH",
                        ),
                      ),
                    )
                  }
                >
                  Приостановить выдачу
                </button>
              )}
            {p.access_available && p.status !== "closed" && (
              <button
                className="text-button"
                disabled={busy}
                onClick={() =>
                  void act(() =>
                    update(() =>
                      api(
                        `/tasks/plans/${p.id}`,
                        { status: "closed" },
                        "PATCH",
                      ),
                    ),
                  )
                }
              >
                Закрыть план
              </button>
            )}
          </div>
          {user.role === "candidate" && p.status === "awaiting" && (
            <p className="muted">
              Согласие разрешает повторную выдачу по расписанию и передачу
              ответов этой компании. Его можно остановить; открытые задания
              будут отменены.
            </p>
          )}
          {p.assignments.map((a) => (
            <AssignmentCard
              key={a.id}
              a={a}
              canAnswer={p.access_available && p.status === "active"}
              access={p.access_available}
              user={user}
              busy={busy}
              act={act}
              update={update}
            />
          ))}
        </section>
      ))}
    </>
  );
}
function AssignmentCard({
  a,
  canAnswer,
  access,
  user,
  busy,
  act,
  update,
}: {
  a: Assignment;
  canAnswer: boolean;
  access: boolean;
  user: User;
  busy: boolean;
  act: Act;
  update: (fn: () => Promise<unknown>) => Promise<void>;
}) {
  const [answer, setAnswer] = useState(""),
    [score, setScore] = useState("75"),
    [feedback, setFeedback] = useState("");
  return (
    <article className="task-assignment">
      <h3>
        Выдача №{a.sequence} · {states[a.status]}
      </h3>
      <p>
        Версия {a.version} · Ответ до {date(a.due_at)}
      </p>
      <p className="task-text">{a.prompt}</p>
      {a.answer !== null && (
        <>
          <strong>Ответ кандидата</strong>
          <p className="task-text">{a.answer}</p>
        </>
      )}
      {a.reviewed_at && (
        <div className="notice">
          <div>
            <strong>Оценка работодателя: {a.score}/100</strong>
            <p className="task-text">{a.feedback}</p>
            <small>
              {date(a.reviewed_at)} · Отдельная оценка, грейд не изменён.
            </small>
          </div>
        </div>
      )}
      {user.role === "candidate" &&
        canAnswer &&
        ["issued", "viewed"].includes(a.status) && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void act(() =>
                update(() =>
                  api(`/tasks/assignments/${a.id}/answer`, { answer }),
                ),
              );
            }}
          >
            <Field label="Ответ на задание">
              <textarea
                required
                maxLength={6000}
                rows={4}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
              />
            </Field>
            <button disabled={busy}>Отправить ответ</button>
          </form>
        )}
      {user.role === "employer" && access && a.status === "submitted" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void act(() =>
              update(() =>
                api(`/tasks/assignments/${a.id}/review`, { score: Number(score), feedback }),
              ),
            );
          }}
        >
          <Field label="Оценка от 0 до 100">
            <input
              type="number"
              required
              min={0}
              max={100}
              value={score}
              onChange={(e) => setScore(e.target.value)}
            />
          </Field>
          <Field label="Обоснование оценки">
            <textarea
              required
              minLength={10}
              maxLength={2000}
              rows={3}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
            />
          </Field>
          <button disabled={busy}>Сохранить оценку</button>
        </form>
      )}
    </article>
  );
}
