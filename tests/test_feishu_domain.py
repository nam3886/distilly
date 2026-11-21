from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

import _paths  # noqa: F401  (puts tools/ on sys.path)
import feishu_auto_collector


def reload_with(env: dict):
    with patch.dict(os.environ, env):
        return importlib.reload(feishu_auto_collector)


class FeishuDomainTests(unittest.TestCase):
    def tearDown(self) -> None:
        reload_with({"FEISHU_DOMAIN": "feishu"})

    def test_defaults_to_feishu(self) -> None:
        with patch.dict(os.environ):
            os.environ.pop("FEISHU_DOMAIN", None)
            mod = importlib.reload(feishu_auto_collector)
        self.assertEqual(mod.BASE_URL, "https://open.feishu.cn/open-apis")

    def test_lark_uses_international_host(self) -> None:
        mod = reload_with({"FEISHU_DOMAIN": " Lark "})
        self.assertEqual(mod.BASE_URL, "https://open.larksuite.com/open-apis")
        self.assertTrue(mod.build_authorize_url("cli_x").startswith("https://open.larksuite.com/open-apis/authen/v1/authorize?"))

    def test_unknown_domain_fails_loudly(self) -> None:
        with self.assertRaises(SystemExit):
            reload_with({"FEISHU_DOMAIN": "larksuite.cn"})


if __name__ == "__main__":
    unittest.main()
