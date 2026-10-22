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

### How to Run Tests Using Docker

1. Ensure the Docker containers are running (see the steps above).
2. Run the tests inside the Docker container:
   ```bash
   docker-compose exec web pytest
   ```

### How to Run/Generate Migrations

1. Ensure the Docker containers are running (see the steps above).
2. To generate a new migration, run the following command inside the Docker container:
   ```bash
   docker-compose exec web alembic revision --autogenerate -m "<migration_message>"
   ```
3. To apply migrations, run:
   ```bash
   docker-compose exec web alembic upgrade head
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

### How to Run Tests Using Virtual Environment and Poetry

1. Ensure the virtual environment is activated (see the steps above).
2. Run the tests:
   ```bash
   poetry run pytest
   ```

### How to Run/Generate Migrations

1. Ensure the virtual environment is activated (see the steps above).
2. To generate a new migration, run:
   ```bash
   poetry run alembic revision --autogenerate -m "<migration_message>"
   ```
3. To apply migrations, run:
   ```bash
   poetry run alembic upgrade head
   ```
