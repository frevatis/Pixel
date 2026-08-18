from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
import random

app = Flask(__name__, static_folder='.')
CORS(app)

DB_NAME = 'pixel.db'

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=10)  # ← timeout=10 решает проблему блокировки
    conn.row_factory = sqlite3.Row
    return conn

def close_db(conn):
    if conn:
        conn.close()

def init_db():
    conn = get_db()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                bonuses INTEGER DEFAULT 100,
                last_bonus_claim INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                device_id TEXT NOT NULL,
                pc INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                duration INTEGER NOT NULL,
                comment TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS verification_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                action TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                action TEXT NOT NULL,
                details TEXT,
                ip TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print('✅ База данных готова')
    except Exception as e:
        print('❌ Ошибка БД:', e)
    finally:
        close_db(conn)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_name(name):
    return len(name.strip()) >= 2 and len(name.strip()) <= 30

def validate_password(password):
    return len(password) >= 6

def add_hours(time_str, hours):
    h, m = map(int, time_str.split(':'))
    total = h + hours
    nh = total % 24
    return f"{str(nh).zfill(2)}:{str(m).zfill(2)}"

def log_action(email, action, details=None, ip=None):
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO logs (email, action, details, ip) VALUES (?, ?, ?, ?)',
            (email, action, details, ip)
        )
        conn.commit()
    except Exception as e:
        print('Log error:', e)
    finally:
        close_db(conn)
