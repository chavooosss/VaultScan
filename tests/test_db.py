from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base, User, get_or_create_user


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_creates_new_user_on_first_login():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")

    assert user.id is not None
    assert user.email == "a@b.com"
    assert db.query(User).count() == 1


def test_returns_existing_user_on_second_login_without_duplicating():
    db = _make_session()
    first = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")
    second = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")

    assert first.id == second.id
    assert db.query(User).count() == 1


def test_updates_profile_fields_when_google_data_changes():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="old@b.com", name="Eski Ad")
    updated = get_or_create_user(db, google_id="g-1", email="new@b.com", name="Yeni Ad", picture="http://x/p.png")

    assert updated.id == user.id
    assert updated.email == "new@b.com"
    assert updated.name == "Yeni Ad"
    assert updated.picture == "http://x/p.png"
    assert db.query(User).count() == 1


def test_different_google_ids_create_separate_users():
    db = _make_session()
    get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")
    get_or_create_user(db, google_id="g-2", email="c@d.com", name="Cem")

    assert db.query(User).count() == 2
