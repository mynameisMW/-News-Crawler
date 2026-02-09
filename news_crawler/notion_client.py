from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

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
                    "title": [{"text": {"content": article.title}}]
                },
                props["url"]: {"url": article.url},
                props["source"]: {"select": {"name": article.source}},
            },
        }
        if article.published_at:
            payload["properties"][props["published_at"]] = {
                "date": {"start": article.published_at}
            }
        if article.summary:
            payload["properties"][props["summary"]] = {
                "rich_text": [{"text": {"content": article.summary}}]
            }
        return payload