@app.route('/api/admin/bookings', methods=['GET'])
def admin_bookings():
    conn = get_db()
    try:
        bookings = conn.execute('SELECT * FROM bookings ORDER BY created_at DESC').fetchall()
        result = []
        for b in bookings:
            result.append({
                'id': b['id'],
                'user_email': b['user_email'],
                'device_id': b['device_id'],
                'pc': b['pc'],
                'date': b['date'],
                'time': b['time'],
                'duration': b['duration'],
                'comment': b['comment'],
                'status': b['status'],
                'created_at': b['created_at']
            })
        return jsonify({'success': True, 'bookings': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        close_db(conn)
# ============================================================
# ОТДАЧА ФАЙЛОВ
# ============================================================
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# ============================================================
# API
# ============================================================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()
    password = data.get('password', '')
    
    if not validate_email(email):
        return jsonify({'success': False, 'message': 'Неверный формат email'})
    if not validate_name(name):
        return jsonify({'success': False, 'message': 'Имя от 2 до 30 символов'})
    if not validate_password(password):
        return jsonify({'success': False, 'message': 'Пароль минимум 6 символов'})
    
    conn = get_db()
    try:
        existing = conn.execute('SELECT * FROM users WHERE email = ? OR name = ?', (email, name)).fetchone()
        if existing:
            if existing['email'] == email:
                return jsonify({'success': False, 'message': 'Email уже используется'})
            if existing['name'] == name:
                return jsonify({'success': False, 'message': 'Имя уже занято'})
        
        hashed = hash_password(password)
        conn.execute(
            'INSERT INTO users (email, name, password, bonuses, last_bonus_claim) VALUES (?, ?, ?, 100, ?)',
            (email, name, hashed, int(datetime.now().timestamp()))
        )
        conn.commit()
        log_action(email, 'register', f'Пользователь {name} зарегистрировался')
        return jsonify({'success': True, 'message': 'Регистрация успешна!'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Заполните все поля'})
    
    conn = get_db()
    try:
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND password = ?',
            (email, hash_password(password))
        ).fetchone()
        
        if user:
            log_action(email, 'login', 'Успешный вход')
            return jsonify({
                'success': True,
                'user': {
                    'name': user['name'],
                    'email': user['email'],
                    'bonuses': user['bonuses']
                }
            })
        
        log_action(email, 'login_failed', 'Неверный пароль')
        return jsonify({'success': False, 'message': 'Неверный email или пароль'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)

@app.route('/api/send-code', methods=['POST'])
def send_code():
    data = request.json
    email = data.get('email', '').strip().lower()
    action = data.get('action', 'login')
    
    if not validate_email(email):
        return jsonify({'success': False, 'message': 'Неверный формат email'})
    
    code = str(random.randint(100000, 999999))
    expires_at = datetime.now() + timedelta(minutes=5)
    
    conn = get_db()
    try:
        conn.execute('DELETE FROM verification_codes WHERE email = ? AND used = 0', (email,))
        conn.execute(
            'INSERT INTO verification_codes (email, code, action, expires_at) VALUES (?, ?, ?, ?)',
            (email, code, action, expires_at.isoformat())
        )
        conn.commit()
        log_action(email, 'code_sent', f'Код {code} отправлен')
        
        return jsonify({
            'success': True,
            'message': 'Код отправлен на почту',
            'code': code
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)

@app.route('/api/verify-code', methods=['POST'])
def verify_code():
    data = request.json
    email = data.get('email', '').strip().lower()
    code = data.get('code', '')
    
    if not code or len(code) != 6:
        return jsonify({'success': False, 'message': 'Введите 6-значный код'})
    
    conn = get_db()
    try:
        record = conn.execute(
            'SELECT * FROM verification_codes WHERE email = ? AND code = ? AND used = 0 AND expires_at > ?',
            (email, code, datetime.now().isoformat())
        ).fetchone()
        
        if record:
            conn.execute('UPDATE verification_codes SET used = 1 WHERE id = ?', (record['id'],))
            conn.commit()
            log_action(email, 'code_verified', 'Код подтверждён')
            return jsonify({'success': True, 'message': 'Код подтверждён'})
        
        log_action(email, 'code_failed', 'Неверный код')
        return jsonify({'success': False, 'message': 'Неверный или просроченный код'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)
@app.route('/api/bookings', methods=['POST'])
def create_booking():
    data = request.json
    print('📥 Получены данные:', data)  # ← ОТЛАДКА
    
    user_email = data.get('user_email', '').strip().lower()
    device_id = data.get('device_id', '')
    pc = data.get('pc')
    date = data.get('date')
    time = data.get('time')
    duration = data.get('duration', 2)
    comment = data.get('comment', '')
    
    if not pc:
        return jsonify({'success': False, 'message': 'Не выбран компьютер'})
    
    conn = get_db()
    try:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (user_email,)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'Пользователь не найден'})
        
        # Проверка занятости
        existing = conn.execute('''
            SELECT * FROM bookings WHERE pc = ? AND date = ? AND status = 'active'
        ''', (pc, date)).fetchall()
        
        for b in existing:
            b_start = b['time']
            b_end = add_hours(b['time'], b['duration'])
            new_start = time
            new_end = add_hours(time, duration)
            if new_start < b_end and new_end > b_start:
                return jsonify({'success': False, 'message': 'ПК уже занят на это время'})
        
        # Создание брони
        conn.execute('''
            INSERT INTO bookings (user_email, device_id, pc, date, time, duration, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_email, device_id, pc, date, time, duration, comment))
        
        # Бонусы
        last_bonus = user['last_bonus_claim']
        now = int(datetime.now().timestamp())
        bonus_added = False
        if now - last_bonus > 24 * 60 * 60:
            conn.execute(
                'UPDATE users SET bonuses = bonuses + 10, last_bonus_claim = ? WHERE email = ?',
                (now, user_email)
            )
            bonus_added = True
        
        conn.commit()
        log_action(user_email, 'booking', f'ПК №{pc} на {date} {time}-{add_hours(time, duration)}')
        
        # Проверяем, что бронь сохранилась
        check = conn.execute('SELECT * FROM bookings WHERE user_email = ? AND device_id = ? AND status = "active"', 
                            (user_email, device_id)).fetchall()
        print('📦 Бронь в БД:', [dict(b) for b in check])  # ← ОТЛАДКА
        
        return jsonify({
            'success': True,
            'message': 'Бронирование создано!',
            'bonus_added': bonus_added
        })
    except Exception as e:
        print('❌ Ошибка:', e)
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)

@app.route('/api/check-email', methods=['POST'])
def check_email():
    data = request.json
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()
    
    if not validate_email(email):
        return jsonify({'success': False, 'message': 'Неверный формат email'})
    
    conn = get_db()
    try:
        # Проверяем email в таблице users
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user:
            return jsonify({'success': False, 'message': 'Этот email уже используется'})
        
        # Проверяем имя
        if name:
            name_exists = conn.execute('SELECT * FROM users WHERE name = ?', (name,)).fetchone()
            if name_exists:
                return jsonify({'success': False, 'message': 'Это имя уже занято'})
        
        return jsonify({'success': True, 'message': 'Можно регистрироваться'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)

@app.route('/api/check-login', methods=['POST'])
def check_login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Заполните все поля'})
    
    conn = get_db()
    try:
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND password = ?',
            (email, hash_password(password))
        ).fetchone()
        
        if user:
            return jsonify({'success': True, 'message': 'Пароль верный'})
        else:
            return jsonify({'success': False, 'message': 'Неверный email или пароль'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)


@app.route('/api/bookings/<device_id>', methods=['GET'])
def get_bookings(device_id):
    conn = get_db()
    try:
        bookings = conn.execute('''
            SELECT b.*, u.name as user_name 
            FROM bookings b
            LEFT JOIN users u ON b.user_email = u.email
            WHERE b.device_id = ? AND b.status = 'active' 
            ORDER BY b.created_at DESC
        ''', (device_id,)).fetchall()
        
        result = []
        for b in bookings:
            result.append({
                'id': b['id'],
                'user_email': b['user_email'],
                'user_name': b['user_name'],
                'deviceId': b['device_id'],
                'pc': b['pc'],
                'date': b['date'],
                'time': b['time'],
                'duration': b['duration'],
                'comment': b['comment'],
                'status': b['status'],
                'created_at': b['created_at']
            })
        
        print('📦 Возвращаем брони:', result)  # ← ОТЛАДКА
        return jsonify({'success': True, 'bookings': result})
    except Exception as e:
        print('❌ Ошибка:', e)
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)
def get_all_bookings():
    conn = get_db()
    try:
        bookings = conn.execute('''
            SELECT b.*, u.name as user_name 
            FROM bookings b
            LEFT JOIN users u ON b.user_email = u.email
            WHERE b.status = 'active'
            ORDER BY b.created_at DESC
        ''').fetchall()
        
        result = []
        for b in bookings:
            result.append({
                'id': b['id'],
                'user_email': b['user_email'],
                'user_name': b['user_name'],
                'device_id': b['device_id'],
                'pc': b['pc'],
                'date': b['date'],
                'time': b['time'],
                'duration': b['duration'],
                'comment': b['comment'],
                'status': b['status'],
                'created_at': b['created_at']
            })
        return jsonify({'success': True, 'bookings': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        close_db(conn)
        
@app.route('/api/bookings/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    conn = get_db()
    try:
        booking = conn.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
        if not booking:
            return jsonify({'success': False, 'message': 'Бронь не найдена'})
        
        conn.execute('UPDATE bookings SET status = "cancelled" WHERE id = ?', (booking_id,))
        conn.commit()
        log_action(booking['user_email'], 'booking_cancel', f'Отмена ПК №{booking["pc"]}')
        
        return jsonify({'success': True, 'message': 'Бронь отменена'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)

@app.route('/api/delete-account', methods=['POST'])
def delete_account():
    data = request.json
    email = data.get('email', '').strip().lower()
    
    conn = get_db()
    try:
        # Удаляем всё
        conn.execute('DELETE FROM bookings WHERE user_email = ?', (email,))
        conn.execute('DELETE FROM verification_codes WHERE email = ?', (email,))
        conn.execute('DELETE FROM logs WHERE email = ?', (email,))
        conn.execute('DELETE FROM users WHERE email = ?', (email,))
        conn.commit()
        
        log_action(email, 'delete_account', 'Аккаунт удалён')
        return jsonify({'success': True, 'message': 'Аккаунт удалён'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)

        

@app.route('/api/admin/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    try:
        users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()
        bookings = conn.execute('SELECT COUNT(*) as count FROM bookings WHERE status = "active"').fetchone()
        logs = conn.execute('SELECT COUNT(*) as count FROM logs').fetchone()
        return jsonify({
            'users': users['count'],
            'active_bookings': bookings['count'],
            'total_logs': logs['count']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ошибка: ' + str(e)})
    finally:
        close_db(conn)

# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == '__main__':
    init_db()
    print('''
    ╔══════════════════════════════════════════════════════════╗
    ║  🚀 Сервер Пиксель запущен!                            ║
    ║  📍 http://127.0.0.1:5000                             ║
    ║  📁 БД: pixel.db                                       ║
    ╚══════════════════════════════════════════════════════════╝
    ''')
    app.run(debug=True, port=5000)