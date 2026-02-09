from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional
from email.utils import parsedate_to_datetime

import requests

from news_crawler.config import NotionConfig
from news_crawler.news_fetcher import Article


@dataclass
class NotionResult:
    created: int
    skipped: int


class NotionClient:
    def __init__(self, config: NotionConfig, timeout_seconds: int = 15) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            }
        )

    def add_articles(self, articles: Iterable[Article]) -> NotionResult:
        created = 0
        skipped = 0
        for article in articles:
            if not article.title or not article.url:
                skipped += 1
                continue
            payload = self._build_payload(article)
            response = self.session.post(
                "https://api.notion.com/v1/pages",
                json=payload,
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Notion API error ({response.status_code}): {response.text}"
                )
            created += 1
        return NotionResult(created=created, skipped=skipped)

    def _build_payload(self, article: Article) -> dict:
        props = self.config.properties
        payload = {
            "parent": {"database_id": self.config.database_id},
            "properties": {
                props["title"]: {
                    "rich_text": [{"text": {"content": article.title}}]
                },
                props["url"]: {"url": article.url},
                props["source"]: {
                    "rich_text": [{"text": {"content": article.source}}]
                },
            },
            "children": [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": article.title}}],
                        "is_toggleable": False
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": f"출처: {article.source} | 링크: {article.url}"}}]
                    }
                }
            ]
        }
        if article.published_at:
            # Convert to ISO 8601 format for Notion
            iso_date = self._convert_to_iso8601(article.published_at)
            payload["properties"][props["published_at"]] = {
                "date": {"start": iso_date}
            }
        if article.summary:
            payload["children"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": article.summary}}]
                }
            })
        return payload

    def _convert_to_iso8601(self, date_str: str) -> str:
        """Convert various date formats to ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss)."""
        try:
            # Try to parse RFC 2822 format (e.g., "Mon, 09 Feb 2026 10:06:00 +0900")
            dt = parsedate_to_datetime(date_str)
            # Return ISO 8601 date format
            return dt.strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            # If it's already in ISO format or another format, return as is
            return date_str
