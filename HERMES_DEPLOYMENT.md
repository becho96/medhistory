# Hermes Agent — развёртывание (NL VPS)

Self-hosted **Hermes Agent** ([NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)) на отдельном зарубежном VPS. Gateway + веб-дашборд работают в Docker; основной доступ — через Telegram-бота `@ironbor_hermes_bot`, расширенный доступ к личному Telegram — через Telethon userbot.

> Дата первого развёртывания: 2026-05-20  
> Актуализация: 2026-05-27 — активный сервер `89.19.216.47`; старый Hermes на `194.87.140.190` должен оставаться остановленным.

---

## 1. Инфраструктура

| Параметр | Значение |
|----------|----------|
| Сервер | NL VPS |
| Hostname | `ams-1-vm-7t0o` |
| IP | `89.19.216.47` |
| OS | Ubuntu 24.04 |
| RAM | ~2 GB |
| Disk | ~38 GB |
| SSH | `ssh -i ~/.ssh/medhistory_deploy root@89.19.216.47` |

Текущее состояние на 2026-06-02: диск `/` и `/opt/hermes-data` ~41% used; включён `/swapfile` 2 GB для пиков памяти при двух Hermes и local STT.

⚠️ Старый экземпляр Hermes на `194.87.140.190` больше не запускать: он использовал тот же `TELEGRAM_BOT_TOKEN` и создавал `getUpdates conflict`.

---

## 2. Компоненты

| Что | Значение |
|-----|----------|
| Docker image | `nousresearch/hermes-agent:latest` |
| Compose | `/opt/hermes/docker-compose.yml` |
| Данные | `/opt/hermes-data/` → `/opt/data` в контейнере |
| Hotfix mounts | `/opt/hermes-hotfix/run_agent.py` → `/opt/hermes/run_agent.py:ro`; `/opt/hermes-hotfix/agent/auxiliary_client.py` → `/opt/hermes/agent/auxiliary_client.py:ro` |
| Конфиг | `/opt/hermes-data/config.yaml` |
| Секреты | `/opt/hermes-data/.env` |
| Контейнер | `hermes-gateway` |
| Restart policy | `unless-stopped` |
| Network | `network_mode: host` |
| Dashboard | `127.0.0.1:9119` |
| API server | выключен: `API_SERVER_ENABLED=false` |
| Docker socket | `/var/run/docker.sock` смонтирован, `group_add: "987"` |
| Ресурсы | `cpus: "1.0"`, `memory: 1536M`, `shm_size: "1gb"` |
| Family VPN | WireGuard на host: `wg0`, UDP `51820`, подсеть `10.66.66.0/24` + `fd66:66:66::/64` |

Docker socket включён осознанно: Hermes может видеть состояние контейнеров и слать watchdog-алерты, но это высокий уровень доверия к агенту.

### Второй изолированный Hermes для жены

Развёрнут и запущен 2026-06-02 на том же NL VPS с отдельными Telegram и Codex credentials.

| Что | Значение |
|-----|----------|
| Compose | `/opt/hermes-wife/docker-compose.yml` |
| Данные | `/opt/hermes-wife-data/` → `/opt/data` в контейнере |
| Контейнер | `hermes-wife-gateway` |
| Docker image | `hermes-agent-faster-whisper:local` (`/opt/hermes-wife/Dockerfile`) |
| Dashboard | `127.0.0.1:9120` |
| Docker socket | не смонтирован |
| Hotfix mounts | те же read-only файлы из `/opt/hermes-hotfix/` |
| Ресурсы | `cpus: "0.5"`, `memory: 1280M`, `shm_size: "768mb"` |
| Telegram bot | `@makaeva_hemes_bot` |
| Allowlist/Home | `585323311` |
| Auth file | `/opt/hermes-wife-data/auth.json` |
| Codex auth | OpenAI Codex ✓ logged in, refreshed `2026-06-02 18:57:36 UTC` |
| Local STT | `faster-whisper==1.2.1`, model `small`, language `ru`, CPU/int8 |
| Model cache | `/opt/hermes-wife-data/.cache/huggingface/hub/models--Systran--faster-whisper-small` |
| Статус | `hermes-wife-gateway` запущен, Telegram configured, jobs `0` |

