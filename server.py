"""Daily Reflection - Backend Server with User Authentication"""
import json
import sqlite3
import os
import hashlib
import secrets
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, g

app = Flask(__name__, static_folder='.')
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reflections.db')

# ── Password hashing ───────────────────────────────────────

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(32)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt + ':' + h.hex()

def verify_password(password, stored):
    salt = stored.split(':')[0]
    return stored == hash_password(password, salt)

# ── Database ──────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    ''')
    # Add role column for existing databases
    try:
        db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    except: pass
    # Make the first user admin if no admin exists
    admin_exists = db.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    if not admin_exists:
        db.execute("UPDATE users SET role='admin' WHERE id = (SELECT MIN(id) FROM users)")
    db.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS reflections (
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            data TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_reflections_user_date ON reflections(user_id, date DESC)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)')
    db.commit()
    db.close()

# ── Auth helpers ───────────────────────────────────────────

def get_current_user():
    """Get (user_id, role) from Authorization header, or (None, None)."""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None, None
    token = auth[7:]
    db = get_db()
    row = db.execute('''
        SELECT u.id, u.role FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
    ''', (token,)).fetchone()
    return (row['id'], row['role']) if row else (None, None)

def auth_required(f):
    """Decorator that requires a valid session token."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id, role = get_current_user()
        if user_id is None:
            return jsonify({'error': 'unauthorized'}), 401
        g.user_id = user_id
        g.role = role
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    """Decorator that requires admin role."""
    @wraps(f)
    @auth_required
    def wrapper(*args, **kwargs):
        if g.role != 'admin':
            return jsonify({'error': 'forbidden'}), 403
        return f(*args, **kwargs)
    return wrapper

# ── CORS ──────────────────────────────────────────────────

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# ── Static files ──────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'daily-reflection.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

# ── Auth endpoints ────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    password = (body.get('password') or '').strip()

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    if len(username) < 2 or len(username) > 30:
        return jsonify({'error': '用户名需 2-30 个字符'}), 400
    if len(password) < 4:
        return jsonify({'error': '密码至少 4 个字符'}), 400

    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        return jsonify({'error': '用户名已存在'}), 409

    pw_hash = hash_password(password)
    db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, pw_hash))
    db.commit()

    user_id = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()['id']
    token = secrets.token_hex(32)
    db.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (token, user_id))
    db.commit()

    return jsonify({'ok': True, 'token': token, 'username': username})

@app.route('/api/auth/login', methods=['POST'])
def login():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    password = (body.get('password') or '').strip()

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'error': '用户名或密码错误'}), 401

    token = secrets.token_hex(32)
    db.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (token, user['id']))
    db.commit()

    return jsonify({'ok': True, 'token': token, 'username': username})

@app.route('/api/auth/logout', methods=['POST'])
@auth_required
def logout():
    db = get_db()
    token = request.headers.get('Authorization', '')[7:]
    db.execute('DELETE FROM sessions WHERE token = ?', (token,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/auth/me')
@auth_required
def me():
    db = get_db()
    user = db.execute('SELECT id, username, role, created_at FROM users WHERE id = ?', (g.user_id,)).fetchone()
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'created_at': user['created_at']
    })

# ── Protected API ─────────────────────────────────────────

@app.route('/api/ping')
def ping():
    user_id, role = get_current_user()
    return jsonify({
        'ok': True,
        'time': datetime.now().isoformat(),
        'logged_in': user_id is not None,
        'role': role
    })

@app.route('/api/reflections', methods=['GET', 'POST', 'DELETE'])
@auth_required
def reflections():
    db = get_db()
    uid = g.user_id

    if request.method == 'GET':
        date = request.args.get('date', '')
        if date:
            row = db.execute(
                'SELECT * FROM reflections WHERE user_id = ? AND date = ?',
                (uid, date)
            ).fetchone()
            if row:
                return jsonify({
                    'date': row['date'],
                    'data': json.loads(row['data']),
                    'updated_at': row['updated_at']
                })
            return jsonify({'date': date, 'data': {}})
        else:
            rows = db.execute(
                'SELECT date, updated_at FROM reflections WHERE user_id = ? ORDER BY date DESC',
                (uid,)
            ).fetchall()
            return jsonify([{'date': r['date'], 'updated_at': r['updated_at']} for r in rows])

    elif request.method == 'POST':
        body = request.get_json(force=True)
        date = body.get('date', '')
        data = body.get('data', {})
        if not date:
            return jsonify({'error': 'date is required'}), 400

        db.execute('''
            INSERT INTO reflections (user_id, date, data, updated_at)
            VALUES (?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(user_id, date) DO UPDATE SET
                data = excluded.data,
                updated_at = datetime('now','localtime')
        ''', (uid, date, json.dumps(data, ensure_ascii=False)))
        db.commit()
        return jsonify({'ok': True, 'date': date})

    elif request.method == 'DELETE':
        date = request.args.get('date', '')
        if not date:
            return jsonify({'error': 'date is required'}), 400
        db.execute('DELETE FROM reflections WHERE user_id = ? AND date = ?', (uid, date))
        db.commit()
        return jsonify({'ok': True, 'date': date})

@app.route('/api/reflections/range')
@auth_required
def reflections_range():
    db = get_db()
    uid = g.user_id
    from_date = request.args.get('from', '')
    to_date = request.args.get('to', '')
    if not from_date or not to_date:
        return jsonify({'error': 'from and to are required'}), 400

    rows = db.execute('''
        SELECT date, data, updated_at FROM reflections
        WHERE user_id = ? AND date >= ? AND date <= ?
        ORDER BY date DESC
    ''', (uid, from_date, to_date)).fetchall()

    return jsonify([{
        'date': r['date'],
        'data': json.loads(r['data']),
        'updated_at': r['updated_at']
    } for r in rows])

@app.route('/api/stats')
@auth_required
def stats():
    db = get_db()
    uid = g.user_id
    total = db.execute('SELECT COUNT(*) as c FROM reflections WHERE user_id = ?', (uid,)).fetchone()['c']

    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    this_week = db.execute(
        'SELECT COUNT(*) as c FROM reflections WHERE user_id = ? AND date >= ? AND date <= ?',
        (uid, week_ago, today)
    ).fetchone()['c']

    rows = db.execute('SELECT data FROM reflections WHERE user_id = ?', (uid,)).fetchall()
    total_entries = 0
    for r in rows:
        data = json.loads(r['data'])
        for section_data in data.values():
            if isinstance(section_data, list):
                total_entries += len(section_data)

    first = db.execute(
        'SELECT date FROM reflections WHERE user_id = ? ORDER BY date ASC LIMIT 1', (uid,)
    ).fetchone()
    last = db.execute(
        'SELECT date FROM reflections WHERE user_id = ? ORDER BY date DESC LIMIT 1', (uid,)
    ).fetchone()

    return jsonify({
        'total_days': total,
        'this_week': this_week,
        'total_entries': total_entries,
        'first_date': first['date'] if first else None,
        'last_date': last['date'] if last else None
    })

@app.route('/api/search')
@auth_required
def search():
    db = get_db()
    uid = g.user_id
    q = request.args.get('q', '')
    if not q:
        return jsonify([])

    rows = db.execute(
        'SELECT date, data FROM reflections WHERE user_id = ? ORDER BY date DESC', (uid,)
    ).fetchall()
    results = []
    for r in rows:
        data = json.loads(r['data'])
        matches = []
        for section_id, items in data.items():
            if not isinstance(items, list): continue
            for item in items:
                text = item.get('text', '') if isinstance(item, dict) else str(item)
                if q.lower() in text.lower():
                    matches.append({
                        'section': section_id,
                        'text': text,
                        'timeStart': item.get('timeStart', '') if isinstance(item, dict) else '',
                        'timeEnd': item.get('timeEnd', '') if isinstance(item, dict) else ''
                    })
        if matches:
            results.append({'date': r['date'], 'matches': matches})
    return jsonify(results)

# ── Admin endpoints ──────────────────────────────────────

def _resolve_uid():
    """For admins: allow ?user_id= to query other users' data."""
    uid = g.user_id
    if g.role == 'admin':
        req_uid = request.args.get('user_id', '')
        if req_uid:
            uid = int(req_uid)
    return uid

