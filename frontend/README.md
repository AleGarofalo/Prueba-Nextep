# Nextep Bookstore SPA

React, TypeScript and Vite with CSS Modules, TanStack Query, Axios and Lucide
icons. Inter and JetBrains Mono fonts are served locally. The implementation
follows the supplied UI specification and uses the existing Django API.

## Run

From the repository root:

```powershell
docker compose up --build
```

Open http://localhost:5173. The same command starts Django and PostgreSQL, with
migrations applied automatically. For optional demo data:

```powershell
docker compose exec backend python manage.py seed_demo_books
```

For frontend development outside Docker, keep the backend running, then run
these commands from `frontend/` with Node 24:

```powershell
npm ci
npm run dev
```

Optional configuration is documented in `.env.example`. `VITE_API_URL=/api`
uses Vite's same-origin proxy to `API_PROXY_TARGET` (localhost:8000 by default,
backend:8000 inside Compose). The proxy strips `/api` before forwarding. A
production static deployment must provide the same reverse proxy, or build with
an explicit API URL and configure Django CORS/allowed hosts for that origin.
Only `VITE_` variables are exposed to the browser; never put secrets in them.

## Workflows

- Global inventory KPIs, 300ms debounced title/author/ISBN search, combined
  category/low-stock filters, sortable IDs and server pagination (10/25/50).
- Responsive table and cards, ISBN copying, book detail, create/edit and confirmed
  deletion. Theme, currency and preferred view persist in browser storage.
- Strict form validation: ISBN-10/13 checksums with separator normalization,
  required title/author/category/country, positive two-decimal USD cost and
  nonnegative integer stock. Duplicate ISBN errors stay attached to the form.
- Native dialogs with focus management, Escape/backdrop dismissal, accessible
  labels, toasts, retryable errors, skeletons and empty states.
- Pricing automatically calls the POST action, displays the real exchange rate,
  converted cost, 40% markup, final saved amount, source and timestamps. Recalculate
  requests another calculation; Done closes the already-saved result.

The header's EUR/USD/GBP/MXN selector converts saved prices for display using
`GET /books/exchange-rate`. It never changes their persisted denomination.
`GET /books/summary` supplies whole-inventory metrics and the configured local
currency, independently of list filters and pagination.

HTTP 400 errors bind to form fields. Missing books (404) trigger a notification
and inventory refresh. Server failures (500) show retry controls. A 503 pricing
response shows that no new price was saved; it never pretends a fallback succeeded.
Successful fallback responses show an amber notice identifying the actual default
or stale cached rate. Provider attribution appears in the pricing dialog.

## Checks

From `frontend/`:

```powershell
npm test
npm run build
npm run test:e2e
```

The browser suite requires the application running at localhost:5173 and the
25-book demo dataset. It uses installed Microsoft Edge on Windows; on other
platforms first run `npx playwright install chromium`. Browser tests create and
remove their own books. They cover CRUD and persistence, validation, pagination,
filters, display conversion, mobile layouts, keyboard behavior, accessibility
scans, loading/empty states, and simulated 404/500/503/fallback responses.
Reports and screenshots are written to ignored `playwright-report/` and
`test-results/` directories. Backend tests mock the external provider, so failure
and fallback behavior is deterministic and does not depend on the public API.

## Source map

- `src/api/apiClient.ts`: request contract, timeouts and safe HTTP error mapping.
- `src/hooks/useInventory.ts`: query caching, cancellation and debounce.
- `src/lib/validation.ts`: form rules and ISBN checksums.
- `src/components/`: layout, KPIs, inventory views, dialogs and feedback.
- `src/index.css`, `src/styles/`: shared light/dark tokens and reusable controls.
- `tests/unit/`, `tests/e2e/`: validation/client and full browser workflows.
