from __future__ import annotations

import unittest
from unittest.mock import patch

import _paths  # noqa: F401  (puts tools/ on sys.path)
import feishu_auto_collector as fac


class DepartmentUserSearchTests(unittest.TestCase):
    def test_finds_user_in_child_department_by_open_department_id(self) -> None:
        def fake_api_get(path, params, config, use_user_token=False):
            if path == "/contact/v3/departments/0/children":
                return {"code": 0, "data": {"items": [
                    {"name": "IT", "department_id": "custom-it", "open_department_id": "od-it"},
                ]}}
            if path.startswith("/contact/v3/departments/"):
                return {"code": 0, "data": {"items": []}}
            if path == "/contact/v3/users/find_by_department":
                # Like the real API: department_id is read as an open_department_id.
                users = {"0": [], "od-it": [{"name": "Gia Huy", "open_id": "ou_gh", "user_id": "u_gh"}]}
                if params["department_id"] not in users:
                    return {"code": 40004, "msg": "no dept authority error"}
                return {"code": 0, "data": {"items": users[params["department_id"]], "has_more": False}}
            raise AssertionError(path)

        with patch.object(fac, "api_get", side_effect=fake_api_get):
            user = fac._find_user_by_department("Gia Huy", {})
        self.assertEqual(user and user["open_id"], "ou_gh")


if __name__ == "__main__":
    unittest.main()
