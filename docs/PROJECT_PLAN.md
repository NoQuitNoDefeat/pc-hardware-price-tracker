# PC Hardware Price Tracker — Project Planning Document

> Status: Planning document only. This `docs/PROJECT_PLAN.md` file exists; no application code has been created and no packages have been installed.
> Date: 2026-05-26
> MVP Stack: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Jinja2, SQLite, pytest, python-dotenv

---

## 1. Product Definition and Non-Goals

### 1.1 What this project IS
A **local, single-user, manually curated** price tracking tool for PC hardware. The user manually confirms which products they care about and which specific platform offers belong to those products. The system records explicit, immutable price snapshots from clearly labeled sources so the user can review history and make informed purchase decisions.

The system is a **decision-support journal**, not a search engine, not a crawler, not a shopping bot.

### 1.2 What this project IS NOT (Non-Goals)
- A web-wide price search engine.
- A crawler-first system. The product identity of an offer is never inferred from a crawl.
- An LLM-driven product matcher.
- An app automation framework.
- A checkout / payment / ordering bot.
- A captcha / anti-bot / login-restriction bypass tool.
- A cookie-export tool. (Later phases will use Playwright persistent browser context, not raw cookie injection.)
- A high-concurrency or multi-tenant service.
- A coupon-claiming or auto-add-to-cart system.

### 1.3 Core Product Principles
1. **Manual confirmation is the gate.** No offer enters tracking without `manual_confirmed = True`.
2. **URL is an entry point, not an identity.** A `Product` exists independently of any URL; URLs are attached to it via `TrackedOffer`.
3. **Standard product identity.** One canonical `Product` row can have many `TrackedOffer` rows across platforms.
4. **Immutable price history.** `PriceSnapshot` rows are append-only. Corrections happen by adding a new snapshot with a `corrects_snapshot_id` reference (optional, future) — never by editing history.
5. **Explicit price source.** `source_type` is mandatory on every snapshot. Public web price, logged-in web price, manual app price, and manually entered price are **never mixed silently**.
6. **Correctness and auditability over automation.** When in doubt, prefer a manual workflow.
7. **MVP runs without Playwright, app automation, LLM matching, or full-web search.**

---

## 2. MVP Scope

The first deliverable supports the following user workflows:

### 2.1 In-Scope for MVP
1. **Product management**
   - Create, read, update, list, soft-delete `Product` records.
2. **Tracked offer management**
   - Create a `TrackedOffer` by entering a URL plus platform + product association.
   - Compute `normalized_url = original_url.strip()`.
   - Compute `url_key = sha256(normalized_url.encode("utf-8")).hexdigest()` (64 hex chars).
   - Store `original_url` in full; never truncate it for business logic.
   - Enforce uniqueness on `url_key`.
   - Toggle `manual_confirmed` and `status`.
3. **Manual price snapshot creation**
   - Add a `PriceSnapshot` with `source_type = manual_input`.
   - Required: `tracked_offer_id`, `source_type`, `price`, `currency`, `captured_at`.
   - Optional: `title_seen`, `shop_seen`, `stock_status`, `promotion_text`, `source_context`.
4. **Local admin UI (Jinja2 + FastAPI)**
   - List Products.
   - Product detail page → lists associated TrackedOffers.
   - TrackedOffer detail page → lists PriceSnapshot history (newest first).
   - Forms to create/edit Products, create/edit TrackedOffers (with manual confirmation toggle), and submit new PriceSnapshots.
5. **Data layer**
   - SQLite database in `./data/app.db`.
   - Alembic migrations from day 1.
6. **Tests**
   - pytest suite covering URL normalization, url_key computation, uniqueness constraints, manual confirmation gate, and snapshot immutability.

### 2.2 Source Type Implementation in MVP
| source_type        | Data model | MVP service implementation |
|--------------------|:----------:|:--------------------------:|
| `manual_input`     | Yes        | Yes (full UI + service)    |
| `web_public`       | Yes        | Deferred — design only, no fetcher |
| `web_logged_in`    | Yes        | Deferred — design only     |
| `manual_app_check` | Yes        | Deferred — design only     |

**MVP creation boundary:** The MVP service and UI create `PriceSnapshot` rows with `source_type = manual_input` **only**. The other three values — `web_public`, `web_logged_in`, `manual_app_check` — remain in the enum, schema, and database column definitions for forward compatibility, but no MVP code path produces them. `web_public` is the next phase extension (Phase 2) after the manual-input loop is solid; `web_logged_in` and `manual_app_check` are later phases per §3.

---

## 3. Deferred Scope (Explicitly Out of MVP)

