import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vaultscan.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

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

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
