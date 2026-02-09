from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NewsSourceConfig:
    name: str
    base_url: str
    params: Dict[str, Any] = field(default_factory=dict)
    items_path: str = "articles"
    title_path: str = "title"
    url_path: str = "url"
    published_at_path: str = "publishedAt"
    summary_path: Optional[str] = "description"
    api_key_env: Optional[str] = None
    api_key_param: Optional[str] = None
    api_key_header: Optional[str] = None


@dataclass
class NotionConfig:
    api_key: str
    database_id: str
    properties: Dict[str, str] = field(
        default_factory=lambda: {
            "title": "Title",
            "url": "URL",
            "source": "Source",
            "published_at": "PublishedAt",
            "summary": "Summary",
        }
    )


@dataclass
class AppConfig:
    sources: List[NewsSourceConfig]
    notion: NotionConfig
    timeout_seconds: int = 15

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        sources = [NewsSourceConfig(**source) for source in data.get("sources", [])]
        notion = NotionConfig(**data["notion"])
        timeout_seconds = data.get("timeout_seconds", 15)
        return cls(sources=sources, notion=notion, timeout_seconds=timeout_seconds)
