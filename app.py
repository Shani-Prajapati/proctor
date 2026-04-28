"""
AI Exam Proctor — Python Flask Backend
=======================================
Optional alternative backend to Firebase (uses local SQLite).
Most users will use Firebase (firebase-config.js) — this file is here
if you want a fully local / self-hosted setup.

Run:
  pip install -r requirements.txt
  python app.py

Then open:
  http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, hashlib, os, random
from datetime import datetime

# ── App setup ──────────────────────────────────────────────────
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'proctor.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS faculty (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE, password TEXT NOT NULL, created TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL, created TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE,
        faculty_email TEXT NOT NULL, exam_name TEXT NOT NULL,
        created TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id TEXT NOT NULL UNIQUE,
        student_id TEXT NOT NULL, student_name TEXT NOT NULL,
        student_email TEXT NOT NULL, subject TEXT NOT NULL,
        room_code TEXT NOT NULL, login_time TEXT NOT NULL,
        violations INTEGER NOT NULL DEFAULT 0, integrity INTEGER NOT NULL DEFAULT 100,
        status TEXT NOT NULL DEFAULT 'active', last_update TEXT,
        quiz_mode INTEGER NOT NULL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id TEXT NOT NULL,
        num INTEGER NOT NULL, time TEXT NOT NULL, msg TEXT NOT NULL,
        integrity INTEGER NOT NULL, kind TEXT DEFAULT 'general')''')
    conn.commit(); conn.close()
    print("Database ready:", DB_PATH)

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def now(): return datetime.now().isoformat()

@app.route('/')
def index(): return send_from_directory(STATIC_DIR, 'login.html')

@app.route('/<path:filename>')
def static_files(filename): return send_from_directory(STATIC_DIR, filename)

@app.route('/api/health')
def health(): return jsonify({'ok': True, 'msg': 'AI Exam Proctor backend running'})

# ── Faculty ────────────────────────────────────────────────────
@app.route('/api/faculty/register', methods=['POST'])
def faculty_register():
    d = request.get_json() or {}
    name = (d.get('name') or '').strip(); email = (d.get('email') or '').strip().lower(); pw = d.get('password') or ''
    if not name or not email or not pw: return jsonify({'ok': False, 'msg': 'All fields required.'}), 400
    if len(pw) < 6: return jsonify({'ok': False, 'msg': 'Password must be at least 6 characters.'}), 400
    try:
        conn = get_db()
        conn.execute('INSERT INTO faculty (name,email,password,created) VALUES (?,?,?,?)',
                     (name, email, hash_password(pw), now()))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    except sqlite3.IntegrityError:
        return jsonify({'ok': False, 'msg': 'Account with this email already exists.'}), 409

@app.route('/api/faculty/login', methods=['POST'])
def faculty_login():
    d = request.get_json() or {}
    email = (d.get('email') or '').strip().lower(); pw = d.get('password') or ''
    conn = get_db()
    row = conn.execute('SELECT * FROM faculty WHERE email=? AND password=?',
                       (email, hash_password(pw))).fetchone()
    conn.close()
    if not row: return jsonify({'ok': False, 'msg': 'Email or password is incorrect.'}), 401
    return jsonify({'ok': True, 'name': row['name'], 'email': row['email']})

# ── Rooms ──────────────────────────────────────────────────────
@app.route('/api/rooms/create', methods=['POST'])
def create_room():
    d = request.get_json() or {}
    code = (d.get('code') or '').strip().upper()
    fac  = (d.get('faculty_email') or '').strip().lower()
    name = (d.get('exam_name') or 'Exam').strip()
    if not code or not fac: return jsonify({'ok': False, 'msg': 'Missing fields.'}), 400
    try:
        conn = get_db()
        conn.execute('INSERT INTO rooms (code,faculty_email,exam_name,created) VALUES (?,?,?,?)',
                     (code, fac, name, now()))
        conn.commit(); conn.close()
        return jsonify({'ok': True, 'code': code})
    except sqlite3.IntegrityError:
        return jsonify({'ok': False, 'msg': 'Room code already exists.'}), 409

@app.route('/api/rooms/validate/<code>')
def validate_room(code):
    conn = get_db()
    row = conn.execute('SELECT * FROM rooms WHERE code=? AND active=1', (code.upper(),)).fetchone()
    conn.close()
    if not row: return jsonify({'ok': False, 'msg': 'Invalid room code.'}), 404
    return jsonify({'ok': True, 'exam_name': row['exam_name']})

# ── Student ────────────────────────────────────────────────────
@app.route('/api/student/login', methods=['POST'])
def student_login():
    d = request.get_json() or {}
    name=(d.get('name') or '').strip(); sid=(d.get('id') or '').strip()
    subj=(d.get('subject') or '').strip(); code=(d.get('code') or '').strip().upper()
    email=(d.get('email') or '').strip().lower(); pw=d.get('password') or ''
    if not all([name,sid,subj,code,email,pw]): return jsonify({'ok':False,'msg':'Please fill in all fields.'}), 400
    if len(pw)<6: return jsonify({'ok':False,'msg':'Password must be at least 6 characters.'}), 400
    conn = get_db()
    room = conn.execute('SELECT * FROM rooms WHERE code=? AND active=1',(code,)).fetchone()
    if not room:
        conn.close(); return jsonify({'ok':False,'msg':'Invalid room code. Ask your faculty.'}), 404
    existing = conn.execute('SELECT * FROM students WHERE email=?',(email,)).fetchone()
    if existing:
        if existing['password'] != hash_password(pw):
            conn.close(); return jsonify({'ok':False,'msg':'Incorrect password for this email.'}), 401
    else:
        conn.execute('INSERT INTO students (email,password,created) VALUES (?,?,?)',
                     (email, hash_password(pw), now()))
    exam_id = 'EX-' + str(random.randint(10000,99999))
    conn.execute('''INSERT INTO sessions
        (exam_id,student_id,student_name,student_email,subject,room_code,login_time)
        VALUES (?,?,?,?,?,?,?)''',
        (exam_id, sid, name, email, subj, code, now()))
    conn.commit(); conn.close()
    return jsonify({'ok':True,'session':{
        'role':'student','name':name,'id':sid,'subject':subj,
        'email':email,'roomCode':code,'examId':exam_id,'loginTime':now()
    }})

# ── Violations ─────────────────────────────────────────────────
@app.route('/api/violations/log', methods=['POST'])
def log_violation():
    d = request.get_json() or {}
    eid = d.get('exam_id'); num=d.get('num'); t=d.get('time')
    msg=d.get('msg'); integ=d.get('integrity',100); kind=d.get('kind','general')
    if not eid or not msg: return jsonify({'ok':False,'msg':'Missing fields.'}), 400
    conn = get_db()
    conn.execute('INSERT INTO violations (exam_id,num,time,msg,integrity,kind) VALUES (?,?,?,?,?,?)',
                 (eid,num,t,msg,integ,kind))
    conn.execute('''UPDATE sessions SET violations=?, integrity=?, status=?, last_update=?
                    WHERE exam_id=?''',
                 (num,integ,'critical' if num>=5 else 'warning', now(), eid))
    conn.commit(); conn.close()
    return jsonify({'ok':True})

# NEW: dedicated endpoint for "extra tab opened during quiz mode" alert
@app.route('/api/violations/quiz-tab', methods=['POST'])
def log_quiz_tab_violation():
    d = request.get_json() or {}
    eid = d.get('exam_id'); tabs=d.get('tab_count',0); t=d.get('time') or now()
    if not eid: return jsonify({'ok':False,'msg':'Missing exam_id.'}), 400
    conn = get_db()
    cur = conn.execute('SELECT violations FROM sessions WHERE exam_id=?',(eid,)).fetchone()
    new_num = (cur['violations'] if cur else 0) + 1
    new_int = max(0, 100 - new_num*7)
    msg = f'Quiz Mode violation: {tabs} tabs open (limit is 2)'
    conn.execute('INSERT INTO violations (exam_id,num,time,msg,integrity,kind) VALUES (?,?,?,?,?,?)',
                 (eid,new_num,t,msg,new_int,'quiz_extra_tab'))
    conn.execute('''UPDATE sessions SET violations=?, integrity=?, status=?, last_update=?
                    WHERE exam_id=?''',
                 (new_num,new_int,'critical' if new_num>=5 else 'warning', now(), eid))
    conn.commit(); conn.close()
    return jsonify({'ok':True,'num':new_num,'integrity':new_int})

@app.route('/api/violations/<exam_id>')
def get_violations(exam_id):
    conn = get_db()
    rows = conn.execute('SELECT * FROM violations WHERE exam_id=? ORDER BY num',(exam_id,)).fetchall()
    conn.close()
    return jsonify({'ok':True,'violations':[dict(r) for r in rows]})

# ── Quiz Mode flag (for faculty dashboard awareness) ──────────
@app.route('/api/session/quiz-mode', methods=['POST'])
def set_quiz_mode():
    d = request.get_json() or {}
    eid=d.get('exam_id'); enabled=1 if d.get('enabled') else 0
    if not eid: return jsonify({'ok':False}), 400
    conn = get_db()
    conn.execute('UPDATE sessions SET quiz_mode=?, last_update=? WHERE exam_id=?',
                 (enabled, now(), eid))
    conn.commit(); conn.close()
    return jsonify({'ok':True})

# ── Dashboard ──────────────────────────────────────────────────
@app.route('/api/dashboard/<room_code>')
def dashboard(room_code):
    conn = get_db()
    rows = conn.execute('''
        SELECT s.*, (SELECT COUNT(*) FROM violations v WHERE v.exam_id=s.exam_id) as vcount
        FROM sessions s WHERE s.room_code=?
        ORDER BY s.violations DESC, s.login_time DESC''', (room_code.upper(),)).fetchall()
    conn.close()
    return jsonify({'ok':True,'students':[dict(r) for r in rows]})

@app.route('/api/session/end', methods=['POST'])
def end_session():
    d = request.get_json() or {}; eid = d.get('exam_id')
    conn = get_db()
    conn.execute("UPDATE sessions SET status='ended', last_update=? WHERE exam_id=?",(now(),eid))
    conn.commit(); conn.close()
    return jsonify({'ok':True})

if __name__ == '__main__':
    init_db()
    print("\nAI Exam Proctor Backend")
    print("  Open: http://localhost:5000")
    print("  DB:  ", DB_PATH)
    app.run(debug=True, host='0.0.0.0', port=5000)
