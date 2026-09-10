import argparse
import unittest
from unittest.mock import patch

from pathlib import Path
import tempfile

from tg_harness.cli import cmd_pull, format_event_section, write_event_section
from tg_harness.policy import event_settings, resolve_chat


class PullRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_reporter_pull_fails_closed_without_watch(self):
        args = argparse.Namespace(
            chat="Example group",
            hours=24,
            limit=1000,
            timezone=None,
            out=None,
            keep_empty=False,
        )
        chat = {"id": 111, "title": "Example group", "mode": "report"}

        with (
            patch("tg_harness.cli.require_role", return_value="reporter"),
            patch("tg_harness.cli.require_chat", return_value=chat),
            patch("tg_harness.cli.watch_up", return_value=False),
            patch("tg_harness.cli.client_from") as client_from,
        ):
            with self.assertRaises(SystemExit):
                await cmd_pull({}, args)

        client_from.assert_not_called()



class EventCliTests(unittest.TestCase):
    def test_format_event_section(self):
        text = format_event_section(enabled=True, name='Meet "Up"')
        self.assertIn("[event]", text)
        self.assertIn("enabled = true", text)
        self.assertIn("Meet", text)

    def test_write_event_preserves_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                'timezone = "UTC"\n\n[[chats]]\nid = 1\ntitle = "Sam"\nmode = "secretary"\n',
                encoding="utf-8",
            )
            write_event_section(path, enabled=True, name="DemoCon")
            raw = path.read_text(encoding="utf-8")
            self.assertIn('timezone = "UTC"', raw)
            self.assertIn("[[chats]]", raw)
            self.assertIn("[event]", raw)
            self.assertIn("enabled = true", raw)
            self.assertIn('name = "DemoCon"', raw)
            # round-trip off keeps chats
            write_event_section(path, enabled=False, name="DemoCon")
            raw2 = path.read_text(encoding="utf-8")
            self.assertIn("[[chats]]", raw2)
            self.assertIn("enabled = false", raw2)
            # tomllib round-trip via resolve when enabled again
            write_event_section(path, enabled=True, name="DemoCon")
            import tomllib
            cfg = tomllib.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(event_settings(cfg)["name"], "DemoCon")
            stranger = resolve_chat(cfg, "424242")
            self.assertTrue(stranger.get("event"))


if __name__ == "__main__":
    unittest.main()
