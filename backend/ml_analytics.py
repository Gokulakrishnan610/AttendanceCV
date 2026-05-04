"""
ML Analytics Module for Attendance System
Implements Linear Regression and Logistic Regression for attendance analysis
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, mean_squared_error, r2_score
import sqlite3
import logging

logger = logging.getLogger(__name__)

class AttendanceMLAnalytics:
    """ML Analytics for Attendance System - Linear & Logistic Regression"""
    
    def __init__(self, db_path='attendance.db'):
        self.db_path = db_path
        self.scaler = StandardScaler()
        
    def get_db(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def fetch_attendance_data(self):
        """Fetch all attendance data as DataFrame"""
        conn = self.get_db()
        query = """
            SELECT 
                a.student_id,
                s.name,
                a.date,
                a.status,
                s.department,
                s.year
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            ORDER BY a.date
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def prepare_student_features(self, df):
        """
        Prepare features for student-level analysis
        Returns: X (features), y (target), feature_names, features_df
        """
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Create features per student
        student_features = []
        
        for student_id in df['student_id'].unique():
            student_data = df[df['student_id'] == student_id].copy()
            student_data = student_data.sort_values('date')
            
            if len(student_data) < 5:  # Need minimum data
                continue
            
            # Calculate features
            total_days = len(student_data)
            present_days = len(student_data[student_data['status'] == 'Present'])
            absent_days = len(student_data[student_data['status'] == 'Absent'])
            late_days = len(student_data[student_data['status'] == 'Late'])
            
            # Attendance rate
            attendance_rate = present_days / total_days if total_days > 0 else 0
            
            # Day of week patterns (0=Monday, 6=Sunday)
            student_data['day_of_week'] = student_data['date'].dt.dayofweek
            monday_rate = len(student_data[(student_data['day_of_week'] == 0) & 
                                          (student_data['status'] == 'Present')]) / \
                         len(student_data[student_data['day_of_week'] == 0]) \
                         if len(student_data[student_data['day_of_week'] == 0]) > 0 else 0
            
            friday_rate = len(student_data[(student_data['day_of_week'] == 4) & 
                                          (student_data['status'] == 'Present')]) / \
                         len(student_data[student_data['day_of_week'] == 4]) \
                         if len(student_data[student_data['day_of_week'] == 4]) > 0 else 0
            
            # Recent trend (last 7 days)
            recent_data = student_data.tail(7)
            recent_attendance_rate = len(recent_data[recent_data['status'] == 'Present']) / \
                                    len(recent_data) if len(recent_data) > 0 else 0
            
            # Consecutive absences
            max_consecutive_absent = 0
            current_consecutive = 0
            for status in student_data['status']:
                if status == 'Absent':
                    current_consecutive += 1
                    max_consecutive_absent = max(max_consecutive_absent, current_consecutive)
                else:
                    current_consecutive = 0
            
            # Late frequency
            late_frequency = late_days / total_days if total_days > 0 else 0
            
            # Get student name
            student_name = student_data.iloc[0]['name']
            
            features = {
                'student_id': student_id,
                'name': student_name,
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'late_days': late_days,
                'attendance_rate': attendance_rate,
                'monday_attendance': monday_rate,
                'friday_attendance': friday_rate,
                'recent_trend': recent_attendance_rate,
                'max_consecutive_absent': max_consecutive_absent,
                'late_frequency': late_frequency,
                # Target: 1 if good attendance (>=75%), 0 otherwise
                'good_attendance': 1 if attendance_rate >= 0.75 else 0
            }
            
            student_features.append(features)
        
        if not student_features:
            return np.array([]), np.array([]), [], pd.DataFrame()
        
        features_df = pd.DataFrame(student_features)
        
        # Separate features and target
        feature_cols = ['total_days', 'present_days', 'absent_days', 'late_days',
                       'attendance_rate', 'monday_attendance', 'friday_attendance',
                       'recent_trend', 'max_consecutive_absent', 'late_frequency']
        
        # Ensure all columns exist
        if not all(col in features_df.columns for col in feature_cols):
            return np.array([]), np.array([]), [], features_df
        
        X = features_df[feature_cols].values
        y = features_df['good_attendance'].values
        
        return X, y, feature_cols, features_df
    
    # ========== 1. LINEAR REGRESSION ==========
    def predict_attendance_rate(self):
        """
        Linear Regression: Predict future attendance rate
        Based on historical daily trends
        """
        try:
            df = self.fetch_attendance_data()
            
            if len(df) == 0:
                return {'success': False, 'error': 'No attendance data found'}
            
            if len(df) < 10:
                return {'success': False, 'error': 'Insufficient data (need at least 10 attendance records)'}
            
            # Prepare time-series data (daily attendance rate)
            daily_stats = df.groupby('date').agg({
                'status': lambda x: (x == 'Present').sum() / len(x) * 100
            }).reset_index()
            daily_stats.columns = ['date', 'attendance_rate']
            daily_stats['date'] = pd.to_datetime(daily_stats['date'])
            daily_stats = daily_stats.sort_values('date')
            
            # Create day index (0, 1, 2, ...)
            daily_stats['day_index'] = range(len(daily_stats))
            
            X = daily_stats[['day_index']].values
            y = daily_stats['attendance_rate'].values
            
            # Train Linear Regression model
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict next 7 days
            last_day = daily_stats['day_index'].max()
            future_days = np.array([[last_day + i] for i in range(1, 8)])
            predictions = model.predict(future_days)
            
            # Calculate metrics on training data
            y_pred = model.predict(X)
            mse = mean_squared_error(y, y_pred)
            r2 = r2_score(y, y_pred)
            
            # Determine trend
            trend_direction = 'improving' if model.coef_[0] > 0 else 'declining'
            trend_strength = abs(model.coef_[0])
            
            # Calculate current average
            current_avg = float(daily_stats['attendance_rate'].tail(7).mean())
            
            return {
                'success': True,
                'model': 'Linear Regression',
                'current_average': round(current_avg, 2),
                'trend': {
                    'direction': trend_direction,
                    'rate_per_day': round(float(model.coef_[0]), 3),
                    'strength': 'strong' if trend_strength > 0.5 else 'moderate' if trend_strength > 0.2 else 'weak'
                },
                'predictions': [
                    {
                        'day': i + 1,
                        'predicted_rate': round(float(max(0, min(100, pred))), 2)
                    }
                    for i, pred in enumerate(predictions)
                ],
                'metrics': {
                    'mse': round(float(mse), 2),
                    'r2_score': round(float(r2), 3),
                    'accuracy': 'good' if r2 > 0.7 else 'moderate' if r2 > 0.5 else 'low'
                },
                'data_points': len(daily_stats),
                'recommendation': self._get_linear_recommendation(trend_direction, current_avg, predictions[-1])
            }
        except Exception as e:
            logger.error(f"Linear Regression error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_linear_recommendation(self, trend, current_avg, last_prediction):
        """Generate recommendation based on linear regression results"""
        if trend == 'declining' and current_avg < 75:
            return "⚠️ Critical: Attendance is declining and below 75%. Immediate intervention needed."
        elif trend == 'declining':
            return "⚠️ Warning: Attendance is declining. Monitor closely and consider preventive measures."
        elif trend == 'improving' and current_avg < 75:
            return "📈 Positive: Attendance is improving but still below target. Continue current efforts."
        else:
            return "✅ Good: Attendance is stable and above target. Maintain current practices."
    
    # ========== 2. LOGISTIC REGRESSION ==========
    def classify_at_risk_students(self):
        """
        Logistic Regression: Classify students as at-risk
        At-risk = attendance < 75%
        """
        try:
            df = self.fetch_attendance_data()
            
            if len(df) == 0:
                return {'success': False, 'error': 'No attendance data found'}
            
            X, y, feature_names, features_df = self.prepare_student_features(df)
            
            if len(X) == 0 or len(X) < 5:
                return {'success': False, 'error': 'Insufficient data (need at least 5 students with 5+ attendance records each)'}
            
            # Scale features for better performance
            X_scaled = self.scaler.fit_transform(X)
            
            # Train Logistic Regression model
            model = LogisticRegression(random_state=42, max_iter=1000)
            model.fit(X_scaled, y)
            
            # Predict
            predictions = model.predict(X_scaled)
            probabilities = model.predict_proba(X_scaled)
            
            # Separate students by risk level
            at_risk_students = []
            good_standing_students = []
            
            for i, (student_id, name, pred, prob) in enumerate(zip(
                features_df['student_id'], 
                features_df['name'],
                predictions, 
                probabilities
            )):
                student_info = {
                    'student_id': student_id,
                    'name': name,
                    'attendance_rate': round(float(features_df.iloc[i]['attendance_rate'] * 100), 2),
                    'present_days': int(features_df.iloc[i]['present_days']),
                    'absent_days': int(features_df.iloc[i]['absent_days']),
                    'late_days': int(features_df.iloc[i]['late_days']),
                    'recent_trend': round(float(features_df.iloc[i]['recent_trend'] * 100), 2),
                    'max_consecutive_absent': int(features_df.iloc[i]['max_consecutive_absent']),
                    'risk_probability': round(float(prob[0] * 100), 2),
                    'good_probability': round(float(prob[1] * 100), 2)
                }
                
                if pred == 0:  # At-risk (poor attendance)
                    student_info['status'] = 'At Risk'
                    student_info['severity'] = self._get_risk_severity(
                        features_df.iloc[i]['attendance_rate'],
                        features_df.iloc[i]['recent_trend'],
                        features_df.iloc[i]['max_consecutive_absent']
                    )
                    at_risk_students.append(student_info)
                else:  # Good standing
                    student_info['status'] = 'Good Standing'
                    good_standing_students.append(student_info)
            
            # Calculate accuracy
            accuracy = accuracy_score(y, predictions)
            
            # Sort at-risk students by risk probability (highest first)
            at_risk_students = sorted(at_risk_students, 
                                     key=lambda x: x['risk_probability'], 
                                     reverse=True)
            
            return {
                'success': True,
                'model': 'Logistic Regression',
                'summary': {
                    'total_students': len(features_df),
                    'at_risk_count': len(at_risk_students),
                    'good_standing_count': len(good_standing_students),
                    'at_risk_percentage': round(len(at_risk_students) / len(features_df) * 100, 2)
                },
                'at_risk_students': at_risk_students,
                'good_standing_students': sorted(good_standing_students, 
                                                key=lambda x: x['attendance_rate'], 
                                                reverse=True),
                'model_performance': {
                    'accuracy': round(float(accuracy * 100), 2),
                    'quality': 'excellent' if accuracy > 0.9 else 'good' if accuracy > 0.8 else 'moderate'
                },
                'recommendations': self._get_logistic_recommendations(at_risk_students)
            }
        except Exception as e:
            logger.error(f"Logistic Regression error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_risk_severity(self, attendance_rate, recent_trend, max_consecutive):
        """Determine risk severity level"""
        if attendance_rate < 0.5 or max_consecutive >= 7:
            return 'Critical'
        elif attendance_rate < 0.65 or max_consecutive >= 5:
            return 'High'
        elif attendance_rate < 0.75 or recent_trend < 0.5:
            return 'Medium'
        else:
            return 'Low'
    
    def _get_logistic_recommendations(self, at_risk_students):
        """Generate recommendations based on at-risk analysis"""
        recommendations = []
        
        if len(at_risk_students) == 0:
            recommendations.append("✅ No students currently at risk. Continue monitoring.")
        else:
            critical = [s for s in at_risk_students if s['severity'] == 'Critical']
            high = [s for s in at_risk_students if s['severity'] == 'High']
            
            if critical:
                recommendations.append(f"🚨 {len(critical)} student(s) in CRITICAL status - immediate intervention required")
            if high:
                recommendations.append(f"⚠️ {len(high)} student(s) at HIGH risk - schedule counseling sessions")
            
            recommendations.append(f"📞 Contact parents/guardians of {len(at_risk_students)} at-risk student(s)")
            recommendations.append("📊 Review attendance policies and support programs")
        
        return recommendations
    
    # ========== COMBINED ANALYSIS ==========
    def run_full_analysis(self):
        """Run both Linear and Logistic Regression models"""
        try:
            linear_results = self.predict_attendance_rate()
            logistic_results = self.classify_at_risk_students()
            
            # Check if we have any valid results
            has_linear = linear_results.get('success', False)
            has_logistic = logistic_results.get('success', False)
            
            if not has_linear and not has_logistic:
                return {
                    'success': False,
                    'error': 'Insufficient data for ML analysis. Need at least 10 days of attendance records and 5 students.',
                    'linear_regression': linear_results,
                    'logistic_regression': logistic_results,
                    'overall_insights': []
                }
            
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'linear_regression': linear_results,
                'logistic_regression': logistic_results,
                'overall_insights': self._generate_overall_insights(linear_results, logistic_results)
            }
        except Exception as e:
            logger.error(f"Full analysis error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_overall_insights(self, linear_results, logistic_results):
        """Generate combined insights from both models"""
        insights = []
        
        # Check if both models succeeded
        if not linear_results.get('success') or not logistic_results.get('success'):
            return ["⚠️ Unable to generate insights due to insufficient data"]
        
        # Overall attendance trend
        trend = linear_results['trend']['direction']
        current_avg = linear_results['current_average']
        at_risk_count = logistic_results['summary']['at_risk_count']
        
        if trend == 'declining' and at_risk_count > 0:
            insights.append(f"🔴 Critical Situation: Attendance declining with {at_risk_count} at-risk students")
        elif trend == 'improving' and at_risk_count > 0:
            insights.append(f"🟡 Mixed Signals: Overall improving but {at_risk_count} students still at risk")
        elif trend == 'declining':
            insights.append("🟠 Warning: Attendance trend is declining - proactive measures needed")
        else:
            insights.append("🟢 Positive: Attendance trend is stable or improving")
        
        # Specific recommendations
        if current_avg < 70:
            insights.append("📉 Overall attendance below 70% - urgent action required")
        elif current_avg < 80:
            insights.append("📊 Overall attendance below 80% - improvement needed")
        
        return insights
