# News Crawler to Notion

This project fetches articles from multiple news APIs and saves them into a Notion database.
All credentials are provided via environment variables to keep secrets out of the repo.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1. Copy or edit `config/news_sources.json`.
2. Set environment variables:

```bash
export NOTION_API_KEY="your_notion_api_key"
export NOTION_DATABASE_ID="your_database_id"
export NEWSAPI_KEY="your_newsapi_key"
```

You can point to a different config file with `NEWS_SOURCES_FILE` or `--config`.

## Run

```bash
python main.py --config config/news_sources.json
```

## Notes

- This repo is public, so avoid committing secrets. Use environment variables instead.
- Each source supports an optional API key param or header. Use `api_key_param` or
  `api_key_header` in the config to pass keys safely.
