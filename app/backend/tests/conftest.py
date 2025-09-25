import pytest
from typing import Iterator
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event
from app.db.base import engine


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
