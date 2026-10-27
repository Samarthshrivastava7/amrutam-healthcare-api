from getpass import getpass

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User, UserRole


def main() -> None:
    print("WARNING: This changes an existing account's privileges.")
    email = input("Exact account email to promote: ").strip().lower()
    if not email or "@" not in email:
        print("ERROR: Enter a valid account email.")
        return

    confirmation = getpass("Type PROMOTE_ADMIN to continue: ")
    if confirmation != "PROMOTE_ADMIN":
        print("Cancelled. No account changes made.")
        return

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print("ERROR: Account not found. No changes made.")
            return
        if user.role == UserRole.ADMIN:
            print("Account is already an administrator.")
            return

        user.role = UserRole.ADMIN
        db.commit()
        print(f"SUCCESS: {user.email} now has role=admin")


if __name__ == "__main__":
    main()
