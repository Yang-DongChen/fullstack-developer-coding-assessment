# Full-Stack App - Variant PDP

A small production-minded product detail page backed by a FastAPI API and a React + TypeScript frontend.

## Stack

- Backend: Python 3.11+ / FastAPI
- Frontend: React / TypeScript / Vite
- Storage: in-memory
- Tests: pytest + FastAPI TestClient

## Seed data

The app contains one product with two option dimensions:

- Colour: Black, White
- Size: S, M, L, XL

There are 7 SKUs covering 7 of the 8 possible combinations. `White + XL` is an unavailable combination. `Black + L` exists but starts with quantity `0` (out of stock).

The frontend gets the variant price, image and stock from the API after a SKU is selected. The client never sends price or stock to the server.

## API contract

### GET `/api/products/{id}`

Returns the product, option dimensions, and all currently known SKUs.

Example:

```http
GET /api/products/pdp-001
```

`200 OK`

```json
{
  "id": "pdp-001",
  "name": "Everyday Cotton Tee",
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

`404`:

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Product does not exist.",
    "details": {}
  }
}
```

### POST `/api/cart/items`

Adds a server-known SKU to the current cart and reserves/decrements stock.

Required header:

```http
Idempotency-Key: unique-logical-request-id
```

Request:

```json
{
  "sku_id": "tee-black-s",
  "quantity": 2
}
```

`201 Created`:

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

Errors:

- `400 MISSING_IDEMPOTENCY_KEY` - required idempotency header is missing.
- `404 SKU_NOT_FOUND` - the SKU does not exist.
- `409 INSUFFICIENT_STOCK` - the requested quantity is above current server-side stock.
- `409 IDEMPOTENCY_KEY_REUSED` - the same key was used with a different request payload.
- `422 VALIDATION_ERROR` - request body validation fails, such as `quantity <= 0`.
- `500 INTERNAL_ERROR` - unexpected server failure. Internal exception details are not returned to the client.

The server derives price and stock from its own SKU data. Client-supplied price/stock are not accepted.

### GET `/api/cart`

Returns the current cart and total item count.

```http
GET /api/cart
```

`200 OK`

```json
{
  "items": [],
  "total_item_count": 2,
  "total_price": 5998
}
```

## Concurrency / overselling

The exercise uses in-memory storage, so the backend protects the inventory check and decrement with one `threading.Lock`.

The critical section is:

```text
check current stock
    -> reject if insufficient
    -> decrement stock
    -> update cart
    -> save idempotency result
```

Because those operations happen while holding the same lock, two concurrent requests cannot both observe the same final unit as available. One request succeeds and the other receives `409 INSUFFICIENT_STOCK`.

For a multi-process production deployment, this lock would not be enough because each process has its own memory. I would move inventory to a shared database and perform the reservation in a transaction with row locking or an atomic conditional update such as `UPDATE ... SET stock = stock - ? WHERE sku_id = ? AND stock >= ?`.

## Idempotency

The `Idempotency-Key` identifies one logical add-to-cart request.

For the same key and the same request payload, the original response is returned without changing the cart or stock again.

The server also hashes the request payload. Reusing an existing key with different data returns `409 IDEMPOTENCY_KEY_REUSED` instead of silently applying a different operation.

For a persistent production implementation, the idempotency records would be stored in a database/Redis with a suitable retention/expiry policy.

## Tests

Tests cover:

- product/seed data success
- successful add-to-cart
- missing/invalid input
- unknown SKU
- insufficient stock
- idempotent replay
- idempotency-key misuse
- concurrent final-unit stock race

Run them from `app/backend`:

```bash
pip install -r requirements.txt
pytest -v
```

## Run locally

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

FastAPI docs:

`http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

## Notes

The backend is intentionally small and framework-native. FastAPI provides automatic OpenAPI documentation, but this README documents the important request/response behaviour and error status codes required by the exercise.

## Frontend requirements covered

The React + TypeScript frontend includes:

- loading and retryable product-load error states
- incomplete selection and unavailable-combination states
- live SKU resolution for price, image, and stock
- quantity clamped to the selected SKU's current stock
- out-of-stock state
- add-to-cart progress, duplicate-click protection, success feedback, validation/stock/server error feedback
- a post-mutation product refresh so UI stock reflects server state after add-to-cart
- responsive layout for narrow mobile screens and desktop widths
- semantic fieldsets/buttons, visible keyboard focus, and ARIA live feedback
- separate API (`api.ts`), domain logic (`domain.ts`), and UI (`App.tsx`) concerns
- frontend tests for variant resolution, option availability, duplicate-click behaviour, and retryable product loading

Run frontend tests:

```bash
cd frontend
npm install
npm test
```

Build the frontend:

```bash
npm run build
```
