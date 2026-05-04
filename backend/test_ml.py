"""
Test script for ML Analytics
Run this to verify ML models are working correctly
"""

from ml_analytics import AttendanceMLAnalytics
import sqlite3
from datetime import datetime, timedelta
import random

def create_sample_data():
    """Create sample attendance data for testing"""
    print("Creating sample data...")
    
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # Create sample students
    students = [
        ('STU001', 'Alice Johnson', 'alice@example.com', 'CS', '2024'),
        ('STU002', 'Bob Smith', 'bob@example.com', 'CS', '2024'),
        ('STU003', 'Charlie Brown', 'charlie@example.com', 'EE', '2024'),
        ('STU004', 'Diana Prince', 'diana@example.com', 'ME', '2024'),
        ('STU005', 'Eve Wilson', 'eve@example.com', 'CS', '2024'),
        ('STU006', 'Frank Miller', 'frank@example.com', 'EE', '2024'),
        ('STU007', 'Grace Lee', 'grace@example.com', 'ME', '2024'),
        ('STU008', 'Henry Davis', 'henry@example.com', 'CS', '2024'),
    ]
    
    for sid, name, email, dept, year in students:
        try:
            c.execute("""INSERT OR IGNORE INTO students 
                        (student_id, name, email, department, year) 
                        VALUES (?, ?, ?, ?, ?)""", 
                     (sid, name, email, dept, year))
        except:
            pass
    
    # Create attendance records for last 30 days
    start_date = datetime.now() - timedelta(days=30)
    
    # Different attendance patterns for different students
    attendance_patterns = {
        'STU001': 0.95,  # Excellent
        'STU002': 0.88,  # Good
        'STU003': 0.78,  # Borderline
        'STU004': 0.65,  # At risk
        'STU005': 0.50,  # Poor
        'STU006': 0.92,  # Excellent
        'STU007': 0.70,  # At risk
        'STU008': 0.85,  # Good
    }
    
    for i in range(30):
        date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        
        for sid, rate in attendance_patterns.items():
            # Randomly mark attendance based on pattern
            rand = random.random()
            if rand < rate:
                status = 'Present'
            elif rand < rate + 0.05:
                status = 'Late'
            else:
                status = 'Absent'
            
            try:
                c.execute("""INSERT OR REPLACE INTO attendance 
                            (student_id, date, status) 
                            VALUES (?, ?, ?)""", 
                         (sid, date, status))
            except:
                pass
    
    conn.commit()
    conn.close()
    print("✅ Sample data created successfully!")

def test_linear_regression():
    """Test Linear Regression model"""
    print("\n" + "="*60)
    print("Testing Linear Regression - Attendance Prediction")
    print("="*60)
    
    ml = AttendanceMLAnalytics()
    result = ml.predict_attendance_rate()
    
    if result.get('success'):
        print(f"✅ Model: {result['model']}")
        print(f"📊 Current Average: {result['current_average']}%")
        print(f"📈 Trend: {result['trend']['direction']} ({result['trend']['strength']})")
        print(f"📉 Rate per day: {result['trend']['rate_per_day']}%")
        print(f"\n🔮 Predictions for next 7 days:")
        for pred in result['predictions']:
            print(f"   Day {pred['day']}: {pred['predicted_rate']}%")
        print(f"\n📊 Model Performance:")
        print(f"   R² Score: {result['metrics']['r2_score']}")
        print(f"   Accuracy: {result['metrics']['accuracy']}")
        print(f"\n💡 Recommendation:")
        print(f"   {result['recommendation']}")
    else:
        print(f"❌ Error: {result.get('error')}")

def test_logistic_regression():
    """Test Logistic Regression model"""
    print("\n" + "="*60)
    print("Testing Logistic Regression - At-Risk Classification")
    print("="*60)
    
    ml = AttendanceMLAnalytics()
    result = ml.classify_at_risk_students()
    
    if result.get('success'):
        print(f"✅ Model: {result['model']}")
        print(f"\n📊 Summary:")
        print(f"   Total Students: {result['summary']['total_students']}")
        print(f"   At Risk: {result['summary']['at_risk_count']} ({result['summary']['at_risk_percentage']}%)")
        print(f"   Good Standing: {result['summary']['good_standing_count']}")
        
        print(f"\n⚠️ At-Risk Students:")
        if result['at_risk_students']:
            for student in result['at_risk_students'][:5]:  # Show top 5
                print(f"   • {student['name']} ({student['student_id']})")
                print(f"     Attendance: {student['attendance_rate']}%")
                print(f"     Risk: {student['risk_probability']}%")
                print(f"     Severity: {student['severity']}")
                print(f"     Consecutive Absences: {student['max_consecutive_absent']}")
        else:
            print("   No at-risk students found!")
        
        print(f"\n✅ Good Standing Students:")
        for student in result['good_standing_students'][:3]:  # Show top 3
            print(f"   • {student['name']} ({student['student_id']}): {student['attendance_rate']}%")
        
        print(f"\n📊 Model Performance:")
        print(f"   Accuracy: {result['model_performance']['accuracy']}%")
        print(f"   Quality: {result['model_performance']['quality']}")
        
        print(f"\n💡 Recommendations:")
        for rec in result['recommendations']:
            print(f"   {rec}")
    else:
        print(f"❌ Error: {result.get('error')}")

def test_full_analysis():
    """Test full analysis"""
    print("\n" + "="*60)
    print("Testing Full Analysis - Combined Insights")
    print("="*60)
    
    ml = AttendanceMLAnalytics()
    result = ml.run_full_analysis()
    
    if result.get('success'):
        print(f"✅ Full Analysis Complete")
        print(f"⏰ Timestamp: {result['timestamp']}")
        print(f"\n🔍 Overall Insights:")
        for insight in result['overall_insights']:
            print(f"   {insight}")
    else:
        print(f"❌ Error: {result.get('error')}")

if __name__ == '__main__':
    print("🤖 ML Analytics Test Suite")
    print("="*60)
    
    # Ask user if they want to create sample data
    response = input("\nCreate sample data? (y/n): ").lower()
    if response == 'y':
        create_sample_data()
    
    # Run tests
    test_linear_regression()
    test_logistic_regression()
    test_full_analysis()
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)
