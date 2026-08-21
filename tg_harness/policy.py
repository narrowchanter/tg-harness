"""Fail-closed chat and role rules. No Telegram I/O here."""

from __future__ import annotations

import os

ROLES = ("reporter", "secretary")
MODES = ("report", "secretary")


class PolicyError(Exception):
    pass


def role_of(cfg: dict, env: dict | None = None) -> str:
    env = os.environ if env is None else env
    raw = (env.get("TG_HARNESS_ROLE") or str(cfg.get("role") or "")).strip().lower()
    if raw not in ROLES:
        raise PolicyError("set TG_HARNESS_ROLE to reporter or secretary")
    return raw


def chat_by_id(cfg: dict, chat_id: int) -> dict:
    hits = [c for c in (cfg.get("chats") or []) if c.get("id") is not None and int(c["id"]) == int(chat_id)]
    return _one(hits, str(chat_id))


def resolve_chat(cfg: dict, raw: str) -> dict:
    key = str(raw or "").strip()
    if not key:
        raise PolicyError("chat is required")
    chats = cfg.get("chats") or []
    numeric = _int(key)
    if numeric is not None:
        hits = [c for c in chats if c.get("id") is not None and int(c["id"]) == numeric]
    else:
        hits = [c for c in chats if (c.get("title") or "").casefold() == key.casefold()]
    chat = _one(hits, key)
    if numeric is not None and int(chat["id"]) != numeric:
        raise PolicyError("resolved id does not match")
    if numeric is None and (chat.get("title") or "").casefold() != key.casefold():
        raise PolicyError("resolved title does not match")
    return chat


def refuse_pull(role: str, chat: dict) -> str | None:
    mode = chat.get("mode")
    if role == "reporter" and mode != "report":
        return "reporter can only pull mode=report chats"
    if role == "secretary" and mode != "secretary":
        return "secretary can only pull mode=secretary chats"
    if mode not in MODES:
        return f"invalid mode {mode!r}"
    return None


def refuse_send(role: str, chat: dict | None) -> str | None:
    if role == "reporter":
        return "reporter cannot send"
    if role != "secretary":
        return "send requires TG_HARNESS_ROLE=secretary"
    if chat is None:
        return "chat is not in config.toml"
    mode = chat.get("mode")
    if mode == "report":
        return "refusing send: report chat is read-only"
    if mode != "secretary":
        return "send only to mode=secretary chats"
    return None


def refuse_watch(role: str) -> str | None:
    if role != "secretary":
        return "watch requires TG_HARNESS_ROLE=secretary"
    return None


def refuse_live_title(chat: dict, live_title: str | None) -> str | None:
    expected = (chat.get("title") or "").strip()
    if not expected:
        return "config row missing title"
    got = (live_title or "").strip()
    if expected.casefold() != got.casefold():
        return f"telegram title {got!r} != config title {expected!r}"
    return None


def echo_chat(chat: dict) -> dict:
    return {"id": int(chat["id"]), "title": chat.get("title"), "mode": chat.get("mode")}


def _int(raw: str) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _one(hits: list[dict], key: str) -> dict:
    uniq: list[dict] = []
    seen: set[int] = set()
    for chat in hits:
        cid = chat.get("id")
        if cid is None:
            continue
        i = int(cid)
        if i in seen:
            continue
        seen.add(i)
        uniq.append(chat)
    if not uniq:
        raise PolicyError(f"chat {key!r} is not in config.toml")
    if len(uniq) > 1:
        raise PolicyError(f"chat {key!r} matches more than one config row")
    chat = uniq[0]
    mode = chat.get("mode")
    if mode not in MODES:
        raise PolicyError(f"chat {key!r} has invalid mode {mode!r}")
    return chat
