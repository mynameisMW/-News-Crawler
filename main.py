from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

from news_crawler.config import AppConfig
from news_crawler.news_fetcher import Article, NewsFetcher
from news_crawler.notion_client import NotionClient


def load_config(config_path: Path) -> AppConfig:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    notion = data.get("notion", {})
    notion["api_key"] = os.getenv("NOTION_API_KEY", "")
    notion["database_id"] = os.getenv("NOTION_DATABASE_ID", "")
    data["notion"] = notion
    if not notion["api_key"] or not notion["database_id"]:
        raise RuntimeError("NOTION_API_KEY and NOTION_DATABASE_ID must be set.")
    return AppConfig.from_dict(data)


def gather_articles(fetcher: NewsFetcher, config: AppConfig) -> List[Article]:
    articles: List[Article] = []
    for source in config.sources:
        articles.extend(fetcher.fetch(source))
    return articles


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch news from APIs and store them in Notion."
    )
    parser.add_argument(
        "--config",
        default=os.getenv("NEWS_SOURCES_FILE", "config/news_sources.json"),
        help="Path to the news sources JSON file.",
    )
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    app_config = load_config(config_path)
    fetcher = NewsFetcher(timeout_seconds=app_config.timeout_seconds)
    articles = gather_articles(fetcher, app_config)

    notion_client = NotionClient(app_config.notion, app_config.timeout_seconds)
    result = notion_client.add_articles(articles)
    print(
        f"Uploaded {result.created} articles to Notion."
        f" Skipped {result.skipped} articles."
    )


if __name__ == "__main__":
    main()
