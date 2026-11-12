# Bookstore Inventory System

Inventory monorepo for the Nextep technical exam. The Django REST Framework
backend implements the Book model, CRUD, category search, low-stock filtering
and exchange-rate pricing with a 40% markup. PostgreSQL 15 stores the data.
The frontend is initialized with React + Vite + Tailwind CSS + TanStack Query.

## Requirements and startup

Install Docker Desktop with Docker Compose support and start its engine. The
backend image uses Python 3.12 and installs `bookstore-inventory-api/requirements.txt`.
Python 3.11+ is supported for local backend development.

From the repository root in PowerShell, create the environment file only if it
does not already exist:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Replace the placeholder database password and `DJANGO_SECRET_KEY` in `.env`.
The existing `POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PASSWORD` names remain
supported. New environment files use `DB_NAME`, `DB_USER` and `DB_PASSWORD`;
nonempty `DB_*` values take precedence in both Django and Compose.

```powershell
docker compose up --build
```

The backend waits for PostgreSQL, applies pending migrations, then starts Django
at http://localhost:8000. PostgreSQL data is stored in the `postgres_data` volume.
Stop containers while retaining data with `docker compose down`.

For a backend container that was already running when code changed:

```powershell
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test inventory
```

Migration `0002_align_exam_book_fields` renames `price` to `cost_usd` and `stock`
to `stock_quantity`, retaining their values, book IDs and timestamps. It adds
nullable `selling_price_local` and `supplier_country`, with an empty country for
existing books whose origin is unknown. The existing initial migration is kept.

## Book data and validation

Create a book with the PDF's payload:

```json
{
  "title": "El Quijote",
  "author": "Miguel de Cervantes",
  "isbn": "978-84-376-0494-7",
  "cost_usd": "15.99",
  "selling_price_local": null,
  "stock_quantity": 25,
  "category": "Literatura Clásica",
  "supplier_country": "ES"
}
```

- `title` and `author` are required and cannot contain only whitespace.
- `isbn` accepts ISBN-10 or ISBN-13, including formatted values with spaces or
  hyphens. Separators are removed and an ISBN-10 check digit `x` becomes `X`
  before checksum and uniqueness checks. The example is stored as `9788437604947`.
- `cost_usd` is positive and has at most two decimal places.
- `stock_quantity` is a nonnegative integer and defaults to zero.
- `selling_price_local` starts as null and is read-only through the CRUD API.
  Only the pricing action sets it. Changing `cost_usd` through the API clears an
  old selling price so it can be recalculated.
- `category` is optional. `supplier_country` is an uppercase two-letter country
  code, or an empty string when unknown; lowercase input is normalized.
- `id`, `created_at` and `updated_at` are read-only and automatically populated.

Money is returned as decimal strings to preserve precision. Normal model saves
run `full_clean()`. Database constraints also enforce positive costs,
nonnegative quantities and selling prices, and unique ISBNs. Bulk ORM operations
bypass model validation and normalization, as in standard Django.

## API routes

The canonical exam routes have no trailing slash:

| Method | Path | Success |
| --- | --- | --- |
| POST | `/books` | 201, created book |
| GET | `/books` | 200, paginated books |
| GET | `/books/{id}` | 200, book |
| PUT | `/books/{id}` | 200, updated book |
| PATCH | `/books/{id}` | 200, partial update |
| DELETE | `/books/{id}` | 204, empty response |
| GET | `/books/search?category=Literatura%20Cl%C3%A1sica` | 200, category results |
| GET | `/books/low-stock?threshold=10` | 200, books at or below the threshold |
| POST | `/books/{id}/calculate-price` | 200, calculation saved and returned |

The existing `/api/inventory/books/` URLs remain available as aliases, with their
trailing slash, including the new search, low-stock and pricing actions. Both
route families now use the exam's field names rather than `price` and `stock`.
The prefixed API root remains at `/api/inventory/`.

Lists, search and low-stock results return `count`, `next`, `previous` and
`results`, ordered by book ID. The default page size is 20; `page_size` can raise
it to a maximum of 100. Select a page with `page=2`.

Category matching ignores case and matches the whole category. The search action
requires a nonempty `category`. The low-stock action defaults to `threshold=10`,
includes the threshold boundary, and accepts zero. Invalid thresholds return 400.
Category filters also work on the low-stock action.

