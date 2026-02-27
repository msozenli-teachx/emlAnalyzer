"""Database models and utilities for EML analyzer."""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import hashlib


class Database:
    """SQLite database for storing email metadata."""

    def __init__(self, db_path: str = "emails.db"):
        """Initialize database connection."""
        self.db_path = Path(db_path)
        self.connection = None
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        cursor = self.connection.cursor()

        # Create emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                from_addr TEXT NOT NULL,
                to_addr TEXT NOT NULL,
                date TEXT NOT NULL,
                subject TEXT,
                in_reply_to TEXT,
                hash TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_id ON emails(message_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_from_addr ON emails(from_addr)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hash ON emails(hash)
        """)

        self.connection.commit()

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

    def _compute_hash(self, from_addr: str, to_addr: str, subject: str, date: str) -> str:
        """Compute a hash for duplicate detection."""
        content = f"{from_addr}|{to_addr}|{subject}|{date}"
        return hashlib.sha256(content.encode()).hexdigest()

    def email_exists_by_hash(self, hash_value: str) -> bool:
        """Check if email exists by hash."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM emails WHERE hash = ?", (hash_value,))
        return cursor.fetchone() is not None

    def email_exists_by_message_id(self, message_id: Optional[str]) -> bool:
        """Check if email exists by Message-ID."""
        if not message_id:
            return False
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM emails WHERE message_id = ?", (message_id,))
        return cursor.fetchone() is not None

    def insert_email(
        self,
        message_id: Optional[str],
        from_addr: str,
        to_addr: str,
        date: str,
        subject: Optional[str],
        in_reply_to: Optional[str],
    ) -> bool:
        """
        Insert an email into the database.

        Returns True if inserted, False if duplicate.
        """
        hash_value = self._compute_hash(from_addr, to_addr, subject or "", date)

        # Check for duplicates
        if self.email_exists_by_hash(hash_value):
            return False

        if message_id and self.email_exists_by_message_id(message_id):
            return False

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO emails
                (message_id, from_addr, to_addr, date, subject, in_reply_to, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, from_addr, to_addr, date, subject, in_reply_to, hash_value),
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_total_messages(self) -> int:
        """Get total number of messages."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM emails")
        return cursor.fetchone()["count"]

    def get_unique_senders(self) -> int:
        """Get number of unique senders."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(DISTINCT from_addr) as count FROM emails")
        return cursor.fetchone()["count"]

    def get_date_range(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the date range of emails."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT MIN(date) as min_date, MAX(date) as max_date FROM emails")
        result = cursor.fetchone()
        return (result["min_date"], result["max_date"])

    def get_senders_list(self) -> List[str]:
        """Get list of unique senders."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT DISTINCT from_addr FROM emails ORDER BY from_addr")
        return [row["from_addr"] for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        """Get comprehensive statistics."""
        total = self.get_total_messages()
        unique_senders = self.get_unique_senders()
        min_date, max_date = self.get_date_range()

        return {
            "total_messages": total,
            "unique_senders": unique_senders,
            "date_range": {
                "start": min_date,
                "end": max_date,
            },
        }
