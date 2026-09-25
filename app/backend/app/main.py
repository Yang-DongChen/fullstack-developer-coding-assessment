from fastapi import FastAPI

app = FastAPI(title="Coding Assessment API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
