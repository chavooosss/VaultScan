from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base, User, get_or_create_user, check_and_increment_quota, FREE_MONTHLY_QUOTA


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


def test_premium_user_always_passes_quota_check():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")
    user.plan = "premium"
    db.commit()

    for _ in range(FREE_MONTHLY_QUOTA + 5):
        assert check_and_increment_quota(db, user) is True


def test_free_user_can_use_up_to_monthly_quota():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")

    for _ in range(FREE_MONTHLY_QUOTA):
        assert check_and_increment_quota(db, user) is True

    assert check_and_increment_quota(db, user) is False
    assert user.analyses_this_month == FREE_MONTHLY_QUOTA


def test_free_user_quota_resets_in_a_new_month():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")
    user.analyses_this_month = FREE_MONTHLY_QUOTA
    user.month_reset_at = datetime.now(timezone.utc) - timedelta(days=40)
    db.commit()

    assert check_and_increment_quota(db, user) is True
    assert user.analyses_this_month == 1


def test_free_user_with_no_reset_date_treated_as_needing_reset():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")
    user.month_reset_at = None
    db.commit()

    assert check_and_increment_quota(db, user) is True
    assert user.analyses_this_month == 1
