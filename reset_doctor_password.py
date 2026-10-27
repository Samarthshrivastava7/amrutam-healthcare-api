from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def main() -> None:
    email = input("Exact doctor account email: ").strip().lower()
    if not email or "@" not in email:
        print("ERROR: Enter a valid account email.")
        return

    password = getpass("Enter NEW doctor password (hidden): ")
    confirm = getpass("Confirm NEW doctor password (hidden): ")

    if not 12 <= len(password) <= 128:
        print("ERROR: Password must be 12 to 128 characters.")
        return
    if password != confirm:
        print("ERROR: Passwords do not match.")
        return

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


if __name__ == "__main__":
    main()
