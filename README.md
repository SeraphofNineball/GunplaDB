# GunplaDB

A self-hosted database of every Gunpla kit ever made, with instruction manuals.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open <http://localhost:8080>

MinIO console (storage management): <http://localhost:9001>

## Services

| Service    | Purpose                    |
|------------|----------------------------|
| backend    | FastAPI REST API           |
| worker     | Celery background scraper  |
| frontend   | React SPA                  |
| nginx      | Reverse proxy              |
| db         | PostgreSQL                 |
| redis      | Task queue                 |
| minio      | Image & PDF storage        |

## Scraping

From the **Admin** tab in the UI:

- **Full Scrape** — scrapes all kits from GunplaCentral (can take several hours for 5000+ kits)
- **Update** — only fetches kits added since your last scrape
- **Fetch Manual** — pulls a Bandai instruction manual by its ID (find the ID in the URL at `manual.bandai-hobby.net/menus/detail/{ID}`)

## Manual Kit Entry

Click **Add Kit** in the Admin panel to add a kit manually. On any kit's page you can:

- Upload images
- Upload a PDF manual

## API Docs

<http://localhost:8080/docs>
