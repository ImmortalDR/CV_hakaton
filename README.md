# ФСП · платформа обратного найма

Код, инструкции и материалы сдачи находятся в рабочей ветке **[codex/fsp-mvp](https://github.com/ImmortalDR/CV_hakaton/tree/codex/fsp-mvp)**. Основная ветка сохранена как указатель; слияние реализации не выполнялось.

```bash
git clone --branch codex/fsp-mvp https://github.com/ImmortalDR/CV_hakaton.git
cd CV_hakaton
python3 scripts/configure.py
docker compose up -d --build --wait
```

Открыть http://localhost:3080. Демонстрационные данные вымышлены; реальные SMTP и ФСП не подключены.

- [README и запуск](https://github.com/ImmortalDR/CV_hakaton/blob/codex/fsp-mvp/README.md)
- [Проверки и ограничения](https://github.com/ImmortalDR/CV_hakaton/blob/codex/fsp-mvp/docs/delivery/VALIDATION.md)
- [Матрица требований](https://github.com/ImmortalDR/CV_hakaton/blob/codex/fsp-mvp/docs/delivery/REQUIREMENTS_STATUS.md)
- [Презентация и видео](https://github.com/ImmortalDR/CV_hakaton/tree/codex/fsp-mvp/demo)
- [PDF/DOCX и OpenAPI](https://github.com/ImmortalDR/CV_hakaton/tree/codex/fsp-mvp/docs/delivery)

36 unit/integration тестов и сквозной сценарий Chromium пройдены. Качество подбора измерено только на авторской синтетической выборке; экспертный пилот на людях предстоит.