The regular list still supports combined query filters:

```text
GET /books?category=Fiction&low_stock=true&threshold=5&page_size=10
```

`low_stock` accepts `true`, `false`, `1` or `0`. Invalid data returns 400; missing
books and nonexistent pages return 404. A pricing failure without a usable
fallback returns 503. Unexpected server errors use HTTP 500. Model validation
errors are translated to field errors or `non_field_errors` in HTTP 400 responses.

## Usage examples

In PowerShell, create, retrieve, update, calculate and delete a book:

```powershell
$bookPayload = @{
    title = 'El Quijote'
    author = 'Miguel de Cervantes'
    isbn = '978-84-376-0494-7'
    cost_usd = '15.99'
    stock_quantity = 25
    category = 'Literatura Clásica'
    supplier_country = 'ES'
} | ConvertTo-Json

$createdBook = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/books' -ContentType 'application/json' -Body $bookPayload
Invoke-RestMethod -Uri "http://localhost:8000/books/$($createdBook.id)"
Invoke-RestMethod -Method Put -Uri "http://localhost:8000/books/$($createdBook.id)" -ContentType 'application/json' -Body $bookPayload
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/books/$($createdBook.id)/calculate-price" -ContentType 'application/json' -Body '{}'
Invoke-RestMethod -Uri 'http://localhost:8000/books/low-stock?threshold=10'
Invoke-RestMethod -Method Delete -Uri "http://localhost:8000/books/$($createdBook.id)"
```

Use an unused valid ISBN when creating the sample book.

## Suggested selling price

The local currency defaults to EUR. The pricing action accepts an empty JSON
body, or an optional matching `target_currency`:

```http
POST /books/1/calculate-price
Content-Type: application/json

{"target_currency": "EUR"}
```

Stored selling prices all use `LOCAL_CURRENCY`; a different requested currency
returns 400. Configure a different local currency and its fallback rate together
before calculating prices, and recalculate existing prices if that configuration
changes. Supplier country is independent of the local currency.

The service fetches USD rates from
`https://api.exchangerate-api.com/v4/latest/USD`, converts `cost_usd`, and applies
a fixed 40% markup. Decimal arithmetic retains the unrounded conversion for the
markup; displayed amounts are rounded to two places with `ROUND_HALF_UP`.

For the PDF's example rate of `0.85`, the response contains:

```json
{
  "book_id": 1,
  "cost_usd": "15.99",
  "exchange_rate": "0.85",
  "cost_local": "13.59",
  "margin_percentage": 40,
  "selling_price_local": "19.03",
  "currency": "EUR",
  "calculation_timestamp": "2026-11-12T18:00:00+00:00"
}
```

The response additionally includes `rate_source`, `rates_fetched_at`,
`is_fallback`, `provider` and `provider_url`. `calculation_timestamp` describes
this calculation, while `rates_fetched_at` describes the rate snapshot.

The result is saved atomically to `selling_price_local`, and `updated_at` is
refreshed. Rates are fetched before locking the book; the calculation then uses
its current saved cost. The response and subsequent GET return the saved price.

### Rate failures and defaults

HTTP failures, timeouts, connection errors, malformed JSON and invalid rates are
handled with these sources:

- `live`: valid rates fetched from the provider.
- `cache`: a validated snapshot fetched less than one hour ago.
- `stale_cache`: during an outage, a validated snapshot less than 24 hours old.
- `default`: during an outage without a usable snapshot, the configured default
  rate for the local currency. This default is never cached as a live rate.
- `identity`: USD-to-USD uses 1; the 40% markup still applies.

Both stale-cache and default-rate responses set `is_fallback=true`. Default and
identity rates have no provider fetch timestamp. If neither a provider rate nor
the configured fallback can produce a supported price, return 503 without saving.

The demo EUR fallback of **0.85** comes from the exam example and is not a current
market quote. The local currency and fallback can be set in `.env`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `LOCAL_CURRENCY` | `EUR` | Currency of all persisted local selling prices |
| `EXCHANGE_RATE_DEFAULT_RATE` | `0.85` for EUR; `1` for USD | Emergency USD-to-local rate |
| `EXCHANGE_RATE_API_URL` | `https://api.exchangerate-api.com/v4/latest/USD` | USD rates endpoint |
| `EXCHANGE_RATE_API_TIMEOUT` | `10` | Connection/read timeout in seconds |
| `EXCHANGE_RATE_CACHE_TTL` | `3600` | Fresh-cache window in seconds |
| `EXCHANGE_RATE_FALLBACK_TTL` | `86400` | Maximum cached snapshot age in seconds |

