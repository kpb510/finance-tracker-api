from fastapi import FastAPI

app = FastAPI(title="Personal Finance Tracker API")

@app.get("/health")
def health_check():
    """Simple health check endpoint to confirm the API is up and running."""
    return {"status": "ok"}