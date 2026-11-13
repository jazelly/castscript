"""SQLite store for the web app: settings and render history. Scripts and voices stay plain files."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS renders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  script TEXT NOT NULL,
  engine TEXT NOT NULL,
  language TEXT NOT NULL,
  status TEXT NOT NULL,          -- running | done | failed | stopped | interrupted
  created_at REAL NOT NULL,
  finished_at REAL,
  audio_seconds REAL,
  log TEXT NOT NULL DEFAULT ''
);
"""
DEFAULT_SETTINGS = {"envs": "", "breeze_dir": "", "breeze_checkpoint": "", "language": "zh", "locale": ""}
COLUMNS = ("id", "script", "engine", "language", "status", "created_at", "finished_at", "audio_seconds")


class Store:
    def __init__(self, path: Path):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.executescript(SCHEMA)
        # A render whose server died with it can never finish.
        self._db.execute("UPDATE renders SET status = 'interrupted' WHERE status = 'running'")
        self._db.commit()

    def _run(self, sql: str, args: tuple = ()) -> list[tuple]:
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
            self._db.commit()
            return rows

    def settings(self) -> dict[str, str]:
        return DEFAULT_SETTINGS | dict(self._run("SELECT key, value FROM settings"))

    def save_settings(self, values: dict[str, str]) -> dict[str, str]:
        for key, value in values.items():
            if key not in DEFAULT_SETTINGS:
                raise ValueError(f"unknown setting: {key}")
            self._run("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                      (key, str(value)))
        return self.settings()

    def add_render(self, script: str, engine: str, language: str) -> int:
        with self._lock:
            cur = self._db.execute("INSERT INTO renders (script, engine, language, status, created_at) VALUES (?, ?, ?, 'running', ?)",
                                   (script, engine, language, time.time()))
            self._db.commit()
            return cur.lastrowid

    def finish_render(self, render_id: int, status: str, log: str, audio_seconds: float | None) -> None:
        self._run("UPDATE renders SET status = ?, log = ?, audio_seconds = ?, finished_at = ? WHERE id = ?",
                  (status, log, audio_seconds, time.time(), render_id))

    def renders(self, script: str | None = None) -> list[dict]:
        sql = f"SELECT {', '.join(COLUMNS)} FROM renders"
        rows = self._run(sql + " WHERE script = ? ORDER BY id DESC", (script,)) if script else self._run(sql + " ORDER BY id DESC")
        return [dict(zip(COLUMNS, row)) for row in rows]

    def render(self, render_id: int) -> dict:
        rows = self._run(f"SELECT {', '.join(COLUMNS)}, log FROM renders WHERE id = ?", (render_id,))
        if not rows:
            raise KeyError(f"no render {render_id}")
        return dict(zip(COLUMNS + ("log",), rows[0]))

    def delete_render(self, render_id: int) -> None:
        self._run("DELETE FROM renders WHERE id = ?", (render_id,))
