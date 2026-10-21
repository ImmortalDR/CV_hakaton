# Closed contour readiness — не потерять (сервер)

**Запрос Данилы (21.10.2026):** показать готовность внедрить у заказчика (инфбез / типовой контур / ПДн·ТД), не превращая демо в VPN-only.

## Где в git на этом сервере

| Место | Путь / ветка |
|---|---|
| **Влито в сдачу** | ветка `codex/fsp-mvp` · worktree `/root/hakaton-fsp-mvp` · tip `83f1f70` |
| Ветка сборки | `codex/closed-contour-readiness` · `/root/hakaton-contour` |
| Ярлык в /root | `/root/CLOSED_CONTOUR_WHERE.md` |

## Читать сразу

1. [`delivery/closed_contour/HANDOFF_CLOSED_CONTOUR.md`](delivery/closed_contour/HANDOFF_CLOSED_CONTOUR.md)
2. [`closed_contour_2026-10-21/00_START_HERE.md`](closed_contour_2026-10-21/00_START_HERE.md)
3. [`delivery/closed_contour/READY_TO_DEPLOY_ONEPAGER.md`](delivery/closed_contour/READY_TO_DEPLOY_ONEPAGER.md)

## Бэкапы на диске сервера

- `/root/backups/closed-contour-readiness-full.bundle`
- `/root/backups/fsp-mvp-with-closed-contour.bundle`
- `/root/backups/closed-contour-docs-20261021.tgz`

Восстановить:
```bash
git clone /root/backups/closed-contour-readiness-full.bundle /tmp/cc-restore
cd /tmp/cc-restore && git checkout codex/closed-contour-readiness
```

**GitHub:** push с VPS без логина не настроен — на сервере пакет уже в `codex/fsp-mvp`.
