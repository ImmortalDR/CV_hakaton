# ФСП · платформа обратного найма

Кандидаты подтверждают навыки, работодатели находят специалистов и отправляют предложения с зарплатой.
Код приложения — в ветке [codex/fsp-mvp](https://github.com/ImmortalDR/CV_hakaton/tree/codex/fsp-mvp).

## Попробовать локально

Нужны Git, Python 3, Docker с Compose v2 и интернет для первой сборки.

```bash
git clone --branch codex/fsp-mvp https://github.com/ImmortalDR/CV_hakaton.git
cd CV_hakaton
python3 scripts/configure.py
docker compose up -d --build --wait
```

Откройте **http://localhost:3080** на этой же машине и нажмите «Я кандидат» или «Я работодатель». Данные демонстрационные; отправка почты без настройки SMTP имитируется только при первой регистрации.

## Открыть сайт для пользователей

Для новой установки нужен Linux-сервер с Docker, Git и Python 3, домен, направленный на него, открытые порты 80/443 и SMTP с STARTTLS (587). [Подготовка сервера и домена](docs/PUBLIC_DEPLOYMENT.md).

### 1. Настроить

На сервере скачайте приложение и создайте `.env`:

```bash
git clone --branch codex/fsp-mvp https://github.com/ImmortalDR/CV_hakaton.git
cd CV_hakaton
python3 scripts/configure.py
```

Откройте `.env`. Сохраните строку `POSTGRES_PASSWORD`, остальные параметры замените на следующие. Вместо `jobs.example.org` и почтовых заглушек укажите свои данные:

```dotenv
DEMO_MODE=false
COMPOSE_PROFILES=https
HTTPS_HOST=jobs.example.org
PUBLIC_URL=https://jobs.example.org
COOKIE_SECURE=true
BIND_ADDRESS=127.0.0.1
SMTP_HOST=smtp.your-provider.example
SMTP_PORT=587
SMTP_TLS=true
SMTP_USER=your-login
SMTP_PASSWORD='your-password'
SMTP_FROM=noreply@your-company.ru
```

### 2. Запустить

```bash
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
```

Сайт запустится, HTTPS-сертификат будет получен автоматически.

### 3. Проверить

Замените домен своим:

```bash
curl --fail https://jobs.example.org/api/health
```

Ожидаемый ответ содержит `"status":"ok"` и `"demo":false`.

Откройте сайт с другого устройства. Зарегистрируйтесь, получите письмо, подтвердите почту и войдите. Для проверки подбора создайте кандидата и работодателя в разных браузерных профилях: кандидат заполняет профиль, проходит тест и включает публикацию; работодатель находит его и отправляет приглашение.

## Подробнее

- [Подготовка, диагностика, резервирование и обновление](docs/PUBLIC_DEPLOYMENT.md)
- [Документация и результаты проверок](https://github.com/ImmortalDR/CV_hakaton/tree/codex/fsp-mvp/docs/delivery)
- [Сценарий демонстрации и презентация](https://github.com/ImmortalDR/CV_hakaton/blob/codex/fsp-mvp/docs/delivery/FINAL_DEMO_AND_PITCH_2026-10-21.md)
