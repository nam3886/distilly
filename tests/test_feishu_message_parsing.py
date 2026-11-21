from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import _paths  # noqa: F401  (puts tools/ on sys.path)
import feishu_auto_collector as fac


def msg(sender: str, msg_type: str, content: dict) -> dict:
    return {
        "sender": {"id": sender, "id_type": "open_id"},
        "msg_type": msg_type,
        "body": {"content": json.dumps(content)},
        "create_time": "1700000000000",
    }


class ParseMessageContentTests(unittest.TestCase):
    def test_plain_text(self) -> None:
        self.assertEqual(fac.parse_message_content('{"text": " hi "}'), "hi")

    def test_post(self) -> None:
        raw = json.dumps({"content": [[{"tag": "text", "text": "a"}, {"tag": "a", "text": "b"}, {"tag": "img"}]]})
        self.assertEqual(fac.parse_message_content(raw), "a b")

    def test_not_json(self) -> None:
        self.assertEqual(fac.parse_message_content(" raw "), "raw")


class GroupChatTextMessagesTests(unittest.TestCase):
    def test_group_chat_keeps_plain_text_messages(self) -> None:
        page = {"code": 0, "data": {"has_more": False, "items": [
            msg("ou_target", "text", {"text": "plain hello"}),
            msg("ou_target", "post", {"content": [[{"tag": "text", "text": "rich hello"}]]}),
            msg("ou_other", "text", {"text": "not mine"}),
        ]}}
        with patch.object(fac, "api_get", return_value=page):
            got = fac.fetch_messages_from_chat("oc_x", "ou_target", 10, {})
        self.assertEqual([m["content"] for m in got], ["plain hello", "rich hello"])


if __name__ == "__main__":
    unittest.main()
