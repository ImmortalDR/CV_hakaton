# Запуск Astra: закрытый контур

**Сервер:** `root@85.137.26.131`  
**SSH с этой машины (VPN):** `ssh -4 -o BindAddress=$(ipconfig getifaddr en0) root@85.137.26.131`  
**Канон на диске:** `/root/hakaton/docs/closed_contour_2026-10-21/`  
**Worktree:** `/root/hakaton-contour` · ветка `codex/closed-contour-readiness`

## Запуск сборки

```bash
ssh -4 -o BindAddress=$(ipconfig getifaddr en0) root@85.137.26.131
# на сервере:
cd /root/hakaton-contour 2>/dev/null || cd /root/hakaton
nohup codex exec -m gpt-6-astra --dangerously-bypass-approvals-and-sandbox \
  -C /root/hakaton-contour \
  - < /root/hakaton/docs/closed_contour_2026-10-21/prompts/ASTRA_CLOSED_CONTOUR.md \
  > /tmp/astra-closed-contour-$(date +%Y%m%d-%H%M%S).log 2>&1 &
```

Если worktree ещё нет — Astra создаст его по W0 промпта; для первого запуска можно стартовать из `/root/hakaton` с тем же промптом (W0 первым делом сделает worktree), указав `-C /root/hakaton`.

## Смотреть прогресс

```bash
tail -f /tmp/astra-closed-contour-*.log
# или
codex resume --last
```

## Не делать

- Не запускать параллельно второй Astra на Stage A в том же worktree.  
- Не давать промпт Stage A verify вместо этого.
