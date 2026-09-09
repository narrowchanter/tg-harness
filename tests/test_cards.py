import tempfile
import unittest
from pathlib import Path

from tg_harness.cards import (
    CardError,
    format_card,
    load_card,
    merge_card,
    parse_card,
    render_card,
    write_card,
)
from tg_harness.policy import PolicyError, refuse_card, resolve_chat


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

    def test_example_file(self):
        root = Path(__file__).resolve().parent.parent
        text = (root / "cards" / "example.md").read_text(encoding="utf-8")
        card = parse_card(text, expected_id=987654321)
        self.assertEqual(card["relationship"], "friend")
        self.assertTrue(card["open_loops"])

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
