"""No-network tests for the Notion-to-GitHub-Pages export rules."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export_notion  # noqa: E402


def rich_text(text):
    return {"type": "rich_text", "rich_text": [{"plain_text": text}]}


def choice(name):
    return {"type": "select", "select": {"name": name}}


def make_page(*, title="太宰府のゲーム", status="配信中", approval="掲載対象", invalid=False):
    return {
        "properties": {
            "タイトル": {"type": "title", "title": [{"plain_text": title}]},
            "作者・スタジオ": rich_text("制作者"),
            "作者ページ": {"type": "url", "url": "https://example.com/creator"},
            "配布ページ": {"type": "url", "url": "https://example.com/game"},
            "舞台になっている県": {
                "type": "multi_select",
                "multi_select": [{"name": "福岡県"}, {"name": "佐賀県"}],
            },
            "舞台地域": rich_text("福岡県太宰府市"),
            "配信形態": {
                "type": "multi_select",
                "multi_select": [{"name": "PC"}, {"name": "Steam"}],
            },
            "価格": choice("無料"),
            "制作主体": choice("個人・同人"),
            "舞台種別": choice("実在地域"),
            "配信開始日": {"type": "date", "date": {"start": "2025-07-08"}},
            "管理人確認済": {"type": "checkbox", "checkbox": True},
            "無効": {"type": "checkbox", "checkbox": invalid},
            "掲載判定": choice(approval),
            "配信ステータス": choice(status),
        }
    }


class ConverterTests(unittest.TestCase):
    def test_public_fields_and_multi_select(self):
        game = export_notion.convert_page(make_page())
        self.assertEqual(game["prefectures"], ["福岡県", "佐賀県"])
        self.assertEqual(game["platforms"], ["PC", "Steam"])
        self.assertEqual(game["releaseDate"], "2025-07-08")
        self.assertTrue(game["confirmed"])
        self.assertFalse(game["disabled"])
        self.assertNotIn("備考", game)
        self.assertNotIn("管理人確認済", game)

    def test_unconfirmed_is_unverified(self):
        page = make_page()
        del page["properties"]["管理人確認済"]
        self.assertFalse(export_notion.convert_page(page)["confirmed"])

    def test_invalid_is_excluded(self):
        self.assertIsNone(export_notion.convert_page(make_page(invalid=True)))

    def test_pending_or_ended_is_excluded(self):
        self.assertIsNone(export_notion.convert_page(make_page(approval="保留")))
        self.assertIsNone(export_notion.convert_page(make_page(status="配信終了")))

    def test_archived_is_excluded(self):
        page = make_page()
        page["archived"] = True
        self.assertIsNone(export_notion.convert_page(page))

    def test_missing_critical_field_fails_closed(self):
        page = make_page()
        del page["properties"]["無効"]
        with self.assertRaisesRegex(ValueError, "無効"):
            export_notion.convert_page(page)

    def test_no_prefecture_fails_closed(self):
        page = make_page()
        page["properties"]["舞台になっている県"]["multi_select"] = []
        with self.assertRaises(ValueError):
            export_notion.convert_page(page)


class ExportTests(unittest.TestCase):
    @patch.object(export_notion, "request_page")
    def test_pagination(self, request):
        request.side_effect = [
            {"results": [make_page(title="A")], "has_more": True, "next_cursor": "next"},
            {"results": [make_page(title="B")], "has_more": False, "next_cursor": None},
        ]
        pages = export_notion.fetch_all_pages("token", "id")
        self.assertEqual(len(pages), 2)
        self.assertEqual(request.call_count, 2)

    @patch.object(export_notion, "fetch_all_pages")
    def test_export_and_no_change(self, fetch):
        fetch.return_value = [make_page(), make_page(approval="保留")]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "games.json"
            self.assertEqual(export_notion.export("token", "id", output), (2, 1, True))
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))[0]["title"], "太宰府のゲーム")
            self.assertEqual(export_notion.export("token", "id", output), (2, 1, False))

    @patch.object(export_notion, "fetch_all_pages")
    def test_all_pending_does_not_overwrite(self, fetch):
        fetch.return_value = [make_page(approval="保留")]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "games.json"
            output.write_text('[{"existing": true}]', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "0件"):
                export_notion.export("token", "id", output)
            self.assertEqual(output.read_text(encoding="utf-8"), '[{"existing": true}]')


if __name__ == "__main__":
    unittest.main()
