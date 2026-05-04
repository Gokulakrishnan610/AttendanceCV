"""Authentication module - JWT + bcrypt + RBAC"""
import jwt
import bcrypt
import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

SECRET_KEY = os.environ.get('SECRET_KEY', 'attendance-secret-key-2024')
TOKEN_EXPIRY_HOURS = 24
ROLES = ['admin', 'teacher', 'student']

DATABASE = os.environ.get('DATABASE_PATH', 'attendance.db')


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_tables():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        student_id TEXT,
        full_name TEXT,
        email TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )''')
    # Migrate: add missing columns to existing tables
    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
    migrations = [
        ("is_active", "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1"),
        ("student_id", "ALTER TABLE users ADD COLUMN student_id TEXT"),
        ("full_name", "ALTER TABLE users ADD COLUMN full_name TEXT"),
        ("email", "ALTER TABLE users ADD COLUMN email TEXT"),
        ("last_login", "ALTER TABLE users ADD COLUMN last_login TIMESTAMP"),
    ]
    for col, sql in migrations:
        if col not in existing_cols:
            c.execute(sql)
    # Default admin
    c.execute("SELECT id FROM users WHERE username='admin'")
    if not c.fetchone():
        ph = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
        c.execute(
            "INSERT INTO users (username,password_hash,role,full_name) VALUES (?,?,?,?)",
            ('admin', ph, 'admin', 'System Administrator')
        )
    # Default teacher
    c.execute("SELECT id FROM users WHERE username='teacher'")
    if not c.fetchone():
        ph = bcrypt.hashpw(b'teacher123', bcrypt.gensalt()).decode()
        c.execute(
            "INSERT INTO users (username,password_hash,role,full_name) VALUES (?,?,?,?)",
            ('teacher', ph, 'teacher', 'Default Teacher')
        )
    conn.commit()
    conn.close()


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def check_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def generate_token(user_id, username, role) -> str:
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])


def get_token_from_request():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:]
    return request.cookies.get('token')


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        try:
            payload = decode_token(token)
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_from_request()
            if not token:
                return jsonify({'error': 'Authentication required'}), 401
            try:
                payload = decode_token(token)
                request.user = payload
                if payload.get('role') not in roles:
                    return jsonify({'error': f'Access denied. Required roles: {list(roles)}'}), 403
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'Invalid token'}), 401
            return f(*args, **kwargs)
        return decorated
    return decorator
