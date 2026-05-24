from fastapi import APIRouter
from ..database import get_db_connection

router = APIRouter()

@router.get("")
async def get_hospitals():
    # Single-hospital profile used by public pages and Hospital Settings.
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM hospitals WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            return [{"id": 1, "name": "Central Blood Donation Hospital", "address": "Thông tin cập nhật bởi bệnh viện trong phần cài đặt", "status": "ACTIVE", "contact_phone": "0900000001"}]
        return [dict(row)]
    finally:
        conn.close()
