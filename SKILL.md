---
name: Telegram Telethon harness
description: >-
  Use this when an agent needs Telegram user I/O via tg-harness: login, pull,
  send, or the secretary NewMessage watcher that webhooks a Grok routine.
  Reporter never sends. Secretary never posts in report chats
---
# Telegram Telethon harness

Checkout: `tg-harness`. 

```bash
python -m tg_harness.cli status
python -m tg_harness.cli pull "Chat" --hours 24
python -m tg_harness.cli send "Chat" --text "..."
python -m tg_harness.cli send "Chat" --reply-to <id> --text "..."   # only when a quote is needed
python -m tg_harness.cli watch
```

Keep `watch` running. `pull` / `send` / `status` go through `watch.sock` on the same Telethon client. Do **not** kill watch to send. Do not open a second client.

`watch` listens on `mode=secretary` only, queues `out/secretary-queue.jsonl`, POSTs the webhook, and on startup backfills inbound after the last outgoing. Report chats (`mode=report`) are ignored and send-blocked.

WARP proxy mode on `127.0.0.1:40000` if MTProto is blocked. Do not change the default route.

Forks use their own `api_id` / `api_hash`. Do not ship session, `.env`, webhook key, or `watch.sock`.

## Roles

- Reporter: `AGENTS_REPORTER.md` — scheduled `pull`, write the brief, never `send`.
- Secretary: `AGENTS_SECRETARY.md` — woken by the webhook, `pull`/`send` through the live watcher.

## Reply targeting

User named it → last inbound in a 1:1 → last @user in a small group → else ask.

## Quoting

Do not quote every message. In a 1:1, just send. Only `--reply-to` when they asked about a specific older message or the group thread would be ambiguous without it.
