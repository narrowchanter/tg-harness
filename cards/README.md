# Relationship cards

Durable per-chat notes for the **secretary** role. Live cards sit under `out/cards/` (gitignored with the rest of `out/`). This folder holds the schema and a fake example only — never commit real people.

## Path

```
out/cards/<chat_id>.md
```

`chat_id` is the numeric Telegram id from `config.toml` (e.g. `987654321.md`).

## Format

Markdown with YAML frontmatter:

```yaml
---
chat_id: 987654321
title: "Example friend"
# relationship: friend | family | work | other
relationship: friend
voice: "short mate texts, no emoji"
taboos: []
open_loops:
  - "weekend climb TBD"
updated_at: "2026-09-09T12:00:00+00:00"
---

Optional freeform body. Keep it short. Facts the secretary should not lose between wakes.
```

## CLI

```bash
export TG_HARNESS_ROLE=secretary
python -m tg_harness.cli card show <chat>
python -m tg_harness.cli card write <chat> \
  --relationship friend \
  --voice "casual, brief" \
  --loop "open item" \
  --body "optional notes"
```

`card` is secretary-only and only for `mode=secretary` chats. Reporter gets a hard error.

## When to write / refresh

1. **First time** on the allowlist: deep `pull` (`--hours 2160` or several pulls), then `card write`.
2. **After a real conversation shift** (new open loop, tone change, taboo): update the card.
3. **Every inbound wake**: `card show` (if present) + recent `pull` (keep the usual ~48h depth — cards add context, they do not replace history).

Do not invent a home address or other secrets. Do not put api keys or session material in a card.
