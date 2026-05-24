import sqlite3
import os
import random
from datetime import datetime, timedelta
from backend.core.security import get_password_hash

DB_PATH = os.path.join(os.getcwd(), "database.sqlite")
BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']


def seed_data():
    """Seed demo data for the single-hospital version only."""
    if not os.path.exists(DB_PATH):
        print("Database not found. Please run the backend once to initialize the DB.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM hospitals WHERE id <> 1")
    cursor.execute(
        """
        INSERT INTO hospitals (id, name, address, contact_phone, contact_email, status)
        VALUES (1, 'Central Blood Donation Hospital', 'Main Blood Donation Center', '1900-0000', 'bloodcenter@example.com', 'ACTIVE')
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            address=excluded.address,
            contact_phone=excluded.contact_phone,
            contact_email=excluded.contact_email,
            status=excluded.status
        """
    )

    for b_type in BLOOD_TYPES:
        qty = 6 if b_type in ('O-', 'A-') else random.randint(12, 28)
        threshold = 10
        cursor.execute(
            """
            INSERT INTO blood_inventory (hospital_id, blood_type, quantity, safety_threshold)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(hospital_id, blood_type) DO UPDATE SET
                quantity=excluded.quantity,
                safety_threshold=excluded.safety_threshold,
                updated_at=CURRENT_TIMESTAMP
            """,
            (b_type, qty, threshold)
        )

    names = ["Nguyen Van An", "Tran Thi Binh", "Le Minh Chau", "Pham Hoang Dung", "Hoang Ngoc Mai", "Dang Quang Huy", "Bui Anh Kiet", "Vu Linh Nhi"]
    donor_ids = []
    for i, name in enumerate(names, 1):
        phone = f"091000000{i}"
        cursor.execute("SELECT id FROM users WHERE phone=?", (phone,))
        found = cursor.fetchone()
        if found:
            donor_ids.append(found[0])
            continue
        cursor.execute(
            """
            INSERT INTO users (phone, email, password, full_name, role, blood_type, humanitarian_points, reliability_score, total_donations)
            VALUES (?, ?, ?, ?, 'DONOR', ?, ?, ?, ?)
            """,
            (phone, None, 'phone-login', name, random.choice(BLOOD_TYPES), random.randint(50, 900), random.randint(80, 100), random.randint(0, 8))
        )
        donor_ids.append(cursor.lastrowid)

    statuses = ['PENDING', 'APPROVED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
    for i in range(24):
        donor_id = random.choice(donor_ids)
        status = random.choice(statuses)
        appt_date = (datetime.now() + timedelta(days=random.randint(-10, 10), hours=random.randint(7, 16))).strftime("%Y-%m-%dT%H:%M")
        cursor.execute(
            """
            INSERT INTO appointments (donor_id, hospital_id, appointment_date, status, notes, pre_screening_result)
            VALUES (?, 1, ?, ?, ?, ?)
            """,
            (donor_id, appt_date, status, "Seeded single-hospital appointment", "Healthy")
        )

    conn.commit()
    conn.close()
    print("Successfully seeded single-hospital demo data.")


if __name__ == "__main__":
    seed_data()