Изоляция: не скопированы `auth.json`, `state.db`, cron, Telegram userbot, SSH-ключи, marketing/job-search/health/calendar данные и любые сессии первого Hermes. Скопирован только `config.yaml` как базовая конфигурация Hermes; данные агента, Telegram и AI auth должны быть отдельными.

Эксплуатация второго агента:

```bash
cd /opt/hermes-wife
docker compose ps
docker compose logs -f hermes-wife-gateway
docker compose restart hermes-wife-gateway

docker exec --user hermes -e HOME=/opt/data hermes-wife-gateway \
  /opt/hermes/.venv/bin/hermes status
```

`TELEGRAM_BOT_TOKEN` второго агента хранится в `/opt/hermes-wife-data/.env` и не совпадает с токеном `@ironbor_hermes_bot`. Если вместо отдельного Codex auth скопировать `/opt/hermes-data/auth.json`, агент будет связан с первым через один OpenAI/Codex аккаунт, поэтому для полной изоляции этого не делать.

2026-06-02: для голосовых сообщений второго агента собран локальный image:

```bash
cd /opt/hermes-wife
docker build -t hermes-agent-faster-whisper:local .
docker compose up -d
```

Smoke-test локального STT внутри `hermes-wife-gateway` прошёл: `success=True`, `provider=local` на тестовом WAV. Первый запуск с лимитом `768M` получил OOM (`code 137`), поэтому лимит поднят до `1280M`, `shm_size` до `768mb`.

Исходящий SSH с NL VPS на RU/OpenClaw настроен 2026-06-01:

- Для root shell на NL: ключ `/root/.ssh/id_ed25519_openclaw_ru`, alias
  `openclaw-ru` / `ru-openclaw` / `medhistory-ru` в `/root/.ssh/config`.
- Для Hermes Agent внутри контейнера: отдельный ключ
  `/opt/hermes-data/.ssh/avito_ru_server_ed25519`, внутри контейнера путь
  `/opt/data/.ssh/avito_ru_server_ed25519`; alias `openclaw-ru` в
  `/opt/hermes-data/.ssh/config`.
- На RU оба публичных ключа добавлены в `/root/.ssh/authorized_keys`; root-shell
  ключ ограничен `from="89.19.216.47"`, Hermes-ключ подписан комментарием
  `hermes-avito-ru-server`.

---

## 3. Модель и auth

На актуальном сервере Hermes работает через импортированные Codex CLI credentials.

| Параметр | Значение |
|----------|----------|
| Провайдер | `openai-codex` |
| Модель | `gpt-5.5` |
| Fallback | не настроен |
| Auth file | `/opt/hermes-data/auth.json` |
| Status | `OpenAI Codex ✓ logged in` |
| Последнее обновление auth | `2026-05-21 21:25:44 UTC` |
| OpenRouter | ключ есть в `.env`, но не основной провайдер |
| Nous Portal | не залогинен |

Проверка:

```bash
docker exec --user hermes -e HOME=/opt/data hermes-gateway \
  /opt/hermes/.venv/bin/hermes status
```

⚠️ На 2026-05-27 основной `openai-codex/gpt-5.5` начал падать с `TypeError: 'NoneType' object is not iterable`: ChatGPT Codex отдавал stream items, но финальный `response.completed` приходил с `response.output = null`, из-за чего OpenAI SDK 2.24.0 падал при parsing. В `/opt/hermes/run_agent.py` добавлен локальный recovery из уже полученных `response.output_item.done` / text delta events. После проверки fallback убран, чат снова идёт через `openai-codex/gpt-5.5`.

Тот же `response.output = null` ломал auxiliary title generation и показывал в Telegram `⚠ Auxiliary title generation failed: 'NoneType' object is not iterable`. В `/opt/hermes/agent/auxiliary_client.py` добавлен recovery для Codex auxiliary stream: `output is None` backfill'ится из collected output items/text deltas, а SDK `NoneType` exception не пробрасывается, если streamed content уже собран.

Hotfix закреплён bind mount’ами в compose: `/opt/hermes-hotfix/run_agent.py:/opt/hermes/run_agent.py:ro` и `/opt/hermes-hotfix/agent/auxiliary_client.py:/opt/hermes/agent/auxiliary_client.py:ro`. При будущем обновлении Hermes проверить, вошли ли эти fixes в upstream; если да — удалить mounts и вернуть штатные файлы из образа.

