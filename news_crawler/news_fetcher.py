from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List
import re

import requests

from news_crawler.config import NewsSourceConfig
from news_crawler.utils import get_by_path


@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: str | None
    summary: str | None


class NewsFetcher:
    def __init__(self, timeout_seconds: int = 15) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, source: NewsSourceConfig) -> List[Article]:
        response = self._request_source(source)
        response.raise_for_status()
        payload = response.json()
        items = get_by_path(payload, source.items_path) or []
        if not isinstance(items, list):
            raise ValueError(f"Items path '{source.items_path}' is not a list.")
        return [
            article
            for article in self._parse_items(items, source)
            if article.title and article.url
        ]

    def _request_source(self, source: NewsSourceConfig) -> requests.Response:
        params = dict(source.params)
        headers: Dict[str, str] = {}
        api_key = self._resolve_api_key(source)
        if api_key and source.api_key_param:
            params[source.api_key_param] = api_key
        if api_key and source.api_key_header:
            headers[source.api_key_header] = api_key
        # Add custom headers from environment variables
        for header_name, env_var_name in source.headers_env.items():
            env_value = _read_env(env_var_name)
            if env_value:
                headers[header_name] = env_value
        return requests.get(
            source.base_url,
            params=params,
            headers=headers,
            timeout=self.timeout_seconds,
        )

    def _resolve_api_key(self, source: NewsSourceConfig) -> str | None:
        if not source.api_key_env:
            return None
        return None if source.api_key_env is None else _read_env(source.api_key_env)

    def _parse_items(
        self, items: Iterable[Any], source: NewsSourceConfig
    ) -> Iterable[Article]:
        for item in items:
            if not isinstance(item, dict):
                continue
            title = get_by_path(item, source.title_path)
            url = get_by_path(item, source.url_path)
            published_at = get_by_path(item, source.published_at_path)
            summary = get_by_path(item, source.summary_path) if source.summary_path else None
            # Remove HTML tags from summary
            if summary:
                summary = re.sub(r'<[^>]+>', '', summary)
            yield Article(
                title=title or "",
                url=url or "",
                source=source.name,
                published_at=published_at,
                summary=summary,
            )


def _read_env(name: str) -> str | None:
    import os

    value = os.getenv(name)
    return value.strip() if value else None
