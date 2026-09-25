# Full-Stack Developer Coding Interview Assessment

Candidate submission repository for the full-stack coding assessment.

## Repository Structure

```text
.
├── A/                    # Task A: Python solution + automated tests
├── B/                    # Task B: Python solution + automated tests
├── C/                    # Task C: Xero integration review (Markdown answers)
├── app/                  # Full-Stack App - Variant PDP
│   ├── backend/          # Python 3.11+ / FastAPI API and backend tests
│   └── frontend/         # React / TypeScript / Vite PDP and frontend tests
└── README.md
```

## Requirements

- Python 3.11+
- Node.js 18+ recommended
- npm
- Git

The assessment uses Python for Tasks A/B/C and a FastAPI + React/TypeScript stack for the full-stack app.

## Quick Start

### Task A

```bash
cd A
python -m pip install -r requirements.txt
python -m pytest -v
```

If Task A does not have a `requirements.txt`, run:

```bash
cd A
python -m pytest -v
```

### Task B

```bash
cd B
python -m pip install -r requirements.txt
python -m pytest -v
```

If Task B does not have a `requirements.txt`, run:

```bash
cd B
python -m pytest -v
```

### Task C

Task C is a written Markdown review. No server is required.

Open:

```text
C/README.md
```

It covers:

- OAuth and Xero tenant verification
- diagnosis of 401 / 403 / 404 failures
- resumable incremental invoice synchronisation
- 429 handling, backoff and retry budgets
- idempotency and data-integrity handling
- observability and secret management

Official Xero documentation links and the SDK/API-version assumptions are included in `C/README.md`.

## Full-Stack App - Variant PDP

The app is a small product detail page backed by a FastAPI API.

### Stack

- Backend: Python 3.11+ / FastAPI / Uvicorn
- Frontend: React / TypeScript / Vite
- Storage: in-memory
- Backend tests: pytest + FastAPI TestClient
- Frontend tests: Vitest + React Testing Library

### Backend setup

Open a terminal:

```bash
cd app/backend
python -m pip install -r requirements.txt
python -m pytest -v
python -m uvicorn app:app --reload --port 8000
```

The backend API is available at:

```text
http://127.0.0.1:8000
```

FastAPI OpenAPI documentation:

```text
http://127.0.0.1:8000/docs
```

Keep this terminal running while using the frontend.

### Frontend setup

Open a second terminal:

```bash
cd app/frontend
npm install
npm test
npm run build
npm run dev
```

Open the Vite URL shown in the terminal, normally:

```text
http://localhost:5173
```

### API contract

The app exposes three required endpoints:

#### GET `/api/products/{id}`

Returns the seeded product, option dimensions and current SKU data.

Example:

```http
GET /api/products/pdp-001
```

Successful response:

```json
{
  "id": "pdp-001",
  "name": "Everyday Cotton Tee",
  "description": "A simple everyday T-shirt with multiple colour and size variants.",
  "options": [
    {"name": "colour", "values": ["Black", "White"]},
    {"name": "size", "values": ["S", "M", "L", "XL"]}
  ],
  "skus": [
    {
      "id": "tee-black-s",
      "price": 2999,
      "available_quantity": 10,
      "image": "https://placehold.co/800x800?text=Black+S",
      "options": {"colour": "Black", "size": "S"}
    }
  ]
}
```

Status codes:

- `200` product returned successfully
- `404` product does not exist

#### POST `/api/cart/items`

Adds a SKU and quantity to the current in-memory cart.

Required header:

```http
Idempotency-Key: unique-logical-request-id
```

Request body:

```json
{
  "sku_id": "tee-black-s",
  "quantity": 2
}
```

Successful response:

```json
{
  "message": "Item added to cart.",
  "cart": {
    "items": [],
    "total_item_count": 2,
    "total_price": 5998
  }
}
```

Status codes:

- `201` item added successfully
- `400` missing idempotency key
- `404` SKU does not exist
- `409` insufficient stock
- `409` idempotency key reused with a different request
- `422` request validation failed
- `500` unexpected server error

The server uses its own SKU price and stock. Client-provided price or stock values are not accepted.

#### GET `/api/cart`

Returns the current cart and total item count.

```http
GET /api/cart
```

Example response:

```json
{
  "items": [],
  "total_item_count": 2,
  "total_price": 5998
}
```

### Structured errors

