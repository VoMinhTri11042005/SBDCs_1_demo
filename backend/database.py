import sqlite3
import os
import time
import bcrypt
from datetime import datetime, timedelta

DB_PATH = os.getenv("DATABASE_PATH", os.path.join(os.getcwd(), "database.sqlite"))
DEFAULT_HOSPITAL_ID = 1

BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']


def _password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def _is_bcrypt_hash(value: str) -> bool:
    return isinstance(value, str) and value.startswith(('$2a$', '$2b$', '$2y$'))


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_names(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def init_db(retry=True):
    print(f"DEBUG: Initializing database at {os.path.abspath(DB_PATH)}")
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("PRAGMA integrity_check")
            res = cursor.fetchone()
            if res and res[0] != "ok":
                raise sqlite3.DatabaseError("database disk image is malformed")
        except sqlite3.DatabaseError:
            raise sqlite3.DatabaseError("database disk image is malformed")

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password TEXT DEFAULT 'phone-login',
                full_name TEXT NOT NULL DEFAULT 'New Donor',
                role TEXT NOT NULL CHECK(role IN ('DONOR', 'HOSPITAL_ADMIN')) DEFAULT 'DONOR',
                blood_type TEXT DEFAULT 'UNKNOWN',
                birth_date TEXT,
                gender TEXT,
                citizen_id TEXT,
                weight REAL,
                height REAL,
                address TEXT,
                occupation TEXT,
                avatar_url TEXT,
                lat REAL,
                lng REAL,
                reliability_score REAL DEFAULT 100,
                total_donations INTEGER DEFAULT 0,
                humanitarian_points INTEGER DEFAULT 0,
                last_donation_date TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS hospitals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                lat REAL,
                lng REAL,
                contact_phone TEXT,
                contact_email TEXT,
                hospital_code TEXT,
                city TEXT,
                district TEXT,
                contact_name TEXT,
                contact_title TEXT,
                contact_person_phone TEXT,
                contact_person_email TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS blood_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospital_id INTEGER DEFAULT 1,
                blood_type TEXT NOT NULL,
                quantity REAL DEFAULT 0,
                safety_threshold REAL DEFAULT 10,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(hospital_id, blood_type)
            );

            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospital_id INTEGER DEFAULT 1,
                blood_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                transaction_type TEXT CHECK(transaction_type IN ('IN', 'OUT')),
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_id INTEGER NOT NULL,
                hospital_id INTEGER DEFAULT 1,
                appointment_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'APPROVED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
                pre_screening_result TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (donor_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS recommendation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospital_id INTEGER DEFAULT 1,
                blood_type TEXT NOT NULL,
                requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                score REAL NOT NULL,
                invitation_status TEXT DEFAULT 'NO_RESPONSE' CHECK(invitation_status IN ('SENT','ACCEPTED','DECLINED','NO_RESPONSE')),
                email_status TEXT DEFAULT 'NOT_SENT',
                email_sent_at DATETIME,
                email_error TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_result_id INTEGER,
                user_id INTEGER NOT NULL,
                blood_type TEXT,
                email_to TEXT,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'MOCK_SENT',
                provider TEXT DEFAULT 'mock',
                error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recommendation_result_id) REFERENCES recommendation_results(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS recommendation_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                w_blood REAL DEFAULT 0.45,
                w_eligibility REAL DEFAULT 0.30,
                w_reliability REAL DEFAULT 0.15,
                w_humanitarian REAL DEFAULT 0.10,
                emergency_w_blood REAL DEFAULT 0.60,
                emergency_w_eligibility REAL DEFAULT 0.25,
                emergency_w_reliability REAL DEFAULT 0.10,
                emergency_w_humanitarian REAL DEFAULT 0.05,
                emergency_auto_adjust INTEGER DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );


            CREATE TABLE IF NOT EXISTS homepage_media (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                hospital_image_url TEXT DEFAULT '/images/hospital-showcase.svg',
                donor_activity_image_url TEXT DEFAULT '/images/donor-activity.svg',
                hospital_title TEXT DEFAULT 'Central Blood Donation Hospital',
                hospital_subtitle TEXT DEFAULT 'SBDCs - Kết nối hiến máu nhân đạo',
                updated_by INTEGER,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender TEXT NOT NULL CHECK(sender IN ('USER', 'BOT')),
                message TEXT NOT NULL,
                intent TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        # Lightweight migrations for older DB files
        user_cols = _column_names(cursor, 'users')
        migrations = {
            'phone': "ALTER TABLE users ADD COLUMN phone TEXT",
            'email': "ALTER TABLE users ADD COLUMN email TEXT",
            'password': "ALTER TABLE users ADD COLUMN password TEXT DEFAULT 'phone-login'",
            'full_name': "ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT 'New Donor'",
            'role': "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'DONOR'",
            'blood_type': "ALTER TABLE users ADD COLUMN blood_type TEXT DEFAULT 'UNKNOWN'",
            'birth_date': "ALTER TABLE users ADD COLUMN birth_date TEXT",
            'gender': "ALTER TABLE users ADD COLUMN gender TEXT",
            'citizen_id': "ALTER TABLE users ADD COLUMN citizen_id TEXT",
            'weight': "ALTER TABLE users ADD COLUMN weight REAL",
            'height': "ALTER TABLE users ADD COLUMN height REAL",
            'address': "ALTER TABLE users ADD COLUMN address TEXT",
            'occupation': "ALTER TABLE users ADD COLUMN occupation TEXT",
            'avatar_url': "ALTER TABLE users ADD COLUMN avatar_url TEXT",
            'reliability_score': "ALTER TABLE users ADD COLUMN reliability_score REAL DEFAULT 100",
            'total_donations': "ALTER TABLE users ADD COLUMN total_donations INTEGER DEFAULT 0",
            'humanitarian_points': "ALTER TABLE users ADD COLUMN humanitarian_points INTEGER DEFAULT 0",
            'last_donation_date': "ALTER TABLE users ADD COLUMN last_donation_date TEXT",
            'updated_at': "ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        }
        for col, sql in migrations.items():
            if col not in user_cols:
                cursor.execute(sql)

        rec_cols = _column_names(cursor, 'recommendation_results')
        rec_migrations = {
            'email_status': "ALTER TABLE recommendation_results ADD COLUMN email_status TEXT DEFAULT 'NOT_SENT'",
            'email_sent_at': "ALTER TABLE recommendation_results ADD COLUMN email_sent_at DATETIME",
            'email_error': "ALTER TABLE recommendation_results ADD COLUMN email_error TEXT",
        }
        for col, sql in rec_migrations.items():
            if col not in rec_cols:
                cursor.execute(sql)

        # Keep only one hospital in the system. The extra hospitals are intentionally not used.
        cursor.execute("SELECT id FROM hospitals WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT OR IGNORE INTO hospitals (id, name, address, lat, lng, contact_phone, contact_email, status) VALUES (1, ?, ?, ?, ?, ?, ?, 'ACTIVE')",
                ("Central Blood Donation Hospital", "Thông tin cập nhật bởi bệnh viện trong phần cài đặt", 10.7572, 106.6590, "0900000001", "hospital@sbdcs.com")
            )
        cursor.execute("UPDATE hospitals SET name=?, address=?, status='ACTIVE' WHERE id=1", ("Central Blood Donation Hospital", "Thông tin cập nhật bởi bệnh viện trong phần cài đặt"))
        cursor.execute("DELETE FROM hospitals WHERE id <> 1")

        # Collapse any legacy multi-hospital inventory into one hospital.
        cursor.execute("""
            SELECT blood_type, SUM(quantity) AS quantity, AVG(safety_threshold) AS safety_threshold
            FROM blood_inventory
            GROUP BY blood_type
        """)
        merged_inventory = {row["blood_type"]: (row["quantity"] or 0, row["safety_threshold"] or 10) for row in cursor.fetchall()}
        cursor.execute("DELETE FROM blood_inventory")
        for b_type in BLOOD_TYPES:
            qty, threshold = merged_inventory.get(b_type, (8 if b_type in ('O-', 'A-') else 15, 10))
            cursor.execute(
                "INSERT INTO blood_inventory (hospital_id, blood_type, quantity, safety_threshold) VALUES (1, ?, ?, ?)",
                (b_type, qty, threshold)
            )
        cursor.execute("UPDATE appointments SET hospital_id = 1 WHERE hospital_id IS NULL OR hospital_id <> 1")
        cursor.execute("UPDATE inventory_transactions SET hospital_id = 1 WHERE hospital_id IS NULL OR hospital_id <> 1")

        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users(phone)")

        cursor.execute("""
            INSERT OR IGNORE INTO recommendation_settings (id, w_blood, w_eligibility, w_reliability, w_humanitarian, emergency_w_blood, emergency_w_eligibility, emergency_w_reliability, emergency_w_humanitarian, emergency_auto_adjust)
            VALUES (1, 0.45, 0.30, 0.15, 0.10, 0.60, 0.25, 0.10, 0.05, 1)
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO homepage_media (id, hospital_image_url, donor_activity_image_url, hospital_title, hospital_subtitle)
            VALUES (1, '/images/hospital-showcase.svg', '/images/donor-activity.svg', 'Central Blood Donation Hospital', 'SBDCs - Kết nối hiến máu nhân đạo')
        """)
        # Preserve uploaded homepage images, but migrate old Cho Ray branding to SBDCs branding.
        cursor.execute("""
            UPDATE homepage_media
            SET hospital_title = 'Central Blood Donation Hospital',
                hospital_subtitle = 'SBDCs - Kết nối hiến máu nhân đạo'
            WHERE id = 1
              AND (hospital_title IS NULL OR hospital_title LIKE '%Chợ Rẫy%' OR hospital_title LIKE '%Choray%' OR hospital_title = 'Central Blood Hospital')
        """)

        # Seed demo users
        hospital_password_hash = _password_hash('Admin@123')
        cursor.execute("SELECT id, password FROM users WHERE phone = '0900000001'")
        hospital_row = cursor.fetchone()
        if not hospital_row:
            cursor.execute(
                "INSERT INTO users (phone, email, password, full_name, role, blood_type, reliability_score, humanitarian_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('0900000001', 'hospital@sbdcs.com', hospital_password_hash, 'Hospital Admin', 'HOSPITAL_ADMIN', 'UNKNOWN', 100, 0)
            )
        elif not _is_bcrypt_hash(hospital_row['password']):
            cursor.execute(
                "UPDATE users SET email=?, password=?, role='HOSPITAL_ADMIN', full_name='Hospital Admin' WHERE phone='0900000001'",
                ('hospital@sbdcs.com', hospital_password_hash)
            )

        # Provisioned Hospital Admin accounts: hospital-owned accounts, not public self-registration.
        second_admin_hash = _password_hash('Admin@123')
        cursor.execute("SELECT id, password FROM users WHERE phone = '0900000099'")
        second_admin = cursor.fetchone()
        if not second_admin:
            cursor.execute(
                "INSERT INTO users (phone, email, password, full_name, role, blood_type, reliability_score, humanitarian_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ('0900000099', 'hospital2@sbdcs.com', second_admin_hash, 'Hospital Admin 2', 'HOSPITAL_ADMIN', 'UNKNOWN', 100, 0)
            )
        elif not _is_bcrypt_hash(second_admin['password']):
            cursor.execute(
                "UPDATE users SET email=?, password=?, role='HOSPITAL_ADMIN', full_name='Hospital Admin 2' WHERE phone='0900000099'",
                ('hospital2@sbdcs.com', second_admin_hash)
            )

        cursor.execute("DELETE FROM users WHERE role='HOSPITAL_ADMIN' AND phone NOT IN ('0900000001','0900000099')")

        cursor.execute("SELECT id FROM users WHERE phone = '0900000002'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (phone, email, password, full_name, role, blood_type, reliability_score, humanitarian_points, total_donations) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ('0900000002', 'donor@sbdcs.com', 'phone-login', 'Nguyen Van Donor', 'DONOR', 'O+', 95, 120, 2)
            )

        # Seed realistic donors only if data is small
        cursor.execute("SELECT COUNT(*) AS c FROM users WHERE role='DONOR'")
        if cursor.fetchone()["c"] < 12:
            sample_donors = [
                ('0910000001', 'Tran Minh Anh', 'tran.minh.anh@example.com', 'A+', 92, 240, 3, 120),
                ('0910000002', 'Le Hoang Nam', 'le.hoang.nam@example.com', 'O-', 98, 800, 9, 100),
                ('0910000003', 'Pham Ngoc Mai', 'pham.ngoc.mai@example.com', 'B+', 88, 160, 2, 40),
                ('0910000004', 'Hoang Duc Huy', 'hoang.duc.huy@example.com', 'AB+', 76, 60, 1, 200),
                ('0910000005', 'Bui Thanh Lam', 'bui.thanh.lam@example.com', 'A-', 99, 560, 6, 92),
                ('0910000006', 'Vu Quang Kiet', 'vu.quang.kiet@example.com', 'O+', 84, 320, 4, 10),
                ('0910000007', 'Dang Gia Han', 'dang.gia.han@example.com', 'B-', 90, 410, 5, 95),
                ('0910000008', 'Nguyen Phuong Linh', 'nguyen.phuong.linh@example.com', 'AB-', 96, 900, 10, 130),
                ('0910000009', 'Tran Bao Chau', 'tran.bao.chau@example.com', 'UNKNOWN', 100, 30, 0, None),
                ('0910000010', 'Le Anh Tuan', 'le.anh.tuan@example.com', 'O+', 70, 50, 1, 160),
            ]
            for phone, name, email, blood_type, reliability, points, total, last_days in sample_donors:
                cursor.execute("SELECT id FROM users WHERE phone=?", (phone,))
                if cursor.fetchone():
                    continue
                last_date = None
                if last_days is not None:
                    last_date = (datetime.utcnow() - timedelta(days=last_days)).isoformat()
                cursor.execute(
                    """
                    INSERT INTO users (phone, email, password, full_name, role, blood_type, reliability_score, humanitarian_points, total_donations, last_donation_date)
                    VALUES (?, ?, 'phone-login', ?, 'DONOR', ?, ?, ?, ?, ?)
                    """,
                    (phone, email, name, blood_type, reliability, points, total, last_date)
                )

        cursor.execute("UPDATE users SET email = LOWER(REPLACE(full_name, ' ', '.')) || '@example.com' WHERE role='DONOR' AND (email IS NULL OR email='')")

        # Seed a few transaction rows for forecast demo
        cursor.execute("SELECT COUNT(*) AS c FROM inventory_transactions")
        if cursor.fetchone()["c"] == 0:
            for month_offset, qty in [(3, 4.5), (2, 7.0), (1, 6.0)]:
                created_at = (datetime.utcnow() - timedelta(days=31 * month_offset)).strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute(
                    "INSERT INTO inventory_transactions (hospital_id, blood_type, quantity, transaction_type, note, created_at) VALUES (1, 'O-', ?, 'OUT', 'Treatment usage seed', ?)",
                    (qty, created_at)
                )

        conn.commit()
        print("DEBUG: Database initialization successful.")
    except sqlite3.DatabaseError as e:
        if conn:
            try: conn.close()
            except Exception: pass
            conn = None
        if "malformed" in str(e).lower() and retry:
            print(f"WARNING: Database is malformed. Attempting to recreate... Error: {e}")
            if os.path.exists(DB_PATH):
                try:
                    os.rename(DB_PATH, DB_PATH + f".bak.{int(time.time())}")
                except Exception:
                    try: os.remove(DB_PATH)
                    except Exception as del_err: print(f"ERROR: Could not remove malformed database: {del_err}")
            return init_db(retry=False)
        print(f"ERROR: Database initialization failed: {str(e)}")
    except Exception as e:
        print(f"ERROR: Database initialization failed: {str(e)}")
        import traceback; traceback.print_exc()
    finally:
        if conn:
            try: conn.close()
            except Exception: pass