These are documented so they are not silently introduced.

| Feature                                         | Phase         | Notes |
|-------------------------------------------------|---------------|-------|
| Public-web fetcher (`web_public` collector)     | Phase 2       | Plain HTTP fetch + parse; no logged-in, no anti-bot evasion. |
| Scheduled jobs via macOS `launchd`              | Phase 2       | Low-frequency only, e.g. once or twice per day. |
| Playwright persistent browser context           | Phase 3       | For `web_logged_in` only. User logs in interactively; profile persisted on disk. Never raw cookie export. |
| Manual app final-price entry workflow           | Phase 3       | A guided form for `manual_app_check`. Still 100% manual. |
| Snapshot diffing & price alert thresholds       | Phase 4       | Read-only notifications, no auto-purchase. |
| Multi-currency display / FX conversion          | Phase 4       | Storage is per-snapshot currency in MVP; conversion is a view concern. |
| CSV / Markdown export                           | Phase 4       | |
| Postgres migration                              | Future        | Schema is designed to be portable. |
| LLM-assisted product matching                   | Out of scope  | Manual only. |
| Full-web automatic search                       | Out of scope  | |
| App automation (UI scripting of native apps)    | Out of scope  | |
| Cookie injection / proxy pools / captcha bypass | Out of scope  | Never. |
| Auto add-to-cart / auto-checkout / payment      | Out of scope  | Never. |

---

## 4. System Architecture

### 4.1 High-Level View
```
                 ┌────────────────────────────────────┐
                 │  Browser (localhost admin UI)      │
                 └─────────────┬──────────────────────┘
                               │ HTTP
                 ┌─────────────▼──────────────────────┐
                 │  FastAPI app                       │
                 │  ┌──────────────┐  ┌────────────┐  │
                 │  │ HTML routes  │  │ JSON API   │  │
                 │  │ (Jinja2)     │  │ (optional) │  │
                 │  └──────┬───────┘  └─────┬──────┘  │
                 │         └────────┬───────┘         │
                 │         ┌────────▼─────────┐       │
                 │         │ Service layer    │       │
                 │         │ (pure functions  │       │
                 │         │  + ORM session)  │       │
                 │         └────────┬─────────┘       │
                 │         ┌────────▼─────────┐       │
                 │         │ SQLAlchemy 2.x   │       │
                 │         │ ORM models       │       │
                 │         └────────┬─────────┘       │
                 └──────────────────┼─────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │ SQLite (data/)    │
                          └───────────────────┘
                          ┌───────────────────┐
                          │ screenshots/      │  (later phases)
                          └───────────────────┘
```

### 4.2 Layering Rules
- **Routers** parse HTTP, call services, render templates or return JSON. No SQL.
- **Services** contain all business rules (URL normalization, manual confirmation gate, snapshot validation). They take a SQLAlchemy `Session` parameter; they do not import FastAPI.
- **Models** are SQLAlchemy ORM definitions. No business rules other than constraints.
- **Schemas** (Pydantic) validate request payloads only at the router boundary.

### 4.3 Process Model
- Single-process FastAPI app, run locally via `uvicorn`.
- No background workers in MVP. Scheduled fetchers are a Phase 2 concern (launchd → CLI command → service call).

---

## 5. Directory Structure Proposal

```
pc-hardware-price-tracker/
├── .env.example
├── .gitignore
├── .python-version              # 3.12
├── pyproject.toml
├── README.md
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory
│   ├── config.py                # settings via python-dotenv
│   ├── database.py              # engine, SessionLocal, Base
│   ├── models/
│   │   ├── __init__.py
│   │   ├── product.py
│   │   ├── tracked_offer.py
│   │   ├── price_snapshot.py
│   │   └── enums.py             # OfferStatus, SourceType
│   ├── schemas/
│   │   ├── product.py
│   │   ├── tracked_offer.py
│   │   └── price_snapshot.py
│   ├── services/
│   │   ├── url_normalizer.py    # normalize + url_key
│   │   ├── product_service.py
│   │   ├── tracked_offer_service.py
│   │   └── price_snapshot_service.py
│   ├── routers/
│   │   ├── ui_products.py
│   │   ├── ui_tracked_offers.py
│   │   ├── ui_price_snapshots.py
│   │   └── health.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── _macros.html
│   │   ├── products/
│   │   │   ├── list.html
│   │   │   ├── detail.html
│   │   │   └── form.html
│   │   ├── tracked_offers/
│   │   │   ├── detail.html
│   │   │   └── form.html
│   │   └── price_snapshots/
│   │       └── form.html
│   └── static/
│       └── style.css
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_url_normalizer.py
│   │   ├── test_product_service.py
│   │   ├── test_tracked_offer_service.py
│   │   └── test_price_snapshot_service.py
│   └── integration/
│       ├── test_products_ui.py
│       ├── test_tracked_offers_ui.py
│       └── test_price_snapshots_ui.py
└── data/                         # gitignored
    └── app.db
```

