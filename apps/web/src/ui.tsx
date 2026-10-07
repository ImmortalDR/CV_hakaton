// Adapted from HireDesk ui.tsx (MIT, Abhinav Tarigoppula). See THIRD_PARTY_NOTICES.md.
import type { ReactNode } from "react";
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="error" role="alert">
      {message}
      {onRetry && (
        <button className="secondary" onClick={onRetry}>
          Повторить
        </button>
      )}
    </div>
  );
}
export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </div>
  );
}
export function Loading() {
  return (
    <div className="empty" role="status">
      Загружаем данные…
    </div>
  );
}
export const currency = (n: number) => new Intl.NumberFormat("ru-RU").format(n);
export const date = (s: string) =>
  new Date(s).toLocaleString("ru-RU", {
    timeZone: "Europe/Moscow",
    dateStyle: "medium",
    timeStyle: "short",
  });
export const statusLabels: Record<string, string> = {
  sent: "Отправлено",
  viewed: "Просмотрено",
  accepted: "Принято",
  rejected: "Отклонено",
  active: "В процессе",
  completed: "Завершено",
  expired: "Время истекло",
};
