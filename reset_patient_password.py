from getpass import getpass
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password

email = "booking.patient.2026@example.com"
new_password = getpass("Enter NEW patient password (hidden): ")
confirm_password = getpass("Confirm NEW patient password (hidden): ")

if len(new_password) < 8:
    print("ERROR: Password must be at least 8 characters.")
elif new_password != confirm_password:
    print("ERROR: Passwords do not match.")
else:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print("ERROR: Patient account not found.")
        elif user.role != UserRole.PATIENT:
            print("ERROR: Account is not a patient. No changes made.")
        else:
            user.password_hash = hash_password(new_password)
            db.commit()
            print("SUCCESS: Patient password reset.")
