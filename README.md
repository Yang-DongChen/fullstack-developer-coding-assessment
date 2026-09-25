# Full-Stack Developer Coding Interview Assessment

Candidate submission repository for the Aeris Health Full Stack coding assessment.

## Repository Structure

```text
.
├── A/                      # Task A - Python solution + tests
├── B/                      # Task B - Python solution + tests
├── C/                      # Task C - Xero integration review
├── app/                    # Full-stack Variant PDP application
│   ├── backend/            # FastAPI backend + API tests
│   └── frontend/           # React + TypeScript frontend + tests
├── .gitignore
└── README.md
```

## Requirements

- Python 3.11+
- Node.js 20.19+ or 22.12+
- npm
- Git

## Setup and Testing

### Task A

Run from the repository root:

```bash
python -m pytest -v A/test_solution.py
```

Task A is implemented in Python and includes validation, state transitions, idempotency, and tests for edge cases.

### Task B

Run from the repository root:

```bash
python -m pytest -v B/test_solution.py
```

Task B uses dynamic programming with tie-breaking rules and includes tests for feasibility, minimum warehouse count, cost, lexicographic tie-breaking, and larger inputs.

### Task C

Task C is a Markdown-based written review covering:

- Xero OAuth and tenant verification
- Authentication, scope, permission, and environment diagnosis
- Resumable incremental invoice synchronisation
- Rate limits and retry handling
- Idempotency and data integrity
- Observability and security

The detailed answer is in:

```text
C/README.md
```

### Full-Stack App — Backend

The backend uses Python, FastAPI, and in-memory storage.

Install dependencies:

```bash
cd app/backend
python -m pip install -r requirements.txt
```

Run backend tests:

```bash
python -m pytest -v
```

Start the API:

```bash
python -m uvicorn app:app --reload --port 8000
```

The FastAPI OpenAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### Full-Stack App — Frontend

The frontend uses React, TypeScript, and Vite.

Install dependencies:

```bash
cd app/frontend
npm install
```

Run frontend tests:

```bash
npm test
```

Start the development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

Build the frontend:

```bash
npm run build
```

## Application Overview

The Full-Stack App is a small Variant Product Detail Page (PDP) backed by a FastAPI API.

It demonstrates:

- Product and SKU selection
- Two option dimensions
- Server-side SKU, price, and stock validation
- Add-to-cart functionality
- Idempotency protection
- Concurrency protection against overselling
- Resilient frontend state handling
- Accessible controls and feedback
- Automated backend and frontend tests

## Architecture Notes

### Backend

The backend keeps product, SKU, cart, and idempotency data in memory.

The add-to-cart operation validates the SKU and current stock on the server. Price and stock values from the client are never trusted.

A process-level lock protects the critical stock check-and-decrement operation so two concurrent requests cannot both reserve the same final unit within the same process.

Idempotency records are stored by idempotency key and request fingerprint. Repeating the same request key with the same payload replays the previous result instead of adding the item again.

### Frontend

The frontend separates concerns into:

```text
src/api.ts       # API calls and HTTP error handling
src/domain.ts    # SKU and variant resolution logic
src/App.tsx      # UI state and interactions
src/App.test.tsx # frontend tests
```

The UI re-fetches product and cart state after add-to-cart so it can recover from newer server-side stock values.

## Assumptions

- The product catalogue contains one seeded product with multiple SKUs.
- Each SKU has its own ID, price, image, stock quantity, and option values.
- The backend uses in-memory storage because persistent storage is not required by the assessment.
- The cart represents the current application session and is not tied to authentication.
- The backend and frontend run as separate development processes.
- The Xero review in Task C is SDK-independent and assumes the current Xero Accounting API and OAuth documentation.

## Known Limitations

- Backend state is in memory and is lost when the process restarts.
- The stock lock protects concurrency only inside one Python process. A multi-process or distributed deployment would require database transactions or another shared concurrency mechanism.
- The frontend is intentionally focused on the assessment scope. Authentication, checkout, payment processing, and deployment are out of scope.
- The application is a small assessment project rather than a complete production commerce system.

## Testing

### Task A

```bash
python -m pytest -v A/test_solution.py
```

### Task B

```bash
python -m pytest -v B/test_solution.py
```

### Backend

```bash
cd app/backend
python -m pytest -v
```

### Frontend

```bash
cd app/frontend
npm test
npm run build
```

The repository includes automated tests for core state transitions, validation, idempotency, SKU resolution, duplicate-click protection, and the backend stock race.

## AI Tool Disclosure

AI-assisted tools were used as development support during this assessment.

AI assistance was used for areas including:

- Explaining assessment requirements
- Drafting and refining implementation ideas
- Generating and reviewing code
- Helping create test cases
- Reviewing documentation and edge cases

The submitted implementation was reviewed and tested by the candidate. The candidate is prepared to explain the submitted design choices, debug issues, and make small changes during a follow-up discussion.

## Security

No credentials, access tokens, refresh tokens, client secrets, or other secrets should be committed to the repository.

Sensitive configuration should be provided through environment variables or a secret-management system in a real deployment.

## Dependencies

### Backend

- FastAPI
- Uvicorn
- Pydantic
- Pytest
- HTTPX

### Frontend

- React
- React DOM
- TypeScript
- Vite
- Vitest
- @vitejs/plugin-react

## Submission Checklist

- [x] Repository contains Tasks A, B, C, and the Full-Stack App
- [x] Setup commands are documented
- [x] Backend and frontend test commands are documented
- [x] Assumptions and limitations are documented
- [x] AI assistance is disclosed
- [x] No credentials or tokens are committed
- [x] Repository is ready for reviewer access