---

## 6. Data Model Design

All timestamps stored as UTC `DATETIME`. Money stored as `NUMERIC(12, 2)` (string-backed in SQLite, exact decimal). No floats for money.

### 6.1 `products`
| Column        | Type           | Constraints                              |
|---------------|----------------|------------------------------------------|
| `id`          | INTEGER PK     | autoincrement                            |
| `name`        | VARCHAR(255)   | NOT NULL                                 |
| `category`    | VARCHAR(64)    | NOT NULL (e.g. `cpu`, `gpu`, `ssd`, `ram`, `mobo`, `psu`, `case`, `cooler`, `other`) |
| `brand`       | VARCHAR(64)    | NOT NULL                                 |
| `model`       | VARCHAR(128)   | NOT NULL                                 |
| `notes`       | TEXT           | NULL                                     |
| `is_archived` | BOOLEAN        | NOT NULL DEFAULT FALSE (soft delete)     |
| `created_at`  | DATETIME       | NOT NULL                                 |
| `updated_at`  | DATETIME       | NOT NULL                                 |

### 6.2 `tracked_offers`
| Column                  | Type           | Constraints |
|-------------------------|----------------|-------------|
| `id`                    | INTEGER PK     | |
| `product_id`            | INTEGER        | NOT NULL, FK → products.id, ON DELETE RESTRICT |
| `platform`              | VARCHAR(64)    | NOT NULL (free-form label, e.g. `amazon`, `bestbuy`, `newegg`, `microcenter_web`, `local_shop_x`) |
| `original_url`          | TEXT           | NOT NULL — stored complete, never truncated for business logic |
| `normalized_url`        | TEXT           | NOT NULL — currently `original_url.strip()` |
| `url_key`               | CHAR(64)       | NOT NULL, UNIQUE — sha256 hex of normalized_url |
| `canonical_url`         | TEXT           | NULL — optional human-curated canonical form |
| `platform_item_id`      | VARCHAR(128)   | NULL |
| `platform_sku_id`       | VARCHAR(128)   | NULL |
| `title_at_confirm`      | VARCHAR(512)   | NULL |
| `shop_name`             | VARCHAR(128)   | NULL |
| `manual_confirmed`      | BOOLEAN        | NOT NULL DEFAULT FALSE |
| `status`                | VARCHAR(32)    | NOT NULL DEFAULT `needs_review` — enum: `active`, `temporarily_failed`, `needs_review`, `unavailable`, `disabled` |
| `last_error`            | TEXT           | NULL |
| `consecutive_failures`  | INTEGER        | NOT NULL DEFAULT 0 |
| `last_checked_at`       | DATETIME       | NULL |
| `created_at`            | DATETIME       | NOT NULL |
| `updated_at`            | DATETIME       | NOT NULL |

### 6.3 `price_snapshots`
**Append-only.** No `updated_at`. Edits are not allowed at the service layer; corrections are recorded as new snapshots.

| Column              | Type           | Constraints |
|---------------------|----------------|-------------|
| `id`                | INTEGER PK     | |
| `tracked_offer_id`  | INTEGER        | NOT NULL, FK → tracked_offers.id, ON DELETE RESTRICT |
| `source_type`       | VARCHAR(32)    | NOT NULL — enum: `manual_input`, `web_public`, `web_logged_in`, `manual_app_check` |
| `price`             | NUMERIC(12,2)  | NOT NULL, CHECK price >= 0 |
| `currency`          | CHAR(3)        | NOT NULL — ISO 4217 (e.g. `USD`, `CNY`, `EUR`) |
| `title_seen`        | VARCHAR(512)   | NULL |
| `shop_seen`         | VARCHAR(128)   | NULL |
| `stock_status`      | VARCHAR(32)    | NULL — free-form enum-ish (`in_stock`, `low_stock`, `out_of_stock`, `preorder`, `unknown`) |
| `promotion_text`    | TEXT           | NULL |
| `screenshot_path`   | TEXT           | NULL — relative path under `data/screenshots/` |
| `source_context`    | TEXT           | NULL — JSON blob for debugging (e.g. HTTP status, raw HTML hash, user notes) |
| `captured_at`       | DATETIME       | NOT NULL — when the price was observed (not when row was created) |
| `created_at`        | DATETIME       | NOT NULL — server time of row insert |

