# Bookstore Inventory System

Initial development skeleton for an inventory monorepo. Business models, API
endpoints and exchange-rate integration are intentionally pending. The frontend
directory is reserved for manual React + Vite + Tailwind CSS + TanStack Query setup.

## Start the backend and database

Install Docker with Docker Compose support and start the Docker engine. From the
repository root in PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace `POSTGRES_PASSWORD` and `DJANGO_SECRET_KEY`. External API
settings may remain empty until that integration is implemented. Then run:

```powershell
docker compose up --build
```

PostgreSQL 15 stores its data in the `postgres_data` volume. The backend waits
for the database health check, applies Django's built-in migrations and starts
the development server at http://localhost:8000. All paths currently return 404
because no endpoints have been implemented yet.

Check configuration and Django setup with:

```powershell
docker compose config --quiet
docker compose exec backend python manage.py check
```

Stop the services while retaining database data with `docker compose down`.
This setup uses Django's development server and is intended for local development.

## Initialize the frontend later

The frontend service uses the optional `frontend` Compose profile. After manually
initializing the Vite application in `frontend/`, run `npm install` there and
retain the generated `package-lock.json`, which the container's `npm ci` requires.
Then start all three services:

```powershell
docker compose --profile frontend up --build
```

The Vite development server will be available at http://localhost:5173. Its
dependencies use a separate `frontend_node_modules` volume.

## Backend layers

- `models.py`: database models.
- `serializers.py`: request and response serialization.
- `views.py` and `urls.py`: HTTP controllers and routing.
- `services.py`: business operations and external API integration.
- `validators.py`: ISBN, cost and stock validation.

Configuration is loaded from environment variables. Local Python commands also
read the root `.env`; use `DB_HOST=127.0.0.1` and expose the database separately
if running Django outside Docker.

Dependency baseline: [Django 5.2 LTS](https://docs.djangoproject.com/en/5.2/releases/5.2/).
The optional frontend follows [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/).
