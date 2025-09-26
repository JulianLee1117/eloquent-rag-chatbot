import pytest
from typing import Iterator
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event
from app.db.base import engine, get_db
from fastapi.testclient import TestClient
import sys
import types


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Provide a database session wrapped in a SAVEPOINT that rolls back.

    This isolates each test even if code under test calls session.commit().
    Pattern based on SQLAlchemy testing docs.
    """
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    session = TestingSessionLocal()

    # Start the nested transaction (SAVEPOINT)
    session.begin_nested()

    # Restart the nested transaction when the SAVEPOINT ends
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess: Session, trans) -> None:  # type: ignore[no-redef]
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """FastAPI TestClient with DB dependency overridden to share the SAVEPOINT session.

    Also stubs the RAG retriever module to avoid Pinecone initialization during tests.
    """
    # Stub out app.rag.retriever before importing the FastAPI app
    if "app.rag.retriever" not in sys.modules:
        stub = types.ModuleType("app.rag.retriever")

        def retrieve_optimal(query_text: str, final_k: int = 4):  # type: ignore[unused-argument]
            return []

        stub.retrieve_optimal = retrieve_optimal  # type: ignore[attr-defined]
        sys.modules["app.rag.retriever"] = stub

    from app.main import app  # import only after stubbing retriever

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    try:
        yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