### 6.4 Enums (Python side)
```text
OfferStatus  = {active, temporarily_failed, needs_review, unavailable, disabled}
SourceType   = {manual_input, web_public, web_logged_in, manual_app_check}
StockStatus  = {in_stock, low_stock, out_of_stock, preorder, unknown}
ProductCategory = {cpu, gpu, ssd, ram, mobo, psu, case, cooler, other}
```
Stored as strings in DB for portability + Alembic friendliness; validated in service layer.

---

## 7. Database Constraints and Indexes

### 7.1 Constraints
- `tracked_offers.url_key`: **UNIQUE** — this is the bounded uniqueness identifier.
- `tracked_offers.product_id`: FK with `ON DELETE RESTRICT` (a Product with offers cannot be hard-deleted; archive instead).
- `price_snapshots.tracked_offer_id`: FK with `ON DELETE RESTRICT`.
- CHECK constraints:
  - `price_snapshots.price >= 0`
  - `tracked_offers.status IN (...)`
  - `price_snapshots.source_type IN (...)`
- Application-layer invariant: `price_snapshots` rows are never UPDATEd or DELETEd through services.

### 7.2 Indexes
- `products`: `idx_products_brand_model (brand, model)`, `idx_products_category (category)`.
- `tracked_offers`:
  - `uq_tracked_offers_url_key (url_key)` — unique.
  - `idx_tracked_offers_product_id (product_id)`.
  - `idx_tracked_offers_platform (platform)`.
  - `idx_tracked_offers_status (status)`.
  - `idx_tracked_offers_last_checked_at (last_checked_at)`.
- `price_snapshots`:
  - `idx_price_snapshots_offer_captured (tracked_offer_id, captured_at DESC)` — primary query path.
  - `idx_price_snapshots_source_type (source_type)`.

### 7.3 Why `url_key` and not `original_url` for uniqueness
- `original_url` is unbounded TEXT; some DB engines limit unique index key length.
- Hash gives a stable, fixed-length identifier that is safe to index and compare.
- We still keep `original_url` complete for audit and human review.
- `url_key` is also a convenient lookup token in URLs and logs without leaking the full URL.

---

## 8. URL Normalization and `url_key` Strategy

### 8.1 MVP Normalization Rules — Intentionally Minimal
```text
normalized_url = original_url.strip()
url_key        = sha256(normalized_url.encode("utf-8")).hexdigest()
```
That is the **complete** MVP rule. Whitespace trimming only.

### 8.2 Why so minimal
- Aggressive normalization (lowercasing the host, sorting query params, stripping tracking params) is **opinionated** and risks merging two genuinely distinct offer pages into one row. That violates Principle 2 (URL is an entry point, not an identity).
- Manual confirmation is the gate. If two URLs are "the same offer," the human confirms that by attaching both `TrackedOffer` rows to the same `Product`.
- Keeping the rule trivially auditable means anyone can reproduce `url_key` from the stored `normalized_url` with one line of Python.

### 8.3 What this implies
- Two visually similar URLs with different query strings, fragments, or trailing slashes produce **different** `url_key`s. That is intentional.
- A future phase MAY introduce per-platform canonicalization, but only in a separate `canonical_url` field, not by changing `normalized_url`. The historical `url_key` will not be rewritten.

### 8.4 Edge cases the service must handle
- Empty / whitespace-only URL → reject with validation error before hashing.
- Non-string input → reject at Pydantic schema.
- Extremely long URLs (>4KB) → still accepted; stored in `original_url` TEXT.
- Unicode in URL → encoded as UTF-8 before hashing (matches the spec).

### 8.5 Reference function (spec, not implementation)
```text
def normalize_and_key(original_url: str) -> tuple[str, str]:
    if not isinstance(original_url, str):
        raise ValueError("url must be a string")
    normalized = original_url.strip()
    if not normalized:
        raise ValueError("url is empty after strip")
    key = sha256(normalized.encode("utf-8")).hexdigest()
    return normalized, key
```

---

## 9. Admin UI Page Plan (Jinja2)

All pages are server-rendered HTML, no JS framework. Minimal CSS in `app/static/style.css`. Forms post via standard HTML.

