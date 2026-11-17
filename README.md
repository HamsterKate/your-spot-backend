# 📍 Your Spot Backend

Backend API for creating, managing, and sharing personal locations with private groups.

## ✨ Features

- 🔐 JWT authentication: registration, login, token refresh, and logout
- 👤 User profile management with avatar upload
- 📍 Place creation, viewing, updating, and deletion
- 🔎 Public place search and filtering by category and tags
- 🏷️ Categories and user-created tags
- 🖼️ Place photo upload, viewing, ordering, and deletion
- 👥 Private groups
- 🗄️ PostgreSQL for application data
- ☁️ MinIO for images and other media files
- 📚 Interactive API documentation with Swagger UI

> Swagger is the source of truth for all endpoints, request bodies, and responses.

## 🔗 Useful links

### Local environment

- API: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/api/v1/docs>
- ReDoc: <http://127.0.0.1:8000/api/v1/redoc>
- OpenAPI schema: <http://127.0.0.1:8000/api/v1/openapi.json>
- Health check: <http://127.0.0.1:8000/api/v1/health>
- MinIO Console: <http://127.0.0.1:9001>

### Production environment

- API: <https://spots.pp.ua/api/v2>
- Swagger UI: <https://spots.pp.ua/api/v2/docs>
- ReDoc: <https://spots.pp.ua/api/v2/redoc>
- OpenAPI schema: <https://spots.pp.ua/api/v2/openapi.json>
- Health check: <https://spots.pp.ua/api/v2/health>

## 🧰 Tech stack

- Python 3.12
- FastAPI
- PostgreSQL 17
- SQLAlchemy Async
- Alembic
- Pydantic
- Poetry
- Docker Compose
- MinIO
- Pytest
- Black

## 🚀 Run locally with Docker

### 1. Create an environment file

PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Fill in the required values in `.env`.

> Never commit `.env`: it contains database credentials and JWT/MinIO secrets.

### 2. Build and start containers

```bash
docker compose up --build -d
```

This starts:

| Service | Purpose | Local port |
| --- | --- | --- |
| `web` | FastAPI application | `8000` |
| `db` | PostgreSQL database | `5432` |
| `minio` | Object storage for avatars and place photos | `9000`, `9001` |

### 3. Apply database migrations

```bash
docker compose exec web poetry run alembic upgrade head
```

### 4. Verify the application

```bash
docker compose ps
```

Open Swagger: <http://127.0.0.1:8000/api/v1/docs>

Or check service health:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## ⚙️ Environment variables

The complete local template is available in [`.env.example`](.env.example).

| Variable | Description |
| --- | --- |
| `API_V1_PREFIX` | API URL prefix. Local default: `/api/v1` |
| `DATABASE_URL` | Async PostgreSQL connection URL |
| `JWT_SECRET_KEY` | Secret used to sign JWT tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token lifetime in days |
| `MINIO_ENDPOINT` | MinIO endpoint inside Docker, for example `minio:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key |
| `MINIO_SECRET_KEY` | MinIO secret key |
| `MINIO_BUCKET` | Bucket for uploaded files |
| `MINIO_SECURE` | Use HTTPS for MinIO connection (`false` locally) |

For production, the server uses:

```env
API_V1_PREFIX=/api/v2
```

This is why production endpoints start with `/api/v2`.

## 🖼️ Image storage

Avatars and place photos are stored in MinIO; image bytes are not stored as Base64 in PostgreSQL.

- Supported formats: JPEG, PNG, WebP
- Maximum image size: 5 MB
- A place can contain up to 10 photos
- Photo order is stored using the `position` field
- MinIO is not publicly exposed; images are served through backend endpoints

When reading a place, use the `photos` field from the response:

```json
{
  "photos": [
    {
      "id": "photo-uuid",
      "name": "photo.jpg",
      "content_type": "image/jpeg",
      "position": 0,
      "url": "https://.../places/{place_id}/photos/{photo_id}/content"
    }
  ]
}
```

The frontend should use the `url` returned by the API as the image source.

## 🗂️ Categories seed

To add predefined categories to the database:

```bash
docker compose exec web poetry run python seed_categories.py
```

The seed script is idempotent: running it again will not duplicate existing categories.

## 🧱 Database migrations

Generate a migration:

```bash
docker compose exec web poetry run alembic revision --autogenerate -m "describe change"
```

Apply all migrations:

```bash
docker compose exec web poetry run alembic upgrade head
```

Check whether models and migrations are in sync:

```bash
docker compose exec web poetry run alembic check
```

## ✅ Code quality and tests

Format code:

```bash
docker compose exec web poetry run black app
```

Check formatting without changing files:

```bash
docker compose exec web poetry run black --check app
```

Run tests:

```bash
docker compose exec web poetry run pytest
```

## 🛑 Stop the local environment

Stop containers while preserving database and MinIO data:

```bash
docker compose down
```

To also remove local Docker volumes and all local database/media data:

```bash
docker compose down -v
```

> ⚠️ `docker compose down -v` permanently removes local PostgreSQL and MinIO data.