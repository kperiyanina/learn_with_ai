from fastapi import FastAPI

from backend_api.routes_auth import router as auth_router
from backend_api.routes_plans import router as plans_router
from storage.database import init_database


init_database()
app = FastAPI(
    title="LearnWithAI API",
    version="1.0.0",
    description="REST API для планов обучения LearnWithAI.",
)
app.include_router(auth_router)
app.include_router(plans_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
