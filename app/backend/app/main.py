from fastapi import FastAPI
import logging
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api.health import router as health_router
from .api.auth import router as auth_router
from .api.sessions import router as sessions_router
from .api.chat import router as chat_router

app = FastAPI(title="Eloquent RAG Chatbot API")


def _configure_rag_logging() -> None:
    """Ensure RAG debug logs show up in console consistently.

    We attach a simple StreamHandler to our RAG loggers at DEBUG level.
    """
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    for name in ("rag.embedder", "rag.retriever", "services.chat", "utils.tokens"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.DEBUG)
        lg.propagate = False 
        if not lg.handlers:
            lg.addHandler(handler)


_configure_rag_logging()

# CORS (tighten later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, tags=["meta"])
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(chat_router)