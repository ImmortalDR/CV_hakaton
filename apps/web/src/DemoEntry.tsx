import { useRef, useState } from "react";
import { api, type User } from "./api";

const AFTER_CALL =
  "https://github.com/ImmortalDR/CV_hakaton/blob/main/docs/delivery/AFTER_ORGANIZERS_CALL_2026-10-21.md";

export function DemoEntry({ onLogin }: { onLogin: (user: User) => void }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const pending = useRef(false);
  const login = async (account: "candidate" | "employer") => {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError("");
    try { onLogin(await api<User>("/auth/demo", { account })); }
    catch (e) { setError(e instanceof Error ? e.message : "Не удалось войти. Повторите попытку."); }
    finally { pending.current = false; setBusy(false); }
  };
  return <div className="demo-entry">
    <strong>Посмотреть без регистрации</strong>
    <div className="actions">
      <button type="button" className="secondary" disabled={busy} onClick={() => void login("candidate")}>Я кандидат</button>
      <button type="button" className="secondary" disabled={busy} onClick={() => void login("employer")}>Я работодатель</button>
    </div>
    <small>Для проверки двух ролей: кандидат — в обычном окне, работодатель — в инкогнито или другом браузере.</small>
    <small>Это общие демонстрационные аккаунты. После часа без действий в обоих аккаунтах пробная история очищается, исходные профили и примеры тестов восстанавливаются. Используйте только вымышленные данные.</small>
    <small className="after-call-note">
      Обновлено 21.10 после созвона с организаторами.{" "}
      <a href={AFTER_CALL} target="_blank" rel="noreferrer">Что изменилось — коротко</a>
    </small>
    {error && <p role="alert" className="field-error">{error}</p>}
  </div>;
}
