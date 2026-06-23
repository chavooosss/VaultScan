"""Bir kullanıcının plan'ını (free/premium) elle değiştirmek için CLI script.

Kullanım:
  .venv/bin/python scripts/set_plan.py list
  .venv/bin/python scripts/set_plan.py set <email> <free|premium>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import SessionLocal, User


def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id).all()
        if not users:
            print("Hiç kullanıcı yok.")
            return
        for u in users:
            print(f"{u.id}\t{u.email}\t{u.plan}\t{u.analyses_this_month} analiz/ay")
    finally:
        db.close()


def set_plan(email: str, plan: str):
    if plan not in ("free", "premium"):
        print("Plan 'free' veya 'premium' olmalı.")
        sys.exit(1)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            print(f"Kullanıcı bulunamadı: {email}")
            sys.exit(1)
        user.plan = plan
        db.commit()
        print(f"{email} -> {plan} olarak güncellendi.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "list":
        list_users()
    elif len(sys.argv) == 4 and sys.argv[1] == "set":
        set_plan(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)
