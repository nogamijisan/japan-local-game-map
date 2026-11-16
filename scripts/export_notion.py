#!/usr/bin/env python3
"""Export approved game records from Notion to the GitHub Pages games.json.

Only public display fields are exported. Requires a read-only Notion API token.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


NOTION_VERSION = "2026-03-11"
NOTION_API_ROOT = "https://api.notion.com/v1/data_sources"
REQUIRED_PROPERTIES = (
    "タイトル",
    "無効",
    "掲載判定",
    "配信ステータス",
    "舞台になっている県",
    "配信形態",
)


def text_property(properties: dict, name: str) -> str:
    prop = properties.get(name) or {}
    kind = prop.get("type")
    if kind not in ("title", "rich_text"):
        return ""
    return "".join(
        part.get("plain_text", part.get("text", {}).get("content", ""))
        for part in prop.get(kind, [])
    ).strip()


def select_property(properties: dict, name: str) -> str:
    prop = properties.get(name) or {}
    kind = prop.get("type")
    option = prop.get(kind) if kind in ("select", "status") else None
    return option.get("name", "") if option else ""


def multi_select_property(properties: dict, name: str) -> list[str]:
    prop = properties.get(name) or {}
    return [opt["name"] for opt in prop.get("multi_select", []) if opt.get("name")]


def url_property(properties: dict, name: str) -> str:
    return (properties.get(name) or {}).get("url") or ""


def date_property(properties: dict, name: str) -> str:
    date = (properties.get(name) or {}).get("date") or {}
    return (date.get("start") or "")[:10]


def checkbox_property(properties: dict, name: str) -> bool:
    return (properties.get(name) or {}).get("checkbox") is True


def convert_page(page: dict) -> dict | None:
    """Return a public record, or None for anything not approved for publication."""
    if page.get("archived") or page.get("in_trash"):
        return None

    properties = page.get("properties") or {}
    missing = [name for name in REQUIRED_PROPERTIES if name not in properties]
    if missing:
        raise ValueError("Notionの必須カラムがありません: " + ", ".join(missing))

    if (
        checkbox_property(properties, "無効")
        or select_property(properties, "掲載判定") != "掲載対象"
        or select_property(properties, "配信ステータス") != "配信中"
    ):
        return None

    title = text_property(properties, "タイトル")
    prefectures = multi_select_property(properties, "舞台になっている県")
    platforms = multi_select_property(properties, "配信形態")
    if not title or not prefectures or not platforms:
        raise ValueError("掲載対象の作品にタイトル・県・配信形態の未入力があります")

    return {
        "title": title,
        "creator": text_property(properties, "作者・スタジオ"),
        "creatorUrl": url_property(properties, "作者ページ"),
        "url": url_property(properties, "配布ページ"),
        "prefectures": prefectures,
        "region": text_property(properties, "舞台地域"),
        "platforms": platforms,
        "price": select_property(properties, "価格"),
        "creatorType": select_property(properties, "制作主体"),
        "settingType": select_property(properties, "舞台種別"),
        "releaseDate": date_property(properties, "配信開始日"),
        "confirmed": checkbox_property(properties, "管理人確認済"),
        "disabled": False,
    }


def request_page(token: str, data_source_id: str, start_cursor: str | None) -> dict:
    payload: dict = {"page_size": 100}
    if start_cursor:
        payload["start_cursor"] = start_cursor

    req = Request(
        f"{NOTION_API_ROOT}/{data_source_id}/query",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    for attempt in range(5):
        try:
            with urlopen(req, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise RuntimeError(
                    f"Notion API HTTP {exc.code}。トークンの権限と台帳への接続を確認してください"
                ) from exc
            retry_after = exc.headers.get("Retry-After", "")
            delay = min(int(retry_after), 30) if retry_after.isdigit() else min(2**attempt, 30)
            time.sleep(delay)
        except (URLError, TimeoutError) as exc:
            if attempt == 4:
                raise RuntimeError("Notion APIへの接続に失敗しました") from exc
            time.sleep(min(2**attempt, 30))
    raise RuntimeError("Notion APIリトライ回数を超えました")


def fetch_all_pages(token: str, data_source_id: str) -> list[dict]:
    pages: list[dict] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        batch = request_page(token, data_source_id, cursor)
        results = batch.get("results")
        if not isinstance(results, list):
            raise ValueError("Notion APIの応答にresults配列がありません")
        pages.extend(results)
        if not batch.get("has_more"):
            return pages
        cursor = batch.get("next_cursor")
        if not cursor or cursor in seen_cursors:
            raise ValueError("Notion APIのページネーション情報が不正です")
        seen_cursors.add(cursor)


def export(token: str, data_source_id: str, output: Path) -> tuple[int, int, bool]:
    pages = fetch_all_pages(token, data_source_id)
    if not pages:
        raise ValueError("Notionから作品が1件も取得できません。既存のJSONを保持します")

    games = [game for page in pages if (game := convert_page(page)) is not None]
    if not games:
        raise ValueError("掲載対象が0件です。誤った空のJSONで上書きしないため処理を中断します")

    games.sort(key=lambda game: game["title"].casefold())
    contents = json.dumps(games, ensure_ascii=False, indent=2) + "\n"
    if output.exists() and output.read_text(encoding="utf-8") == contents:
        return len(pages), len(games), False

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=output.parent, delete=False
    ) as tmp:
        tmp.write(contents)
        temp_path = Path(tmp.name)
    os.replace(temp_path, output)
    return len(pages), len(games), True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("games.json"))
    args = parser.parse_args()
    token = os.getenv("NOTION_TOKEN", "").strip()
    data_source_id = os.getenv("NOTION_DATA_SOURCE_ID", "").strip()
    if not token or not data_source_id:
        print("NOTION_TOKENとNOTION_DATA_SOURCE_IDが必要です", file=sys.stderr)
        return 1

    try:
        total, published, changed = export(token, data_source_id, args.output)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"JSON更新を中止しました: {exc}", file=sys.stderr)
        return 1

    print(f"Notion {total}件 → 公開 {published}件 / JSON: {'更新' if changed else '変更なし'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
