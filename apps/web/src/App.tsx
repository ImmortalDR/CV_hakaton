import {
  useCallback,
  useRef,
  useEffect,
  useState,
  useId,
  cloneElement,
  isValidElement,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  ArrowRight,
  Award,
  BookOpen,
  BriefcaseBusiness,
  Check,
  ChevronRight,
  Download,
  FileUser,
  FlaskConical,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Mail,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
} from "./icons";
import {
  api,
  ApiError,
  type Attempt,
  type AssessmentAvailability,
  type Catalog,
  type Company,
  type Criteria,
  type Invitation,
  type Profile,
  type Snapshot,
  type User,
} from "./api";
import {
  currency,
  date,
  EmptyState,
  ErrorState,
  Loading,
  StatCard,
  statusLabels,
} from "./ui";

import { Auth } from "./Auth";
import { Tasks, type TaskInbox } from "./Tasks";
import { countLabel, evidenceLabels } from "./formatting";

type Act = (fn: () => Promise<void>) => Promise<void>;
type Actions = {
  act: Act;
  busy: boolean;
  catalog: Catalog;
  refresh: () => void;
};
const emptyCatalog: Catalog = {
  specializations: {},
  grades: [],
  skills: {},
  demo: false,
};

function Field({ label, children }: { label: string; children: ReactNode }) {
  const [error, setError] = useState("");
  const errorId = useId();
  const validate = (target: EventTarget | null, show: boolean) => {
    if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) return;
    if (target.type === "checkbox" || target.type === "radio") return;
    const length = target.value.trim().length;
    const message = target.required && !length ? `Заполните поле «${label}».`
      : length && target.minLength > length ? `Введите не менее ${target.minLength} символов без крайних пробелов.` : "";
    target.setCustomValidity(message);
    if (show || !message) {
      setError(message);
      target.setAttribute("aria-invalid", String(!!message));
      if (message) target.setAttribute("aria-describedby", errorId);
      else target.removeAttribute("aria-describedby");
    }
  };
  return (
    <label className="field"
      onInputCapture={(e) => validate(e.target, !!error)}
      onBlurCapture={(e) => validate(e.target, true)}
      onInvalidCapture={(e) => {
        validate(e.target, true);
        const target = e.target as HTMLInputElement;
        setError(target.validationMessage);
        target.setAttribute("aria-invalid", "true");
        target.setAttribute("aria-describedby", errorId);
      }}>
      <span id={`${errorId}-label`}>{label}</span>
      {isValidElement<Record<string, unknown>>(children) ? cloneElement(children, {"aria-labelledby": `${errorId}-label`}) : children}
      {error && <small id={errorId} className="field-error" role="alert">{error}</small>}
    </label>
  );
}
function Skills({
  values,
  onChange,
  catalog,
}: {
  values: string[];
  onChange: (v: string[]) => void;
  catalog: Catalog;
}) {
  return (
    <div className="skill-options">
      {Object.entries(catalog.skills).map(([id, name]) => (
        <label key={id} className={values.includes(id) ? "selected" : ""}>
          <input
            type="checkbox"
            checked={values.includes(id)}
            onChange={(e) =>
              onChange(
                e.target.checked
                  ? [...values, id]
                  : values.filter((x) => x !== id),
              )
            }
          />
          {name}
        </label>
      ))}
    </div>
  );
}

function useSessionState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try { return JSON.parse(sessionStorage.getItem(key) ?? "null") ?? initial; }
    catch { return initial; }
  });
  useEffect(() => {
    try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* Storage can be disabled. */ }
  }, [key, value]);
  return [value, setValue] as const;
}

