import unittest

from tg_harness.policy import (
    PolicyError,
    chat_by_id,
    refuse_live_title,
    refuse_pull,
    refuse_send,
    refuse_watch,
    resolve_chat,
    role_of,
)

CFG = {
    "chats": [
        {"id": 111, "title": "Example group", "mode": "report"},
        {"id": 222, "title": "Example friend", "mode": "secretary"},
        {"id": 333, "title": "Example group", "mode": "report"},
    ]
}


class RoleTests(unittest.TestCase):
    def test_env_wins(self):
        self.assertEqual(role_of({"role": "secretary"}, {"TG_HARNESS_ROLE": "reporter"}), "reporter")

    def test_missing_role(self):
        with self.assertRaises(PolicyError):
            role_of({}, {})

    def test_watch_reporter_blocked(self):
        self.assertEqual(refuse_watch("reporter"), "watch requires TG_HARNESS_ROLE=secretary")
        self.assertIsNone(refuse_watch("secretary"))


class ResolveTests(unittest.TestCase):
    def test_by_title(self):
        chat = resolve_chat(CFG, "Example friend")
        self.assertEqual(int(chat["id"]), 222)

    def test_by_id(self):
        chat = resolve_chat(CFG, "111")
        self.assertEqual(chat["title"], "Example group")

    def test_unknown(self):
        with self.assertRaises(PolicyError):
            resolve_chat(CFG, "999")
        with self.assertRaises(PolicyError):
            resolve_chat(CFG, "not-a-chat")

    def test_duplicate_title(self):
        with self.assertRaises(PolicyError):
            resolve_chat(CFG, "Example group")

    def test_no_raw_id_fallback(self):
        with self.assertRaises(PolicyError):
            chat_by_id(CFG, 999)


class PullSendTests(unittest.TestCase):
    def test_reporter_cannot_send(self):
        friend = resolve_chat(CFG, "Example friend")
        self.assertEqual(refuse_send("reporter", friend), "reporter cannot send")

    def test_reporter_cannot_pull_secretary(self):
        friend = resolve_chat(CFG, "Example friend")
        self.assertIn("mode=report", refuse_pull("reporter", friend) or "")

    def test_secretary_cannot_pull_report(self):
        group = chat_by_id(CFG, 111)
        self.assertIn("mode=secretary", refuse_pull("secretary", group) or "")

    def test_secretary_cannot_send_report(self):
        group = chat_by_id(CFG, 111)
        self.assertIn("read-only", refuse_send("secretary", group) or "")

    def test_secretary_can_send_friend(self):
        friend = resolve_chat(CFG, "Example friend")
        self.assertIsNone(refuse_send("secretary", friend))
        self.assertIsNone(refuse_pull("secretary", friend))

    def test_title_mismatch(self):
        friend = resolve_chat(CFG, "Example friend")
        self.assertIsNotNone(refuse_live_title(friend, "Someone else"))
        self.assertIsNone(refuse_live_title(friend, "example friend"))


if __name__ == "__main__":
    unittest.main()
