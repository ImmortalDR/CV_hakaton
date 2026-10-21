import { useEffect, useState } from "react";
import { api, type User } from "./api";

const key = "fsp-demo-run";
export function demoToken() {
  try { return sessionStorage.getItem(key) ?? ""; } catch { return ""; }
}
function storeToken(token: string) {
  try { if (token) sessionStorage.setItem(key, token); else sessionStorage.removeItem(key); } catch { /* Current screen still works. */ }
}
export function DemoLink({ token }: { token: string }) {
  const [copied, setCopied] = useState(false);
  const link = `${location.origin}/login#demo=${encodeURIComponent(token)}`;
  return <div className="demo-share">
    <label>Ссылка на этот демопроход<input aria-label="Ссылка на этот демопроход" readOnly value={link} onFocus={e => e.target.select()} /></label>
    <button type="button" className="secondary" onClick={() => {
      void navigator.clipboard?.writeText(link).then(() => setCopied(true)).catch(() => setCopied(false));
    }}>{copied ? "Ссылка скопирована" : "Скопировать ссылку"}</button>
    <small>Откройте эту ссылку в инкогнито или другом браузере и выберите вторую роль. Используйте только вымышленные данные.</small>
  </div>;
}
export function DemoEntry({ onLogin }: { onLogin: (user: User) => void }) {
  const [token, setToken] = useState(() => {
    const incoming = new URLSearchParams(location.hash.slice(1)).get("demo");
    return incoming ?? demoToken();
  });
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  useEffect(() => {
    storeToken(token);
    if (location.hash.startsWith("#demo=")) history.replaceState(history.state, "", location.pathname + location.search);
  }, [token]);
  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setError("");
    try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : "Не удалось открыть демопроход"); }
    finally { setBusy(false); }
  };
  return <div className="demo-entry">
    <strong>{token ? "Ваш отдельный демопроход" : "Посмотреть без регистрации"}</strong>
    <button className="full" disabled={busy} onClick={() => void run(async () => {
      const result = await api<{ token: string }>("/auth/demo-runs", {});
      storeToken(result.token); setToken(result.token);
    })}>{token ? "Начать ещё один демопроход" : "Начать новый демопроход"}</button>
    <small>Новый проход: готовая история тестов, опубликованный Junior, пустые приглашения и диалоги. Предыдущие проходы сохраняются отдельно.</small>
    {token && <DemoLink token={token} />}
    <div className="actions">{(["candidate", "employer"] as const).map(account =>
      <button key={account} className="secondary" disabled={busy} onClick={() => void run(async () => {
        onLogin(await api<User>("/auth/demo", { account, run_token: token || null }));
      })}>{account === "candidate" ? "Я кандидат" : "Я работодатель"}</button>)}</div>
    {!token && <small>Кнопки ролей без нового прохода открывают общие демоаккаунты с действиями прошлых посетителей.</small>}
    {token && <button className="text-button" disabled={busy} onClick={() => { storeToken(""); setToken(""); }}>Перейти к общим демоаккаунтам</button>}
    {error && <p role="alert" className="field-error">{error}</p>}
  </div>;
}
