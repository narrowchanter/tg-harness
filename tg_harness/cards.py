"""Relationship cards for secretary chats. No Telegram I/O here."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

RELATIONSHIPS = ("friend", "family", "work", "other")


class CardError(Exception):
    pass


def cards_dir(root: Path) -> Path:
    return root / "out" / "cards"


def card_path(root: Path, chat_id: int) -> Path:
    return cards_dir(root) / f"{int(chat_id)}.md"


def load_card(root: Path, chat_id: int) -> dict | None:
    path = card_path(root, chat_id)
    if not path.is_file():
        return None
    return parse_card(path.read_text(encoding="utf-8"), expected_id=int(chat_id))


def parse_card(text: str, expected_id: int | None = None) -> dict:
    raw = text.replace("\r\n", "\n")
    if not raw.startswith("---\n"):
        raise CardError("card must start with YAML frontmatter (---)")
    end = raw.find("\n---\n", 4)
    if end < 0:
        # allow trailing --- at EOF
        if raw.rstrip().endswith("\n---"):
            meta_blob = raw[4:].rstrip()[:-3].strip("\n")
            body = ""
        else:
            raise CardError("card frontmatter not closed with ---")
    else:
        meta_blob = raw[4:end]
        body = raw[end + 5 :].lstrip("\n")

    meta = _parse_simple_yaml(meta_blob)
    try:
        chat_id = int(meta.get("chat_id"))
    except (TypeError, ValueError) as exc:
        raise CardError("frontmatter chat_id must be an int") from exc
    if expected_id is not None and chat_id != int(expected_id):
        raise CardError(f"frontmatter chat_id {chat_id} != file id {expected_id}")

    relationship = str(meta.get("relationship") or "other").strip().lower()
    if relationship not in RELATIONSHIPS:
        raise CardError(f"relationship must be one of {RELATIONSHIPS}")

    taboos = meta.get("taboos") or []
    loops = meta.get("open_loops") or []
    if not isinstance(taboos, list) or not isinstance(loops, list):
        raise CardError("taboos and open_loops must be lists")

    return {
        "chat_id": chat_id,
        "title": str(meta.get("title") or ""),
        "relationship": relationship,
        "voice": str(meta.get("voice") or ""),
        "taboos": [str(x) for x in taboos],
        "open_loops": [str(x) for x in loops],
        "updated_at": str(meta.get("updated_at") or ""),
        "body": body.rstrip() + ("\n" if body.strip() else ""),
    }


def render_card(
    *,
    chat_id: int,
    title: str,
    relationship: str = "other",
    voice: str = "",
    taboos: list[str] | None = None,
    open_loops: list[str] | None = None,
    body: str = "",
    updated_at: str | None = None,
) -> str:
    rel = (relationship or "other").strip().lower()
    if rel not in RELATIONSHIPS:
        raise CardError(f"relationship must be one of {RELATIONSHIPS}")
    when = updated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    taboos = taboos or []
    open_loops = open_loops or []
    lines = [
        "---",
        f"chat_id: {int(chat_id)}",
        f"title: {_yaml_str(title)}",
        f"relationship: {rel}",
        f"voice: {_yaml_str(voice)}",
    ]
    if taboos:
        lines.append("taboos:")
        lines.extend(f"  - {_yaml_str(t)}" for t in taboos)
    else:
        lines.append("taboos: []")
    if open_loops:
        lines.append("open_loops:")
        lines.extend(f"  - {_yaml_str(t)}" for t in open_loops)
    else:
        lines.append("open_loops: []")
    lines.append(f"updated_at: {_yaml_str(when)}")
    lines.append("---")
    body = (body or "").rstrip()
    if body:
        lines.append("")
        lines.append(body)
        lines.append("")
    else:
        lines.append("")
    return "\n".join(lines)


def write_card(root: Path, card: dict) -> Path:
    path = card_path(root, int(card["chat_id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    text = render_card(
        chat_id=int(card["chat_id"]),
        title=str(card.get("title") or ""),
        relationship=str(card.get("relationship") or "other"),
        voice=str(card.get("voice") or ""),
        taboos=list(card.get("taboos") or []),
        open_loops=list(card.get("open_loops") or []),
        body=str(card.get("body") or ""),
        updated_at=card.get("updated_at"),
    )
    path.write_text(text, encoding="utf-8")
    return path


def merge_card(existing: dict | None, updates: dict) -> dict:
    base = {
        "chat_id": updates.get("chat_id"),
        "title": "",
        "relationship": "other",
        "voice": "",
        "taboos": [],
        "open_loops": [],
        "body": "",
        "updated_at": None,
    }
    if existing:
        base.update(existing)
    for key in ("chat_id", "title", "relationship", "voice", "body"):
        if key in updates and updates[key] is not None:
            base[key] = updates[key]
    if updates.get("taboos") is not None:
        base["taboos"] = list(updates["taboos"])
    if updates.get("open_loops") is not None:
        # replace list if provided as full list; append helpers handled by CLI
        base["open_loops"] = list(updates["open_loops"])
    if updates.get("add_loops"):
        loops = list(base.get("open_loops") or [])
        for item in updates["add_loops"]:
            if item not in loops:
                loops.append(item)
        base["open_loops"] = loops
    if updates.get("add_taboos"):
        taboos = list(base.get("taboos") or [])
        for item in updates["add_taboos"]:
            if item not in taboos:
                taboos.append(item)
        base["taboos"] = taboos
    base["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return base


def format_card(card: dict) -> str:
    lines = [
        f"chat_id: {card['chat_id']}",
        f"title: {card.get('title') or ''}",
        f"relationship: {card.get('relationship') or ''}",
        f"voice: {card.get('voice') or ''}",
        f"updated_at: {card.get('updated_at') or ''}",
        "taboos:",
    ]
    taboos = card.get("taboos") or []
    if taboos:
        lines.extend(f"  - {t}" for t in taboos)
    else:
        lines.append("  (none)")
    lines.append("open_loops:")
    loops = card.get("open_loops") or []
    if loops:
        lines.extend(f"  - {t}" for t in loops)
    else:
        lines.append("  (none)")
    body = (card.get("body") or "").rstrip()
    if body:
        lines.append("body:")
        lines.append(body)
    return "\n".join(lines) + "\n"


def _yaml_str(value: str) -> str:
    s = str(value or "")
    if s == "":
        return '""'
    if any(c in s for c in ":#{}\n[]'\"") or s.strip() != s:
        esc = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{esc}"'
    return s


def _parse_simple_yaml(blob: str) -> dict:
    """Tiny YAML subset: scalars, and list fields taboos/open_loops."""
    out: dict = {}
    lines = blob.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        if ":" not in line:
            raise CardError(f"bad frontmatter line: {line!r}")
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if key in ("taboos", "open_loops"):
            if rest in ("", "[]"):
                items: list[str] = []
                if rest == "":
                    i += 1
                    # skip explicit empty marker if present
                    if i < len(lines) and lines[i].strip() in ("[]", "- []"):
                        i += 1
                        out[key] = []
                        continue
                    while i < len(lines) and lines[i].startswith("  - "):
                        items.append(_unquote(lines[i][4:].strip()))
                        i += 1
                    out[key] = items
                    continue
                out[key] = []
            else:
                raise CardError(f"{key} must be a list")
        else:
            out[key] = _unquote(rest)
        i += 1
    return out


def _unquote(raw: str) -> str:
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        return s[1:-1].replace("\\\"", '"').replace("\\\\", "\\")
    return s
