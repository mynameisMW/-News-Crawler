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
2. Create a `.env` file in the project root:

```bash
# .env
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_database_id
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
```

Or for Windows:
```cmd
copy .env.example .env
# Then edit .env with your actual credentials
```

### Getting Naver API Keys

1. Go to [Naver Developers](https://developers.naver.com/)
2. Register an application
3. Enable Search API (뉴스 검색)
4. Get your Client ID and Client Secret
5. Add them to `.env`

### Crawling Settings

In `config/news_sources.json`, you can customize the crawling behavior:

```json
{
  "params": {
    "query": "키워드",      // 📌 검색 키워드 (원하는 주제로 변경)
    "display": 10,        // 한 번에 가져올 기사 수 (1-100)
    "sort": "date"        // 정렬 기준: "date"(최신), "sim"(정확도)
  }
}
```

**Example queries:**
- `"query": "AI"` - AI 관련 뉴스
- `"query": "스포츠"` - 스포츠 뉴스
- `"query": "주식"` - 주식 뉴스
- `"query": "날씨"` - 날씨 뉴스

You can point to a different config file with `NEWS_SOURCES_FILE` or `--config`.

## Run

```bash
python main.py --config config/news_sources.json
```

## Notes

- This repo is public, so avoid committing secrets. Use environment variables instead.
- Each source supports an optional API key param or header. Use `api_key_param` or
  `api_key_header` in the config to pass keys safely.