| Route                                  | Method  | Purpose |
|----------------------------------------|---------|---------|
| `GET  /`                               | GET     | Dashboard: counts of Products, TrackedOffers (by status), recent PriceSnapshots. |
| `GET  /products`                       | GET     | List Products with filter by category/brand; archived toggle. |
| `GET  /products/new`                   | GET     | Form to create a Product. |
| `POST /products`                       | POST    | Create Product. |
| `GET  /products/{id}`                  | GET     | Product detail + list of associated TrackedOffers. |
| `GET  /products/{id}/edit`             | GET     | Edit Product form. |
| `POST /products/{id}`                  | POST    | Update Product. |
| `POST /products/{id}/archive`          | POST    | Soft-archive Product. |
| `GET  /tracked-offers/new?product_id=` | GET     | Form to create a TrackedOffer for a Product. |
| `POST /tracked-offers`                 | POST    | Create TrackedOffer (computes normalized_url, url_key, sets `manual_confirmed`). |
| `GET  /tracked-offers/{id}`            | GET     | Offer detail + PriceSnapshot history (paginated, newest first). |
| `GET  /tracked-offers/{id}/edit`       | GET     | Edit offer (incl. toggling `manual_confirmed`, `status`). |
| `POST /tracked-offers/{id}`            | POST    | Update offer. |
| `GET  /price-snapshots/new?offer_id=`  | GET     | Form to add a manual PriceSnapshot. In MVP the form creates `source_type = manual_input` only; the field is rendered as an explicit, read-only badge so the user is never confused about the source. |
| `POST /price-snapshots`                | POST    | Create PriceSnapshot. |
| `GET  /healthz`                        | GET     | Liveness. |

UI rules:
- `source_type` is always shown as a labeled, color-coded badge in any snapshot list. No implicit display of "the price."
- A TrackedOffer with `manual_confirmed = False` shows a prominent "**Needs review — not tracked**" banner and disables "Add Snapshot" action.
- Currency is shown next to every price; no implicit currency.

---

## 10. Service Layer Plan

Each service is a module of pure functions taking a SQLAlchemy `Session`. No global state. No HTTP awareness.

### 10.1 `url_normalizer.py`
- `normalize_and_key(original_url) -> (normalized_url, url_key)`

### 10.2 `product_service.py`
- `create_product(session, payload) -> Product`
- `update_product(session, product_id, payload) -> Product`
- `archive_product(session, product_id) -> Product`
- `get_product(session, product_id) -> Product | None`
- `list_products(session, filters) -> list[Product]`

### 10.3 `tracked_offer_service.py`
- `create_tracked_offer(session, payload) -> TrackedOffer`
  - Computes normalized_url, url_key.
  - Enforces `manual_confirmed` semantics: caller may pass `True` only if all required confirm fields are present (`platform`, `product_id`, `title_at_confirm`, `shop_name`).
  - Rejects duplicate `url_key` with a clear error.
- `update_tracked_offer(session, offer_id, payload) -> TrackedOffer`
- `confirm_tracked_offer(session, offer_id) -> TrackedOffer`
- `set_status(session, offer_id, new_status) -> TrackedOffer`
- `get_tracked_offer(session, offer_id) -> TrackedOffer | None`
- `list_tracked_offers(session, filters) -> list[TrackedOffer]`

### 10.4 `price_snapshot_service.py`
- `create_price_snapshot(session, payload) -> PriceSnapshot`
  - **MVP creation policy (strict):** validates `source_type == "manual_input"` and **rejects** any other value at the service boundary, including `web_public`, `web_logged_in`, and `manual_app_check`. The MVP service therefore validates `source_type` against the **MVP creation policy**, not merely the full enum.
  - The three non-`manual_input` values remain defined in the `SourceType` enum, the Pydantic schema, and the database `source_type` CHECK constraint for **forward compatibility only** — they are not MVP creation paths and the MVP UI form does not offer them. Each will be unlocked by its own future phase (per §3): `web_public` by the Phase 2 public-web fetcher, `web_logged_in` by the Phase 3 Playwright workflow, `manual_app_check` by the Phase 3 manual-app entry workflow.
  - Validates that the parent `TrackedOffer.manual_confirmed == True`.
  - Validates `price >= 0`, `currency` ISO 4217-like.
  - Defaults `captured_at` to "now UTC" if not provided.
- `list_snapshots_for_offer(session, offer_id, limit, offset) -> list[PriceSnapshot]`
- `get_latest_snapshot(session, offer_id, source_type=None) -> PriceSnapshot | None`

There is **no** `update_price_snapshot` and **no** `delete_price_snapshot` in the service layer — by design.

---

## 11. Testing Strategy

### 11.1 Tooling
- `pytest`, `pytest-asyncio` (only if needed), `httpx` for testing FastAPI via `TestClient`.
- A `conftest.py` provides an in-memory SQLite engine per test, with all tables created via Alembic-generated metadata (or `Base.metadata.create_all` against a fresh engine for unit tests).

