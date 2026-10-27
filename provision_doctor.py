import getpass
import sys

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.doctor import Doctor
from app.models.user import User, UserRole


def main():
    print("=== Amrutam Doctor Account Provisioning ===")

    try:
        doctor_id = int(input("Existing doctor ID: ").strip())
        if doctor_id <= 0:
            raise ValueError
    except ValueError:
        print("ERROR: Doctor ID must be a positive integer.")
        sys.exit(1)

    email = input("Doctor account email: ").strip().lower()
    if not email or "@" not in email:
        print("ERROR: Enter a valid email address.")
        sys.exit(1)

    password = getpass.getpass("Set doctor account password (minimum 12 characters): ")
    confirm = getpass.getpass("Confirm password: ")

    if len(password) < 12 or len(password) > 128:
        print("ERROR: Password must contain 12 to 128 characters.")
        sys.exit(1)

    if password != confirm:
        print("ERROR: Passwords do not match.")
        sys.exit(1)

    with SessionLocal() as db:
        doctor = db.scalar(
            select(Doctor).where(Doctor.id == doctor_id).with_for_update()
        )

        if doctor is None:
            print("ERROR: Doctor record not found.")
            sys.exit(1)

        if not doctor.is_active:
            print("ERROR: Cannot provision an inactive doctor.")
            sys.exit(1)

        if doctor.user_id is not None:
            print("ERROR: This doctor is already linked to a user account.")
            sys.exit(1)

        existing_user = db.scalar(
            select(User).where(User.email == email)
        )
        if existing_user is not None:
            print("ERROR: This email already belongs to an account.")
            sys.exit(1)

        user = User(
            full_name=doctor.full_name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.DOCTOR,
            is_active=True,
        )

        try:
            db.add(user)
            db.flush()

            doctor.user_id = user.id
            db.commit()

            print("\nSUCCESS: Doctor account created and linked.")
            print(f"Doctor ID: {doctor.id}")
            print(f"User ID: {user.id}")
            print(f"Email: {user.email}")
            print("Role: doctor")
            print("Password: not displayed")

        except IntegrityError:
            db.rollback()
            print("ERROR: A database uniqueness or relationship constraint failed.")
            sys.exit(1)


if __name__ == "__main__":
    main()
