import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, String, DateTime, Integer, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vaultscan.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

FREE_MONTHLY_QUOTA = 10

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
    plan: Mapped[str] = mapped_column(String(16), default="free")
    analyses_this_month: Mapped[int] = mapped_column(Integer, default=0)
    month_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)

def _migrate_users_table():
    """create_all yeni tablo açar ama var olan tabloya kolon eklemez; SQLite için elle ALTER TABLE gerekir."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    statements = []
    if "plan" not in existing:
        statements.append("ALTER TABLE users ADD COLUMN plan VARCHAR(16) DEFAULT 'free'")
    if "analyses_this_month" not in existing:
        statements.append("ALTER TABLE users ADD COLUMN analyses_this_month INTEGER DEFAULT 0")
    if "month_reset_at" not in existing:
        statements.append("ALTER TABLE users ADD COLUMN month_reset_at DATETIME")
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

def _same_month(a: datetime, b: datetime) -> bool:
    return a.year == b.year and a.month == b.month

def remaining_quota(user: User) -> Optional[int]:
    """Premium kullanıcı için None (sınırsız) döner, free kullanıcı için kalan hak sayısını döner."""
    if user.plan == "premium":
        return None
    now = datetime.now(timezone.utc)
    if user.month_reset_at is None or not _same_month(user.month_reset_at, now):
        return FREE_MONTHLY_QUOTA
    return max(0, FREE_MONTHLY_QUOTA - user.analyses_this_month)

def check_and_increment_quota(db, user: User) -> bool:
    """Premium kullanıcı her zaman geçer. Free kullanıcı için aylık hakkı kontrol eder ve kullanırsa sayacı artırır."""
    if user.plan == "premium":
        return True

    now = datetime.now(timezone.utc)
    if user.month_reset_at is None or not _same_month(user.month_reset_at, now):
        user.analyses_this_month = 0
        user.month_reset_at = now

    if user.analyses_this_month >= FREE_MONTHLY_QUOTA:
        db.commit()
        return False

    user.analyses_this_month += 1
    db.commit()
    return True

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
