from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api.health import router as health_router
from .api.auth import router as auth_router
from .api.sessions import router as sessions_router
from .api.chat import router as chat_router

app = FastAPI(title="Eloquent RAG Chatbot API")

# CORS (tighten later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["meta"])
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(chat_router)