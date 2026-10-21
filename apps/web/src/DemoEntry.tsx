import { useRef, useState } from "react";
import { api, type User } from "./api";

const DAY_PROOF =
  "https://github.com/ImmortalDR/CV_hakaton/blob/main/docs/delivery/AFTER_ORGANIZERS_CALL_2026-10-21.md";
const FOR_JURY =
  "https://github.com/ImmortalDR/CV_hakaton/blob/main/docs/delivery/FOR_JURY.md#%D0%BF%D1%80%D0%BE%D0%B2%D0%B5%D1%80%D0%BA%D0%B8-%D0%BF%D0%BE%D1%81%D0%BB%D0%B5-%D0%B7%D0%B0%D0%BC%D0%B5%D1%87%D0%B0%D0%BD%D0%B8%D0%B9";

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
    <small>Это общие демонстрационные аккаунты. Действия сохраняются. Используйте только вымышленные данные.</small>
    <small className="after-call-note">
      После созвона с организаторами технический объём дня закрыт (11 из 12 пунктов плана).{" "}
      <a href={FOR_JURY} target="_blank" rel="noreferrer">3 проверки за ~5 минут</a>
      {" · "}
      <a href={DAY_PROOF} target="_blank" rel="noreferrer">доказательства и скриншоты «было»</a>
    </small>
    {error && <p role="alert" className="field-error">{error}</p>}
  </div>;
}
