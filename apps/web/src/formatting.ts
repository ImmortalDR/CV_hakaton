const plural = new Intl.PluralRules("ru-RU");
export const countForms = {
  year: ["год", "года", "лет"],
  attempt: ["попытка", "попытки", "попыток"],
  task: ["задание", "задания", "заданий"],
  minute: ["минута", "минуты", "минут"],
  profile: ["профиль", "профиля", "профилей"],
} as const;

export function countLabel(value: number, kind: keyof typeof countForms): string {
  const category = plural.select(value);
  const form = category === "one" ? 0 : category === "few" ? 1 : 2;
  return `${new Intl.NumberFormat("ru-RU").format(value)} ${countForms[kind][form]}`;
}

export const evidenceLabels: Record<string, string> = {
  met: "Подтверждено",
  unmet: "Требование не выполнено",
  unknown: "Не проверено",
};
