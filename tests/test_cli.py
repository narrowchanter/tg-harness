import argparse
import unittest
from unittest.mock import patch

from tg_harness.cli import cmd_pull


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


if __name__ == "__main__":
    unittest.main()