export function App() {
  const [catalog, setCatalog] = useState(emptyCatalog),
    [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true);
  const [tab, setTabState] = useState("overview"),
    [profile, setProfile] = useState<Profile | null>(null),
    [company, setCompany] = useState<Company | null>(null);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [version, setVersion] = useState(0);
  const [resetToken, setResetToken] = useState("");
  const [verificationVersion, setVerificationVersion] = useState(0);
  const unsavedAssessment = useRef(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const confirmLeave = () => !unsavedAssessment.current || window.confirm("Есть ответы, не сохранённые на сервере. Покинуть тест? Черновик останется в этом браузере; срок теста продолжает идти.");
  const setTab = (value: string) => {
    if (tab === "assessment" && value !== tab && !confirmLeave()) return;
    setTabState(value);
    if (user) try { sessionStorage.setItem(`fsp-tab-${user.id}`, value); } catch { /* Optional UI context. */ }
  };
  const act: Act = useCallback(async (fn) => {
    setError("");
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Не удалось выполнить действие",
      );
    } finally {
      setBusy(false);
    }
  }, []);
  const refresh = () => setVersion((v) => v + 1);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [tab]);
  useEffect(() => {
    const resetting = location.hash.startsWith("#reset=");
    Promise.all([
      api<Catalog>("/catalog").then(setCatalog),
      api<User>("/auth/me")
        .then(u => {
          if (resetting) return;
          setUser(u);
          try { setTabState(sessionStorage.getItem(`fsp-tab-${u.id}`) ?? "overview"); } catch { /* Default overview. */ }
        })
        .catch(() => {}),
    ]).finally(() => setLoading(false));
    const confirmEmailFromHash = () => {
      if (location.hash.startsWith("#reset=")) {
        setResetToken(location.hash.slice(7));
        setUser(null);
        history.replaceState(null, "", location.pathname);
        return;
      }
      if (!location.hash.startsWith("#verify=")) return;
      const token = location.hash.slice(8);
      history.replaceState(null, "", location.pathname);
      void act(async () => {
        await api("/auth/verify", { token });
        setNotice("Почта подтверждена. Войдите в кабинет.");
        setVerificationVersion(n => n + 1);
      });
    };
    confirmEmailFromHash();
    window.addEventListener("hashchange", confirmEmailFromHash);
    return () => window.removeEventListener("hashchange", confirmEmailFromHash);
  }, [act]);
  useEffect(() => {
    if (!user) return;
    const path = user.role === "candidate" ? "/me/profile" : "/me/company";
    void act(async () => {
      if (user.role === "candidate") setProfile(await api<Profile>(path));
      else setCompany(await api<Company>(path));
    });
  }, [user?.id, version, act]);
  const signedIn = (u: User) => {
    setProfile(null);
    setCompany(null);
    setUser(u);
    setTab("overview");
    setNotice("");
  };
  const [taskPending, setTaskPending] = useState(0);
  useEffect(() => {
    setTaskPending(0);
    if (!user) return;
    let disposed = false;
    const poll = () => { void api<TaskInbox>("/tasks").then(x => { if (!disposed) setTaskPending(x.pending); }).catch(() => {}); };
    poll(); const timer = window.setInterval(poll, 30000);
    return () => { disposed = true; window.clearInterval(timer); };
  }, [user?.id, version]);
  const props = { act, busy, catalog, refresh };
  if (loading) return <Loading />;
  if (!user)
    return (
      <div className="welcome">
        <header className="welcome-head">
          <Brand />
          <span>Подтверждённые навыки. Прямой контакт.</span>
        </header>
        <main className="welcome-main">
          <section className="hero">
            <div className="eyebrow">
              <span className="dot" /> Обратный найм в ИТ
            </div>
            <h1>
              Пусть ваши
              <br />
              <em>навыки</em>{" "}
              <br />
              говорят за вас.
            </h1>
            <p>
              Подтвердите свой уровень. Получайте предложения от команд, которым
              нужны именно ваши компетенции — сразу с зарплатой.
            </p>
            <div className="hero-path">
              <span>
                <ShieldCheck />
                Подтвердить
              </span>
              <ChevronRight />
              <span>
                <Users />
                Совпасть
              </span>
              <ChevronRight />
              <span>
                <Mail />
                Договориться
              </span>
            </div>
            <div className="hero-proof">
              <div className="mini-icon">
                <Award />
              </div>
              <div>
                <strong>Сильнее резюме — доказательства</strong>
                <p>Результаты теста и достижения ФСП с понятным источником.</p>
              </div>
            </div>
          </section>
          <section className="auth-box">
            {error && <ErrorState message={error} />}{" "}
            {notice && (
              <p role="status" className="notice">
                {notice}
              </p>
            )}
            <Auth {...props} verificationVersion={verificationVersion} onLogin={signedIn} resetToken={resetToken} onResetDone={() => setResetToken("")} />
          </section>
        </main>
        <footer>
          ФСП · Платформа обратного найма{" "}
          <span>
            {catalog.demo
              ? "Демонстрационный стенд · используйте только вымышленные данные"
              : "Ваши контакты раскрываются только с вашего согласия"}
          </span>
        </footer>
      </div>
    );
  const items =
    user.role === "candidate"
      ? ([
          ["overview", "Обзор", LayoutDashboard],
          ["profile", "Мой профиль", FileUser],
          ["assessment", "Подтверждение навыков", ShieldCheck],
          ["invitations", "Приглашения", Mail],
          ["tasks", "Задания от компаний", BookOpen],
          ["fsp", "Достижения ФСП", Award],
        ] as const)
      : ([
          ["overview", "Обзор", LayoutDashboard],
          ["search", "Подбор кандидатов", Search],
          ["invitations", "Приглашения", Mail],
          ["tasks", "Задания от компаний", BookOpen],
          ["company", "Моя компания", BriefcaseBusiness],
        ] as const);
  return (
    <div className="shell">
      <aside className="sidebar">
        <Brand />
        <div className="workspace-label">
          {user.role === "candidate"
            ? "КАБИНЕТ КАНДИДАТА"
            : "КАБИНЕТ РАБОТОДАТЕЛЯ"}
        </div>
        <button className="mobile-menu" aria-expanded={menuOpen} aria-controls="workspace-nav" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? "Свернуть меню" : "Все разделы"} · {items.find(([key]) => key === tab)?.[1]}
        </button>
        <nav id="workspace-nav" className={menuOpen ? "mobile-open" : ""} aria-label="Разделы кабинета">
          {items.map(([key, label, Icon]) => (
            <button
              key={key}
              className={tab === key ? "active" : ""}
              onClick={() => {
                setTab(key);
                setMenuOpen(false);
                setError("");
                setNotice("");
              }}
            >
              <Icon size={19} />
              {label}{key === "tasks" && taskPending > 0 && <span className="task-count" aria-label="Требуют внимания">{taskPending}</span>}
              {tab === key && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={23} />
          <strong>Контроль остаётся у вас</strong>
          <p>
            Контакты открываются конкретной компании после принятия приглашения.
          </p>
        </div>
        <button
          className="logout"
          onClick={() =>
            void act(async () => {
              if (!confirmLeave()) return;
              await api("/auth/logout", {});
              setUser(null);
              setProfile(null);
              setCompany(null);
            })
          }
        >
          <LogOut size={17} />
          Выйти
        </button>
      </aside>
      <div className="main">
        <header className="topbar">
          <span>
            Личный кабинет <ChevronRight size={14} />{" "}
            {items.find((i) => i[0] === tab)?.[1]}
          </span>
          <div className="account">
            <div className="avatar">
              {user.role === "candidate" ? "К" : "Р"}
            </div>
            <div>
              <strong>
                {user.role === "candidate"
                  ? "Кандидат"
                  : (company?.name ?? "Работодатель")}
              </strong>
              <small>{user.email}</small>
            </div>
          </div>
        </header>
        <main className="content">
          {catalog.demo && (
            <div className="demo-banner">
              <FlaskConical size={16} />
              <span>
                Демонстрационный стенд. Данные примеров и достижения ФСП —
                синтетические.
              </span>
            </div>
          )}
          {error && <ErrorState message={error} />}{" "}
          {notice && (
            <div className="notice" role="status">
              {notice}
            </div>
          )}
          {tab === "overview" && (
            <Overview
              profile={profile}
              company={company}
              user={user}
              catalog={catalog}
              navigate={setTab}
            />
          )}
          {tab === "profile" &&
            (profile ? (
              <ProfileForm
                key={profile.id + version}
                profile={profile}
                {...props}
                saved={() => {
                  refresh();
                  setNotice("Профиль сохранён");
                  window.scrollTo(0, 0);
                }}
              />
            ) : (
              <Loading />
            ))}
          {profile && user.role === "candidate" && (
            <div hidden={tab !== "assessment"}>
              <Assessments {...props} profile={profile} visible={tab === "assessment"} dirtyRef={unsavedAssessment} />
            </div>
          )}
          {tab === "tasks" && <Tasks user={user} {...props} />}
          {tab === "search" && <SearchPage {...props} userId={user.id} openInvitations={() => setTab("invitations")} />}
          {tab === "invitations" && (
            <Invitations {...props} user={user} profile={profile} version={version} />
          )}
          {tab === "company" &&
            (company ? (
              <CompanyForm
                company={company}
                {...props}
                saved={() => {
                  refresh();
                  setNotice("Компания сохранена");
                  window.scrollTo(0, 0);
                }}
              />
            ) : (
              <Loading />
            ))}
          {tab === "fsp" && profile && (
            <section>
              <PageTitle
                kicker="Спортивный опыт"
                title="Достижения ФСП"
                description="Дополнительный сигнал для работодателя. Достижения влияют на порядок внутри категории и не меняют ваш грейд."
              />
              <div className="panel">
                <Award className="big-icon" />
                <h2>
                  {profile.achievements.length
                    ? "Демонстрационный профиль связан"
                    : "ФСП — дополнительная возможность"}
                </h2>
                <p>Без истории соревнований доступны все функции платформы.</p>
                {profile.achievements.map((a, i) => (
                  <p key={i} className="notice">
                    {a.title} · {a.result} · демоданные
                  </p>
                ))}
                <div className="actions">
                  {catalog.demo && (
                    <>
                      <button
                        disabled={busy}
                        onClick={() =>
                          void act(async () => {
                            await api("/me/fsp", { identity: "demo-winner" });
                            refresh();
                          })
                        }
                      >
                        Связать демонстрационный ФСП ID
                      </button>
                      <button
                        className="secondary"
                        disabled={busy}
                        onClick={() =>
                          void act(async () => {
                            await api("/me/fsp", {
                              identity: "demo-participant",
                            });
                            refresh();
                          })
                        }
                      >
                        Пример участника
                      </button>
                    </>
                  )}
                  {profile.fsp_identity && (
                    <button
                      className="secondary"
                      onClick={() =>
                        void act(async () => {
                          await api("/me/fsp", { identity: "unlink" });
                          refresh();
                        })
                      }
                    >
                      Отвязать
                    </button>
                  )}
                </div>
                <small>
                  Подключение к реальному реестру ФСП пока не предоставлено.
                </small>
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
function Brand() {
  return (
    <div className="brand">
      <div className="brand-mark">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <div>
        ФСП<span>карьера</span>
      </div>
    </div>
  );
}
function PageTitle({
  kicker,
  title,
  description,
}: {
  kicker: string;
  title: string;
  description: string;
}) {
  return (
    <div className="page-title">
      <div className="eyebrow">{kicker}</div>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  );
}

function Overview({
  profile: p,
  company: c,
  user,
  catalog,
  navigate,
}: {
  profile: Profile | null;
  company: Company | null;
  user: User;
  catalog: Catalog;
  navigate: (s: string) => void;
}) {
  const candidate = user.role === "candidate";
  return (
    <>
      <PageTitle
        kicker={
          candidate ? "Ваш следующий шаг" : "Найм начинается с компетенций"
        }
        title={
          candidate
            ? "Возможности начинаются с вас"
            : "Найдите своего специалиста"
        }
        description={
          candidate
            ? "Подтверждайте навыки, выбирайте предложения и знакомьтесь с командами на своих условиях."
            : "Опишите потребность. Получите кандидатов с доказательствами навыков и пригласите подходящих лично."
        }
      />
      <div className="feature-banner">
        <div>
          <span className="light-label">
            {candidate
              ? "Ваш профиль — больше, чем резюме"
              : "От потребности к человеку"}
          </span>
          <h2>
            {candidate
              ? p?.verified_grade
                ? `${catalog.specializations[p.specialization]} · ${p.verified_grade}`
                : "Покажите, что вы умеете"
              : "Навыки подтверждены. Условия открыты."}
          </h2>
          <p>
            {candidate
              ? !p?.name
                ? "Заполните профиль, чтобы выбрать специализацию и подтвердить навыки."
                : p.verified_grade
                ? p.published && p.processing
                  ? "Ваш уровень подтверждён тестом. Работодатели могут найти вас в соответствующей категории."
                  : "Ваш уровень подтверждён, но профиль скрыт. Включите публикацию и согласие в профиле, чтобы попасть в подбор."
                : "Тест по основному и вспомогательному навыкам поможет подтвердить выбранный уровень. ФСП ID для этого не нужен."
              : "Никакого потока случайных откликов: выбирайте подтверждённую категорию и смотрите основания подбора."}
          </p>
          <button
            className="white"
            onClick={() =>
              navigate(
                candidate ? (!p?.name ? "profile" : !p.verified_grade ? "assessment" : p.published && p.processing ? "invitations" : "profile") : "search",
              )
            }
          >
            {candidate
              ? p?.name
                ? !p.verified_grade ? "Перейти к тестированию" : p.published && p.processing ? "Посмотреть приглашения" : "Настроить видимость"
                : "Заполнить профиль"
              : "Подобрать кандидатов"}
            <ArrowRight size={18} />
          </button>
        </div>
        <div className="orb">
          <ShieldCheck size={78} />
          <span>
            {candidate
              ? p?.verified_grade
                ? <>навыки<br />подтверждены</>
                : <>навыки<br />к проверке</>
              : <>навыки<br />в основе</>}
          </span>
        </div>
      </div>
      <div className="stats">
        {candidate ? (
          <>
            <StatCard
              label="Подтверждённый уровень"
              value={p?.verified_grade ?? "Впереди"}
              hint="Присваивается только тестом"
            />
            <StatCard
              label="Видимость профиля"
              value={p?.published ? "Опубликован" : "Скрыт"}
              hint="Вы управляете публикацией"
            />
            <StatCard
              label="Достижения ФСП"
              value={p?.achievements.length ?? 0}
              hint="Не меняют профессиональный грейд"
            />
          </>
        ) : (
          <>
            <StatCard
              label="Направления"
              value="2"
              hint="Python / бэкенд и аналитика / SQL"
            />
            <StatCard label="Уровни" value="3" hint="Junior, Middle, Senior" />
            <StatCard
              label="Компания"
              value={c?.contact ? "Готова к найму" : "Заполните профиль"}
              hint="Условия и контакт видны кандидату"
            />
          </>
        )}
      </div>
      <div className="section-heading">
        <h2>{candidate ? "Ваш путь к предложению" : "Как устроен подбор"}</h2>
        <span>Прозрачно на каждом шаге</span>
      </div>
      <div className="steps">
        {(candidate
          ? [
              [
                "01",
                "Расскажите о себе",
                "Укажите специализацию, стек и опыт.",
                "profile",
              ],
              [
                "02",
                "Подтвердите уровень",
                "Варианты заданий и оценка на сервере.",
                "assessment",
              ],
              [
                "03",
                "Выберите команду",
                "Зарплата известна до начала общения.",
                "invitations",
              ],
            ]
          : [
              [
                "01",
                "Опишите потребность",
                "Стек, категория и задачи команды.",
                "search",
              ],
              [
                "02",
                "Изучите доказательства",
                "Видно, что проверено, а что неизвестно.",
                "search",
              ],
              [
                "03",
                "Пригласите лично",
                "С вилкой в рублях и способом связи.",
                "invitations",
              ],
            ]
        ).map(([n, title, desc, key]) => (
          <button className="step" key={n} onClick={() => navigate(key)}>
            <span>{n}</span>
            <strong>{title}</strong>
            <p>{desc}</p>
            <ArrowRight size={18} />
          </button>
        ))}
      </div>
    </>
  );
}

function ProfileForm({
  profile: p,
  act,
  busy,
  catalog,
  saved,
}: Actions & { profile: Profile; saved: () => void }) {
  const [form, setForm] = useState({
    name: p.name ?? "",
    phone: p.phone ?? "",
    about: p.about ?? "",
    industry: "ИТ",
    specialization: p.specialization,
    claimed_grade: p.claimed_grade ?? "Junior",
    skills: p.skills,
    roles: p.roles ?? "",
    soft_skills: p.soft_skills ?? "",
    experience_years: p.experience_years,
    processing: p.processing ?? true,
    published: p.published ?? false,
    show_experience: p.show_experience ?? true,
  });
  const change = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [k]: v }));
  return (
    <>
      <PageTitle
        kicker="Основа вашего профиля"
        title="Расскажите о себе"
        description="Эти сведения указаны вами. Подтверждённые результаты тестирования работодатель увидит отдельно."
      />
      <form
        className="panel"
        onSubmit={(e) => {
          e.preventDefault();
          void act(async () => {
            await api("/me/profile", form, "PUT");
            saved();
          });
        }}
      >
        <div className="form-grid">
          <Field label="Имя и фамилия">
            <input
              required
              minLength={2}
              maxLength={160}
              value={form.name}
              onChange={(e) => change("name", e.target.value)}
            />
          </Field>
          <Field label="Телефон / способ связи">
            <input
              maxLength={80}
              value={form.phone}
              onChange={(e) => change("phone", e.target.value)}
            />
          </Field>
          <Field label="Специализация">
            <select
              disabled={!!p.verified_grade}
              value={form.specialization}
              onChange={(e) => change("specialization", e.target.value)}
            >
              {Object.entries(catalog.specializations).map(([id, n]) => (
                <option key={id} value={id}>
                  {n}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Предполагаемый уровень">
            <select
              value={form.claimed_grade}
              onChange={(e) => change("claimed_grade", e.target.value)}
            >
              {catalog.grades.map((g) => (
                <option key={g}>{g}</option>
              ))}
            </select>
          </Field>
          <Field label="Роли в команде">
            <input
              maxLength={500}
              value={form.roles}
              onChange={(e) => change("roles", e.target.value)}
              placeholder="Например, бэкенд-разработчик"
            />
          </Field>
          <Field label="Стаж, лет · можно оставить неизвестным">
            <input
              type="number"
              min={0}
              max={60}
              value={form.experience_years ?? ""}
              onChange={(e) =>
                change(
                  "experience_years",
                  e.target.value === "" ? null : Number(e.target.value),
                )
              }
            />
          </Field>
        </div>
        <div className="field">
          <span>Стек · со слов кандидата</span>
          <Skills
            values={form.skills}
            onChange={(v) => change("skills", v)}
            catalog={catalog}
          />
        </div>
        <Field label="Навыки совместной работы">
          <input
            maxLength={1000}
            value={form.soft_skills}
            onChange={(e) => change("soft_skills", e.target.value)}
            placeholder="Командная работа, презентация решений…"
          />
        </Field>
        <Field label="О себе">
          <textarea
            maxLength={3000}
            value={form.about}
            onChange={(e) => change("about", e.target.value)}
            rows={3}
          />
        </Field>
        <div className="privacy">
          <LockKeyhole />
          <div>
            <h3>Публикация и контакты</h3>
            <p>
              До принятия приглашения видны категория, структурированный стек и
              доказательства. Имя, контакты и свободный текст закрыты.
              Отключение публикации отзывает существующие разрешения на контакты
              и диалоги.
            </p>
          </div>
        </div>
        <label className="checkline">
          <input
            type="checkbox"
            checked={form.processing}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                processing: e.target.checked,
                published: e.target.checked ? f.published : false,
              }))
            }
          />
          Согласен на обработку данных для работы профиля
        </label>
        <label className="checkline">
          <input
            type="checkbox"
            disabled={!form.processing}
            checked={form.published}
            onChange={(e) => change("published", e.target.checked)}
          />
          Публиковать профиль в банке кандидатов
        </label>
        <label className="checkline">
          <input
            type="checkbox"
            checked={form.show_experience}
            onChange={(e) => change("show_experience", e.target.checked)}
          />
          Показывать заявленный стаж
        </label>
        <div className="actions">
          <button disabled={busy}>Сохранить профиль</button>
          <a className="button secondary" href={`/api/profiles/${p.id}/pdf`}>
            <Download size={16} />
            Скачать мой PDF
          </a>
        </div>
      </form>
    </>
  );
}

function Assessments({
  profile,
  act,
  busy,
  catalog,
  refresh,
  visible,
  dirtyRef,
}: Actions & { profile: Profile; visible: boolean; dirtyRef: { current: boolean } }) {
  const [attempts, setAttempts] = useState<Attempt[]>([]),
    [current, setCurrent] = useState<Attempt | null>(null),
    [answers, setAnswers] = useState<Record<string, string>>({}),
    [grade, setGrade] = useState(profile.claimed_grade ?? "Junior");
  const [saveStatus, setSaveStatus] = useState("");
  const saveQueue = useRef(Promise.resolve());
  const inFlight = useRef(false);
  const draft = useRef<Record<string, string>>({});
  const confirmed = useRef<Record<string, string>>({});
  const activeId = useRef<string | null>(null);
  const draftKey = (id: string) => `fsp-attempt-${id}`;
  const pending = () => Object.fromEntries(Object.entries(draft.current)
    .filter(([id, value]) => value !== (confirmed.current[id] ?? "")));
  const persist = () => {
    const changes = pending();
    dirtyRef.current = inFlight.current || Object.keys(changes).length > 0;
    if (!activeId.current) return;
    try {
      if (dirtyRef.current) localStorage.setItem(draftKey(activeId.current), JSON.stringify(draft.current));
      else localStorage.removeItem(draftKey(activeId.current));
      sessionStorage.removeItem(draftKey(activeId.current));
    } catch {
      setSaveStatus("Ответы не сохранены в браузере. Не закрывайте вкладку до подтверждения сервера.");
    }
  };
  const flush = () => {
    const attemptId = activeId.current;
    if (!attemptId || !dirtyRef.current) return;
    setSaveStatus("Есть несохранённые ответы. Сохраняем…");
    saveQueue.current = saveQueue.current.then(async () => {
      if (activeId.current !== attemptId) return;
      const changes = pending();
      if (!Object.keys(changes).length) return;
      try {
        inFlight.current = true;
        await api(`/me/attempts/${attemptId}/answers`, { answers: changes }, "PUT");
        if (activeId.current !== attemptId) return;
        inFlight.current = false;
        confirmed.current = { ...confirmed.current, ...changes };
        persist();
        setSaveStatus(dirtyRef.current ? "Есть несохранённые ответы. Сохраняем…" : "Ответы сохранены");
      } catch {
        inFlight.current = false;
        persist();
        setSaveStatus("Не удалось сохранить на сервере. Есть несохранённые ответы. При возврате в тест повторим сохранение; можно повторить сейчас.");
      }
    });
  };
  const restore = (a: Attempt) => {
    let local: Record<string, string> = {};
    try {
      const stored = JSON.parse(localStorage.getItem(draftKey(a.id)) ?? sessionStorage.getItem(draftKey(a.id)) ?? "{}");
      local = Object.fromEntries(Object.entries(stored).filter(([id, value]) =>
        typeof value === "string" && a.questions.some(q => q.id === id))) as Record<string, string>;
    } catch { /* Server copy remains available. */ }
    activeId.current = a.id;
    confirmed.current = { ...a.answers };
    draft.current = { ...a.answers, ...local };
    setAnswers(draft.current);
    persist();
    if (dirtyRef.current) flush();
    else setSaveStatus("Ответы сохранены");
  };
  const saveAnswer = (id: string, value: string) => {
    if (!current) return;
    draft.current = { ...draft.current, [id]: value };
    setAnswers(draft.current);
    persist();
    flush();
  };
  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirtyRef.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", beforeUnload);
    const online = () => flush();
    window.addEventListener("online", online);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      window.removeEventListener("online", online);
      dirtyRef.current = false;
    };
  }, []);
  useEffect(() => { if (visible) flush(); }, [visible]);
  const [availability, setAvailability] = useState<AssessmentAvailability | null>(null);
  const selectedLevel = availability?.levels.find((level) => level.grade === grade);
  const policy = current?.rubric ?? selectedLevel?.rubric;
  const questionCount = current ? current.questions.length : policy?.question_count;
  const loadAvailability = async () => {
    try {
      setAvailability(await api<AssessmentAvailability>("/me/assessment-availability"));
    } catch (error) {
      setAvailability(null);
      throw error;
    }
  };
  const ruleText = policy
    ? `Не менее ${policy.threshold}%` + (policy.core_min_correct
      ? ` и ${policy.core_min_correct} из ${policy.core_total} верных ответов по основному навыку (Python или SQL).`
      : ".")
    : "Правила теста загружаются.";
  const load = async () => {
    const [list] = await Promise.all([api<Attempt[]>("/me/attempts"), loadAvailability()]);
    setAttempts(list);
    const active = list.find(x => x.status === "active" && new Date(x.expires_at) > new Date());
    if (!current && active) restore(active);
    setCurrent(
      (a) =>
        (a ? list.find((x) => x.id === a.id) : null) ??
        list.find(
          (x) => x.status === "active" && new Date(x.expires_at) > new Date(),
        ) ??
        null,
    );
  };
  useEffect(() => {
    void act(load);
    const refreshAccess = () => { void loadAvailability().catch(() => {}); };
    const timer = window.setInterval(refreshAccess, 30000);
    window.addEventListener("focus", refreshAccess);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshAccess);
    };
  }, [profile.specialization]);
  return (
    <>
      <PageTitle
        kicker="Навыки с доказательствами"
        title="Подтвердите свой уровень"
        description={`${catalog.specializations[current?.specialization ?? profile.specialization]} · ${questionCount === undefined ? "Количество заданий загружается" : countLabel(questionCount, "task")} · ${policy ? countLabel(policy.minutes, "minute") : "Длительность загружается"}. ${ruleText}`}
      />
      <div className="notice subtle">
        <ShieldCheck size={18} />
        <span>
          Неудачная попытка не понижает грейд. Первый тест на уровень ниже можно
          выбрать сразу. Смена подтверждённого уровня — раз в 90 дней, пересдача
          того же — через 24 часа.
        </span>
      </div>
      {current ? (
        <div className="panel">
          <div className="section-heading">
            <h2>
              {current.grade} · {statusLabels[current.status]}
            </h2>
            <span>{countLabel(current.questions.length, "task")} · Методика {current.version}<br />
              {current.status === "active" ? "До" : "Срок попытки:"} {date(current.expires_at)}</span>
          </div>
          {current.result && (
            <div
              className={current.result.passed ? "result success" : "result"}
            >
              <strong>{current.result.score.toLocaleString("ru-RU")}%</strong>
              <div>
                <h3>
                  {current.result.passed
                    ? "Уровень подтверждён"
                    : "Пока не подтверждён"}
                </h3>
                <p>Верных ответов: {current.result.details.filter((d) => d.correct).length} из {current.questions.length}.</p>
                <p>
                  {current.result.passed
                    ? "Результат добавлен в профиль."
                    : `${ruleText} Прежний подтверждённый уровень, если он был, сохранён. Первый тест ниже можно выбрать сразу; смена подтверждённого уровня — через 90 дней.`}
                </p>
              </div>
            </div>
          )}
          {current.result && current.specialization === "data" && !["2.1.0", "2.1.1"].includes(current.version) && (
            <p className="notice subtle">Историческая попытка: результат сохранён по методике {current.version}. В старых дробных заданиях правило округления половины не было явно указано, поэтому 90,625 могло оцениваться как 90,62. Новые попытки используют явное округление половины вверх; прежний результат автоматически не пересчитывался.</p>
          )}
          <p role={saveStatus.startsWith("Не удалось") ? "alert" : "status"} className={saveStatus.startsWith("Не удалось") ? "save-failure" : undefined}>{saveStatus}</p>
          {dirtyRef.current && <button type="button" className="secondary" onClick={flush}>Повторить сохранение</button>}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const empty = current.questions.filter(q => !(answers[q.id] ?? "").trim()).length;
              if (empty && !window.confirm(
                `Не заполнено ${empty} из ${current.questions.length} заданий. Завершить тест? Пропуски будут засчитаны как неверные ответы. Пересдача этого уровня — через 24 часа.`,
              )) return;
              void act(async () => {
                await saveQueue.current;
                const result = await api<Attempt>(
                  `/me/attempts/${current.id}/submit`,
                  { answers, confirm_incomplete: empty > 0 },
                );
                confirmed.current = { ...draft.current };
                persist();
                activeId.current = null;
                setSaveStatus("Ответы сданы");
                setCurrent(result);
                await load();
                refresh();
              });
            }}
          >
            {current.questions.map((q, index) => (
              <div className="question" key={q.id}>
                <div className="question-label">
                  <span>Задание {index + 1} из {current.questions.length}</span>
                  <span>{catalog.skills[q.skill]}</span>
                </div>
                <pre>{q.text}</pre>
                {current.result ? (
                  <p
                    className={
                      current.result.details[index].correct
                        ? "correct"
                        : "incorrect"
                    }
                  >
                    {current.result.details[index].correct
                      ? "Верно"
                      : "Неверно"}{" "}
                    · Ответ: {current.result.details[index].expected}.{" "}
                    {current.result.details[index].explanation}
                  </p>
                ) : current.status === "active" ? (
                  <Field label={`Ответ на задание ${index + 1}`}>
                    <input
                      value={answers[q.id] ?? ""}
                      maxLength={100}
                      onChange={(e) =>
                        saveAnswer(q.id, e.target.value)
                      }
                      placeholder="Число"
                      inputMode="decimal"
                    />
                  </Field>
                ) : (
                  <p className="muted">
                    Время истекло. Ответы больше не принимаются.
                  </p>
                )}
              </div>
            ))}
            {current.status === "active" && (
              <button disabled={busy}>Завершить и узнать результат</button>
            )}
          </form>
          {(current.result || current.status === "expired") && (
            <button
              className="secondary"
              onClick={() => {
                setCurrent(null);
                setAnswers({});
              }}
            >
              К выбору уровня
            </button>
          )}
        </div>
      ) : (
        <div className="panel assessment-start">
          <div className="mini-icon">
            <BookOpen />
          </div>
          <div>
            <h2>Выберите уровень самостоятельно</h2>
            <p>
              Профиль: {profile.verified_grade ?? "грейд ещё не подтверждён"}.
              Задания первичного теста относятся к специализации.
            </p>
            {profile.next_grade_change && (
              <small>
                Следующая смена подтверждённого уровня:{" "}
                {date(profile.next_grade_change)}
              </small>
            )}
          </div>
          <div>
            <Field label="Уровень теста">
              <select value={grade} onChange={(e) => setGrade(e.target.value)}>
                {catalog.grades.map((g) => (
                  <option key={g} value={g}>{g}{availability ? (availability.levels.find((l) => l.grade === g)?.available ? " · доступен" : " · ограничен") : ""}</option>
                ))}
              </select>
            </Field>
            <div className="assessment-access" role="status" aria-live="polite">
              {!selectedLevel ? (
                <><p>Проверяем доступность теста…</p><button className="text-button" disabled={busy} onClick={() => void act(loadAvailability)}>Обновить доступность</button></>
              ) : selectedLevel.available ? <p>Тест {grade} доступен сейчас.</p> : (
                <>
                  <strong>Тест {grade} пока недоступен</strong>
                  {selectedLevel.reasons.map((r) => <p key={r.code}>{r.message}</p>)}
                  {selectedLevel.next_available_at && <p>Ближайшее начало: {date(selectedLevel.next_available_at)}.</p>}
                </>
              )}
            </div>
            <button
              disabled={busy || !selectedLevel?.available}
              onClick={() =>
                void act(async () => {
                  try {
                    const started = await api<Attempt>("/me/attempts", { grade });
                    setCurrent(started);
                    restore(started);
                  } finally {
                    await load();
                  }
                })
              }
            >
              Начать тест
              <ArrowRight size={17} />
            </button>
            {!profile.name && <small>Сначала заполните профиль.</small>}
          </div>
        </div>
      )}
      <div className="section-heading">
        <h2>История тестирования</h2>
        <span>{countLabel(attempts.length, "attempt")}</span>
      </div>
      {!attempts.length ? (
        <EmptyState
          title="Первый результат ещё впереди"
          description="После завершения здесь появится история и объяснение оценки."
        />
      ) : (
        <div className="panel history-list">
          {attempts.map((a) => (
            <div key={a.id}>
              <div>
                <strong>{catalog.specializations[a.specialization]} · {a.grade}</strong>
                <small>{countLabel(a.questions.length, "task")} · Методика {a.version}</small>
                <small>{date(a.created_at)}</small>
              </div>
              <span className="badge">{statusLabels[a.status]}</span>
              <strong>{a.result ? `${a.result.score.toLocaleString("ru-RU")}%` : "—"}</strong>
              <button
                className="text-button"
                onClick={() => {
                  setCurrent(a);
                  setAnswers({});
                }}
              >
                Посмотреть
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function CompanyForm({
  company: c,
  act,
  busy,
  saved,
}: Actions & { company: Company; saved: () => void }) {
  const [form, setForm] = useState({
    name: c.name,
    description: c.description,
    sector: c.sector,
    contact: c.contact,
  });
  return (
    <>
      <PageTitle
        kicker="Ваша команда"
        title="Профиль компании"
        description="Кандидат увидит название, предложение и способ связи до начала общения."
      />
      <form
        className="panel"
        onSubmit={(e) => {
          e.preventDefault();
          void act(async () => {
            await api("/me/company", form, "PUT");
            saved();
          });
        }}
      >
        {(["name", "sector", "contact"] as const).map((key, i) => (
          <Field
            key={key}
            label={
              [
                "Название компании",
                "Направление деятельности",
                "Способ связи с работодателем",
              ][i]
            }
          >
            <input
              required
              minLength={key === "contact" ? 5 : 2}
              maxLength={key === "contact" ? 300 : 160}
              value={form[key]}
              onChange={(e) =>
                setForm((f) => ({ ...f, [key]: e.target.value }))
              }
            />
          </Field>
        ))}
        <Field label="О компании и команде">
          <textarea
            required
            minLength={10}
            maxLength={3000}
            rows={5}
            value={form.description}
            onChange={(e) =>
              setForm((f) => ({ ...f, description: e.target.value }))
            }
          />
        </Field>
        <button disabled={busy}>Сохранить компанию</button>
      </form>
    </>
  );
}

function SearchPage({ catalog, act, busy, userId, openInvitations }: Actions & { userId: string; openInvitations: () => void }) {
  const key = `fsp-search-${userId}`;
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const loadInvitations = async () => setInvitations(await api<Invitation[]>("/invitations"));
  const latestInvitation = (id: string) => invitations.filter(i => i.candidate_id === id).sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
  const [criteria, setCriteria] = useSessionState<Criteria>(key + "-criteria", {
    title: "Python-разработчик в команду API",
    description:
      "Разработка и тестирование серверных API для продуктов команды.",
    specialization: "python",
    grades: ["Junior", "Middle", "Senior"],
    required_skills: ["python"],
    desired_skills: ["testing"],
    min_years: null,
    fsp_only: false,
    confirmed: true,
  });
  const [items, setItems] = useState<Profile[]>([]),
    [history, setHistory] = useState<
      { id: string; title: string; created_at: string }[]
    >([]),
    [snapshot, setSnapshot] = useState<Snapshot | null>(null),
    [selected, setSelected] = useState<Profile | null>(null),
    [bank, setBank] = useSessionState(key + "-bank", true);
  const [snapshotId, setSnapshotId] = useSessionState<string | null>(key + "-snapshot", null);
  const [filter, setFilter] = useSessionState(key + "-filter", {
      specialization: "",
      grade: "",
      skill: "",
      fsp_only: false,
    }),
    [initialLoading, setInitialLoading] = useState(true);
  const savedScroll = useRef(Number(sessionStorage.getItem(key + "-scroll") ?? 0));
  useEffect(() => {
    if (initialLoading) return;
    window.scrollTo(0, savedScroll.current);
    const save = () => { try { sessionStorage.setItem(key + "-scroll", String(window.scrollY)); } catch { /* Optional. */ } };
    window.addEventListener("scroll", save);
    return () => window.removeEventListener("scroll", save);
  }, [initialLoading]);
  const resultsRef = useRef<HTMLElement>(null);
  const showResults = () => window.requestAnimationFrame(() => {
    if (window.innerWidth <= 850) resultsRef.current?.scrollIntoView({behavior: "smooth", block: "start"});
  });
  const switchMode = (toBank: boolean) => {
    if (bank === toBank) return;
    void act(async () => {
      if (toBank) {
        const params = new URLSearchParams();
        Object.entries(filter).forEach(([k, v]) => { if (v) params.set(k, String(v)); });
        const rows = await api<Profile[]>("/candidates?" + params);
        setItems(rows); setSnapshot(null);
      } else if (snapshotId) {
        const saved = await api<Snapshot>("/searches/" + snapshotId);
        setSnapshot(saved); setItems(saved.items);
      } else { setSnapshot(null); setItems([]); }
      setBank(toBank);
    });
  };
  const loadHistory = async () => setHistory(await api("/searches"));
  useEffect(() => {
    void act(async () => {
      try {
        if (!bank && snapshotId) {
          const saved = await api<Snapshot>("/searches/" + snapshotId);
          setSnapshot(saved);
          setItems(saved.items);
        } else {
          const params = new URLSearchParams();
          Object.entries(filter).forEach(([k, v]) => { if (v) params.set(k, String(v)); });
          setItems(await api("/candidates?" + params));
        }
        await loadHistory();
        await loadInvitations();
      } finally {
        setInitialLoading(false);
      }
    });
  }, []);
  const search = (e: FormEvent) => {
    e.preventDefault();
    void act(async () => {
      const s = await api<Snapshot>("/searches", { ...criteria, confirmed: true });
      setSnapshot(s);
      setSnapshotId(s.id);
      window.scrollTo(0, 0);
      setItems(s.items);
      setBank(false);
      showResults();
      await loadHistory();
    });
  };
  return (
    <>
      <PageTitle
        kicker="Обратный подбор"
        title="Найдите нужные компетенции"
        description="Категория определяется тестом. Каждое основание подбора можно проверить — неизвестные сведения не считаются подтверждёнными."
      />
      <div className="search-layout">
        <aside className="search-form panel">
          <div className="segmented">
            <button
              className={!bank ? "selected" : ""}
              onClick={() => switchMode(false)}
            >
              По потребности
            </button>
            <button
              className={bank ? "selected" : ""}
              onClick={() => switchMode(true)}
            >
              Банк кандидатов
            </button>
          </div>
          {bank ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void act(async () => {
                  const params = new URLSearchParams();
                  Object.entries(filter).forEach(([k, v]) => {
                    if (v) params.set(k, String(v));
                  });
                  setItems(await api("/candidates?" + params.toString()));
                  setSnapshot(null);
                  showResults();
                });
              }}
            >
              <Field label="Специализация">
                <select
                  value={filter.specialization}
                  onChange={(e) =>
                    setFilter((f) => ({ ...f, specialization: e.target.value }))
                  }
                >
                  <option value="">Все направления</option>
                  {Object.entries(catalog.specializations).map(([id, n]) => (
                    <option key={id} value={id}>
                      {n}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Подтверждённый уровень">
                <select
                  value={filter.grade}
                  onChange={(e) =>
                    setFilter((f) => ({ ...f, grade: e.target.value }))
                  }
                >
                  <option value="">Все уровни</option>
                  {catalog.grades.map((g) => (
                    <option key={g}>{g}</option>
                  ))}
                </select>
              </Field>
              <Field label="Подтверждённый навык">
                <select
                  value={filter.skill}
                  onChange={(e) =>
                    setFilter((f) => ({ ...f, skill: e.target.value }))
                  }
                >
                  <option value="">Любой</option>
                  {Object.entries(catalog.skills).map(([id, n]) => (
                    <option key={id} value={id}>
                      {n}
                    </option>
                  ))}
                </select>
              </Field>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={filter.fsp_only}
                  onChange={(e) =>
                    setFilter((f) => ({ ...f, fsp_only: e.target.checked }))
                  }
                />
                С достижениями ФСП (демо)
              </label>
              <button className="full" disabled={busy}>
                Применить фильтры
              </button>
            </form>
          ) : (
            <form onSubmit={search}>
              <Field label="Специализация">
                <select
                  value={criteria.specialization}
                  onChange={(e) =>
                    setCriteria((c) => ({
                      ...c,
                      specialization: e.target.value,
                      required_skills:
                        e.target.value === "data" ? ["sql"] : ["python"],
                      desired_skills: [],
                    }))
                  }
                >
                  {Object.entries(catalog.specializations).map(([id, n]) => (
                    <option key={id} value={id}>
                      {n}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="field">
                <span>Допустимые уровни</span>
                <div className="skill-options">
                  {catalog.grades.map((g) => (
                    <label key={g}>
                      <input
                        type="checkbox"
                        checked={criteria.grades.includes(g)}
                        onChange={(e) =>
                          setCriteria((c) => ({
                            ...c,
                            grades: e.target.checked
                              ? [...c.grades, g]
                              : c.grades.filter((x) => x !== g),
                          }))
                        }
                      />
                      {g}
                    </label>
                  ))}
                </div>
              </div>
              <div className="field">
                <span>Навыки и важность</span>
                {(criteria.specialization === "data" ? ["sql", "statistics", "transactions"] : ["python", "testing", "http"]).map(skill => (
                  <Field key={skill} label={catalog.skills[skill]}>
                    <select value={criteria.required_skills.includes(skill) ? "required" : criteria.desired_skills.includes(skill) ? "desired" : "none"}
                      onChange={e => setCriteria(c => ({ ...c,
                        required_skills: [...c.required_skills.filter(s => s !== skill), ...(e.target.value === "required" ? [skill] : [])],
                        desired_skills: [...c.desired_skills.filter(s => s !== skill), ...(e.target.value === "desired" ? [skill] : [])],
                      }))}>
                      <option value="none">Не учитывать</option>
                      <option value="required">Обязательный</option>
                      <option value="desired">Желательный</option>
                    </select>
                  </Field>
                ))}
                <small>Docker и React пока не проверяются тестом.</small>
              </div>
              <details><summary>Контекст для обсуждения · не влияет на баллы</summary>
              <Field label="Название потребности">
                <input
                  required
                  minLength={3}
                  value={criteria.title}
                  onChange={(e) =>
                    setCriteria((c) => ({ ...c, title: e.target.value }))
                  }
                />
              </Field>
              <Field label="Задачи команды">
                <textarea
                  required
                  minLength={10}
                  rows={3}
                  value={criteria.description}
                  onChange={(e) =>
                    setCriteria((c) => ({ ...c, description: e.target.value }))
                  }
                />
              </Field>
              <p className="muted">
                Текст описывает контекст работы. На подбор влияют выбранные
                ниже требования; автоматического разбора текста пока нет.
                Docker и React можно указать, но текущий банк тестов их
                не проверяет — подтверждённых совпадений по ним не будет.
              </p>
              <Field label="Минимальный стаж · необязательно">
                <input
                  type="number"
                  min={0}
                  max={60}
                  value={criteria.min_years ?? ""}
                  onChange={(e) =>
                    setCriteria((c) => ({
                      ...c,
                      min_years:
                        e.target.value === "" ? null : Number(e.target.value),
                    }))
                  }
                />
              </Field>
              <p className="muted">
                Стаж указан со слов кандидата. Он сохраняется для обсуждения,
                не подтверждается тестом и не влияет на баллы или фильтрацию.
                Полное совпадение ниже относится только к обязательным навыкам.
              </p>
              </details>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={criteria.fsp_only}
                  onChange={(e) =>
                    setCriteria((c) => ({ ...c, fsp_only: e.target.checked }))
                  }
                />
                Только с достижениями ФСП (демо)
              </label>
              <button
                className="full"
                disabled={busy || !criteria.grades.length}
              >
                Сформировать подборку
                <Search size={17} />
              </button>
            </form>
          )}
          {!!history.length && (
            <div className="saved-searches">
              <h3>Сохранённые подборки</h3>
              {history.map((s) => (
                <button
                  key={s.id}
                  onClick={() =>
                    void act(async () => {
                      const r = await api<Snapshot>("/searches/" + s.id);
                      setSnapshot(r);
                      setSnapshotId(r.id);
                      setItems(r.items);
                      setCriteria(r.criteria);
                      setBank(false);
                    })
                  }
                >
                  {s.title}
                  <small>{date(s.created_at)}</small>
                </button>
              ))}
            </div>
          )}
        </aside>
        <section ref={resultsRef}>
          <div className="section-heading">
            <h2>{snapshot ? snapshot.criteria.title : "Банк кандидатов"}</h2>
            <span>{countLabel(items.length, "profile")}</span>
          </div>
          {snapshot && (
            <p className="muted">
              Сохранённая подборка на {date(snapshot.created_at)}. Уточнение запроса создаст
              новую подборку.
              {snapshot.hidden_count > 0 &&
                ` Скрыто после отзыва публикации: ${countLabel(snapshot.hidden_count, "profile")}.`}
            </p>
          )}
          {snapshot && <p className="muted">Применено: {catalog.specializations[snapshot.criteria.specialization]} · {snapshot.criteria.grades.join(", ")} · обязательные: {snapshot.criteria.required_skills.map(s => catalog.skills[s]).join(", ") || "нет"}.</p>}
          {snapshot && items.length > 0 && <p className="match-gap">
            {items.every(p => p.match?.required_skills_met === false) ? "Подтверждённых соответствий нет. " : ""}
            Полное покрытие обязательных навыков: {items.filter(p => p.match?.required_skills_met).length} из {items.length}.
            Внутри категории кандидаты идут по общему баллу; пробелы указаны в карточках.
          </p>}
          {!bank && snapshot && JSON.stringify(criteria) !== JSON.stringify(snapshot.criteria) && <p role="status">Параметры изменены — сформируйте новую подборку. Ниже сохранённый результат.</p>}
          {initialLoading ? (
            <Loading />
          ) : !items.length ? (
            <EmptyState
              title="Подходящих профилей пока нет"
              description="Попробуйте изменить специализацию или фильтры. Прежние подборки остаются в истории."
            />
          ) : (
            items.map((p, index) => (
              <div key={p.id}>
                {(index === 0 ||
                  p.verified_grade !== items[index - 1].verified_grade ||
                  p.specialization !== items[index - 1].specialization) && (
                  <h3 className="category-heading">
                    {catalog.specializations[p.specialization]}{" "}
                    <span>{p.verified_grade ?? "Не подтверждён"}</span>
                  </h3>
                )}
                <CandidateCard
                  profile={p}
                  catalog={catalog}
                  onInvite={() => setSelected(p)}
                      invitation={latestInvitation(p.id)}
                      openInvitations={openInvitations}
                />
              </div>
            ))
          )}
        </section>
      </div>
      {selected && (
        <InviteModal
          profile={selected}
          act={act}
          busy={busy}
          close={() => { setSelected(null); void act(loadInvitations); }}
        />
      )}
    </>
  );
}

function CandidateCard({
  profile: p,
  catalog,
  onInvite,
  invitation,
  openInvitations,
}: {
  profile: Profile;
  catalog: Catalog;
  onInvite: () => void;
  invitation?: Invitation;
  openInvitations: () => void;
}) {
  return (
    <article className="candidate-card">
      <div className="candidate-top">
        <div className="avatar large">
          <FileUser size={24} />
        </div>
        <div className="candidate-name">
          <h3>{p.display_name}</h3>
          <p>
            {p.experience_years === null
              ? "Стаж не указан"
              : `${countLabel(p.experience_years, "year")} · со слов кандидата`}
            {p.demo && " · демопрофиль"}
          </p>
        </div>
        <span className="badge violet">
          <ShieldCheck size={13} />
          {p.verified_grade ?? "Не подтверждён"}
        </span>
      </div>
      <div className="tags">
        {p.evidence.map((e) => (
          <span
            key={e.id}
            className={e.state === "met" ? "tag verified" : "tag"}
          >
            {e.state === "met" && <Check size={13} />} {catalog.skills[e.skill]}{" "}
            · тест {e.correct}/{e.total}
          </span>
        ))}
        {p.achievements.length > 0 && (
          <span className="tag sport">
            <Award size={13} />
            ФСП · демо
          </span>
        )}
      </div>
      {p.match && p.match.facts.length > 0 && (
        <div className="evidence">
          <h4>Почему в подборке</h4>
          {p.match.required_skills_met === false && <p className="match-gap">Неполное соответствие обязательным навыкам. Общий балл учитывает тест и ФСП; проверьте требования ниже перед приглашением.</p>}
          {p.match.facts.map((f, i) => (
            <div key={i}>
              <span className={"signal " + f.state} />
              <strong>{catalog.skills[f.skill] ?? "Стаж"}</strong>
              <span>
                {evidenceLabels[f.state] ?? evidenceLabels.unknown}
              </span>
              <small>
                {f.evidence
                  ? `Тест ${date(f.evidence.date)} · ${f.evidence.correct}/${f.evidence.total}`
                  : f.source === "self_report"
                    ? "Только самодекларация"
                    : "Доказательств нет"}
              </small>
            </div>
          ))}
          <small>
            Балл {p.match.score.toFixed(2)} = навыки {((p.match.breakdown.required_skills ?? 0) + (p.match.breakdown.desired_skills ?? 0)).toFixed(2)} + тест {(p.match.breakdown.test ?? 0).toFixed(2)} + ФСП {(p.match.breakdown.fsp ?? 0).toFixed(2)}. Сравнение только внутри категории.
          </small>
        </div>
      )}
      <details>
        <summary>Результаты и источники</summary>
        {p.match && <p>Формула: {p.match.methodology ?? "историческая (номер не сохранён)"}. Балл не является вероятностью найма. Без ФСП бонус равен нулю.</p>}
        {p.evidence.map((e) => (
          <p key={e.id}>
            {catalog.skills[e.skill]} · {e.correct}/{e.total} · {date(e.date)} ·
            версия {e.version}
          </p>
        ))}
        <p>
          Стек со слов кандидата:{" "}
          {p.skills.map((s) => catalog.skills[s]).join(", ") || "не указан"}
        </p>
        {p.task_last_reviewed_at && <p>Последняя оценка задания вашей компанией: {date(p.task_last_reviewed_at)}. Грейд не изменён.</p>}
        {p.contacts && (
          <p>
            Электронная почта: {p.contacts.email} · Телефон: {p.contacts.phone || "не указан"}
          </p>
        )}
      </details>
      {invitation && <p className="invitation-status">Приглашение: {statusLabels[invitation.status]} · {date(invitation.created_at)} <button className="text-button" onClick={openInvitations}>Открыть приглашения</button></p>}
      <div className="candidate-footer">
        <span>
          <LockKeyhole size={14} />
          {p.contacts ? "Контакты раскрыты вам" : "Контакты после согласия"}
        </span>
        <a
          className="icon-button"
          aria-label="Скачать PDF профиля"
          href={`/api/profiles/${p.id}/pdf`}
        >
          <Download size={17} />
        </a>
        <button onClick={onInvite}>
          Пригласить
          <ArrowRight size={15} />
        </button>
      </div>
    </article>
  );
}

function InviteModal({
  profile,
  act,
  busy,
  close,
}: {
  profile: Profile;
  act: Act;
  busy: boolean;
  close: () => void;
}) {
  const [description, setDescription] = useState(
      "Приглашаем обсудить работу в нашей команде. Задачи — развитие и поддержка продукта.",
    ),
    [minText, setMin] = useState("100000"),
    [maxText, setMax] = useState("160000"),
    [sent, setSent] = useState(false),
    [salaryError, setSalaryError] = useState(""),
    [requestId] = useState(() => crypto.randomUUID());
  const min = Number(minText), max = Number(maxText);
  const dialogRef = useRef<HTMLElement>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [companyError, setCompanyError] = useState("");
  const dirty = description !== "Приглашаем обсудить работу в нашей команде. Задачи — развитие и поддержка продукта." || min !== 100000 || max !== 160000;
  const dismiss = () => {
    if (!busy && (sent || !dirty || window.confirm("Закрыть приглашение? Изменения предложения и зарплаты не будут сохранены."))) close();
  };
  const dismissRef = useRef(dismiss);
  dismissRef.current = dismiss;
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null;
    const dialog = dialogRef.current!;
    const backdrop = dialog.parentElement!;
    // Disable every sibling along the ancestor chain, including the sidebar.
    const backgrounds: {node: HTMLElement; inert: boolean}[] = [];
    let node: HTMLElement = backdrop;
    while (node.parentElement && node !== document.body) {
      for (const sibling of node.parentElement.children) {
        if (sibling !== node && sibling instanceof HTMLElement) {
          backgrounds.push({node: sibling, inert: sibling.inert}); sibling.inert = true;
        }
      }
      node = node.parentElement;
    }
    (dialog.querySelector("textarea") as HTMLElement | null)?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); dismissRef.current(); }
      if (event.key === "Tab") {
        const targets = [...dialog.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]')].filter(el => el.getClientRects().length);
        const first = targets[0], last = targets[targets.length - 1];
        if (!first) { event.preventDefault(); dialog.focus(); }
        else if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", keydown);
    let cancelled = false;
    api<Company>("/me/company").then(value => { if (!cancelled) setCompany(value); }).catch(() => { if (!cancelled) setCompanyError("Не удалось загрузить компанию. Закройте приглашение и повторите попытку."); });
    return () => {
      cancelled = true;
      document.removeEventListener("keydown", keydown);
      backgrounds.forEach(({node, inert}) => { node.inert = inert; });
      if (trigger?.isConnected) trigger.focus();
    };
  }, []);
  useEffect(() => { if (sent) dialogRef.current?.querySelector<HTMLButtonElement>("button.close")?.focus(); }, [sent]);
  return (
    <div className="modal-backdrop">
      <section
        className="modal"
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="invite-title"
      >
        <button
          className="close"
          aria-label="Закрыть приглашение"
          onClick={dismiss}
          disabled={busy}
        >
          ×
        </button>
        <div className="eyebrow">Личное предложение</div>
        <h2 id="invite-title">
          {sent ? "Приглашение отправлено" : "Начните с открытых условий"}
        </h2>
        {sent ? (
          <>
            <p>
              Кандидат увидит вашу компанию, предложение и зарплату. Контакты
              откроются после принятия.
            </p>
            <button onClick={close}>Готово</button>
          </>
        ) : (
          <form noValidate
            onSubmit={(e) => {
              e.preventDefault();
              setSalaryError("");
              if (!Number.isInteger(min) || !Number.isInteger(max) || min > max || min <= 0 || max <= 0 || min > 10000000 || max > 10000000) {
                setSalaryError("Укажите зарплату от 1 до 10 000 000 ₽. Нижняя граница не должна превышать верхнюю.");
                e.currentTarget.querySelector<HTMLInputElement>('input[type="number"]')?.focus();
                return;
              }
              if (!e.currentTarget.reportValidity()) return;
              void act(async () => {
                await api("/invitations", {
                  candidate_id: profile.id,
                  request_id: requestId,
                  description: description.trim(),
                  salary_min: min,
                  salary_max: max,
                  currency: "RUB",
                });
                setSent(true);
              });
            }}
          >
            <p>
              {profile.display_name} ·{" "}
              {profile.verified_grade ?? "Уровень не подтверждён"}
            </p>
            <Field label="Предложение и задачи">
              <textarea
                required
                minLength={10}
                maxLength={3000}
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </Field>
            <div className="form-grid">
              <Field label="Зарплата от, ₽ / месяц">
                <input
                  required
                  type="number"
                  min={1}
                  max={10000000}
                  value={minText}
                  onChange={(e) => {
                    setMin(e.target.value);
                    setSalaryError("");
                  }}
                  aria-invalid={!!salaryError}
                  aria-describedby={salaryError ? "salary-error" : undefined}
                />
              </Field>
              <Field label="Зарплата до, ₽ / месяц">
                <input
                  required
                  type="number"
                  min={1}
                  max={10000000}
                  value={maxText}
                  onChange={(e) => { setMax(e.target.value); setSalaryError(""); }}
                  aria-invalid={!!salaryError}
                  aria-describedby={salaryError ? "salary-error" : undefined}
                />
              </Field>
            </div>
            {company && minText && maxText && <p className="invitation-preview">{company.name} · {min === max ? currency(min) : `${currency(min)} — ${currency(max)}`} / месяц до вычета налогов. Связь: {company.contact}.</p>}
            {companyError && <ErrorState message={companyError} />}
            {salaryError && <p id="salary-error" className="field-error" role="alert">{salaryError}</p>}
            <button className="full" disabled={busy || !company}>
              Отправить приглашение
              <Mail size={16} />
            </button>
          </form>
        )}
      </section>
    </div>
  );
}

function Invitations({
  user,
  profile,
  version,
  act,
  busy,
  refresh,
}: Actions & { user: User; profile: Profile | null; version: number }) {
  const [items, setItems] = useState<Invitation[]>([]),
    [chat, setChat] = useState<string | null>(null),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    void act(async () => {
      try {
        setItems(await api("/invitations"));
      } finally {
        setLoading(false);
      }
    });
  }, [version]);
  useEffect(() => {
    let stopped = false;
    let pending = false;
    const reload = async () => {
      if (pending || stopped) return;
      pending = true;
      try { const result = await api<Invitation[]>("/invitations"); if (!stopped) setItems(result); }
      catch { /* Keep the existing UI on transient network failure. Server still enforces access. */ }
      finally { pending = false; }
    };
    const timer = window.setInterval(reload, 15000);
    window.addEventListener("focus", reload);
    return () => { stopped = true; window.clearInterval(timer); window.removeEventListener("focus", reload); };
  }, [user.id]);
  return (
    <>
      <PageTitle
        kicker="От предложения к знакомству"
        title="Приглашения"
        description={
          user.role === "candidate"
            ? "Изучите условия до начала общения. При принятии контакты получит только пригласившая компания."
            : "Отслеживайте ответы кандидатов. После принятия откроются контакты и внутренний диалог."
        }
      />
      {loading ? (
        <EmptyState
          title="Загружаем приглашения"
          description="Секунда — подтягиваем актуальные статусы с сервера."
        />
      ) : !items.length ? (
        <EmptyState
          title="Пока нет приглашений"
          description={
            user.role === "candidate"
              ? !profile?.name
                ? "Заполните профиль, чтобы начать путь к предложениям."
                : !profile.verified_grade
                  ? "Подтвердите навыки тестом, чтобы попасть в категорию кандидатов."
                  : !profile.published || !profile.processing
                    ? "Ваш уровень подтверждён. Включите публикацию и согласие на обработку в профиле."
                    : "Ваш профиль опубликован, уровень подтверждён. Ожидайте приглашений работодателей; настройки видимости доступны в профиле."
              : "Откройте подбор, выберите кандидата и отправьте предложение с зарплатой."
          }
        />
      ) : (
        items.map((i) => (
          <article className="panel invitation" key={i.id}>
            <div className="section-heading">
              <h2>
                {user.role === "candidate" ? i.company_name : i.candidate_name}
              </h2>
              <span className={"badge " + i.status}>
                {statusLabels[i.status]}
              </span>
            </div>
            <div className="salary">
              {currency(i.salary_min)} — {currency(i.salary_max)} ₽
              <small>в месяц · до вычета налогов</small>
            </div>
            <p className="muted">Отправлено: {date(i.created_at)}</p>
            <p className="preserve">{i.description}</p>
            <p className="muted">Связь с работодателем: {i.employer_contact}</p>
            {i.contacts && (
              <div className="notice">
                <LockKeyhole size={16} />
                Электронная почта: {i.contacts.email} · Телефон: {i.contacts.phone || "не указан"}
              </div>
            )}
            <div className="actions">
              {user.role === "candidate" &&
                ["sent", "viewed"].includes(i.status) && (
                  <>
                    <button
                      disabled={busy}
                      onClick={() =>
                        void act(async () => {
                          await api(
                            "/invitations/" + i.id,
                            { status: "accepted" },
                            "PATCH",
                          );
                          refresh();
                        })
                      }
                    >
                      Принять и раскрыть контакты
                      <Check size={16} />
                    </button>
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() =>
                        void act(async () => {
                          await api(
                            "/invitations/" + i.id,
                            { status: "rejected" },
                            "PATCH",
                          );
                          refresh();
                        })
                      }
                    >
                      Отклонить
                    </button>
                    {i.status === "sent" && (
                      <button
                        className="text-button"
                        onClick={() =>
                          void act(async () => {
                            await api(
                              "/invitations/" + i.id,
                              { status: "viewed" },
                              "PATCH",
                            );
                            refresh();
                          })
                        }
                      >
                        Отметить просмотренным
                      </button>
                    )}
                  </>
                )}
              {i.chat_available && (
                <button
                  className="secondary"
                  onClick={() => setChat(chat === i.id ? null : i.id)}
                >
                  Открыть диалог
                  <Mail size={16} />
                </button>
              )}
            </div>
            {i.status === "accepted" && !i.chat_available && <p className="muted">Диалог недоступен: согласие на доступ к профилю отозвано.</p>}
            {chat === i.id && i.chat_available && (
              <Chat invitationId={i.id} act={act} busy={busy} />
            )}
          </article>
        ))
      )}
    </>
  );
}
function Chat({
  invitationId,
  act,
  busy,
}: {
  invitationId: string;
  act: Act;
  busy: boolean;
}) {
  const [messages, setMessages] = useState<
      { id: string; text: string; mine: boolean; created_at: string }[]
    >([]),
    [text, setText] = useState("");
  const [available, setAvailable] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const handleError = (error: unknown) => {
    if (error instanceof ApiError && [401, 403, 404, 409].includes(error.status)) {
      setAvailable(false);
      setMessages([]);
      setConnectionError("Доступ к диалогу закрыт. Проверьте статус приглашения.");
    } else {
      setConnectionError(error instanceof ApiError && error.status === 422
        ? "Проверьте сообщение: от 1 до 2000 символов без крайних пробелов."
        : "Не удалось связаться с сервером. Переписка и черновик сохранены на экране; повторите попытку.");
    }
  };
  const load = async () => {
    try {
      setMessages(await api("/invitations/" + invitationId + "/messages"));
      setAvailable(true);
      setConnectionError("");
    } catch (error) {
      handleError(error);
      throw error;
    }
  };
  useEffect(() => {
    setAvailable(false); setMessages([]); setText("");
    void act(load);
    const timer = window.setInterval(() => { void load().catch(() => {}); }, 15000);
    return () => window.clearInterval(timer);
  }, [invitationId]);
  return (
    <div className="chat">
      <div className="section-heading">
        <h3>Диалог</h3>
        <button className="text-button" onClick={() => void act(load)}>
          Обновить
        </button>
      </div>
      {messages.map((m) => (
        <div className={"message " + (m.mine ? "mine" : "")} key={m.id}>
          <span>{m.text}</span>
          <small>
            {m.mine ? "Вы" : "Собеседник"} · {date(m.created_at)}
          </small>
        </div>
      ))}
      {!available && <p role="status">Диалог недоступен или загружается. Отправка сообщений закрыта до проверки доступа.</p>}
      {connectionError && <p role="alert" className="field-error">{connectionError}</p>}
      {available && <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!text.trim()) return;
          void act(async () => {
            try {
              await api("/invitations/" + invitationId + "/messages", { text: text.trim() });
            } catch (error) {
              handleError(error);
              return;
            }
            setText("");
            await load();
          });
        }}
      >
        <Field label="Сообщение">
          <textarea
            required
            maxLength={2000}
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={2}
          />
        </Field>
        <button disabled={busy || !text.trim()}>Отправить</button>
      </form>}
    </div>
  );
}
