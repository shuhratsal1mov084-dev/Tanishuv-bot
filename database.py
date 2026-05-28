import sqlite3
from typing import Optional, List, Dict


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                city TEXT NOT NULL,
                photo_id TEXT,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    # ---- USERS ----

    def add_user(self, user_id, name, age, gender, city, photo_id=None, username=None):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO users (user_id, name, age, gender, city, photo_id, username)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, age, gender, city, photo_id, username))
        conn.commit()
        conn.close()

    def get_user(self, user_id: int) -> Optional[Dict]:
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_user(self, user_id: int):
        conn = self._connect()
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    def get_users_by_gender(self, gender: str, exclude_id: int) -> List[Dict]:
        conn = self._connect()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE gender = ? AND user_id != ?",
            (gender, exclude_id)
        )
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_user_ids(self) -> List[int]:
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        rows = c.fetchall()
        conn.close()
        return [r["user_id"] for r in rows]

    def get_users_count(self) -> int:
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM users")
        row = c.fetchone()
        conn.close()
        return row["cnt"] if row else 0

    def get_count_by_gender(self, gender: str) -> int:
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM users WHERE gender = ?", (gender,))
        row = c.fetchone()
        conn.close()
        return row["cnt"] if row else 0

    # ---- CHANNELS ----

    def add_channel(self, username: str):
        conn = self._connect()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO channels (username) VALUES (?)", (username,))
        conn.commit()
        conn.close()

    def remove_channel(self, username: str):
        conn = self._connect()
        c = conn.cursor()
        c.execute("DELETE FROM channels WHERE username = ?", (username,))
        conn.commit()
        conn.close()

    def get_channels(self) -> List[Dict]:
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM channels")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
