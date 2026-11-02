# Your Spot Backend

Backend API for creating personal locations and sharing them with private groups.

## Preconditions
1. Copy the `.env.example` file to `.env` and fill in the required environment variables:
    ```bash
    copy .env.example .env
    ```

## How to Run the Project Using Docker

1. Ensure you have Docker and Docker Compose installed on your system.
2. Navigate to the project root directory.
3. Build and start the Docker containers:
   ```bash
   docker-compose up --build
   ```
4. The application will be available at `http://127.0.0.1:8000`.
5. To see Swagger documentation, visit `http://127.0.0.1:8000/docs`.

> **Note:** When you add or change dependencies in `pyproject.toml`, run `poetry lock`
> and rebuild the image (`docker-compose build web`), otherwise the container will
> keep using the old dependencies.

### How to Run Tests Using Docker

1. Ensure the Docker containers are running (see the steps above).
2. Run the tests inside the Docker container:
   ```bash
   docker-compose exec web pytest
   ```

### How to Run/Generate Migrations Using Docker

1. Ensure the Docker containers are running (see the steps above).
2. To generate a new migration, run the following command inside the Docker container:
   ```bash
   docker-compose exec web alembic revision --autogenerate -m "<migration_message>"
   ```
3. To apply migrations, run:
   ```bash
   docker-compose exec web alembic upgrade head
   ```

### How to Seed the Database Using Docker

1. Ensure the Docker containers are running and migrations are applied (see the steps above).
2. Run the seed script inside the `web` container:
   ```bash
   docker-compose exec web poetry run python seed_categories.py
   ```

If you see `ModuleNotFoundError: No module named '<module_name>'`, the image was built before
`<module_name>` was added to the dependencies. Rebuild it and try again:
```bash
docker-compose build web
docker-compose up -d
```

## How to Run the Project Using Virtual Environment and Poetry

1. Ensure you have Python and Poetry installed on your system.
2. Navigate to the project root directory.
3. Create a virtual environment and install dependencies:
   ```bash
   poetry install
   ```
4. Start the application:
   ```bash
   poetry run uvicorn app.main:app --reload
   ```
5. The application will be available at `http://127.0.0.1:8000`.
6. To see Swagger documentation, visit `http://127.0.0.1:8000/docs`.

> **Note:** When running outside Docker, the database host in `DATABASE_URL` must be
> `localhost` (the `db` hostname only resolves inside the Docker network). The Postgres
> container publishes port `5432` to your machine, so start it with
> `docker-compose up -d db`.

### How to Run Tests Using Virtual Environment and Poetry

1. Ensure the virtual environment is activated (see the steps above).
2. Run the tests:
   ```bash
   poetry run pytest
   ```

### How to Run/Generate Migrations Using Virtual Environment and Poetry

1. Ensure the virtual environment is activated (see the steps above).
2. To generate a new migration, run:
   ```bash
   poetry run alembic revision --autogenerate -m "<migration_message>"
   ```
3. To apply migrations, run:
   ```bash
   poetry run alembic upgrade head
   ```

### How to Seed the Database Using Virtual Environment and Poetry

1. Ensure the database is running and migrations are applied (see the steps above).
2. Run the seed script from the project root:
   ```bash
   poetry run python seed_categories.py
   ```

## About the Seed Script

`seed_categories.py` seeds the `categories` table with default values
(Cafe, Restaurant, Bar, Bakery, Street food, Museum, Park, Shopping).

Example output:

```
Categories seeded: 8 inserted, 0 already existed.
```

- The script is **idempotent**: it is safe to run multiple times. Existing categories
  (matched by ID or name) are skipped, not duplicated or overwritten.
- Category IDs are fixed UUIDs, so they stay consistent across environments
  (local, staging, production).
- To add or change default categories, edit the `CATEGORIES` dict in
  `seed_categories.py`. Renaming an existing category will not update it in a database
  that has already been seeded; that requires a migration or a manual update.