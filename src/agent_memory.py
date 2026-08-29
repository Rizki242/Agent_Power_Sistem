import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'agent_memory.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Table for conversational history
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
