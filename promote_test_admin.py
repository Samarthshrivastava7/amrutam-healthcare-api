from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User, UserRole

email = "patient.test.2026@example.com"

db = SessionLocal()
try:
    user = db.scalar(select(User).where(User.email == email))

    if user is None:
        print("ERROR: Test user not found. Register the test account first.")
    else:
        user.role = UserRole.ADMIN
        db.commit()
        db.refresh(user)
        print(f"SUCCESS: {user.email} now has role={user.role.value}")
finally:
    db.close()