В логах также остаются 402 от OpenRouter для auxiliary/session summary/compression: OpenRouter-ключ есть, но баланса хватает не на все большие summary-запросы.

---

## 4. Telegram bot

| Параметр | Значение |
|----------|----------|
| Bot | `@ironbor_hermes_bot` |
| Token | `TELEGRAM_BOT_TOKEN` в `/opt/hermes-data/.env` |
| Allowlist | `TELEGRAM_ALLOWED_USERS=290722791` |
| Home channel | `TELEGRAM_HOME_CHANNEL=290722791` |

Проверка Bot API без вывода токена:

```bash
python3 - <<'PY'
from pathlib import Path
import re, json, urllib.request
token = re.findall(r"^TELEGRAM_BOT_TOKEN=(.+)$", Path("/opt/hermes-data/.env").read_text(), re.M)[-1].strip()
print(json.load(urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe")))
PY
```

Проверка gateway logs:

```bash
docker logs -f hermes-gateway
```

---

## 5. Telegram userbot

Telethon userbot авторизован под личным аккаунтом Бориса.

| Параметр | Значение |
|----------|----------|
| Script | `/opt/hermes-data/telegram-userbot/tg_userbot.py` |
| Venv | `/opt/hermes-data/telegram-userbot/.venv/` |
| Session | `/opt/hermes-data/telegram-userbot/boris.session` |
| Status | `authorized=True` |
| Account | `Boris`, `@ironbor15`, id `290722791` |

Команды:

```bash
# статус
docker exec --user hermes -e HOME=/opt/data hermes-gateway \
  /opt/data/telegram-userbot/.venv/bin/python /opt/data/telegram-userbot/tg_userbot.py status

# диалоги
docker exec --user hermes -e HOME=/opt/data hermes-gateway \
  /opt/data/telegram-userbot/.venv/bin/python /opt/data/telegram-userbot/tg_userbot.py dialogs --limit 30

# dry-run отправки
docker exec --user hermes -e HOME=/opt/data hermes-gateway \
  /opt/data/telegram-userbot/.venv/bin/python /opt/data/telegram-userbot/tg_userbot.py send \
  --peer me --message "test"

# реальная отправка требует явный --confirm
docker exec --user hermes -e HOME=/opt/data hermes-gateway \
  /opt/data/telegram-userbot/.venv/bin/python /opt/data/telegram-userbot/tg_userbot.py send \
  --peer me --message "test" --confirm
```

Safety: `send` по умолчанию показывает preview и не отправляет сообщение. Реальная отправка возможна только с `--confirm`. Файл `boris.session` равен доступу к личному Telegram-аккаунту — не копировать и не публиковать.

---

## 6. Cron и автономность

На 2026-05-25 активны 6 cron job’ов. Все работают в `no-agent` режиме: script stdout доставляется напрямую, пустой stdout = тихий успешный тик.

| Job ID | Имя | Расписание | Delivery | Script | Последний статус |
|--------|-----|------------|----------|--------|------------------|
| `fee1554279da` | `Server watchdog` | `*/15 * * * *` | `telegram` | `server-watchdog.sh` | ok |
| `460e5b699e60` | `Daily ops brief` | `0 6 * * *` UTC = 09:00 MSK | `telegram` | `daily-ops-brief.sh` | ok |
| `52f852d773a2` | `Утренняя сводка Яндекс Календаря` | `0 5 * * *` UTC = 08:00 MSK | `origin` | `yandex_calendar_daily_summary.sh` | ok |
| `7ca2c902c404` | `HH вакансии для Бориса — мониторинг новых релевантных` | `every 120m` | `origin` | `hh_monitor_boris.py` | ok |
| `7ceff645b1de` | `Career pages top-25 — вакансии для Бориса` | `every 360m` | `origin` | `career_pages_monitor_boris.py` | ok |
| `b19818172ed4` | `Precise career pages — точные вакансии Бориса` | `every 240m` | `origin` | `career_precise_monitor_boris.py` | ok |
| `36536fd4b094` | `Ежедневный анализ дневника питания и давления` | `30 18 * * *` UTC = 21:30 MSK | `origin` | `health_diary_collect.sh` | ok |
| `d8ff70d9c9b2` | `Проверка ответов мед.блогеров` | `every 30m` | `origin` | `check_med_bloggers_replies.sh` | ok |

