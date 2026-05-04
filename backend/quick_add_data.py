#!/usr/bin/env python3
"""
Quick script to add sample data for ML Analytics testing
Run this if you see "Insufficient data" error
"""

import sqlite3
from datetime import datetime, timedelta
import random
import os

# Database path
DB_PATH = os.environ.get('DATABASE_PATH', 'attendance.db')

def add_sample_data():
    """Add sample students and attendance records"""
    
    print("🤖 Adding Sample Data for ML Analytics")
    print("=" * 50)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Sample students with different attendance patterns
    students = [
        ('STU001', 'Alice Johnson', 'alice@example.com', 'CS', '2024', 0.95),  # Excellent
        ('STU002', 'Bob Smith', 'bob@example.com', 'CS', '2024', 0.88),        # Good
        ('STU003', 'Charlie Brown', 'charlie@example.com', 'EE', '2024', 0.78), # Borderline
        ('STU004', 'Diana Prince', 'diana@example.com', 'ME', '2024', 0.65),   # At risk
        ('STU005', 'Eve Wilson', 'eve@example.com', 'CS', '2024', 0.50),       # Poor
        ('STU006', 'Frank Miller', 'frank@example.com', 'EE', '2024', 0.92),   # Excellent
        ('STU007', 'Grace Lee', 'grace@example.com', 'ME', '2024', 0.70),      # At risk
        ('STU008', 'Henry Davis', 'henry@example.com', 'CS', '2024', 0.85),    # Good
    ]
    
    print(f"\n📝 Adding {len(students)} students...")
    added_students = 0
    
    for sid, name, email, dept, year, _ in students:
        try:
            c.execute("""
                INSERT OR IGNORE INTO students 
                (student_id, name, email, department, year) 
                VALUES (?, ?, ?, ?, ?)
            """, (sid, name, email, dept, year))
            if c.rowcount > 0:
                added_students += 1
                print(f"   ✅ {name} ({sid})")
        except Exception as e:
            print(f"   ❌ Error adding {name}: {e}")
    
    print(f"\n✅ Added {added_students} new students")
    
    # Add attendance records for last 30 days
    days = 30
    start_date = datetime.now() - timedelta(days=days)
    
    print(f"\n📅 Adding {days} days of attendance records...")
    added_records = 0
    
    for i in range(days):
        date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        
        for sid, name, _, _, _, rate in students:
            # Generate attendance based on pattern
            rand = random.random()
            if rand < rate:
                status = 'Present'
            elif rand < rate + 0.05:
                status = 'Late'
            else:
                status = 'Absent'
            
            try:
                c.execute("""
                    INSERT OR REPLACE INTO attendance 
                    (student_id, date, status) 
                    VALUES (?, ?, ?)
                """, (sid, date, status))
                added_records += 1
            except Exception as e:
                print(f"   ❌ Error adding record for {sid} on {date}: {e}")
    
    print(f"✅ Added {added_records} attendance records")
    
    conn.commit()
    
    # Show summary
    print("\n" + "=" * 50)
    print("📊 Database Summary:")
    print("=" * 50)
    
    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]
    print(f"   Total Students: {total_students}")
    
    c.execute("SELECT COUNT(*) FROM attendance")
    total_records = c.fetchone()[0]
    print(f"   Total Attendance Records: {total_records}")
    
    c.execute("SELECT COUNT(DISTINCT date) FROM attendance")
    total_days = c.fetchone()[0]
    print(f"   Days of Data: {total_days}")
    
    c.execute("""
        SELECT student_id, COUNT(*) as records 
        FROM attendance 
        GROUP BY student_id 
        ORDER BY records DESC 
        LIMIT 3
    """)
    print(f"\n   Top Students by Records:")
    for row in c.fetchall():
        print(f"      {row[0]}: {row[1]} records")
    
    conn.close()
    
    print("\n" + "=" * 50)
    print("✅ Sample Data Added Successfully!")
    print("=" * 50)
    print("\n🚀 Next Steps:")
    print("   1. Restart backend: python app.py")
    print("   2. Open ML Analytics page")
    print("   3. Click 'Run Analysis'")
    print("   4. View your ML predictions!")
    print("\n")

if __name__ == '__main__':
    try:
        add_sample_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you're in the backend directory and attendance.db exists.")
        print("Run: cd backend && python quick_add_data.py")
