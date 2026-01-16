"""
W19.3 Local Sync Store.
SQLite database for tracking snapshots and conflicts.
"""
import sqlite3
import os
import json
import logging
from typing import Optional, List
from .snapshot import Snapshot

logger = logging.getLogger("SyncStore")

class LocalSyncStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Snapshots Table
        c.execute('''CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id TEXT PRIMARY KEY,
            user_id TEXT,
            device_id TEXT,
            revision INTEGER,
            created_at REAL,
            encrypted_payload TEXT,
            is_applied INTEGER DEFAULT 0
        )''')
        
        # Meta Table
        c.execute('''CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        conn.commit()
        conn.close()

    def save_snapshot(self, snap: Snapshot, applied: bool = False):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO snapshots 
                     (snapshot_id, user_id, device_id, revision, created_at, encrypted_payload, is_applied)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (snap.snapshot_id, snap.user_id, snap.device_id, snap.revision, 
                   snap.created_at, snap.encrypted_payload, 1 if applied else 0))
        conn.commit()
        conn.close()
        
    def get_latest_snapshot(self) -> Optional[Snapshot]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM snapshots ORDER BY revision DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        
        if row:
            return Snapshot(
                snapshot_id=row['snapshot_id'],
                user_id=row['user_id'],
                device_id=row['device_id'],
                revision=row['revision'],
                created_at=row['created_at'],
                encrypted_payload=row['encrypted_payload']
            )
        return None

    def get_last_revision(self) -> int:
        snap = self.get_latest_snapshot()
        return snap.revision if snap else 0
