import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'agent_memory.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Table for conversational history (legacy)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            content TEXT
        )
    ''')
    # Table for equipment state memory
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment_state (
            equipment_name TEXT PRIMARY KEY,
            last_checked DATETIME,
            last_status TEXT,
            notes TEXT
        )
    ''')
    # Table for multi-session chat & tasks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            session_type TEXT DEFAULT 'chat',
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata_json TEXT
        )
    ''')
    # Table for messages per session
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            content TEXT,
            summary_for_speech TEXT,
            payload_json TEXT,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
        )
    ''')
    conn.commit()

    # Seed demo sessions if empty
    cursor.execute('SELECT COUNT(*) FROM chat_sessions')
    if cursor.fetchone()[0] == 0:
        seed_sessions = [
            ("session-1", "Chat dan voice assistant PPLE", "chat", "active"),
            ("session-2", "Untitled", "chat", "active"),
            ("session-3", "Untitled", "chat", "active"),
            ("session-4", "Mempercepat evaluasi vibrasi pompa CWP", "chat", "active"),
            ("session-5", "Analisis oil sampling dan keausan BFP 1A", "chat", "active"),
            ("session-6", "Tugas terjadwal baru", "task", "active"),
            ("session-7", "Skill building dengan contoh", "task", "pending_review"),
            ("session-8", "Inspeksi hotspot termografi busbar", "chat", "active"),
        ]
        cursor.executemany(
            'INSERT INTO chat_sessions (session_id, title, session_type, status) VALUES (?, ?, ?, ?)',
            seed_sessions,
        )
        conn.commit()

    conn.close()

def save_chat(role, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO conversation_history (role, content) VALUES (?, ?)', (role, content))
    conn.commit()
    conn.close()

def get_recent_chat_history(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT role, content FROM conversation_history ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows[::-1]  # Reverse to chronological order

def create_chat_session(title=None, session_type="chat", status="active", metadata=None) -> str:
    import uuid
    import json
    session_id = f"ses-{uuid.uuid4().hex[:8]}"
    clean_title = title.strip() if title and title.strip() else "Untitled"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO chat_sessions (session_id, title, session_type, status, metadata_json)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (session_id, clean_title, session_type, status, json.dumps(metadata or {})),
    )
    conn.commit()
    conn.close()
    return session_id

def list_chat_sessions(session_type=None, limit=50) -> list[dict]:
    import json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if session_type:
        cursor.execute(
            '''
            SELECT s.session_id, s.title, s.session_type, s.status, s.created_at, s.updated_at,
                   COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN session_messages m ON s.session_id = m.session_id
            WHERE s.session_type = ?
            GROUP BY s.session_id
            ORDER BY s.updated_at DESC LIMIT ?
            ''',
            (session_type, limit),
        )
    else:
        cursor.execute(
            '''
            SELECT s.session_id, s.title, s.session_type, s.status, s.created_at, s.updated_at,
                   COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN session_messages m ON s.session_id = m.session_id
            GROUP BY s.session_id
            ORDER BY s.updated_at DESC LIMIT ?
            ''',
            (limit,),
        )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "session_id": r[0],
            "title": r[1] or "Untitled",
            "session_type": r[2] or "chat",
            "status": r[3] or "active",
            "created_at": r[4],
            "updated_at": r[5],
            "message_count": r[6],
        }
        for r in rows
    ]

def get_chat_session_messages(session_id: str) -> list[dict]:
    import json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, timestamp, role, content, summary_for_speech, payload_json
        FROM session_messages
        WHERE session_id = ?
        ORDER BY id ASC
        ''',
        (session_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        payload = {}
        if r[5]:
            try:
                payload = json.loads(r[5])
            except Exception:
                payload = {}
        msg = {
            "id": f"msg-{r[0]}",
            "timestamp": r[1],
            "role": r[2],
            "text": r[3],
            "summary_for_speech": r[4],
            **payload,
        }
        results.append(msg)
    return results

def save_session_message(session_id: str, role: str, content: str, summary_for_speech=None, payload=None) -> None:
    import json
    now = datetime.datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO session_messages (session_id, timestamp, role, content, summary_for_speech, payload_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (session_id, now, role, content, summary_for_speech, json.dumps(payload or {})),
    )
    # Update session updated_at
    cursor.execute(
        'UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?',
        (now, session_id),
    )
    conn.commit()
    conn.close()

def update_session_title(session_id: str, title: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE chat_sessions SET title = ? WHERE session_id = ?', (title.strip(), session_id))
    conn.commit()
    conn.close()

def delete_chat_session(session_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM session_messages WHERE session_id = ?', (session_id,))
    cursor.execute('DELETE FROM chat_sessions WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()
    return True

def update_equipment_state(equipment_name, status, notes=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO equipment_state (equipment_name, last_checked, last_status, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(equipment_name) DO UPDATE SET
            last_checked=excluded.last_checked,
            last_status=excluded.last_status,
            notes=excluded.notes
    ''', (equipment_name, now, status, notes))
    conn.commit()
    conn.close()

def get_equipment_state(equipment_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT last_checked, last_status, notes FROM equipment_state WHERE equipment_name = ?', (equipment_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"last_checked": row[0], "status": row[1], "notes": row[2]}
    return None

# Initialize on load
init_db()
