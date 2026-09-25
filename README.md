# Full-Stack Developer Coding Interview Assessment

Candidate submission repository.

## Repository Structure

```text
.
├── A/                    # Python solution + tests
├── B/                    # Python solution + tests
├── C/                    # Written answers
├── app/                  # FastAPI backend + React/TypeScript frontend
│   ├── backend/
│   └── frontend/
└── README.md
```

## Setup

> Replace placeholder commands/notes with the final assessment-specific details as the tasks are implemented.

### A

```bash
cd A
pytest
```

### B

```bash
cd B
pytest
```

### App — Backend

```bash
cd app/backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows CMD: .venv\Scripts\activate.bat
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run backend tests:

```bash
cd app/backend
pytest
```

### App — Frontend

```bash
cd app/frontend
npm install
npm run dev
```

Run frontend tests:

```bash
cd app/frontend
npm test
```

Build for production:

```bash
cd app/frontend
npm run build
```

## Architecture Notes

_To be completed during implementation._

## Assumptions

_To be completed during implementation._

## Known Limitations

_To be completed during implementation._

## Testing

Document all automated test commands here before submission.

## AI Tool Disclosure

AI-assisted tools were used only as development support where applicable. Before submission, document the areas where AI was used and ensure every submitted decision can be explained and defended during live review.

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
