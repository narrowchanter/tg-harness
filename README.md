# tg-harness

Thin Telegram **I/O** for agents. Not a product. No website, no FastAPI, no ChatGPT, no tasks.

The script logs in, pulls a chat, and sends a nested reply. **You** (or a Grok) write reports and decide what to say.

## Why this exists

Teletasker was a full web app. Agents only needed Telethon + a session. This is that.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # your TELEGRAM_API_ID / TELEGRAM_API_HASH
cp config.example.toml config.toml
```

Get `api_id` / `api_hash` at https://my.telegram.org/auth → API development tools. **Use your own** in a public fork. Sharing one app id means Telegram can ban *that* app for everyone.

### If MTProto is blocked (handshake `IncompleteReadError`)

Do **not** change the machine default route. Use Cloudflare WARP in **proxy mode** (`127.0.0.1:40000`) and keep those values in `config.toml`.

```bash
# warp-svc; warp-cli mode proxy; warp-cli connect
curl --socks5-hostname 127.0.0.1:40000 https://www.cloudflare.com/cdn-cgi/trace
```

Direct Telethon `connect()` should still fail. Proxied `connect()` should work.

### Login (once)

```bash
python -m tg_harness.cli login --phone +15555550100
```

SMS/app code, then 2FA if asked. Writes `user.session`. Never commit it, never print it.

## Commands

```bash
python -m tg_harness.cli status
python -m tg_harness.cli chats
python -m tg_harness.cli pull "Example group" --hours 24
python -m tg_harness.cli send "Example friend" --text "hello"
python -m tg_harness.cli watch
```

Keep `watch` running. `pull` / `send` / `status` go through `watch.sock` so you never open a second Telethon client. `send` refuses `mode=report` chats. In 1:1s omit `--reply-to` unless a quote is needed. `watch` POSTs secretary inbound to `webhook_url` / `SECRETARY_WEBHOOK_URL`.

## Two agents

Copy these onto **different** Groks. One Telegram session, one running client — don’t let both bots open Telethon at once.

- [AGENTS_REPORTER.md](AGENTS_REPORTER.md) — weekday briefs, never sends
- [AGENTS_SECRETARY.md](AGENTS_SECRETARY.md) — allowlisted replies, relationship cards

Full recipe: [SKILL.md](SKILL.md)

## Do not ship

- `.env`, `config.toml` with real chats, `*.session`, `user.session.string`
- Webhook URL / sender key, `watch.sock`
- Someone else’s `api_hash` in git (Telegram can ban that app for everyone)
