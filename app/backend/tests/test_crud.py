from app.db import crud
from app.db.models import Role

def test_crud_cycle(db_session):
    sess = crud.get_or_create_anon_session(db_session, anon_id="pytest_anon")
    m1 = crud.append_message(db_session, sess.id, Role.user, "Q?", tokens_in=2)
    m2 = crud.append_message(db_session, sess.id, Role.assistant, "A!", tokens_out=1)

    msgs = crud.list_messages(db_session, sess.id)
    assert len(msgs) >= 2
    assert msgs[0].role == Role.user
    assert msgs[1].role == Role.assistant
    assert msgs[0].tokens_in == 2
    assert msgs[1].tokens_out == 1


def test_get_or_create_anon_session_idempotent(db_session):
    first = crud.get_or_create_anon_session(db_session, anon_id="same_id")
    second = crud.get_or_create_anon_session(db_session, anon_id="same_id")
    assert first.id == second.id
