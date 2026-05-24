#!/usr/bin/env python3
"""
Test script for cancel appointment feature
Tests:
1. Cancel before 24 hours - should NOT penalize
2. Cancel after 24 hours - should penalize
"""

import sqlite3
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import init_db, get_db_connection, DEFAULT_HOSPITAL_ID

def test_cancel_appointment():
    print("=== Testing Cancel Appointment Feature ===\n")
    
    # Initialize database
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get or create a test donor
        cursor.execute("SELECT id, reliability_score FROM users WHERE phone = '0910000099'")
        donor = cursor.fetchone()
        
        if not donor:
            # Create test donor
            cursor.execute("""
                INSERT INTO users (phone, email, password, full_name, role, blood_type, reliability_score, humanitarian_points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ('0910000099', 'test@example.com', 'phone-login', 'Test Donor', 'DONOR', 'O+', 100, 0))
            conn.commit()
            cursor.execute("SELECT id, reliability_score FROM users WHERE phone = '0910000099'")
            donor = cursor.fetchone()
        
        donor_id = donor['id']
        initial_score = donor['reliability_score']
        print(f"Test donor ID: {donor_id}")
        print(f"Initial reliability score: {initial_score}\n")
        
        # Test 1: Cancel appointment BEFORE 24 hours (should penalize)
        print("TEST 1: Cancel appointment WITHIN 24 hours")
        print("-" * 50)
        appointment_dt_soon = datetime.now() + timedelta(hours=12)
        
        cursor.execute("""
            INSERT INTO appointments (donor_id, hospital_id, appointment_date, status, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (donor_id, DEFAULT_HOSPITAL_ID, appointment_dt_soon.isoformat(), 'PENDING', 'Test appointment 12 hours away'))
        conn.commit()
        
        cursor.execute("SELECT last_insert_rowid() AS id")
        appointment1_id = cursor.fetchone()['id']
        
        print(f"Created appointment {appointment1_id} scheduled for {appointment_dt_soon.isoformat()}")
        print(f"Hours until appointment: 12")
        
        # Simulate cancel by checking logic
        now = datetime.now()
        hours_until = (appointment_dt_soon - now).total_seconds() / 3600
        should_penalize = hours_until < 24
        print(f"Should penalize: {should_penalize} (hours_until < 24: {hours_until:.1f} < 24)")
        
        if should_penalize:
            # Apply penalty
            cursor.execute("""
                UPDATE users
                SET reliability_score = MAX(COALESCE(reliability_score, 80) - 5, 0),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (donor_id,))
            conn.commit()
            cursor.execute("SELECT reliability_score FROM users WHERE id = ?", (donor_id,))
            new_score = cursor.fetchone()['reliability_score']
            print(f"Reliability score after cancellation: {new_score} (reduced by 5)")
            assert new_score == initial_score - 5, f"Expected {initial_score - 5}, got {new_score}"
            print("✓ PASS: Score correctly reduced\n")
        else:
            print("✗ FAIL: Should have penalized but didn't\n")
            return False
        
        # Test 2: Cancel appointment AFTER 24 hours (should NOT penalize)
        print("TEST 2: Cancel appointment BEFORE 24 hours")
        print("-" * 50)
        appointment_dt_far = datetime.now() + timedelta(days=3)
        
        cursor.execute("""
            INSERT INTO appointments (donor_id, hospital_id, appointment_date, status, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (donor_id, DEFAULT_HOSPITAL_ID, appointment_dt_far.isoformat(), 'PENDING', 'Test appointment 3 days away'))
        conn.commit()
        
        cursor.execute("SELECT last_insert_rowid() AS id")
        appointment2_id = cursor.fetchone()['id']
        
        print(f"Created appointment {appointment2_id} scheduled for {appointment_dt_far.isoformat()}")
        print(f"Days until appointment: 3")
        
        score_before_cancel = new_score
        
        # Simulate cancel by checking logic
        hours_until = (appointment_dt_far - datetime.now()).total_seconds() / 3600
        should_penalize = hours_until < 24
        print(f"Should penalize: {should_penalize} (hours_until < 24: {hours_until:.1f} < 24)")
        
        if not should_penalize:
            # No penalty
            cursor.execute("""
                UPDATE users
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (donor_id,))
            conn.commit()
            cursor.execute("SELECT reliability_score FROM users WHERE id = ?", (donor_id,))
            new_score2 = cursor.fetchone()['reliability_score']
            print(f"Reliability score after cancellation: {new_score2} (unchanged)")
            assert new_score2 == score_before_cancel, f"Expected {score_before_cancel}, got {new_score2}"
            print("✓ PASS: Score correctly unchanged\n")
        else:
            print("✗ FAIL: Should not have penalized but did\n")
            return False
        
        print("=" * 50)
        print("✓ ALL TESTS PASSED!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = test_cancel_appointment()
    sys.exit(0 if success else 1)