Проверка:

```bash
docker exec --user hermes -e HOME=/opt/data hermes-gateway \
  /opt/hermes/.venv/bin/hermes cron list

docker exec --user hermes -e HOME=/opt/data hermes-gateway \
  /opt/hermes/.venv/bin/hermes cron status
```

Скрипты лежат в `/opt/hermes-data/scripts/`. Дополнительные данные job-search — в `/opt/hermes-data/job-search/`; Яндекс.Календарь — в `/opt/hermes-data/yandex-calendar/`.

---

## 7. Интеграции и инструменты

Текущий `hermes status`:

- Telegram configured, home `290722791`.
- MCP servers: **нет настроенных MCP серверов**.
- Slack/Email/WhatsApp/Signal/Discord: не настроены.
- Built-in memory активна; внешнего memory provider нет.
- Сессий в state.db: около 60; активных session mappings: 25.

`hermes doctor` на 2026-05-25:

- OpenAI Codex auth — ok.
- OpenRouter connectivity — ok.
- Docker, git, `rg`, Node.js, agent-browser, Playwright Chromium — ok.
- Не критично: `~/.local/bin/hermes` symlink отсутствует; использовать `/opt/hermes/.venv/bin/hermes`.
- Не критично: нет `GITHUB_TOKEN` в `.env`, поэтому Skills Hub ограничен 60 GitHub API req/hr.
- Не настроены web-search API keys (`EXA_API_KEY`, `PARALLEL_API_KEY`, `TAVILY_API_KEY`, `FIRECRAWL_*`), X, Discord, Home Assistant, Spotify и др.

Из недавних warning’ов:

- OpenRouter 402 для compression/session summaries.
- Иногда browser tool ругается `Chrome not found`, хотя doctor видит `agent-browser` и Playwright Chromium.
- В terminal окружении отдельных задач встречались `ModuleNotFoundError: requests` и `gh: command not found`.
- Были `Non-streaming API call stale for 300s` от `openai-codex`.
- Telegram иногда переключался на fallback IP `149.154.166.110`.

### MedHistory marketing workspace

На 2026-05-27 внешний контур памяти для маркетингового агента MedHistory загружен на активный Hermes VPS:

| Что | Путь |
|-----|------|
| Host path | `/opt/hermes-data/medhistory-marketing/` |
| Path inside container | `/opt/data/medhistory-marketing/` |
| Entrypoint | `/opt/data/medhistory-marketing/HERMES_MARKETING.md` |
| Marketing files | `/opt/data/medhistory-marketing/marketing/` |
| Root instruction pointer | `/opt/data/AGENTS.md` |
| Owner/group | `hermes:hermes` внутри контейнера (`10000:10000` на host) |

Перед маркетинговыми задачами Hermes должен читать:

```bash
/opt/data/medhistory-marketing/HERMES_MARKETING.md
/opt/data/medhistory-marketing/marketing/hermes_handoff.md
```

Ключевые файлы состояния:

- `marketing/acquisition_crm.csv`
- `marketing/placement_quotes.csv`
- `marketing/experiments.csv`
- `marketing/inbox.md`
- `marketing/learnings.md`

---

## 8. Дашборд, VPN и порты

Dashboard слушает только loopback:

```bash
ssh -i ~/.ssh/medhistory_deploy -L 9119:127.0.0.1:9119 root@89.19.216.47
# браузер: http://localhost:9119
```

OpenAI-compatible API gateway на `8642` выключен (`API_SERVER_ENABLED=false`). Если включать — только с loopback/reverse proxy и `API_SERVER_KEY`.

Family VPN работает через WireGuard на host-системе, отдельно от Docker/Hermes:

