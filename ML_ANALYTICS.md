# 🤖 ML Analytics Documentation

Complete guide for Machine Learning features in the Face Recognition Attendance System.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [ML Models](#ml-models)
4. [API Endpoints](#api-endpoints)
5. [Frontend Dashboard](#frontend-dashboard)
6. [Adding Sample Data](#adding-sample-data)
7. [Requirements](#requirements)
8. [Troubleshooting](#troubleshooting)
9. [Technical Details](#technical-details)

---

## Overview

The system includes **2 Machine Learning models** for attendance analysis:

### 1. **Linear Regression** 📈
- Predicts attendance rates for next 7 days
- Identifies improving or declining trends
- Provides R² score for accuracy

### 2. **Logistic Regression** ⚠️
- Classifies students as at-risk (<75% attendance)
- Calculates risk probability per student
- Categorizes severity: Critical, High, Medium, Low

---

## Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Add Sample Data (if needed)
```bash
python quick_add_data.py
```

### 3. Start Backend
```bash
python app.py
```

### 4. Access ML Analytics
- Open http://localhost:5080
- Login (admin/admin123 or teacher/teacher123)
- Click "ML Analytics" in sidebar (🤖 icon)
- Click "Run Analysis"

---

## ML Models

### Linear Regression - Attendance Prediction

**Purpose**: Forecast future attendance trends

**Input**: Historical daily attendance rates

**Output**:
```json
{
  "success": true,
  "current_average": 78.5,
  "trend": {
    "direction": "improving",
    "rate_per_day": 0.45,
    "strength": "moderate"
  },
  "predictions": [
    {"day": 1, "predicted_rate": 79.0},
    {"day": 2, "predicted_rate": 79.5},
    ...
  ],
  "metrics": {
    "r2_score": 0.85,
    "mse": 12.3
  },
  "recommendation": "✅ Good: Attendance is stable"
}
```

**Use Cases**:
- 📅 Plan ahead for low attendance days
- 📊 Track if interventions are working
- 🎯 Set realistic attendance goals

---

### Logistic Regression - Risk Classification

**Purpose**: Identify students at risk of poor attendance

**Input**: 10 features per student:
1. total_days
2. present_days
3. absent_days
4. late_days
5. attendance_rate
6. monday_attendance
7. friday_attendance
8. recent_trend (last 7 days)
9. max_consecutive_absent
10. late_frequency

**Output**:
```json
{
  "success": true,
  "summary": {
    "total_students": 25,
    "at_risk_count": 5,
    "at_risk_percentage": 20.0
  },
  "at_risk_students": [
    {
      "student_id": "STU001",
      "name": "John Doe",
      "attendance_rate": 65.5,
      "risk_probability": 85.2,
      "severity": "High",
      "max_consecutive_absent": 5
    }
  ],
  "recommendations": [
    "⚠️ 2 students at HIGH risk - schedule counseling",
    "📞 Contact parents of 5 at-risk students"
  ]
}
```

**Severity Levels**:
- 🔴 **Critical**: <50% attendance OR 7+ consecutive absences
- 🟠 **High**: <65% attendance OR 5+ consecutive absences
- 🟡 **Medium**: <75% attendance OR recent trend <50%
- 🟢 **Low**: 70-75% with improving trend

**Use Cases**:
- ⚠️ Early intervention for struggling students
- 📞 Prioritize parent communications
- 💼 Allocate counseling resources

---

## API Endpoints

All endpoints require authentication token.

### 1. Predict Attendance
```bash
GET /api/ml/predict_attendance
Authorization: Bearer <token>
```

**Returns**: 7-day predictions + trend analysis

### 2. At-Risk Students
```bash
GET /api/ml/at_risk_students
Authorization: Bearer <token>
```

**Returns**: Risk classification + recommendations

### 3. Full Analysis
```bash
GET /api/ml/full_analysis
Authorization: Bearer <token>
```

**Returns**: Both models + combined insights

### Example Usage
```bash
curl http://localhost:5080/api/ml/predict_attendance \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Frontend Dashboard

### Features

**4 Stat Cards**:
- Current Trend (improving/declining)
- At-Risk Students count
- Current Average attendance
- Model Accuracy

**Interactive Chart**:
- 7-day prediction line chart
- Hover for details
- Color-coded by trend

**Data Tables**:
- At-Risk Students (sortable)
- Good Standing Students
- Severity badges
- Risk probabilities

**Recommendations**:
- Actionable insights
- Color-coded by severity
- Specific next steps

### Navigation
1. Click "ML Analytics" in sidebar (🤖 icon)
2. Page loads automatically
3. Click "Run Analysis" to refresh
4. Switch tabs to view different data

---

## Adding Sample Data

### Option 1: Quick Script (Recommended)
```bash
cd backend
python quick_add_data.py
```

**Adds**:
- 8 sample students
- 30 days of attendance
- 240 attendance records
- Realistic patterns

### Option 2: Test Script
```bash
cd backend
python test_ml.py
```
Type `y` when prompted.

### Option 3: Manual Entry
1. Go to "Register Student" page
2. Add at least 5 students
3. Go to "Manual Entry" page
4. Mark attendance for 10+ days per student

### Option 4: SQL Direct
```sql
sqlite3 backend/attendance.db

INSERT INTO students (student_id, name) VALUES
('STU001', 'Alice Johnson'),
('STU002', 'Bob Smith'),
('STU003', 'Charlie Brown');

INSERT INTO attendance (student_id, date, status) VALUES
('STU001', '2026-04-20', 'Present'),
('STU001', '2026-04-21', 'Present'),
-- ... add more records
```

---

## Requirements

### Minimum Data

**Linear Regression**:
- ✅ 10+ days of attendance records
- ✅ At least 1 student

**Logistic Regression**:
- ✅ 5+ students
- ✅ Each student has 5+ records

### Recommended Data
- ✅ 30+ days of attendance
- ✅ 20+ students
- ✅ Consistent daily marking

### Dependencies
```
scikit-learn==1.3.2
pandas==2.1.4
numpy==1.24.3
```

Installed via: `pip install -r requirements.txt`

---

## Troubleshooting

### "Insufficient data" Error

**Cause**: Not enough attendance records

**Solution**:
```bash
cd backend
python quick_add_data.py
```

**Verify Data**:
```bash
# Check student count
sqlite3 backend/attendance.db "SELECT COUNT(*) FROM students;"
# Should be ≥ 5

# Check attendance records
sqlite3 backend/attendance.db "SELECT COUNT(*) FROM attendance;"
# Should be ≥ 50

# Check date range
sqlite3 backend/attendance.db "SELECT COUNT(DISTINCT date) FROM attendance;"
# Should be ≥ 10
```

### Charts Not Rendering

**Cause**: Chart.js not loaded

**Solution**: Check `frontend/index.html` has:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

### Low Accuracy (<70%)

**Cause**: Insufficient data

**Solution**:
- Collect 30+ days of data
- Ensure 20+ students
- Check data quality

### API Returns 401

**Cause**: Invalid or expired token

**Solution**:
- Re-login to get new token
- Check token in localStorage
- Verify backend is running

### Import Errors

**Cause**: Missing dependencies

**Solution**:
```bash
pip install --upgrade scikit-learn pandas numpy
```

---

## Technical Details

### Algorithms

**Linear Regression**:
- Method: Ordinary Least Squares (OLS)
- Formula: y = mx + b
- Metric: R² score (0-1, higher is better)

**Logistic Regression**:
- Method: Maximum Likelihood Estimation
- Formula: P(y=1) = 1 / (1 + e^-(mx+b))
- Metric: Accuracy % (higher is better)

### Feature Engineering

10 features calculated per student:
- Attendance metrics (total, present, absent, late)
- Rates (overall, Monday, Friday)
- Trends (recent 7 days)
- Patterns (consecutive absences, late frequency)

### Feature Scaling

Logistic Regression uses StandardScaler:
```python
X_scaled = (X - mean) / std_dev
```

Ensures all features contribute equally.

### Model Training

1. Fetch attendance data from database
2. Engineer features per student
3. Scale features (Logistic only)
4. Train model on historical data
5. Generate predictions/classifications
6. Calculate metrics
7. Return results

### Expected Accuracy

With sufficient data (30+ days, 20+ students):

| Model | Metric | Expected |
|-------|--------|----------|
| Linear Regression | R² Score | > 0.70 |
| Logistic Regression | Accuracy | > 85% |

---

## File Structure

```
backend/
├── ml_analytics.py          # ML models implementation
├── test_ml.py              # Test script with validation
├── quick_add_data.py       # Quick sample data generator
├── app.py                  # API endpoints (3 ML routes)
└── requirements.txt        # Dependencies (includes scikit-learn)

frontend/
├── index.html              # ML Analytics page section
├── app.js                  # ML functions and chart rendering
└── styles.css              # ML dashboard styling
```

---

## Best Practices

### For Development
- Use `quick_add_data.py` for instant testing
- Run `test_ml.py` for comprehensive validation
- Check backend logs for errors

### For Production
- Collect real attendance data (30+ days)
- Aim for 20+ students minimum
- Mark attendance consistently
- Run weekly ML analysis
- Act on recommendations
- Track intervention effectiveness

### For Accuracy
- Ensure quality data entry
- Avoid gaps in attendance records
- Register students with complete info
- Use consistent status values

---

## Use Cases by Role

### Administrators
- 📊 Forecast attendance trends
- 📈 Track intervention effectiveness
- 🎯 Set data-driven goals
- 📋 Generate reports for stakeholders

### Teachers
- ⚠️ Identify struggling students early
- 📞 Prioritize parent communications
- 📚 Plan targeted interventions
- 📊 Monitor class patterns

### Counselors
- 🎯 Focus on high-risk students
- 📈 Monitor intervention effectiveness
- 📞 Schedule counseling sessions
- 📊 Track student progress

---

## Quick Reference

### Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Add sample data
python backend/quick_add_data.py

# Test ML models
python backend/test_ml.py

# Start backend
python backend/app.py
```

### API Endpoints
```
GET /api/ml/predict_attendance      # Linear Regression
GET /api/ml/at_risk_students        # Logistic Regression
GET /api/ml/full_analysis           # Both models
```

### Data Requirements
- **Minimum**: 10 days, 5 students
- **Recommended**: 30 days, 20 students

### Severity Levels
- 🔴 Critical: <50% or 7+ consecutive absences
- 🟠 High: <65% or 5+ consecutive absences
- 🟡 Medium: <75% or recent trend <50%
- 🟢 Low: 70-75% with improving trend

---

## Support

### Getting Help
1. Check this documentation
2. Run `python backend/test_ml.py`
3. Check backend logs (terminal output)
4. Check browser console (F12)
5. Verify data requirements met

### Common Issues
- **Insufficient data**: Run `quick_add_data.py`
- **Import errors**: `pip install scikit-learn`
- **Charts not showing**: Check Chart.js loaded
- **API errors**: Check authentication token

---

## License

MIT License - Free to use and modify

---

## Summary

✅ **2 ML models** (Linear & Logistic Regression)  
✅ **3 API endpoints** (predict, classify, analyze)  
✅ **10 features** analyzed per student  
✅ **7-day predictions** for attendance trends  
✅ **Risk classification** with severity levels  
✅ **Beautiful dashboard** with charts & tables  
✅ **Complete documentation** in one file  

**Start using ML analytics to improve attendance!** 🚀