### 11.2 Unit tests
- **`test_url_normalizer`**
  - Strip whitespace produces expected normalized form.
  - Identical normalized URLs produce identical `url_key`.
  - Different by even one char produces different `url_key`.
  - Empty/whitespace-only raises.
  - Unicode URL hashed via UTF-8.
- **`test_product_service`** — CRUD + archive + filter list.
- **`test_tracked_offer_service`**
  - Duplicate `url_key` is rejected.
  - `manual_confirmed = True` without required fields is rejected.
  - Status transitions validated.
  - `original_url` is stored complete even when very long.
- **`test_price_snapshot_service`**
  - Snapshot on unconfirmed offer is rejected.
  - `manual_input` snapshot creation succeeds end-to-end (the only MVP creation path).
  - Schema/enum recognizes all four `source_type` values for forward compatibility; the MVP service exposes no creation path for `web_public`, `web_logged_in`, or `manual_app_check`.
  - Negative price rejected.
  - Missing currency rejected.
  - No public method exists to update or delete a snapshot.

### 11.3 Integration tests (HTTP layer)
- Create Product → create TrackedOffer (unconfirmed) → confirm → add Snapshot → list history.
- Attempt to add a snapshot to an unconfirmed offer → 4xx.
- Attempt to create two offers with the same URL → 4xx (or clear UI error).
- URL with leading/trailing whitespace ends up with the trimmed form stored in `normalized_url`.

### 11.4 Coverage target
- ≥ 90% for `app/services/` and `app/models/` in MVP. Routers covered by integration tests.

---

## 12. Git and Environment Setup Plan

### 12.1 `.gitignore` (must-have entries)
```
__pycache__/
*.pyc
.venv/
.env
.env.*
!.env.example
data/
!data/.gitkeep
data/screenshots/
logs/
*.log
*.db
*.sqlite
*.sqlite3
.alembic_cache/
playwright_profiles/
.pytest_cache/
.coverage
htmlcov/
.DS_Store
.idea/
.vscode/
```

### 12.2 `.env.example`
```
DATABASE_URL=sqlite:///./data/app.db
APP_ENV=local
APP_LOG_LEVEL=INFO
```
Real `.env` is **never** committed.

### 12.3 Python environment
- `pyproject.toml` declares dependencies. Use `uv` or `pip` + `venv` — user's choice; not a project decision.
- `.python-version` pins 3.12.

### 12.4 Tooling (suggested, not mandated for MVP)
- `ruff` for lint+format.
- `mypy` (lenient mode) for type checks on services.

### 12.5 Branching
- `main` is the default branch.
- Feature branches per milestone.
- No CI required for MVP; tests are run locally before merging.

---

## 13. Security and Safety Boundaries

These are hard rules. They are part of the product definition, not a code style preference.

1. **No automated checkout, payment, or ordering.** Ever. Not even via "harmless" wishlist add.
2. **No automated coupon claiming.**
3. **No automated add-to-cart.**
4. **No captcha, anti-bot, or login-restriction bypass.** If a site requires login, the user logs in by hand in a persistent Playwright profile (future phase). The tool does not exfiltrate or inject cookies into raw HTTP requests.
5. **No proxy pools.**
6. **No high-concurrency crawling.** When `web_public` is added (Phase 2), it runs at most a few requests per minute per host, with a per-host minimum interval enforced in the fetcher.
7. **No raw cookie export.** Logged-in collection uses Playwright persistent browser context only.
8. **No secrets in Git.** `.env`, database files, screenshots, browser profiles, and logs are gitignored.
9. **No third-party telemetry.** This is a local tool.
10. **Respect site terms.** The user is responsible for ensuring their use complies with each platform's terms of service. The tool defaults to manual-only.
11. **Screenshots stored locally** under `data/screenshots/`, never uploaded.
12. **Database file is local-only.** No remote replication in MVP.

---

## 14. Development Milestones (In Order)

