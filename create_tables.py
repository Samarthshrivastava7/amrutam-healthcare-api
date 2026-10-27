from app.db.session import Base, engine
from app.models.user import User
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.consultation import Consultation
from app.models.prescription import Prescription

def main():
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified successfully:")
    for table_name in Base.metadata.tables:
        print(f" - {table_name}")

if __name__ == "__main__":
    main()