Errors use a consistent shape:

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Only 1 unit(s) are currently available.",
    "details": {
      "available_quantity": 1
    }
  }
}
```

Unexpected internal exception details are not returned to the browser.

## Full-Stack App design notes

### Product and SKU model

The seeded product has two option dimensions:

- Colour: Black, White
- Size: S, M, L, XL

There are 7 SKUs covering 7 of the 8 possible combinations.

- `White + XL` is intentionally unavailable.
- `Black + L` exists but starts out of stock.

Each SKU has its own ID, price, available quantity, image and option values.

### Frontend state handling

The frontend keeps selection state separate from server data and resolves the selected SKU from the complete option selection.

When the selected options change, the UI updates the corresponding:

- price
- product image
- stock status
- available quantity
- quantity control bounds

Impossible combinations are disabled instead of allowing the user to select a SKU that does not exist.

Quantity is clamped to the selected SKU's current available stock, including when the selected variant changes.

### Async and failure handling

The frontend explicitly handles:

- initial product loading
- retryable product-load failure
- incomplete variant selection
- invalid/unavailable combinations
- out-of-stock SKU
- add-to-cart in progress
- successful add-to-cart
- client/server validation failures
- insufficient stock
- unexpected server errors

After a successful cart mutation, the frontend refreshes product data so the displayed stock comes from the server instead of relying on stale client state.

This also helps when the backend returns newer stock than the initial product response or when network latency is introduced.

### Accessibility

The frontend uses semantic controls such as buttons and fieldsets, visible keyboard focus styles, labels, disabled states and ARIA live feedback for async success/error messages.

The layout is responsive for approximately 375 px mobile width and 1280 px desktop width.

### Separation of concerns

The frontend keeps responsibilities separate:

```text
frontend/src/
├── api.ts       # HTTP/API calls and API error handling
├── domain.ts    # SKU and variant-resolution logic
├── App.tsx      # React UI and interaction state
└── styles.css   # responsive presentation
```

This avoids putting API calls, SKU business logic and rendering concerns into one large component.

## Concurrency and idempotency

The backend uses a single in-process `threading.Lock` around the inventory check, stock decrement, cart update and idempotency record.

The critical section is:

```text
check current stock
    -> reject if insufficient
    -> decrement stock
    -> update cart
    -> save idempotency result
```

Therefore, two concurrent requests attempting to reserve the final unit cannot both succeed in the same Python process.

Repeated requests with the same `Idempotency-Key` and the same payload return the original result without decrementing stock again. Reusing the same key with a different payload is rejected with `409`.

For a real multi-process deployment, the in-memory lock would not be sufficient because separate processes do not share memory. A production system should use shared transactional storage and an atomic inventory update or row-level locking.

## Automated tests

### Task A

```bash
cd A
python -m pytest -v
```

### Task B

```bash
cd B
python -m pytest -v
```

### Full-stack backend

```bash
cd app/backend
python -m pytest -v
```

The backend tests cover successful operations, validation, idempotency and the final-unit stock race.

### Full-stack frontend

```bash
cd app/frontend
npm test
```

Frontend tests include meaningful cases for:

- variant resolution
- unavailable variant handling
- duplicate-click protection for Add to Cart
- product-load retry behaviour

### Production build check

```bash
cd app/frontend
npm run build
```

## Architecture / engineering trade-offs

The assessment intentionally uses in-memory storage to keep the implementation small and focused on API correctness, state management and concurrency behaviour.

Trade-offs:

- Restarting the backend resets product stock, cart contents and idempotency state.
- The `threading.Lock` protects a single Python process only.
- There is no authentication, checkout, payment processing or production deployment because those are outside the scope of the exercise.
- Remote placeholder images are used to keep the repository small and avoid committing binary assets.
- The frontend refreshes product data after a successful cart mutation instead of using a fully optimistic inventory update. This favours correctness and makes rollback logic unnecessary for the required flow.

## Task-specific assumptions

- Task A and Task B are evaluated from their own implementation and tests under `A/` and `B/`.
- Task C assumes the current Xero Accounting API documentation and documents its OAuth, tenant, scope, retry, synchronisation and security decisions in `C/README.md`.
- The Variant PDP uses one seeded product and an in-memory cart because persistent accounts and checkout are explicitly out of scope.

## AI Tool Disclosure

AI-assisted tools were used as development support during the assessment. They were used to help interpret task requirements, draft and review some boilerplate code, identify edge cases, suggest tests and improve documentation.

The submitted implementation was reviewed and adjusted for the assessment requirements. The candidate should be able to explain the main design decisions, including:

- server-side stock and price validation
- idempotency handling
- the in-process concurrency lock
- incremental / resumable synchronisation decisions in Task C
- frontend SKU resolution and async state handling
- the documented trade-offs and limitations

## Security / repository hygiene

No credentials, access tokens or secrets should be committed to this repository.

Before final submission, verify the working tree and repository contents, for example:

```bash
git status
git ls-files
```

Environment-specific secrets should be provided through environment variables or a secret manager rather than source code. The included `.gitignore` should be used to keep local environment files out of Git.

## Final submission checklist

Before submission, verify all of the following:

- [ ] Repository access is correct and the expected branch has been pushed.
- [ ] Task A tests pass.
- [ ] Task B tests pass.
- [ ] Task C answers and official Xero documentation links are present.
- [ ] Backend tests pass.
- [ ] Frontend tests pass.
- [ ] Frontend production build passes.
- [ ] The backend starts from the documented command.
- [ ] The frontend starts from the documented command.
- [ ] The full-stack app works without requiring authentication or external accounts.
- [ ] No credentials, access tokens or personal data are committed.
- [ ] AI assistance is disclosed.
- [ ] Main implementation decisions and limitations are documented and explainable.

## Submission

Push the repository after the final local verification:

```bash
git status
git add A B C app README.md
git commit -m "Complete full-stack coding assessment"
git push
```
