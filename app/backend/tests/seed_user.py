from app.db.base import SessionLocal
from app.db import crud
from app.core.security import hash_password

def run():
    db = SessionLocal()
    try:
        email = "demo@example.com"
        if not crud.get_user_by_email(db, email):
            user = crud.create_user(db, email=email, hashed_password=hash_password("demo1234"))
            print("Created:", user.email)
        else:
            print("User already exists")
    finally:
        db.close()

if __name__ == "__main__":
    run()
