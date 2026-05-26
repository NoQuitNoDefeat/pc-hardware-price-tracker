from fastapi import FastAPI

app = FastAPI(title="PC Hardware Price Tracker", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
