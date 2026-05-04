from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import sqlite3, cv2, numpy as np, face_recognition, os, csv, io, base64
from datetime import datetime
from werkzeug.utils import secure_filename
import logging, openpyxl, pandas as pd
from auth import init_auth_tables, hash_password, check_password, generate_token, decode_token, require_auth, require_role, get_token_from_request
from pdf_reports import generate_daily_report, generate_summary_report
from ml_analytics import AttendanceMLAnalytics

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app, supports_credentials=True)

# Initialize ML Analytics
ml_analytics = AttendanceMLAnalytics()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = 'uploads'
EXPORT_FOLDER = 'exports'
DATABASE = os.environ.get('DATABASE_PATH', 'attendance.db')
ALLOWED_IMG = {'png','jpg','jpeg'}
ALLOWED_VID = {'mp4','avi','mov','mkv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

trained_faces = {}

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, student_id TEXT UNIQUE NOT NULL,
        face_encoding BLOB, email TEXT, department TEXT, year TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Migrate students table
    existing_student_cols = {row[1] for row in c.execute("PRAGMA table_info(students)").fetchall()}
    for col, sql in [
        ("email",      "ALTER TABLE students ADD COLUMN email TEXT"),
        ("department", "ALTER TABLE students ADD COLUMN department TEXT"),
        ("year",       "ALTER TABLE students ADD COLUMN year TEXT"),
    ]:
        if col not in existing_student_cols:
            c.execute(sql)
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL, date DATE NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present','Absent','Late')),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(student_id),
        UNIQUE(student_id, date))''')
    # Migrate attendance table
    existing_att_cols = {row[1] for row in c.execute("PRAGMA table_info(attendance)").fetchall()}
    if "updated_at" not in existing_att_cols:
        c.execute("ALTER TABLE attendance ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    conn.commit(); conn.close()
    init_auth_tables()
    logger.info("DB initialized")

def load_faces():
    global trained_faces
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT student_id, face_encoding FROM students WHERE face_encoding IS NOT NULL")
    trained_faces = {}
    for row in c.fetchall():
        if row['face_encoding']:
            trained_faces[row['student_id']] = np.frombuffer(row['face_encoding'], dtype=np.float64)
    conn.close()
    return len(trained_faces)

def allowed(fn, exts): return '.' in fn and fn.rsplit('.',1)[1].lower() in exts

# ── FRONTEND SERVING ─────────────────────────────────────────
@app.route('/')
def index(): return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    fp = os.path.join('../frontend', path)
    if os.path.exists(fp): return send_from_directory('../frontend', path)
    return send_from_directory('../frontend', 'index.html')

# ── HEALTH ───────────────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({"status":"healthy","faces":len(trained_faces),"time":datetime.now().isoformat()})

# ── AUTH ─────────────────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username','').strip()
    password = data.get('password','')
    if not username or not password:
        return jsonify({'error':'Username and password required'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND is_active=1", (username,))
    user = c.fetchone()
    if not user or not check_password(password, user['password_hash']):
        conn.close()
        return jsonify({'error':'Invalid credentials'}), 401
    c.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now().isoformat(), user['id']))
    conn.commit(); conn.close()
    token = generate_token(user['id'], user['username'], user['role'])
    return jsonify({'token':token,'role':user['role'],'username':user['username'],'name':user['full_name']})

@app.route('/api/auth/register', methods=['POST'])
@require_role('admin')
def register_user():
    data = request.get_json() or {}
    required = ['username','password','role']
    if not all(k in data for k in required):
        return jsonify({'error':'Missing fields'}), 400
    if data['role'] not in ['admin','teacher','student']:
        return jsonify({'error':'Invalid role'}), 400
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username,password_hash,role,full_name,email,student_id) VALUES (?,?,?,?,?,?)",
            (data['username'], hash_password(data['password']), data['role'],
             data.get('full_name',''), data.get('email',''), data.get('student_id','')))
        conn.commit()
        return jsonify({'message':f"User {data['username']} created"})
    except sqlite3.IntegrityError:
        return jsonify({'error':'Username already exists'}), 409
    finally: conn.close()

@app.route('/api/auth/users', methods=['GET'])
@require_role('admin')
def list_users():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id,username,role,full_name,email,is_active,created_at,last_login FROM users ORDER BY created_at DESC")
    users = [dict(r) for r in c.fetchall()]
    conn.close(); return jsonify(users)

@app.route('/api/auth/users/<int:uid>', methods=['PUT'])
@require_role('admin')
def update_user(uid):
    data = request.get_json() or {}
    conn = get_db(); c = conn.cursor()
    fields, vals = [], []
    for k in ['full_name','email','role','is_active']:
        if k in data: fields.append(f"{k}=?"); vals.append(data[k])
    if 'password' in data: fields.append("password_hash=?"); vals.append(hash_password(data['password']))
    if not fields: return jsonify({'error':'Nothing to update'}), 400
    vals.append(uid)
    c.execute(f"UPDATE users SET {','.join(fields)} WHERE id=?", vals)
    conn.commit(); conn.close()
    return jsonify({'message':'User updated'})

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    return jsonify({'user_id':request.user['user_id'],'username':request.user['username'],'role':request.user['role']})

# ── STUDENTS ─────────────────────────────────────────────────
@app.route('/api/students', methods=['GET'])
@require_auth
def get_students():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT student_id,name,email,department,year,created_at FROM students ORDER BY name")
    students = [dict(r) for r in c.fetchall()]
    conn.close(); return jsonify(students)

@app.route('/api/add_student', methods=['POST'])
@require_role('admin','teacher')
def add_student():
    global trained_faces
    if 'name' not in request.form or 'student_id' not in request.form:
        return jsonify({'error':'Missing name or student_id'}), 400
    name = request.form['name'].strip()
    sid = request.form['student_id'].strip()
    email = request.form.get('email','')
    dept = request.form.get('department','')
    year = request.form.get('year','')
    encoding_blob = None
    if 'image' in request.files and request.files['image'].filename:
        img_file = request.files['image']
        if not allowed(img_file.filename, ALLOWED_IMG):
            return jsonify({'error':'Invalid image type'}), 400
        path = os.path.join(UPLOAD_FOLDER, secure_filename(f"{sid}_{img_file.filename}"))
        img_file.save(path)
        img = face_recognition.load_image_file(path)
        encs = face_recognition.face_encodings(img)
        os.remove(path)
        if not encs: return jsonify({'error':'No face detected'}), 400
        encoding_blob = encs[0].tobytes()
        trained_faces[sid] = encs[0]
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("SELECT id FROM students WHERE student_id=?", (sid,))
        if c.fetchone():
            q = "UPDATE students SET name=?,email=?,department=?,year=? WHERE student_id=?"
            params = [name,email,dept,year,sid]
            if encoding_blob: q = "UPDATE students SET name=?,email=?,department=?,year=?,face_encoding=? WHERE student_id=?"; params = [name,email,dept,year,encoding_blob,sid]
            c.execute(q, params); msg = f"Student {sid} updated"
        else:
            c.execute("INSERT INTO students (name,student_id,face_encoding,email,department,year) VALUES (?,?,?,?,?,?)", (name,sid,encoding_blob,email,dept,year))
            msg = f"Student {sid} registered"
        conn.commit(); return jsonify({'message':msg})
    except sqlite3.IntegrityError as e:
        return jsonify({'error':str(e)}), 400
    finally: conn.close()

@app.route('/api/students/<sid>', methods=['DELETE'])
@require_role('admin')
def delete_student(sid):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM students WHERE student_id=?", (sid,))
    c.execute("DELETE FROM attendance WHERE student_id=?", (sid,))
    conn.commit(); conn.close()
    trained_faces.pop(sid, None)
    return jsonify({'message':f'Student {sid} deleted'})

# ── BATCH IMPORT ─────────────────────────────────────────────
@app.route('/api/import_students', methods=['POST'])
@require_role('admin','teacher')
def import_students():
    if 'file' not in request.files: return jsonify({'error':'No file'}), 400
    f = request.files['file']
    ext = f.filename.rsplit('.',1)[-1].lower()
    rows, errors, added = [], [], 0
    try:
        if ext == 'csv':
            import csv as _csv
            content = f.read().decode('utf-8').splitlines()
            reader = _csv.DictReader(content)
            rows = list(reader)
        elif ext in ('xlsx','xls'):
            df = pd.read_excel(f)
            rows = df.to_dict('records')
        else:
            return jsonify({'error':'Only CSV or Excel files allowed'}), 400
    except Exception as e:
        return jsonify({'error':f'Parse error: {e}'}), 400

    conn = get_db(); c = conn.cursor()
    for i, row in enumerate(rows, 1):
        sid = str(row.get('student_id') or row.get('Student ID','')).strip()
        name = str(row.get('name') or row.get('Name','')).strip()
        if not sid or not name: errors.append(f"Row {i}: missing id or name"); continue
        email = str(row.get('email') or row.get('Email','')).strip()
        dept = str(row.get('department') or row.get('Department','')).strip()
        year = str(row.get('year') or row.get('Year','')).strip()
        try:
            c.execute("INSERT OR REPLACE INTO students (name,student_id,email,department,year) VALUES (?,?,?,?,?)", (name,sid,email,dept,year))
            added += 1
        except Exception as e:
            errors.append(f"Row {i} ({sid}): {e}")
    conn.commit(); conn.close()
    return jsonify({'imported':added,'errors':errors,'total':len(rows)})

# ── TRAINING ─────────────────────────────────────────────────
@app.route('/api/train_model', methods=['POST'])
@require_role('admin','teacher')
def train_model():
    count = load_faces()
    return jsonify({'message':f'Model trained with {count} students','student_count':count})

# ── VIDEO RECOGNITION ────────────────────────────────────────
@app.route('/api/recognize', methods=['POST'])
@require_role('admin','teacher')
def recognize():
    global trained_faces
    if 'video' not in request.files: return jsonify({'error':'No video'}), 400
    video = request.files['video']
    if not allowed(video.filename, ALLOWED_VID): return jsonify({'error':'Invalid video type'}), 400
    if not trained_faces: load_faces()
    if not trained_faces: return jsonify({'error':'No trained faces'}), 400
    path = os.path.join(UPLOAD_FOLDER, secure_filename(f"vid_{datetime.now().strftime('%Y%m%d%H%M%S')}_{video.filename}"))
    video.save(path)
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT student_id FROM students"); all_s = {r['student_id'] for r in c.fetchall()}
    c.close(); conn.close()
    cap = cv2.VideoCapture(path)
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    skip = max(1, fps//5)
    counts = {}; fc = 0
    while cap.isOpened() and fc < 300:
        ret, frame = cap.read()
        if not ret: break
        if fc % skip == 0:
            small = cv2.resize(frame,(0,0),fx=0.5,fy=0.5)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb)
            if locs:
                encs = face_recognition.face_encodings(rgb, locs)
                for enc in encs:
                    dists = face_recognition.face_distance(list(trained_faces.values()), enc)
                    if len(dists):
                        idx = np.argmin(dists)
                        if dists[idx] < 0.5:
                            sid = list(trained_faces.keys())[idx]
                            counts[sid] = counts.get(sid,0)+1
        fc += 1
    cap.release()
    try: os.remove(path)
    except: pass
    present = {s for s,n in counts.items() if n>=3}
    absent = all_s - present
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db(); c = conn.cursor()
    for sid in present:
        c.execute("INSERT INTO attendance (student_id,date,status) VALUES (?,?,'Present') ON CONFLICT(student_id,date) DO UPDATE SET status='Present',updated_at=CURRENT_TIMESTAMP", (sid,today))
    for sid in absent:
        c.execute("INSERT INTO attendance (student_id,date,status) VALUES (?,?,'Absent') ON CONFLICT(student_id,date) DO UPDATE SET status=CASE WHEN status='Present' THEN 'Present' ELSE 'Absent' END,updated_at=CURRENT_TIMESTAMP", (sid,today))
    conn.commit(); conn.close()
    return jsonify({'message':'Done','present':list(present),'absent':list(absent),'present_count':len(present),'absent_count':len(absent)})

# ── WEBCAM FRAME ─────────────────────────────────────────────
@app.route('/api/recognize_frame', methods=['POST'])
@require_role('admin','teacher')
def recognize_frame():
    global trained_faces
    data = request.get_json() or {}
    img_b64 = data.get('image','')
    if not img_b64: return jsonify({'error':'No image data'}), 400
    if not trained_faces: load_faces()
    try:
        img_data = base64.b64decode(img_b64.split(',')[-1])
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb)
        results = []
        if locs and trained_faces:
            encs = face_recognition.face_encodings(rgb, locs)
            for enc, loc in zip(encs, locs):
                dists = face_recognition.face_distance(list(trained_faces.values()), enc)
                if len(dists):
                    idx = np.argmin(dists)
                    if dists[idx] < 0.5:
                        sid = list(trained_faces.keys())[idx]
                        conn = get_db(); c2 = conn.cursor()
                        c2.execute("SELECT name FROM students WHERE student_id=?", (sid,))
                        row = c2.fetchone(); conn.close()
                        results.append({'student_id':sid,'name':row['name'] if row else sid,'confidence':float(1-dists[idx]),'location':loc})
                    else:
                        results.append({'student_id':None,'name':'Unknown','confidence':0,'location':loc})
        return jsonify({'faces':results,'count':len(results)})
    except Exception as e:
        return jsonify({'error':str(e)}), 500

# ── ATTENDANCE ───────────────────────────────────────────────
@app.route('/api/attendance', methods=['GET'])
@require_auth
def get_attendance():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db(); c = conn.cursor()
    c.execute('''SELECT a.student_id,s.name,a.date,a.status,a.updated_at
        FROM attendance a JOIN students s ON a.student_id=s.student_id
        WHERE a.date=? ORDER BY s.name''', (date,))
    records = [dict(r) for r in c.fetchall()]
    conn.close(); return jsonify(records)

@app.route('/api/attendance/history', methods=['GET'])
@require_auth
def attendance_history():
    sid = request.args.get('student_id', '')
    from_d = request.args.get('from', '')
    to_d = request.args.get('to', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db(); c = conn.cursor()
    query = '''SELECT a.student_id,s.name,a.date,a.status FROM attendance a
               JOIN students s ON a.student_id=s.student_id WHERE 1=1'''
    params = []
    if sid:
        query += ' AND a.student_id=?'
        params.append(sid)
    if from_d:
        query += ' AND a.date BETWEEN ? AND ?'
        params.extend([from_d, to_d])
    query += ' ORDER BY a.date DESC, s.name LIMIT 300'
    c.execute(query, params)
    records = [dict(r) for r in c.fetchall()]
    conn.close(); return jsonify(records)

@app.route('/api/update_attendance', methods=['POST'])
@require_role('admin','teacher')
def update_attendance():
    data = request.get_json() or {}
    sid = data.get('student_id'); status = data.get('status')
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    if not sid or status not in ('Present','Absent','Late'):
        return jsonify({'error':'Invalid data'}), 400
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM students WHERE student_id=?", (sid,))
    if not c.fetchone(): conn.close(); return jsonify({'error':'Student not found'}), 404
    c.execute('''INSERT INTO attendance (student_id,date,status) VALUES (?,?,?)
        ON CONFLICT(student_id,date) DO UPDATE SET status=?,updated_at=CURRENT_TIMESTAMP''', (sid,date,status,status))
    conn.commit(); conn.close()
    return jsonify({'message':f'{sid} marked {status} on {date}'})

# ── ANALYTICS ────────────────────────────────────────────────
@app.route('/api/stats', methods=['GET'])
@require_auth
def stats():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT status,COUNT(*) as n FROM attendance WHERE date=? GROUP BY status", (today,))
    today_stats = {'Present':0,'Absent':0,'Late':0}
    for r in c.fetchall(): today_stats[r['status']] = r['n']
    c.execute("SELECT COUNT(*) as n FROM students"); total = c.fetchone()['n']
    conn.close()
    return jsonify({'today':today_stats,'total_students':total})

@app.route('/api/analytics', methods=['GET'])
@require_auth
def analytics():
    conn = get_db(); c = conn.cursor()
    # 30 day trend
    c.execute('''SELECT date, status, COUNT(*) as n FROM attendance
        WHERE date >= date('now','-30 days') GROUP BY date,status ORDER BY date''')
    trend_rows = c.fetchall()
    trend = {}
    for r in trend_rows:
        d = r['date']
        if d not in trend: trend[d] = {'Present':0,'Absent':0,'Late':0}
        trend[d][r['status']] = r['n']
    # Per student summary
    c.execute('''SELECT s.student_id,s.name,
        SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present,
        SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) as absent,
        SUM(CASE WHEN a.status='Late' THEN 1 ELSE 0 END) as late,
        COUNT(a.id) as total
        FROM students s LEFT JOIN attendance a ON s.student_id=a.student_id
        GROUP BY s.student_id ORDER BY s.name''')
    student_stats = [dict(r) for r in c.fetchall()]
    # Weekly stats
    c.execute('''SELECT strftime('%w',date) as dow, COUNT(*) as n,
        AVG(CASE WHEN status='Present' THEN 1.0 ELSE 0 END)*100 as rate
        FROM attendance GROUP BY dow''')
    weekly = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'daily_trend':trend,'student_stats':student_stats,'weekly':weekly})

# ── EXPORT ───────────────────────────────────────────────────
@app.route('/api/export_csv', methods=['GET'])
@require_auth
def export_csv():
    from_d = request.args.get('from','')
    to_d = request.args.get('to', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db(); c = conn.cursor()
    if from_d:
        c.execute('''SELECT a.id,a.student_id,s.name,a.date,a.status,a.updated_at
            FROM attendance a JOIN students s ON a.student_id=s.student_id
            WHERE a.date BETWEEN ? AND ? ORDER BY a.date DESC,s.name''', (from_d,to_d))
    else:
        c.execute('''SELECT a.id,a.student_id,s.name,a.date,a.status,a.updated_at
            FROM attendance a JOIN students s ON a.student_id=s.student_id ORDER BY a.date DESC,s.name''')
    records = c.fetchall(); conn.close()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['ID','Student ID','Name','Date','Status','Updated'])
    for r in records: w.writerow(list(r))
    fname = f"attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    fpath = os.path.join(EXPORT_FOLDER, fname)
    with open(fpath,'w',newline='') as f: f.write(out.getvalue())
    return send_file(fpath, as_attachment=True, download_name=fname, mimetype='text/csv')

@app.route('/api/export_pdf', methods=['GET'])
@require_auth
def export_pdf():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db(); c = conn.cursor()
    c.execute('''SELECT a.student_id,s.name,a.date,a.status,a.updated_at
        FROM attendance a JOIN students s ON a.student_id=s.student_id
        WHERE a.date=? ORDER BY s.name''', (date,))
    records = [dict(r) for r in c.fetchall()]
    c.execute("SELECT status,COUNT(*) as n FROM attendance WHERE date=? GROUP BY status",(date,))
    s = {'Present':0,'Absent':0,'Late':0}
    for r in c.fetchall(): s[r['status']]=r['n']
    total = len(records); s['total']=total
    s['rate'] = f"{(s['Present']/total*100):.1f}%" if total else '0%'
    conn.close()
    buf = generate_daily_report(records, date, s)
    return send_file(buf, as_attachment=True, download_name=f"attendance_{date}.pdf", mimetype='application/pdf')

@app.route('/api/export_pdf_summary', methods=['GET'])
@require_auth
def export_pdf_summary():
    from_d = request.args.get('from', datetime.now().strftime('%Y-%m-01'))
    to_d = request.args.get('to', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db(); c = conn.cursor()
    c.execute('''SELECT s.student_id,s.name,
        SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present,
        SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) as absent,
        SUM(CASE WHEN a.status='Late' THEN 1 ELSE 0 END) as late,
        COUNT(a.id) as total
        FROM students s LEFT JOIN attendance a ON s.student_id=a.student_id
        AND a.date BETWEEN ? AND ? GROUP BY s.student_id ORDER BY s.name''', (from_d,to_d))
    data = [dict(r) for r in c.fetchall()]; conn.close()
    buf = generate_summary_report(data, from_d, to_d)
    return send_file(buf, as_attachment=True, download_name=f"summary_{from_d}_{to_d}.pdf", mimetype='application/pdf')

# ── ML ANALYTICS ─────────────────────────────────────────────
@app.route('/api/ml/predict_attendance', methods=['GET'])
@require_auth
def ml_predict_attendance():
    """Linear Regression: Predict future attendance rates"""
    result = ml_analytics.predict_attendance_rate()
    return jsonify(result)

@app.route('/api/ml/at_risk_students', methods=['GET'])
@require_auth
def ml_at_risk_students():
    """Logistic Regression: Identify at-risk students"""
    result = ml_analytics.classify_at_risk_students()
    return jsonify(result)

@app.route('/api/ml/full_analysis', methods=['GET'])
@require_auth
def ml_full_analysis():
    """Run both Linear and Logistic Regression models"""
    result = ml_analytics.run_full_analysis()
    return jsonify(result)

if __name__ == '__main__':
    init_db(); load_faces()
    logger.info("Starting Attendance System on port 5080")
    app.run(host='0.0.0.0', port=5080, debug=True)