| Параметр | Значение |
|----------|----------|
| Service | `wg-quick@wg0` (`systemctl status wg-quick@wg0`) |
| Server config | `/etc/wireguard/wg0.conf` (`chmod 600`) |
| Endpoint | `89.19.216.47:51820/udp` |
| Interface | `wg0` |
| Server VPN IPs | `10.66.66.1/24`, `fd66:66:66::1/64` |
| Client configs on server | `/root/wireguard-clients/*.conf` |
| Client QR PNGs on server | `/root/wireguard-clients/*.png` |
| Local client copies | `/Users/boris/Desktop/hermes-vpn-clients/` (outside repo, private keys inside) |
| NAT | `iptables`/`ip6tables` MASQUERADE via `eth0` in `wg0.conf` `PostUp`/`PostDown` |
| Forwarding | `/etc/sysctl.d/99-hermes-wireguard.conf`: IPv4 + IPv6 forwarding enabled |

Initial profiles created on 2026-05-31:

- `boris-phone` → `10.66.66.2`, `fd66:66:66::2`
- `family-1` → `10.66.66.3`, `fd66:66:66::3`
- `family-2` → `10.66.66.4`, `fd66:66:66::4`
- `family-3` → `10.66.66.5`, `fd66:66:66::5`

Additional profile created on 2026-06-18:

- `family-win-1` → `10.66.66.6` (IPv4-only, simplified profile for Windows/WireGuard)

Additional profile created on 2026-06-24:

- `yanis` → `10.66.66.7`, `fd66:66:66::7`

Правила эксплуатации:

- Один WireGuard-профиль использовать только на одном устройстве.
- Не коммитить `.conf`/QR-файлы: в них лежат приватные ключи клиента.
- Для проверки подключений: `wg show wg0` на сервере; у активных клиентов появится `latest handshake`.
- Для временной остановки VPN: `systemctl stop wg-quick@wg0`; для возврата: `systemctl start wg-quick@wg0`.
- Для постоянного отключения VPN: `systemctl disable --now wg-quick@wg0`.

---

## 9. Эксплуатация

Все команды — на `89.19.216.47`.

```bash
cd /opt/hermes
docker compose ps
docker compose logs -f hermes-gateway
docker compose restart hermes-gateway
docker compose pull && docker compose up -d
```

Правило для Hermes CLI внутри контейнера:

```bash
docker exec --user hermes -e HOME=/opt/data hermes-gateway /opt/hermes/.venv/bin/hermes <subcommand>
```

Почему важно: команды без `--user hermes` могут создать/перезаписать файлы в `/opt/hermes-data/` от root, после чего gateway под uid `10000` может потерять доступ к auth/config/session файлам.

Если права сломались:

```bash
chown -R 10000:10000 /opt/hermes-data/
cd /opt/hermes && docker compose restart hermes-gateway
```

---

## 10. Инциденты и риски

- **2026-05-21:** старый Hermes на `194.87.140.190` был случайно поднят и создал `getUpdates conflict`; старый контейнер остановлен.
- **2026-05-21:** gateway перезапускался изнутри командой `hermes gateway restart`, из-за чего Telegram получил `Gateway shutting down — current task will be interrupted`.
- **Docker socket:** высокий уровень доверия к агенту; нужен для watchdog, но потенциально даёт контроль над Docker daemon.
- **WireGuard VPN:** клиентские `.conf` и QR-коды равны доступу к VPN; при утечке удалить peer из `/etc/wireguard/wg0.conf`, перезапустить `wg-quick@wg0` и выдать новый профиль.
- **RAM:** сервер ~2 GB + `/swapfile` 2 GB; основной Hermes ограничен 1536 MB, Hermes жены 1280 MB. Watchdog отслеживает low-memory.
- **Секреты:** при утечке ротировать `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`, Codex auth и `boris.session`.

---

## 11. Что сделать дальше

- [x] Перенести активный Hermes на NL VPS `89.19.216.47`.
- [x] Остановить старый Hermes на `194.87.140.190`.
- [x] Авторизовать Telegram userbot для чтения диалогов и точечной отправки.
- [x] Настроить watchdog, daily ops, Яндекс.Календарь и job-search cron.
- [x] Поднять WireGuard VPN на NL VPS и создать семейные профили.
- [ ] Разобраться с OpenRouter 402 для compression/session_search или перевести auxiliary на другой доступный provider.
- [ ] Починить browser runtime (`Chrome not found`) и проверить browser tool end-to-end.
- [ ] Добавить `requests`/`gh` в persistent terminal environment, если Hermes продолжит использовать эти команды.
- [ ] Подключить MCP/Slack/Email/GitHub по официальной схеме, если они нужны как постоянные интеграции.
