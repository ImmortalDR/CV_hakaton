import { useSyncExternalStore } from "react";

// Only screen addresses belong in history. Never tokens, answers or API actions.
export type AuthMode = "login" | "register" | "forgot" | "verify" | "reset";
export const authPaths: Record<AuthMode, string> = {
  login: "/login", register: "/register", forgot: "/forgot-password",
  verify: "/verify-email", reset: "/reset-password",
};
export const sections = ["overview", "profile", "assessment", "invitations", "tasks", "fsp", "search", "company"];
export function allowedSection(path: string, role: string) {
  const section = path.split("?")[0].slice(1);
  return (role === "candidate"
    ? ["overview", "profile", "assessment", "invitations", "tasks", "fsp"]
    : ["overview", "search", "invitations", "tasks", "company"]).includes(section);
}
export function authMode(path: string): AuthMode {
  return (Object.entries(authPaths).find(([, value]) => value === path)?.[0] as AuthMode) ?? "login";
}
const address = () => location.pathname + location.search;
type Entry = { index: number; scroll: number };
const initial: Entry = history.state?.fspNavigation ?? { index: 0, scroll: 0 };
let entry = initial;
const initialHref = address();
let href = initialHref;
let restoring = false;
type Guard = (from: string, to: string) => boolean;
const guards = new Set<Guard>();
const guard: Guard = (from, to) => [...guards].every(check => check(from, to));
const listeners = new Set<() => void>();
const positions = new Map<number, number>();
history.replaceState({ fspNavigation: entry }, "");
history.scrollRestoration = "manual";
let stopScrollRestore = () => {};
function publish(scroll: number) {
  listeners.forEach(fn => fn());
  restoreScroll(scroll);
}
function restoreScroll(scroll: number) {
  stopScrollRestore();
  // Data-backed screens can be taller only after their request finishes.
  let stopped = false;
  const restore = () => {
    if (stopped) return;
    window.scrollTo(0, scroll);
    if (document.documentElement.scrollHeight - innerHeight >= scroll) stop();
  };
  const observer = new ResizeObserver(restore);
  const stop = () => {
    stopped = true; observer.disconnect(); clearTimeout(timer);
    window.removeEventListener("wheel", stop); window.removeEventListener("touchstart", stop);
    window.removeEventListener("keydown", stop);
  };
  const timer = window.setTimeout(stop, 5000);
  observer.observe(document.body);
  window.addEventListener("wheel", stop, { passive: true });
  window.addEventListener("touchstart", stop, { passive: true });
  window.addEventListener("keydown", stop);
  requestAnimationFrame(restore);
  stopScrollRestore = stop;
}
export function restoreInitialScroll() {
  if (href === initialHref && entry.index === initial.index && initial.scroll > 0) restoreScroll(initial.scroll);
}
export function setNavigationGuard(next: Guard) {
  guards.add(next);
  return () => { guards.delete(next); };
}
export function navigate(to: string, options: { replace?: boolean; bypass?: boolean } = {}) {
  const url = new URL(to, location.origin);
  if (url.origin !== location.origin) throw new Error("Navigation must stay on this site");
  const next = url.pathname + url.search;
  if (restoring) return false;
  if (next === href && !location.hash) return true;
  if (!options.bypass && !guard(href, next)) return false;
  positions.set(entry.index, window.scrollY);
  history.replaceState({ fspNavigation: { ...entry, scroll: window.scrollY } }, "");
  entry = { index: entry.index + (options.replace ? 0 : 1), scroll: 0 };
  history[options.replace ? "replaceState" : "pushState"]({ fspNavigation: entry }, "", next);
  href = next;
  publish(0);
  return true;
}
window.addEventListener("popstate", event => {
  const target: Entry | undefined = event.state?.fspNavigation;
  if (restoring) { restoring = false; return; }
  const next = address();
  // Email links are handled by App's hash handler; do not put secrets in state.
  if (location.hash.startsWith("#reset=") || location.hash.startsWith("#verify=")) {
    positions.set(entry.index, window.scrollY);
    entry = target ?? { index: entry.index + 1, scroll: 0 };
    return;
  }
  if (!guard(href, next)) {
    if (target && target.index !== entry.index) {
      restoring = true;
      history.go(entry.index - target.index);
    } else history.replaceState({ fspNavigation: entry }, "", href);
    return;
  }
  positions.set(entry.index, window.scrollY);
  entry = target ?? { index: entry.index + 1, scroll: 0 };
  history.replaceState({ fspNavigation: entry }, "");
  href = next;
  publish(positions.get(entry.index) ?? entry.scroll);
});
window.addEventListener("pagehide", () => {
  history.replaceState({ fspNavigation: { ...entry, scroll: window.scrollY } }, "");
});
export function useLocation() {
  const value = useSyncExternalStore(
    fn => { listeners.add(fn); return () => { listeners.delete(fn); }; },
    () => href,
  );
  const [path, search = ""] = value.split("?");
  return { href: value, path, params: new URLSearchParams(search) };
}
export function screenUrl(section: string, values: Record<string, string | null | undefined> = {}) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, value); });
  return `/${section}${params.size ? "?" + params : ""}`;
}