| #   | Milestone                                | Scope |
|-----|------------------------------------------|-------|
| M0  | Repo bootstrap                           | pyproject, .gitignore, .env.example, FastAPI hello, healthz. |
| M1  | DB layer + Alembic                       | Engine, SessionLocal, Base, Alembic init. |
| M2  | Models + first migration                 | Product, TrackedOffer, PriceSnapshot tables + indexes + constraints. |
| M3  | URL normalization service                | `normalize_and_key` + full unit tests. |
| M4  | Product service + tests                  | CRUD + archive. |
| M5  | TrackedOffer service + tests             | Create with url_key, confirm, status transitions, dup detection. |
| M6  | PriceSnapshot service + tests (manual_input only) | Append-only enforcement, validation. |
| M7  | FastAPI HTML UI: Products                | List, detail, new, edit, archive. |
| M8  | FastAPI HTML UI: TrackedOffers           | New (from product page), detail w/ snapshot list, edit, confirm. |
| M9  | FastAPI HTML UI: PriceSnapshot create    | Manual snapshot form on offer detail page. |
| M10 | Dashboard + polish                       | Counts, recent snapshots, source_type badges, currency display. |
| M11 | End-to-end manual acceptance walkthrough | Real-data smoke test using one CPU, one GPU, one SSD. |

Phase 2+ milestones (deferred, not detailed here): `web_public` fetcher, launchd scheduler, Playwright persistent context, manual-app workflow, exports, alerts.

---

## 15. Acceptance Criteria per Milestone

**M0 — Repo bootstrap**
- `uvicorn app.main:app` starts; `GET /healthz` returns 200.
- `.gitignore` blocks `.env`, `data/`, `*.db`.
- `.env.example` committed; `.env` not committed.

**M1 — DB layer + Alembic**
- `alembic upgrade head` creates an empty schema with the `alembic_version` table.
- `app.database.get_session()` yields a working session against `DATABASE_URL`.

**M2 — Models + migration**
- `alembic upgrade head` creates `products`, `tracked_offers`, `price_snapshots` with all columns from §6.
- Unique index on `tracked_offers.url_key` exists.
- All §7 indexes exist (verified via `PRAGMA index_list`).
- `alembic downgrade base` cleanly drops them.

**M3 — URL normalization**
- All unit tests in §11.2 pass.
- `url_key` is 64 hex characters.
- Trimming-only behavior documented in the module docstring.

**M4 — Product service**
- Create / read / update / archive / list all work in tests.
- Archived products do not appear in default list, do appear with `include_archived=True`.

**M5 — TrackedOffer service**
- Cannot create two offers whose `normalized_url` strips to the same string.
- Cannot mark `manual_confirmed=True` without `platform`, `product_id`, `title_at_confirm`, `shop_name`.
- Status transitions to/from each of the five states succeed; invalid status string rejected.
- `original_url` of length 5,000 chars round-trips intact.

**M6 — PriceSnapshot service**
- Snapshot insertion on a confirmed offer succeeds for `source_type = manual_input` (the only MVP creation path); insertion on an unconfirmed offer is rejected with a clear error.
- The enum/schema recognizes `web_public`, `web_logged_in`, and `manual_app_check` for forward compatibility, but the MVP service and UI do not create snapshots with those values. Tests assert recognition at the schema level, not creation.
- No service-layer function exists to update or delete a snapshot (verified by test inspecting the public API).
- `captured_at` defaults to UTC now when not supplied.

**M7 — Product UI**
- List page renders products with category filter.
- Create form validates required fields and shows server-side errors inline.
- Archived products show with an "Archived" badge.

**M8 — TrackedOffer UI**
- From Product detail, "Add offer" goes to a form pre-populated with `product_id`.
- Submitting a URL with whitespace stores the trimmed form.
- Submitting a duplicate URL shows a clear error and does not create a row.
- Offer detail page shows `manual_confirmed` status prominently and disables snapshot creation when not confirmed.

**M9 — PriceSnapshot UI**
- From a confirmed offer, the snapshot form posts and the new row appears at the top of the history list.
- The snapshot list shows `source_type`, `price + currency`, `captured_at`, and `stock_status` in every row.

**M10 — Dashboard + polish**
- Dashboard shows counts and the 10 most recent snapshots.
- `source_type` is rendered as a badge with distinct color for each of the four values.
- Currency is shown adjacent to every price; no implicit currency anywhere.

**M11 — End-to-end manual acceptance**
- A 30-minute walkthrough creating 3 products, 3 offers, and 6 snapshots succeeds without console errors.
- DB file size is reasonable (< 5 MB).
- All tests pass; coverage ≥ 90% on services + models.

---

