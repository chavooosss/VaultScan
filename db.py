import os
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, String, DateTime, Text, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from config import ENCRYPTION_KEY

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vaultscan.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# provider adı -> User modelindeki şifreli key kolonu
API_KEY_COLUMNS = {
    "claude": "anthropic_api_key_enc",
    "chatgpt": "openai_api_key_enc",
    "gemini": "gemini_api_key_enc",
}

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    google_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    picture: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    anthropic_api_key_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    openai_api_key_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    gemini_api_key_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

def _migrate_users_table():
    """create_all yeni tablo açar ama var olan tabloya kolon eklemez; SQLite için elle ALTER TABLE gerekir."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    # Eski plan/kota kolonları (plan, analyses_this_month, month_reset_at) artık
    # kullanılmıyor (BYOK mimarisine geçildi) ama SQLite'ta DROP COLUMN riskli
    # olduğu için tablo üzerinde zararsız şekilde kalmaya bırakıldı.
    existing = {col["name"] for col in inspector.get_columns("users")}
    statements = []
    for column in API_KEY_COLUMNS.values():
        if column not in existing:
            statements.append(f"ALTER TABLE users ADD COLUMN {column} TEXT")
    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))

def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_users_table()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _fernet() -> Fernet:
    return Fernet(ENCRYPTION_KEY.encode())

def set_user_api_key(db, user: User, provider: str, raw_key: str) -> None:
    column = API_KEY_COLUMNS[provider]
    encrypted = _fernet().encrypt(raw_key.encode()).decode()
    setattr(user, column, encrypted)
    db.commit()

def get_user_api_key(user: User, provider: str) -> Optional[str]:
    column = API_KEY_COLUMNS[provider]
    encrypted = getattr(user, column)
    if not encrypted:
        return None
    return _fernet().decrypt(encrypted.encode()).decode()

def clear_user_api_key(db, user: User, provider: str) -> None:
    column = API_KEY_COLUMNS[provider]
    setattr(user, column, None)
    db.commit()

def get_or_create_user(db, google_id: str, email: str, name: str, picture: str = "") -> User:
    user = db.query(User).filter(User.google_id == google_id).one_or_none()
    if user is None:
        user = User(google_id=google_id, email=email, name=name, picture=picture)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.email != email or user.name != name or user.picture != picture:
        user.email = email
        user.name = name
        user.picture = picture
        db.commit()
    return user
