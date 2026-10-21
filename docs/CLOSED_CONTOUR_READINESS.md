# Closed contour readiness — не потерять

**Запрос Данилы (21.10.2026):** показать готовность внедрить у заказчика (инфбез / типовой контур / ПДн·ТД), не превращая демо в VPN-only.

## Где лежит (согласовано)

| Место | Значение |
|---|---|
| Ветка сдачи | `codex/fsp-mvp` · tip `792b024` · worktree `/root/hakaton-fsp-mvp` |
| Ветка сборки | `codex/closed-contour-readiness` · `/root/hakaton-contour` · tip `d146b9e` |
| GitHub | https://github.com/ImmortalDR/CV_hakaton/tree/codex/fsp-mvp |
| Handoff на GitHub | https://github.com/ImmortalDR/CV_hakaton/blob/codex/fsp-mvp/docs/delivery/closed_contour/HANDOFF_CLOSED_CONTOUR.md |
| Ярлык на сервере | `/root/CLOSED_CONTOUR_WHERE.md` |

## Читать сразу

1. [`delivery/closed_contour/HANDOFF_CLOSED_CONTOUR.md`](delivery/closed_contour/HANDOFF_CLOSED_CONTOUR.md)
2. [`closed_contour_2026-10-21/00_START_HERE.md`](closed_contour_2026-10-21/00_START_HERE.md)
3. [`delivery/closed_contour/READY_TO_DEPLOY_ONEPAGER.md`](delivery/closed_contour/READY_TO_DEPLOY_ONEPAGER.md)

## Бэкапы на диске сервера

- `/root/backups/closed-contour-readiness-full.bundle`
- `/root/backups/fsp-mvp-with-closed-contour.bundle` (может отставать на 1–2 docs-коммита; истина — ветка `codex/fsp-mvp`)
- `/root/backups/closed-contour-docs-20261021.tgz`

## Статус проверки (на момент push)

- Агентские must: PASS (`must_gaps=[]`)
- `CCV2` / human ★: ещё **HUMAN_ONLY / PENDING**
- Безусловное «готовы внедрить» до human ★ — **нельзя**
