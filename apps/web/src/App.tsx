import {
  useCallback,
  useEffect,
  useState,
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
  type Attempt,
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
  return (
    <label className="field">
      <span>{label}</span>
      {children}
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

export function App() {
  const [catalog, setCatalog] = useState(emptyCatalog),
    [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("overview"),
    [profile, setProfile] = useState<Profile | null>(null),
    [company, setCompany] = useState<Company | null>(null);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [version, setVersion] = useState(0);
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
    Promise.all([
      api<Catalog>("/catalog").then(setCatalog),
      api<User>("/auth/me")
        .then(setUser)
        .catch(() => {}),
    ]).finally(() => setLoading(false));
    if (location.hash.startsWith("#verify=")) {
      const token = location.hash.slice(8);
      history.replaceState(null, "", location.pathname);
      void act(async () => {
        await api("/auth/verify", { token });
        setNotice("Почта подтверждена. Войдите в кабинет.");
      });
    }
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
              <em>навыки</em>
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
            <Auth {...props} onLogin={signedIn} />
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
          ["fsp", "Достижения ФСП", Award],
        ] as const)
      : ([
          ["overview", "Обзор", LayoutDashboard],
          ["search", "Подбор кандидатов", Search],
          ["invitations", "Приглашения", Mail],
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
        <nav>
          {items.map(([key, label, Icon]) => (
            <button
              key={key}
              className={tab === key ? "active" : ""}
              onClick={() => {
                setTab(key);
                setError("");
                setNotice("");
              }}
            >
              <Icon size={19} />
              {label}
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
          {tab === "assessment" &&
            (profile ? (
              <Assessments {...props} profile={profile} />
            ) : (
              <Loading />
            ))}
          {tab === "search" && <SearchPage {...props} />}
          {tab === "invitations" && (
            <Invitations {...props} user={user} version={version} />
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

function Auth({
  act,
  busy,
  catalog,
  onLogin,
}: Actions & { onLogin: (u: User) => void }) {
  const [register, setRegister] = useState(false),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [role, setRole] = useState("candidate"),
    [consent, setConsent] = useState(false),
    [letter, setLetter] = useState(""),
    [message, setMessage] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    void act(async () => {
      if (register) {
        const r = await api<{
          demo_verification_url: string | null;
          message: string;
        }>("/auth/register", { email, password, role, processing: consent });
        setLetter(r.demo_verification_url ?? "");
        setMessage(r.message);
      } else onLogin(await api<User>("/auth/login", { email, password }));
    });
  };
  return (
    <>
      <div className="eyebrow">Начните с одного шага</div>
      <h2>{register ? "Создать аккаунт" : "Добро пожаловать"}</h2>
      <div className="segmented">
        <button
          className={!register ? "selected" : ""}
          onClick={() => {
            setRegister(false);
            setMessage("");
          }}
        >
          Вход
        </button>
        <button
          className={register ? "selected" : ""}
          onClick={() => {
            setRegister(true);
            setMessage("");
          }}
        >
          Регистрация
        </button>
      </div>
      <form onSubmit={submit}>
        {register && (
          <Field label="Я на платформе как">
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="candidate">Кандидат</option>
              <option value="employer">Работодатель</option>
            </select>
          </Field>
        )}
        <Field label="Электронная почта">
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.org"
          />
        </Field>
        <Field label="Пароль">
          <input
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            required
            minLength={register ? 10 : 1}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={register ? "Не менее 10 символов" : "Ваш пароль"}
          />
        </Field>
        {register && (
          <label className="checkline">
            <input
              type="checkbox"
              required
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            <span>
              Согласен на обработку данных для профиля, тестирования и
              приглашений. Публикацию включу отдельно. В демо использую
              вымышленные данные.
            </span>
          </label>
        )}
        <button disabled={busy} className="full">
          {busy
            ? "Подождите…"
            : register
              ? "Создать аккаунт"
              : "Войти в кабинет"}
          <ArrowRight size={17} />
        </button>
      </form>
      {message && (
        <p className="notice" role="status">
          {message}
        </p>
      )}
      {letter && (
        <div className="demo-letter">
          <strong>Демонстрационное письмо</strong>
          <p>
            Реальное письмо не отправлялось. На этом стенде подтверждение адреса
            имитируется.
          </p>
          <button
            className="secondary"
            disabled={busy}
            onClick={() =>
              void act(async () => {
                await api("/auth/verify", {
                  token: letter.split("#verify=")[1],
                });
                setLetter("");
                setMessage("Почта подтверждена. Войдите с указанным паролем.");
                setRegister(false);
              })
            }
          >
            Подтвердить почту
          </button>
        </div>
      )}
      {catalog.demo && (
        <div className="demo-entry">
          <span>Посмотреть без регистрации</span>
          <div>
            <button
              className="secondary"
              disabled={busy}
              onClick={() =>
                void act(async () =>
                  onLogin(
                    await api<User>("/auth/demo", { account: "candidate" }),
                  ),
                )
              }
            >
              Я кандидат
            </button>
            <button
              className="secondary"
              disabled={busy}
              onClick={() =>
                void act(async () =>
                  onLogin(
                    await api<User>("/auth/demo", { account: "employer" }),
                  ),
                )
              }
            >
              Я работодатель
            </button>
          </div>
          <small>Общие демоаккаунты. Не вводите персональные данные.</small>
        </div>
      )}
    </>
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
              ? p?.verified_grade
                ? "Ваш уровень подтверждён тестом. Работодатели могут найти вас в соответствующей категории."
                : "Четыре коротких задания помогут подтвердить выбранный уровень. ФСП ID для этого не нужен."
              : "Никакого потока случайных откликов: выбирайте подтверждённую категорию и смотрите основания подбора."}
          </p>
          <button
            className="white"
            onClick={() =>
              navigate(
                candidate ? (p?.name ? "assessment" : "profile") : "search",
              )
            }
          >
            {candidate
              ? p?.name
                ? "Перейти к тестированию"
                : "Заполнить профиль"
              : "Подобрать кандидатов"}
            <ArrowRight size={18} />
          </button>
        </div>
        <div className="orb">
          <ShieldCheck size={78} />
          <span>
            навыки
            <br />
            подтверждены
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
}: Actions & { profile: Profile }) {
  const [attempts, setAttempts] = useState<Attempt[]>([]),
    [current, setCurrent] = useState<Attempt | null>(null),
    [answers, setAnswers] = useState<Record<string, string>>({}),
    [grade, setGrade] = useState(profile.claimed_grade ?? "Junior");
  const load = async () => {
    const list = await api<Attempt[]>("/me/attempts");
    setAttempts(list);
    setCurrent(
      (a) =>
        a ??
        list.find(
          (x) => x.status === "active" && new Date(x.expires_at) > new Date(),
        ) ??
        null,
    );
  };
  useEffect(() => {
    void act(load);
  }, []);
  return (
    <>
      <PageTitle
        kicker="Навыки с доказательствами"
        title="Подтвердите свой уровень"
        description={`${catalog.specializations[profile.specialization]} · 4 задания · 30 минут. Для новых тестов: не менее 75% и оба задания по основному навыку (Python или SQL) решены верно.`}
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
            <span>До {date(current.expires_at)}</span>
          </div>
          {current.result && (
            <div
              className={current.result.passed ? "result success" : "result"}
            >
              <strong>{current.result.score}%</strong>
              <div>
                <h3>
                  {current.result.passed
                    ? "Уровень подтверждён"
                    : "Пока не подтверждён"}
                </h3>
                <p>
                  {current.result.passed
                    ? "Результат добавлен в профиль."
                    : "Для новых тестов нужны не менее 75% и оба верных ответа по основному навыку. Прежний подтверждённый уровень, если он был, сохранён. Первый тест ниже можно выбрать сразу; смена подтверждённого уровня — через 90 дней."}
                </p>
              </div>
            </div>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void act(async () => {
                const result = await api<Attempt>(
                  `/me/attempts/${current.id}/submit`,
                  { answers },
                );
                setCurrent(result);
                await load();
                refresh();
              });
            }}
          >
            {current.questions.map((q, index) => (
              <div className="question" key={q.id}>
                <div className="question-label">
                  <span>Задание {index + 1} из 4</span>
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
                        setAnswers((v) => ({ ...v, [q.id]: e.target.value }))
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
                  <option key={g}>{g}</option>
                ))}
              </select>
            </Field>
            <button
              disabled={busy || !profile.name || !profile.processing}
              onClick={() =>
                void act(async () => {
                  setCurrent(await api<Attempt>("/me/attempts", { grade }));
                  setAnswers({});
                  await load();
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
        <span>{attempts.length} попыток</span>
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
                <strong>{a.grade}</strong>
                <small>{date(a.created_at)}</small>
              </div>
              <span className="badge">{statusLabels[a.status]}</span>
              <strong>{a.result ? `${a.result.score}%` : "—"}</strong>
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

function SearchPage({ catalog, act, busy }: Actions) {
  const [criteria, setCriteria] = useState<Criteria>({
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
    [bank, setBank] = useState(true);
  const [filter, setFilter] = useState({
      specialization: "",
      grade: "",
      skill: "",
      fsp_only: false,
    }),
    [initialLoading, setInitialLoading] = useState(true);
  const loadHistory = async () => setHistory(await api("/searches"));
  useEffect(() => {
    void act(async () => {
      try {
        setItems(await api("/candidates"));
        await loadHistory();
      } finally {
        setInitialLoading(false);
      }
    });
  }, []);
  const search = (e: FormEvent) => {
    e.preventDefault();
    void act(async () => {
      const s = await api<Snapshot>("/searches", criteria);
      setSnapshot(s);
      window.scrollTo(0, 0);
      setItems(s.items);
      setBank(false);
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
              onClick={() => setBank(false)}
            >
              По потребности
            </button>
            <button
              className={bank ? "selected" : ""}
              onClick={() => setBank(true)}
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
                <span>Обязательные навыки</span>
                <Skills
                  catalog={catalog}
                  values={criteria.required_skills}
                  onChange={(v) =>
                    setCriteria((c) => ({ ...c, required_skills: v }))
                  }
                />
              </div>
              <div className="field">
                <span>Желательные навыки</span>
                <Skills
                  catalog={catalog}
                  values={criteria.desired_skills}
                  onChange={(v) =>
                    setCriteria((c) => ({ ...c, desired_skills: v }))
                  }
                />
              </div>
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
              <label className="checkline">
                <input
                  type="checkbox"
                  required
                  checked={criteria.confirmed}
                  onChange={(e) =>
                    setCriteria((c) => ({ ...c, confirmed: e.target.checked }))
                  }
                />
                Подтверждаю выбранные структурированные требования
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
        <section>
          <div className="section-heading">
            <h2>{snapshot ? snapshot.criteria.title : "Банк кандидатов"}</h2>
            <span>{items.length} профилей</span>
          </div>
          {snapshot && (
            <p className="muted">
              Сохранено {date(snapshot.created_at)}. Уточнение запроса создаст
              новую подборку.
              {snapshot.hidden_count > 0 &&
                ` ${snapshot.hidden_count} профилей скрыты после отзыва публикации.`}
            </p>
          )}
          {initialLoading ? (
            <Loading />
          ) : !items.length ? (
            <EmptyState
              title="Подходящих профилей пока нет"
              description="Попробуйте изменить специализацию или фильтры. Прежние подборки остаются в истории."
            />
          ) : snapshot ? (
            (() => {
              const required = snapshot.criteria.required_skills;
              const full = items.filter((p) =>
                p.match?.required_skills_met ?? required.every((skill) =>
                  p.match?.facts.some(
                    (f) => f.skill === skill && f.state === "met",
                  ),
                ),
              );
              const partial = items.filter(
                (p) => !full.some((f) => f.id === p.id),
              );
              const renderList = (list: Profile[]) =>
                list.map((p, index) => (
                  <div key={p.id}>
                    {(index === 0 ||
                      p.verified_grade !== list[index - 1].verified_grade ||
                      p.specialization !== list[index - 1].specialization) && (
                      <h3 className="category-heading">
                        {catalog.specializations[p.specialization]}{" "}
                        <span>{p.verified_grade ?? "Не подтверждён"}</span>
                      </h3>
                    )}
                    <CandidateCard
                      profile={p}
                      catalog={catalog}
                      onInvite={() => setSelected(p)}
                    />
                  </div>
                ));
              return (
                <>
                  <h3 className="category-heading">
                    Все обязательные навыки подтверждены{" "}
                    <span>{full.length}</span>
                  </h3>
                  {full.length ? (
                    renderList(full)
                  ) : (
                    <EmptyState
                      title="Подтверждённых соответствий нет"
                      description="Ни у кого в этой подборке нет всех обязательных навыков со статусом «подтверждено». Ниже — частичные совпадения, если они есть."
                    />
                  )}
                  {!!partial.length && (
                    <>
                      <h3 className="category-heading">
                        Частичное соответствие{" "}
                        <span>{partial.length}</span>
                      </h3>
                      <p className="muted">
                        Здесь обязательные навыки не проверены или не
                        подтверждены тестом. Не считайте таких кандидатов
                        подтверждёнными по всем требованиям.
                      </p>
                      {renderList(partial)}
                    </>
                  )}
                </>
              );
            })()
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
          close={() => setSelected(null)}
        />
      )}
    </>
  );
}

function CandidateCard({
  profile: p,
  catalog,
  onInvite,
}: {
  profile: Profile;
  catalog: Catalog;
  onInvite: () => void;
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
              : `${p.experience_years} лет · со слов кандидата`}
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
          {p.match.facts.map((f, i) => (
            <div key={i}>
              <span className={"signal " + f.state} />
              <strong>{catalog.skills[f.skill] ?? "Стаж"}</strong>
              <span>
                {f.state === "met"
                  ? "Подтверждено"
                  : f.state === "unmet"
                    ? "Критерий теста не выполнен"
                    : "Не проверено"}
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
            Индекс соответствия {p.match.score.toFixed(0)} · ФСП +
            {p.match.breakdown.fsp ?? 0}. Сравнение только внутри категории.
          </small>
        </div>
      )}
      <details>
        <summary>Результаты и источники</summary>
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
        {p.contacts && (
          <p>
            {p.contacts.email} · {p.contacts.phone}
          </p>
        )}
      </details>
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
    [min, setMin] = useState(100000),
    [max, setMax] = useState(160000),
    [sent, setSent] = useState(false),
    [requestId] = useState(() => crypto.randomUUID());
  return (
    <div className="modal-backdrop">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="invite-title"
      >
        <button
          className="close"
          aria-label="Закрыть приглашение"
          onClick={close}
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
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (min > max || min <= 0 || max <= 0) {
                window.alert(
                  "Вилка зарплаты: «от» и «до» должны быть больше 0, и «от» не больше «до».",
                );
                return;
              }
              void act(async () => {
                await api("/invitations", {
                  candidate_id: profile.id,
                  request_id: requestId,
                  description,
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
                  value={min}
                  onChange={(e) => {
                    const next = Number(e.target.value);
                    setMin(next);
                    if (next > max) setMax(next);
                  }}
                />
              </Field>
              <Field label="Зарплата до, ₽ / месяц">
                <input
                  required
                  type="number"
                  min={min}
                  max={10000000}
                  value={max}
                  onChange={(e) => setMax(Number(e.target.value))}
                />
              </Field>
            </div>
            <small>
              До вычета налогов. Название компании и способ связи добавятся из
              её профиля.
            </small>
            <button className="full" disabled={busy}>
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
  version,
  act,
  busy,
  refresh,
}: Actions & { user: User; version: number }) {
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
              ? "Подтвердите навыки и опубликуйте профиль, чтобы работодатели могли вас найти."
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
            <p className="preserve">{i.description}</p>
            <p className="muted">Связь с работодателем: {i.employer_contact}</p>
            {i.contacts && (
              <div className="notice">
                <LockKeyhole size={16} />
                Контакты: {i.contacts.email} · {i.contacts.phone}
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
              {i.status === "accepted" && (
                <button
                  className="secondary"
                  onClick={() => setChat(chat === i.id ? null : i.id)}
                >
                  Открыть диалог
                  <Mail size={16} />
                </button>
              )}
            </div>
            {chat === i.id && (
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
  const load = async () =>
    setMessages(await api("/invitations/" + invitationId + "/messages"));
  useEffect(() => {
    void act(load);
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
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void act(async () => {
            await api("/invitations/" + invitationId + "/messages", { text });
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
        <button disabled={busy}>Отправить</button>
      </form>
    </div>
  );
}
