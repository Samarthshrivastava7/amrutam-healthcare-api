from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def main() -> None:
    email = input("Exact patient account email: ").strip().lower()
    if not email or "@" not in email:
        print("ERROR: Enter a valid account email.")
        return

    new_password = getpass("Enter NEW patient password (hidden): ")
    confirm_password = getpass("Confirm NEW patient password (hidden): ")

    if not 12 <= len(new_password) <= 128:
        print("ERROR: Password must be 12 to 128 characters.")
        return
    if new_password != confirm_password:
        print("ERROR: Passwords do not match.")
        return

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


if __name__ == "__main__":
    main()
