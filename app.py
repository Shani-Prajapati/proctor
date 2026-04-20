"""
AI Exam Proctor — Python Flask Backend
=======================================
Replaces localStorage with a real server-side database (SQLite).
Handles:
  - Faculty registration / login
  - Student login + room code validation
  - Room (exam session) creation
  - Real-time violation logging from student
  - Faculty dashboard data API
  - Static file serving (all HTML/JS/CSS/model files)

Run:
  python app.py
Then open:
  http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import sqlite3, hashlib, os, json
from datetime import datetime

# ── App setup ──────────────────────────────────────────────────
app = Flask(__name__, static_folder='static')
CORS(app)  # allow requests from phone (different origin via PeerJS)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'proctor.db')

# ── Database init ───────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Faculty accounts
    c.execute('''CREATE TABLE IF NOT EXISTS faculty (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT    NOT NULL,
        email    TEXT    NOT NULL UNIQUE,
        password TEXT    NOT NULL,
        created  TEXT    NOT NULL
    )''')

    # Student accounts
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        email    TEXT    NOT NULL UNIQUE,
        password TEXT    NOT NULL,
        created  TEXT    NOT NULL
    )''')

    # Exam rooms created by faculty
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        code         TEXT    NOT NULL UNIQUE,
        faculty_email TEXT   NOT NULL,
        exam_name    TEXT    NOT NULL,
        created      TEXT    NOT NULL,
        active       INTEGER NOT NULL DEFAULT 1
    )''')

    # Active exam sessions (one per student per exam)
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id      TEXT    NOT NULL UNIQUE,
        student_id   TEXT    NOT NULL,
        student_name TEXT    NOT NULL,
        student_email TEXT   NOT NULL,
        subject      TEXT    NOT NULL,
        room_code    TEXT    NOT NULL,
        login_time   TEXT    NOT NULL,
        violations   INTEGER NOT NULL DEFAULT 0,
        integrity    INTEGER NOT NULL DEFAULT 100,
        status       TEXT    NOT NULL DEFAULT 'active',
        last_update  TEXT
    )''')

    # Violation log
    c.execute('''CREATE TABLE IF NOT EXISTS violations (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id    TEXT    NOT NULL,
        num        INTEGER NOT NULL,
        time       TEXT    NOT NULL,
        msg        TEXT    NOT NULL,
        integrity  INTEGER NOT NULL
    )''')

    conn.commit()
    conn.close()
    print("✅ Database ready:", DB_PATH)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def now():
    return datetime.now().isoformat()

# ══════════════════════════════════════════════════════════════
#  STATIC FILE SERVING
#  Serves all HTML, JS, CSS, model files from /static folder
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory('static', 'login.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ══════════════════════════════════════════════════════════════
#  FACULTY API
# ══════════════════════════════════════════════════════════════

@app.route('/api/faculty/register', methods=['POST'])
def faculty_register():
    data = request.get_json()
    name  = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    pw    = data.get('password') or ''
    if not name or not email or not pw:
        return jsonify({'ok': False, 'msg': 'All fields required.'}), 400
    if len(pw) < 6:
        return jsonify({'ok': False, 'msg': 'Password must be at least 6 characters.'}), 400
    try:
        conn = get_db()
        conn.execute(
            'INSERT INTO faculty (name, email, password, created) VALUES (?,?,?,?)',
            (name, email, hash_password(pw), now())
        )
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except sqlite3.IntegrityError:
        return jsonify({'ok': False, 'msg': 'Account with this email already exists.'}), 409

@app.route('/api/faculty/login', methods=['POST'])
def faculty_login():
    data  = request.get_json()
    email = (data.get('email') or '').strip().lower()
    pw    = data.get('password') or ''
    conn  = get_db()
    row   = conn.execute(
        'SELECT * FROM faculty WHERE email=? AND password=?',
        (email, hash_password(pw))
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'ok': False, 'msg': 'Email or password is incorrect.'}), 401
    return jsonify({'ok': True, 'name': row['name'], 'email': row['email']})

# ══════════════════════════════════════════════════════════════
#  ROOM (EXAM SESSION) API
# ══════════════════════════════════════════════════════════════

@app.route('/api/rooms/create', methods=['POST'])
def create_room():
    data         = request.get_json()
    code         = (data.get('code') or '').strip().upper()
    faculty_email= (data.get('faculty_email') or '').strip().lower()
    exam_name    = (data.get('exam_name') or 'Exam').strip()
    if not code or not faculty_email:
        return jsonify({'ok': False, 'msg': 'Missing fields.'}), 400
    try:
        conn = get_db()
        conn.execute(
            'INSERT INTO rooms (code, faculty_email, exam_name, created) VALUES (?,?,?,?)',
            (code, faculty_email, exam_name, now())
        )
        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'code': code})
    except sqlite3.IntegrityError:
        return jsonify({'ok': False, 'msg': 'Room code already exists.'}), 409

@app.route('/api/rooms/validate/<code>', methods=['GET'])
def validate_room(code):
    conn = get_db()
    row  = conn.execute(
        'SELECT * FROM rooms WHERE code=? AND active=1',
        (code.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'ok': False, 'msg': 'Invalid room code. Ask your faculty.'}), 404
    return jsonify({'ok': True, 'exam_name': row['exam_name']})

@app.route('/api/rooms/faculty/<email>', methods=['GET'])
def faculty_rooms(email):
    conn  = get_db()
    rows  = conn.execute(
        'SELECT * FROM rooms WHERE faculty_email=? ORDER BY created DESC',
        (email.lower(),)
    ).fetchall()
    conn.close()
    return jsonify({'ok': True, 'rooms': [dict(r) for r in rows]})

# ══════════════════════════════════════════════════════════════
#  STUDENT API
# ══════════════════════════════════════════════════════════════

@app.route('/api/student/login', methods=['POST'])
def student_login():
    data    = request.get_json()
    name    = (data.get('name') or '').strip()
    sid     = (data.get('id') or '').strip()
    subject = (data.get('subject') or '').strip()
    code    = (data.get('code') or '').strip().upper()
    email   = (data.get('email') or '').strip().lower()
    pw      = data.get('password') or ''

    if not all([name, sid, subject, code, email, pw]):
        return jsonify({'ok': False, 'msg': 'Please fill in all fields.'}), 400
    if len(pw) < 6:
        return jsonify({'ok': False, 'msg': 'Password must be at least 6 characters.'}), 400

    conn = get_db()

    # Validate room
    room = conn.execute(
        'SELECT * FROM rooms WHERE code=? AND active=1', (code,)
    ).fetchone()
    if not room:
        conn.close()
        return jsonify({'ok': False, 'msg': 'Invalid room code. Ask your faculty.'}), 404

    # Register or verify student password
    existing = conn.execute(
        'SELECT * FROM students WHERE email=?', (email,)
    ).fetchone()
    if existing:
        if existing['password'] != hash_password(pw):
            conn.close()
            return jsonify({'ok': False, 'msg': 'Incorrect password for this email.'}), 401
    else:
        conn.execute(
            'INSERT INTO students (email, password, created) VALUES (?,?,?)',
            (email, hash_password(pw), now())
        )

    # Create exam session
    import random
    exam_id = 'EX-' + str(random.randint(10000, 99999))
    try:
        conn.execute('''INSERT INTO sessions
            (exam_id, student_id, student_name, student_email, subject, room_code, login_time)
            VALUES (?,?,?,?,?,?,?)''',
            (exam_id, sid, name, email, subject, code, now())
        )
    except sqlite3.IntegrityError:
        # exam_id collision — try again
        exam_id = 'EX-' + str(random.randint(10000, 99999))
        conn.execute('''INSERT INTO sessions
            (exam_id, student_id, student_name, student_email, subject, room_code, login_time)
            VALUES (?,?,?,?,?,?,?)''',
            (exam_id, sid, name, email, subject, code, now())
        )

    conn.commit()
    conn.close()

    return jsonify({
        'ok': True,
        'session': {
            'role': 'student',
            'name': name,
            'id': sid,
            'subject': subject,
            'email': email,
            'roomCode': code,
            'examId': exam_id,
            'loginTime': now()
        }
    })

# ══════════════════════════════════════════════════════════════
#  VIOLATION LOGGING API
#  Called by index.html when a violation is detected
# ══════════════════════════════════════════════════════════════

@app.route('/api/violations/log', methods=['POST'])
def log_violation():
    data      = request.get_json()
    exam_id   = data.get('exam_id')
    num       = data.get('num')
    time_str  = data.get('time')
    msg       = data.get('msg')
    integrity = data.get('integrity', 100)

    if not exam_id or not msg:
        return jsonify({'ok': False, 'msg': 'Missing fields.'}), 400

    conn = get_db()
    conn.execute(
        'INSERT INTO violations (exam_id, num, time, msg, integrity) VALUES (?,?,?,?,?)',
        (exam_id, num, time_str, msg, integrity)
    )
    # Update session
    conn.execute('''UPDATE sessions SET
        violations=?, integrity=?, status=?, last_update=?
        WHERE exam_id=?''',
        (num, integrity,
         'critical' if num >= 5 else 'warning',
         now(), exam_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/violations/<exam_id>', methods=['GET'])
def get_violations(exam_id):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM violations WHERE exam_id=? ORDER BY num',
        (exam_id,)
    ).fetchall()
    conn.close()
    return jsonify({'ok': True, 'violations': [dict(r) for r in rows]})

# ══════════════════════════════════════════════════════════════
#  FACULTY DASHBOARD API
#  Returns all active students for a room
# ══════════════════════════════════════════════════════════════

@app.route('/api/dashboard/<room_code>', methods=['GET'])
def dashboard(room_code):
    conn = get_db()
    rows = conn.execute('''
        SELECT s.*, 
               (SELECT COUNT(*) FROM violations v WHERE v.exam_id=s.exam_id) as vcount
        FROM sessions s
        WHERE s.room_code=?
        ORDER BY s.violations DESC, s.login_time DESC
    ''', (room_code.upper(),)).fetchall()
    conn.close()
    return jsonify({'ok': True, 'students': [dict(r) for r in rows]})

@app.route('/api/dashboard/all/<faculty_email>', methods=['GET'])
def dashboard_all(faculty_email):
    """All students across all rooms for this faculty"""
    conn = get_db()
    rooms = conn.execute(
        'SELECT code FROM rooms WHERE faculty_email=?',
        (faculty_email.lower(),)
    ).fetchall()
    codes = [r['code'] for r in rooms]
    if not codes:
        conn.close()
        return jsonify({'ok': True, 'students': []})
    placeholders = ','.join('?' * len(codes))
    rows = conn.execute(f'''
        SELECT s.*
        FROM sessions s
        WHERE s.room_code IN ({placeholders})
        ORDER BY s.violations DESC, s.login_time DESC
    ''', codes).fetchall()
    conn.close()
    return jsonify({'ok': True, 'students': [dict(r) for r in rows]})

@app.route('/api/session/end', methods=['POST'])
def end_session():
    data    = request.get_json()
    exam_id = data.get('exam_id')
    conn    = get_db()
    conn.execute(
        "UPDATE sessions SET status='ended', last_update=? WHERE exam_id=?",
        (now(), exam_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'msg': 'AI Exam Proctor backend running ✅'})

# ── Run ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("\n🚀 AI Exam Proctor Backend")
    print("   Open: http://localhost:5000")
    print("   DB:  ", DB_PATH)
    print("   Put your HTML files in the /static folder\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