## 16. Risks and Mitigation

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| 1 | **Over-aggressive URL normalization** silently merges distinct offers. | Lost price history fidelity. | Keep MVP rule as `.strip()` only. Document this explicitly. Any future canonicalization goes into `canonical_url`, never overwrites `normalized_url` or `url_key`. |
| 2 | **Source-type confusion** in UI causes user to mistake a `web_public` price for a logged-in price. | Bad purchase decisions. | Mandatory, colored, labeled `source_type` badge on every snapshot row. No "headline price" without source. |
| 3 | **Snapshot mutation** by accident (e.g. via Alembic data migration or direct ORM session). | Loss of audit trail. | No service method to update/delete snapshots. Document the invariant. Add a regression test asserting the public service API. |
| 4 | **SQLite → Postgres portability** later. | Migration pain. | Avoid SQLite-only features (no `JSON1`-dependent queries; `source_context` stored as TEXT and parsed in Python). Use Alembic from day 1. |
| 5 | **Long URLs** exceed expected sizes. | Index / DB errors. | `original_url` is unbounded TEXT. Uniqueness is on `url_key` (fixed 64 chars). |
| 6 | **Scope creep into automation.** | Violates product principles 6 and 7. | Deferred-scope table (§3) is the source of truth. Anything in §13 is a hard "no." |
| 7 | **Local data loss** (laptop wipe, accidental rm). | Loss of history. | Document a manual backup step in README (copy `data/app.db`). Encourage periodic export to CSV in Phase 4. |
| 8 | **Currency drift** (mixing USD and CNY rows in a single chart). | Misleading trend display. | Currency required on every snapshot; UI groups history charts by currency; no implicit FX. |
| 9 | **Manual confirmation drift** (offer page changes after confirmation). | Tracking stale page. | `title_seen` and `shop_seen` on each snapshot let the user spot drift. `status` can move to `needs_review`. |
| 10 | **Screenshot path leakage / unbounded growth.** | Disk fill, privacy. | Screenshots stored under `data/screenshots/` only, gitignored; deletion policy is a Phase 4 concern. |

---

## 17. First-Week Implementation Checklist

> Reminder: per current request, no code is written yet. This is the sequence to follow once implementation begins.

**Day 1 — Bootstrap (M0)**
- [ ] Init git repo, set default branch to `main`.
- [ ] Add `.gitignore` per §12.1.
- [ ] Add `.python-version` = `3.12`.
- [ ] Create `pyproject.toml` with: fastapi, uvicorn, sqlalchemy>=2, alembic, jinja2, python-dotenv, pydantic>=2, pytest, httpx.
- [ ] Add `.env.example`; create local `.env`.
- [ ] Create `app/main.py` with a FastAPI app and `/healthz`.
- [ ] Verify `uvicorn app.main:app --reload` runs.

**Day 2 — DB & first migration (M1, M2)**
- [ ] `app/database.py`: engine from `DATABASE_URL`, `SessionLocal`, `Base`.
- [ ] `alembic init alembic`; wire `env.py` to `Base.metadata`.
- [ ] Define `Product`, `TrackedOffer`, `PriceSnapshot` models per §6.
- [ ] Generate the initial migration; verify `upgrade head` and `downgrade base`.
- [ ] Manually inspect `PRAGMA index_list` for each table.

**Day 3 — URL normalization (M3)**
- [ ] `app/services/url_normalizer.py` per §8.5.
- [ ] `tests/unit/test_url_normalizer.py` with cases from §11.2.
- [ ] Confirm `url_key` length and determinism in tests.

**Day 4 — Product service (M4)**
- [ ] `app/services/product_service.py` per §10.2.
- [ ] Pydantic schemas in `app/schemas/product.py`.
- [ ] Unit tests covering CRUD + archive + filter.

**Day 5 — TrackedOffer service (M5)**
- [ ] `app/services/tracked_offer_service.py` per §10.3.
- [ ] Pydantic schemas.
- [ ] Tests: duplicate url_key rejected, confirm gate, status transitions, long URL.

**Day 6 — PriceSnapshot service (M6)**
- [ ] `app/services/price_snapshot_service.py` per §10.4 (manual_input path only).
- [ ] Pydantic schemas.
- [ ] Tests: append-only invariant; `manual_input` is the only MVP creation path and is covered end-to-end; MVP service rejects `web_public`/`web_logged_in`/`manual_app_check` creation attempts; schema/enum still recognizes all four values for forward compatibility; other validation rejections (negative price, missing currency, unconfirmed offer).

**Day 7 — Minimal admin UI (M7 partial)**
- [ ] `app/templates/base.html`, `_macros.html`, basic CSS.
- [ ] Products list + detail + create form wired to services.
- [ ] Integration test: full happy path through HTTP for creating a Product.
- [ ] Smoke test: load `/products` in a real browser and create one Product.

**End of week deliverable:** Database, migrations, three services with tests, and a working Products page in the admin UI. TrackedOffers and PriceSnapshots UI come in week 2 (M8, M9, M10, M11).

---

*End of planning document. This `docs/PROJECT_PLAN.md` file exists; no application code has been created and no packages have been installed.*
