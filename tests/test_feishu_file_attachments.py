from __future__ import annotations

import io
import json
import unittest
import zipfile
from unittest.mock import patch

import _paths  # noqa: F401  (puts tools/ on sys.path)
import feishu_auto_collector as fac

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
S = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'


def zipped(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


def docx(*paras: str) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paras)
    return zipped({"word/document.xml": f"<w:document {W}><w:body>{body}</w:body></w:document>"})


def file_msg(sender: str, key: str, name: str) -> dict:
    return {
        "message_id": f"om_{key}",
        "sender": {"id": sender, "id_type": "open_id"},
        "msg_type": "file",
        "body": {"content": json.dumps({"file_key": key, "file_name": name})},
        "create_time": "1700000000000",
    }


class ExtractFileTextTests(unittest.TestCase):
    def test_docx_paragraphs_and_entities(self) -> None:
        data = docx("User story", "A &amp; B", " ")
        self.assertEqual(fac.extract_file_text("spec.DOCX", data), "User story\nA & B")

    def test_xlsx_shared_inline_and_numbers(self) -> None:
        data = zipped({
            "xl/sharedStrings.xml": f"<sst {S}><si><t>Name</t></si><si><t>Huy</t></si></sst>",
            "xl/worksheets/sheet1.xml": (
                f"<worksheet {S}><sheetData>"
                '<row><c t="s"><v>0</v></c><c t="inlineStr"><is><t>Age</t></is></c></row>'
                '<row><c t="s"><v>1</v></c><c><v>30</v></c></row>'
                "</sheetData></worksheet>"
            ),
        })
        self.assertEqual(fac.extract_file_text("a.xlsx", data), "## sheet1.xml\nName\tAge\nHuy\t30")

    def test_plain_text(self) -> None:
        self.assertEqual(fac.extract_file_text("n.md", "xin chào".encode()), "xin chào")

    def test_unsupported(self) -> None:
        with self.assertRaises(ValueError):
            fac.extract_file_text("app.zip", b"PK")


class FileMessageTests(unittest.TestCase):
    def test_group_chat_records_target_files_only(self) -> None:
        page = {"code": 0, "data": {"has_more": False, "items": [
            file_msg("ou_target", "k1", "spec.docx"),
            file_msg("ou_other", "k2", "theirs.docx"),
        ]}}
        files: list = []
        with patch.object(fac, "api_get", return_value=page):
            msgs = fac.fetch_messages_from_chat("oc_x", "ou_target", 10, {}, files)
        self.assertEqual(msgs, [])
        self.assertEqual(files, [{"message_id": "om_k1", "file_key": "k1", "file_name": "spec.docx"}])

    def test_collect_files_dedupes_skips_and_truncates(self) -> None:
        files = [
            {"message_id": "m1", "file_key": "k1", "file_name": "spec.docx"},
            {"message_id": "m2", "file_key": "k1", "file_name": "spec.docx"},
            {"message_id": "m3", "file_key": "k3", "file_name": "app.zip"},
            {"message_id": "m4", "file_key": "k4", "file_name": "notes.txt"},
        ]
        blobs = {"k1": docx("x" * 50), "k4": b"oops"}

        def fake_download(message_id: str, file_key: str, config: dict) -> bytes:
            if file_key == "k4":
                raise RuntimeError("boom")
            return blobs[file_key]

        with patch.object(fac, "download_message_file", side_effect=fake_download) as dl, \
                patch.object(fac, "MAX_FILE_CHARS", 10):
            out = fac.collect_files(files, 20, {})
        self.assertEqual(dl.call_count, 2)
        self.assertIn("## spec.docx\n\nxxxxxxxxxx\n\n（已截断，原文 50 字符）", out)
        self.assertIn("## notes.txt\n（读取失败：boom）", out)
        self.assertIn("- app.zip", out)
        self.assertIn("共 3 个文件，读取 2 个", out)

    def test_collect_files_respects_limit(self) -> None:
        files = [{"message_id": f"m{i}", "file_key": f"k{i}", "file_name": f"{i}.txt"} for i in range(3)]
        with patch.object(fac, "download_message_file", return_value=b"hi") as dl:
            out = fac.collect_files(files, 1, {})
        self.assertEqual(dl.call_count, 1)
        self.assertIn("- 1.txt", out)


if __name__ == "__main__":
    unittest.main()
