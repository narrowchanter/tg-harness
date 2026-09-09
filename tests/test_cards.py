import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from tg_harness.cards import (
    CardError,
    card_path,
    format_card,
    load_card,
    merge_card,
    parse_card,
    render_card,
    update_card,
    write_card,
)
from tg_harness.policy import refuse_card, resolve_chat


CFG = {
    "chats": [
        {"id": 111, "title": "Example group", "mode": "report"},
        {"id": 222, "title": "Example friend", "mode": "secretary"},
    ]
}


class CardParseTests(unittest.TestCase):
    def test_round_trip_empty_lists(self):
        text = render_card(chat_id=222, title="Example friend", relationship="friend", voice="brief")
        card = parse_card(text, expected_id=222)
        self.assertEqual(card["taboos"], [])
        self.assertEqual(card["open_loops"], [])
        self.assertEqual(card["relationship"], "friend")

    def test_round_trip_with_lists_and_body(self):
        text = render_card(
            chat_id=222,
            title="Example friend",
            relationship="family",
            voice="teasing",
            taboos=["money talk"],
            open_loops=["visit Sunday"],
            body="Sister. Keep it light.",
        )
        card = parse_card(text, expected_id=222)
        self.assertEqual(card["taboos"], ["money talk"])
        self.assertEqual(card["open_loops"], ["visit Sunday"])
        self.assertIn("Sister", card["body"])

    def test_multiline_scalar_round_trip(self):
        voice = "short texts\nno emoji"
        taboo = "line\nbreak"
        loop = "call\nmum"
        text = render_card(
            chat_id=222,
            title="Example friend",
            relationship="friend",
            voice=voice,
            taboos=[taboo],
            open_loops=[loop],
        )
        card = parse_card(text, expected_id=222)
        self.assertEqual(card["voice"], voice)
        self.assertEqual(card["taboos"], [taboo])
        self.assertEqual(card["open_loops"], [loop])

    def test_inline_comment_on_relationship(self):
        text = (
            "---\n"
            "chat_id: 222\n"
            'title: "Example friend"\n'
            "relationship: friend   # friend | family | work | other\n"
            "voice: brief\n"
            "taboos: []\n"
            "open_loops: []\n"
            'updated_at: "2026-09-09T12:00:00+00:00"\n'
            "---\n"
        )
        card = parse_card(text, expected_id=222)
        self.assertEqual(card["relationship"], "friend")

    def test_example_file(self):
        root = Path(__file__).resolve().parent.parent
        text = (root / "cards" / "example.md").read_text(encoding="utf-8")
        card = parse_card(text, expected_id=987654321)
        self.assertEqual(card["relationship"], "friend")
        self.assertTrue(card["open_loops"])

    def test_readme_template_parses(self):
        root = Path(__file__).resolve().parent.parent
        readme = (root / "cards" / "README.md").read_text(encoding="utf-8")
        m = re.search(r"```yaml\n(.*?)```", readme, re.S)
        self.assertIsNotNone(m, "README should contain a yaml fence template")
        card = parse_card(m.group(1).strip() + "\n", expected_id=987654321)
        self.assertEqual(card["relationship"], "friend")
        self.assertEqual(card["chat_id"], 987654321)

    def test_id_mismatch(self):
        text = render_card(chat_id=1, title="x")
        with self.assertRaises(CardError):
            parse_card(text, expected_id=2)

    def test_bad_relationship(self):
        with self.assertRaises(CardError):
            render_card(chat_id=1, title="x", relationship="enemy")


class CardFileTests(unittest.TestCase):
    def test_write_load_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = write_card(
                root,
                {
                    "chat_id": 222,
                    "title": "Example friend",
                    "relationship": "friend",
                    "voice": "mate",
                    "taboos": [],
                    "open_loops": ["gym"],
                    "body": "",
                },
            )
            self.assertTrue(path.is_file())
            loaded = load_card(root, 222)
            self.assertIsNotNone(loaded)
            merged = merge_card(loaded, {"add_loops": ["climb"], "voice": "mate short"})
            write_card(root, merged)
            again = load_card(root, 222)
            self.assertEqual(again["voice"], "mate short")
            self.assertEqual(again["open_loops"], ["gym", "climb"])
            self.assertIn("open_loops", format_card(again))

    def test_atomic_write_preserves_old_on_replace_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_card(
                root,
                {
                    "chat_id": 222,
                    "title": "Example friend",
                    "relationship": "friend",
                    "voice": "mate",
                    "open_loops": ["gym"],
                },
            )
            path = card_path(root, 222)
            before = path.read_text(encoding="utf-8")
            with mock.patch("tg_harness.cards.os.replace", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    write_card(
                        root,
                        {
                            "chat_id": 222,
                            "title": "Example friend",
                            "relationship": "friend",
                            "voice": "changed",
                            "open_loops": ["gym", "climb"],
                        },
                    )
            self.assertEqual(path.read_text(encoding="utf-8"), before)
            self.assertEqual(load_card(root, 222)["voice"], "mate")

    def test_concurrent_update_card_keeps_both_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_card(
                root,
                {
                    "chat_id": 222,
                    "title": "Example friend",
                    "relationship": "friend",
                    "voice": "mate",
                    "open_loops": ["gym"],
                },
            )
            barrier = threading.Barrier(2)
            errors = []

            def append(item: str) -> None:
                try:
                    barrier.wait(timeout=5)
                    update_card(root, 222, {"add_loops": [item]})
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

            t1 = threading.Thread(target=append, args=("climb",))
            t2 = threading.Thread(target=append, args=("call mum",))
            t1.start()
            t2.start()
            t1.join(timeout=10)
            t2.join(timeout=10)
            self.assertEqual(errors, [])
            loops = load_card(root, 222)["open_loops"]
            self.assertEqual(sorted(loops), sorted(["gym", "climb", "call mum"]))


class CardPolicyTests(unittest.TestCase):
    def test_reporter_blocked(self):
        friend = resolve_chat(CFG, "Example friend")
        self.assertEqual(refuse_card("reporter", friend), "reporter cannot use cards")

    def test_secretary_report_blocked(self):
        group = resolve_chat(CFG, "111")
        self.assertIn("mode=secretary", refuse_card("secretary", group) or "")

    def test_secretary_ok(self):
        friend = resolve_chat(CFG, "Example friend")
        self.assertIsNone(refuse_card("secretary", friend))


if __name__ == "__main__":
    unittest.main()
