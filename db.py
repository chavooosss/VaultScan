import os
import re
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, String, DateTime, Text, Boolean, ForeignKey, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from config import ENCRYPTION_KEY

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vaultscan.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True, pool_recycle=300)
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
    history_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    providers: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(20))
    source_label: Mapped[str] = mapped_column(String(255))
    result_html: Mapped[str] = mapped_column(Text)
    severity_counts: Mapped[str] = mapped_column(String(32), default="0,0,0,0")

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
    if "history_enabled" not in existing:
        statements.append("ALTER TABLE users ADD COLUMN history_enabled BOOLEAN DEFAULT TRUE")
    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))

_SEVERITY_BADGE_RE = re.compile(r"badge-(critical|high|medium|low)\b")

def severity_counts_str(result_html: str) -> str:
    """Geçmiş listesinde küçük bir önem derecesi göstergesi çizebilmek için
    sonuç HTML'indeki badge-* sınıflarını sayar. Sırasıyla: kritik,yüksek,orta,düşük."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for match in _SEVERITY_BADGE_RE.finditer(result_html):
        counts[match.group(1)] += 1
    return f"{counts['critical']},{counts['high']},{counts['medium']},{counts['low']}"

def _migrate_analyses_table():
    """analyses tablosu zaten varsa (önceki bir deploy'dan), eksik kolonları ekle."""
    inspector = inspect(engine)
    if "analyses" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("analyses")}
    if "severity_counts" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE analyses ADD COLUMN severity_counts VARCHAR(32) DEFAULT '0,0,0,0'"))
        # Bu kolon yeni eklendiği için var olan kayıtlarda hepsi '0,0,0,0' olur;
        # gerçek değeri zaten kaydedilmiş result_html'den geriye dönük hesapla.
        with SessionLocal() as backfill_db:
            for analysis in backfill_db.query(Analysis).all():
                analysis.severity_counts = severity_counts_str(analysis.result_html)
            backfill_db.commit()

def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_users_table()
    _migrate_analyses_table()

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

def set_history_enabled(db, user: User, enabled: bool) -> None:
    user.history_enabled = enabled
    db.commit()

def save_analysis(
    db, user: User, providers: list[str], source_type: str, source_label: str, result_html: str,
    severity_counts: str = "0,0,0,0",
) -> Analysis:
    analysis = Analysis(
        user_id=user.id,
        providers=",".join(providers),
        source_type=source_type,
        source_label=source_label[:255],
        result_html=result_html,
        severity_counts=severity_counts,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis

def get_user_history(db, user: User, limit: int = 50) -> list[Analysis]:
    return (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
        .all()
    )

def get_analysis_by_id(db, user: User, analysis_id: int) -> Optional[Analysis]:
    return (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id, Analysis.user_id == user.id)
        .one_or_none()
    )

def delete_analysis(db, user: User, analysis_id: int) -> bool:
    analysis = get_analysis_by_id(db, user, analysis_id)
    if analysis is None:
        return False
    db.delete(analysis)
    db.commit()
    return True
