from fastapi import FastAPI

from app.database import Base, engine
from app import models # noqa: F401 (import needed so Base "sees" the models)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Finance Tracker API")

@app.get("/health")
def health_check():
    """Simple health check endpoint to confirm the API is up and running."""
    return {"status": "ok"}