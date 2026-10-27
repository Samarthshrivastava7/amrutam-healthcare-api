from getpass import getpass
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password

email = "dr.priya.test@example.com"
password = getpass("Enter NEW doctor password (hidden): ")
confirm = getpass("Confirm NEW doctor password (hidden): ")

if len(password) < 8:
    print("ERROR: Password must be at least 8 characters.")
elif password != confirm:
    print("ERROR: Passwords do not match.")
else:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print("ERROR: Doctor account not found.")
        elif user.role != UserRole.DOCTOR:
            print("ERROR: Account is not a doctor. No changes made.")
        else:
            user.password_hash = hash_password(password)
            db.commit()
            print("SUCCESS: Doctor password reset.")