@app.route('/api/admin/users')
@admin_required
def admin_users():
    db = get_db()
    users = db.execute('SELECT id, username, role, created_at FROM users ORDER BY id').fetchall()
    return jsonify([{
        'id': u['id'],
        'username': u['username'],
        'role': u['role'],
        'created_at': u['created_at']
    } for u in users])

@app.route('/api/admin/stats')
@admin_required
def admin_stats():
    db = get_db()
    total_users = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    total_days = db.execute('SELECT COUNT(*) as c FROM reflections').fetchone()['c']
    total_entries = 0
    rows = db.execute('SELECT data FROM reflections').fetchall()
    for r in rows:
        data = json.loads(r['data'])
        for section_data in data.values():
            if isinstance(section_data, list):
                total_entries += len(section_data)

    first = db.execute('SELECT date FROM reflections ORDER BY date ASC LIMIT 1').fetchone()
    last = db.execute('SELECT date FROM reflections ORDER BY date DESC LIMIT 1').fetchone()

    return jsonify({
        'total_users': total_users,
        'total_days': total_days,
        'total_entries': total_entries,
        'first_date': first['date'] if first else None,
        'last_date': last['date'] if last else None
    })

# Override reflections to support admin cross-user query
@app.route('/api/reflections/all')
@admin_required
def reflections_all():
    """Admin: list all reflections across all users with optional filters."""
    db = get_db()
    user_id = request.args.get('user_id', '')
    if user_id:
        rows = db.execute(
            'SELECT r.*, u.username FROM reflections r JOIN users u ON u.id=r.user_id WHERE r.user_id=? ORDER BY r.date DESC',
            (int(user_id),)
        ).fetchall()
    else:
        rows = db.execute(
            'SELECT r.*, u.username FROM reflections r JOIN users u ON u.id=r.user_id ORDER BY r.date DESC'
        ).fetchall()
    return jsonify([{
        'date': r['date'],
        'user_id': r['user_id'],
        'username': r['username'],
        'data': json.loads(r['data']),
        'updated_at': r['updated_at']
    } for r in rows])

# ── Main ──────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print('✦ 每日反思后端已启动 (含用户系统)')
    print(f'  主页面:    http://localhost:5001')
    print(f'  管理后台:  http://localhost:5001/admin')
    print(f'  API 就绪:  http://localhost:5001/api/ping')
    app.run(host='0.0.0.0', port=5001, debug=True)
