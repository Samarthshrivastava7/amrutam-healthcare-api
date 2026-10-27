from getpass import getpass
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from main import app

patient_email = input("Test patient email: ").strip()
patient_password = getpass("Test patient password: ")

doctor_email = input("Doctor email [dr.priya.test@example.com]: ").strip()
if not doctor_email:
    doctor_email = "dr.priya.test@example.com"
doctor_password = getpass("Doctor password: ")

with TestClient(app) as client:
    # 1. Patient login
    r = client.post(
        "/auth/login",
        json={"email": patient_email, "password": patient_password},
    )
    print("Patient login:", r.status_code)
    if r.status_code != 200:
        print(r.text)
        raise SystemExit("Patient login failed.")
    patient_headers = {
        "Authorization": "Bearer " + r.json()["access_token"]
    }

    # 2. Doctor login
    r = client.post(
        "/auth/login",
        json={"email": doctor_email, "password": doctor_password},
    )
    print("Doctor login:", r.status_code)
    if r.status_code != 200:
        print(r.text)
        raise SystemExit("Doctor login failed.")
    doctor_headers = {
        "Authorization": "Bearer " + r.json()["access_token"]
    }

    # 3. Book a future appointment, using an explicit timezone.
    scheduled_at = (
        datetime.now(timezone.utc) + timedelta(days=2)
    ).replace(minute=0, second=0, microsecond=0).isoformat()

    r = client.post(
        "/appointments/",
        headers={
            **patient_headers,
            "Idempotency-Key": "amrutam-e2e-" + str(
                int(datetime.now(timezone.utc).timestamp())
            ),
        },
        json={"doctor_id": 1, "scheduled_at": scheduled_at},
    )
    print("Book appointment:", r.status_code)
    if r.status_code != 201:
        print(r.text)
        raise SystemExit("Appointment booking failed.")
    appointment_id = r.json()["id"]
    print("Appointment ID:", appointment_id)

    # 4. Start consultation as the assigned doctor.
    r = client.post(
        "/consultations/",
        headers=doctor_headers,
        json={"appointment_id": appointment_id},
    )
    print("Start consultation:", r.status_code)
    if r.status_code != 201:
        print(r.text)
        raise SystemExit("Consultation start failed.")
    consultation_id = r.json()["id"]
    print("Consultation ID:", consultation_id)

    # 5. Create a clearly labelled test-only prescription.
    r = client.post(
        "/prescriptions/",
        headers=doctor_headers,
        json={
            "consultation_id": consultation_id,
            "medication_details": "TEST ONLY - not a real prescription",
            "instructions": "API testing only. Do not use for patient care.",
        },
    )
    print("Create test prescription:", r.status_code)
    if r.status_code != 201:
        print(r.text)
        raise SystemExit("Prescription creation failed.")
    print("Prescription ID:", r.json()["id"])

    # 6. Complete consultation.
    r = client.post(
        f"/consultations/{consultation_id}/complete",
        headers=doctor_headers,
    )
    print("Complete consultation:", r.status_code)
    if r.status_code != 200:
        print(r.text)
        raise SystemExit("Consultation completion failed.")

    # 7. Verify patient can see their own prescription.
    r = client.get("/prescriptions/me", headers=patient_headers)
    print("Patient prescriptions:", r.status_code)
    if r.status_code == 200:
        print("Visible prescription count:", len(r.json()))
    else:
        print(r.text)

    # 8. Verify doctor can see their own consultation.
    r = client.get("/consultations/me", headers=doctor_headers)
    print("Doctor consultations:", r.status_code)
    if r.status_code == 200:
        print("Visible consultation count:", len(r.json()))
    else:
        print(r.text)