For a currency other than EUR or USD, explicitly configure its fallback rate.
Timeouts, rates and durations must be positive and finite; the fallback window
must be at least the fresh-cache window. An empty endpoint URL uses the default.
Changing container environment variables requires recreating the backend
container, for example with `docker compose up -d --force-recreate backend`.

Django's default cache is in memory per process and resets when that process
restarts. The configured default rate still supports calculations after restart
if the external API is unavailable. No API key is required for the public API.
Rates and attribution: [ExchangeRate-API](https://www.exchangerate-api.com/docs/free).
A client displaying converted prices should display the attribution link in
`provider_url`. The provider refreshes its data daily.

## Postman collection

Import [the exported collection](bookstore-inventory-api/postman/bookstore-inventory.postman_collection.json)
into Postman. Set `base_url`, `isbn`, `category` and `currency` in its collection
variables; the defaults target http://localhost:8000 and EUR. Use an unused valid
ISBN. Run requests in order: the collection saves the created ID, exercises CRUD,
category search, low stock and calculation, verifies the saved selling price,
then deletes only the created demo book. It also includes validation, 404 and
prefixed-route checks. Request scripts assert expected status codes and results.

The test suite exercises this exported request sequence on a separate test
database with mocked exchange rates, and verifies the PDF's pricing example,
normalization, fallback behavior and migration preservation.

## Demo data for manual testing

Load 25 fictional books into the development database with:

```powershell
docker compose exec backend python manage.py seed_demo_books
```

The command creates missing demo ISBNs and leaves existing records unchanged,
including edits you make to seeded books. Re-running it does not duplicate books
or reset costs, quantities or calculated prices. It does not call the exchange
rate provider or run automatically during container startup.

The dataset has five books in each of these categories: `Literatura Clásica`,
`Ciencia`, `Tecnología`, `Historia` and `Ficción`. Each category includes stock
quantities of 0, 5, 10, 11 and 25. All ISBNs have valid checksums, but the titles,
authors, costs and ISBN associations are fictional test data.

Try these requests in a browser or Postman:

```text
GET /books?page_size=5
GET /books?page=2
GET /books/search?category=Ciencia
GET /books/low-stock?threshold=10
GET /books/low-stock?threshold=0
```

Use a returned book ID for `GET /books/{id}` and
`POST /books/{id}/calculate-price` with body `{}`. Selling prices start as null
and are populated when that action is called. Live rates can differ from the
PDF's example; `rate_source` and `is_fallback` identify the rate actually used.
The exported Postman collection uses a separate ISBN, so its create/delete
sequence does not remove these 25 demo records.

## Development structure

- `bookstore-inventory-api/config/`: Django settings and root routes.
- `inventory/models.py`: persistence, constraints and model validation.
- `inventory/serializers.py`: API payload validation and normalization.
- `inventory/views.py` and `inventory/urls.py`: controllers and routes.
- `inventory/services.py`: rate integration, calculations and price persistence.
- `inventory/validators.py`: reusable ISBN validation and normalization.
- `inventory/tests/`: model, API, integration, collection and migration tests.

Local Python commands load the root `.env`. After installing the requirements
into the root `.venv`, run `./.venv/Scripts/python.exe ./bookstore-inventory-api/manage.py check`.
Running Django outside Docker requires an accessible PostgreSQL instance and
the corresponding `DB_HOST` and `DB_PORT`. `DEBUG` and `ALLOWED_HOSTS` are loaded
from the environment, with the older `DJANGO_` names retained as fallbacks.
Local Vite origins are allowed by default through CORS.

To start the existing frontend with Docker, enable its profile:

```powershell
docker compose --profile frontend up --build
```

The frontend uses http://localhost:5173, installs its lockfile with `npm ci`, and
keeps dependencies in the `frontend_node_modules` volume. Django's development
server and this Compose configuration are intended for local development.
