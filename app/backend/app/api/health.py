from fastapi import APIRouter
from ..core.config import settings

router = APIRouter()

@router.get("/health")
def health():
    return {
        "ok": True,
        "env": settings.python_env,
        "db_url_driver": settings.postgres_url.split(":")[0],  # "postgresql+psycopg"
    }