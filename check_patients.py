from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User

with SessionLocal() as db:
    for email in ["patient1@gmail.com", "booking.patient.2026@example.com"]:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            print(f"{email}: EXISTS | ID={user.id} | ROLE={user.role}")
        else:
            print(f"{email}: NOT FOUND")
