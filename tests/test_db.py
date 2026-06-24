from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import (
    Base, User, get_or_create_user, set_user_api_key, get_user_api_key, clear_user_api_key,
    save_analysis, get_user_history, get_analysis_by_id, delete_analysis, set_history_enabled,
)


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


def test_user_has_no_api_key_by_default():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")

    assert get_user_api_key(user, "claude") is None


def test_set_and_get_user_api_key_roundtrips():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")

    set_user_api_key(db, user, "claude", "sk-ant-secret-123")

    assert get_user_api_key(user, "claude") == "sk-ant-secret-123"
    assert user.anthropic_api_key_enc != "sk-ant-secret-123"


def test_different_providers_store_independent_keys():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")

    set_user_api_key(db, user, "claude", "claude-key")
    set_user_api_key(db, user, "chatgpt", "chatgpt-key")
    set_user_api_key(db, user, "gemini", "gemini-key")

    assert get_user_api_key(user, "claude") == "claude-key"
    assert get_user_api_key(user, "chatgpt") == "chatgpt-key"
    assert get_user_api_key(user, "gemini") == "gemini-key"


def test_clear_user_api_key_removes_it():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")
    set_user_api_key(db, user, "claude", "claude-key")

    clear_user_api_key(db, user, "claude")

    assert get_user_api_key(user, "claude") is None


def test_history_enabled_defaults_to_true():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")

    assert user.history_enabled is True


def test_set_history_enabled_toggles_flag():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")

    set_history_enabled(db, user, False)

    assert user.history_enabled is False


def test_save_analysis_and_list_for_user():
    db = _make_session()
    user = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")

    save_analysis(db, user, ["claude", "gemini"], "paste", "Yapıştırılan kod", "<div>r1</div>")
    save_analysis(db, user, ["claude"], "file", "test.py", "<div>r2</div>")

    history = get_user_history(db, user)
    assert len(history) == 2
    # en yeni en üstte
    assert history[0].source_label == "test.py"
    assert history[0].providers == "claude"
    assert history[1].providers == "claude,gemini"


def test_history_is_scoped_per_user():
    db = _make_session()
    user1 = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")
    user2 = get_or_create_user(db, google_id="g-2", email="c@d.com", name="Cem")

    save_analysis(db, user1, ["claude"], "paste", "Kod 1", "<div>r1</div>")
    save_analysis(db, user2, ["claude"], "paste", "Kod 2", "<div>r2</div>")

    assert len(get_user_history(db, user1)) == 1
    assert len(get_user_history(db, user2)) == 1
    assert get_user_history(db, user1)[0].source_label == "Kod 1"


def test_get_analysis_by_id_rejects_other_users_entries():
    db = _make_session()
    user1 = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")
    user2 = get_or_create_user(db, google_id="g-2", email="c@d.com", name="Cem")
    analysis = save_analysis(db, user1, ["claude"], "paste", "Kod 1", "<div>r1</div>")

    assert get_analysis_by_id(db, user1, analysis.id) is not None
    assert get_analysis_by_id(db, user2, analysis.id) is None


def test_delete_analysis_removes_it_and_rejects_other_users():
    db = _make_session()
    user1 = get_or_create_user(db, google_id="g-1", email="a@b.com", name="Ali")
    user2 = get_or_create_user(db, google_id="g-2", email="c@d.com", name="Cem")
    analysis = save_analysis(db, user1, ["claude"], "paste", "Kod 1", "<div>r1</div>")

    assert delete_analysis(db, user2, analysis.id) is False
    assert delete_analysis(db, user1, analysis.id) is True
    assert get_user_history(db, user1) == []
