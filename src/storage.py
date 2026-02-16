"""
Storage layer: RawStore (raw items) and InsightStore (analyzed insights).
Raw items: id, title, url, summary, source, fetched_at.
Insights: id, raw_item_id, data (JSON blob, structure flexible), analyzed_at.
"""
import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class RawItem:
    """Original entry from a source (e.g. arXiv)."""
    id: int | None
    title: str
    url: str
    summary: str
    source: str
    fetched_at: str  # ISO format


@dataclass
class Insight:
    """Analyzed insight linked to a raw item. data is arbitrary JSON from the analyzer."""
    id: int | None
    raw_item_id: int
    data: dict[str, Any]
    analyzed_at: str  # ISO format


def _ensure_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


# --- RawStore ---

RAW_TABLE = """
CREATE TABLE IF NOT EXISTS raw_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    summary TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE(source, url)
)
"""


class RawStore:
    """Persists raw entries from sources. Unique key: (source, url)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        _ensure_dir(db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(RAW_TABLE)

    def insert(self, title: str, url: str, summary: str, source: str) -> int | None:
        """Insert one raw item. Returns id or None if duplicate (source, url)."""
        fetched_at = datetime.utcnow().isoformat() + "Z"
        with sqlite3.connect(self.db_path) as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO raw_items (title, url, summary, source, fetched_at) VALUES (?, ?, ?, ?, ?)",
                    (title, url, summary, source, fetched_at),
                )
                conn.commit()
                return cur.lastrowid
            except sqlite3.IntegrityError:
                return None

    def insert_many(self, items: list[dict[str, Any]], source: str) -> int:
        """Insert multiple items; skip duplicates. Returns count inserted."""
        count = 0
        for it in items:
            if self.insert(
                it.get("title", ""),
                it.get("url", ""),
                it.get("summary", ""),
                source,
            ):
                count += 1
        return count

    def get_by_id(self, id: int) -> RawItem | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM raw_items WHERE id = ?", (id,)).fetchone()
            if row is None:
                return None
            return RawItem(
                id=row["id"],
                title=row["title"],
                url=row["url"],
                summary=row["summary"],
                source=row["source"],
                fetched_at=row["fetched_at"],
            )

    def list_since(self, since_iso: str | None = None, limit: int = 500) -> list[RawItem]:
        """List raw items, optionally since a given fetched_at (ISO)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if since_iso:
                rows = conn.execute(
                    "SELECT * FROM raw_items WHERE fetched_at >= ? ORDER BY fetched_at DESC LIMIT ?",
                    (since_iso, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM raw_items ORDER BY fetched_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [
                RawItem(
                    id=r["id"],
                    title=r["title"],
                    url=r["url"],
                    summary=r["summary"],
                    source=r["source"],
                    fetched_at=r["fetched_at"],
                )
                for r in rows
            ]


# --- InsightStore ---

INSIGHT_TABLE = """
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_item_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    analyzed_at TEXT NOT NULL,
    FOREIGN KEY (raw_item_id) REFERENCES raw_items(id)
)
"""


class InsightStore:
    """Persists analyzed insights. data is a flexible JSON object from the analyzer."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        _ensure_dir(db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(INSIGHT_TABLE)

    def insert(self, raw_item_id: int, data: dict[str, Any]) -> int:
        analyzed_at = datetime.utcnow().isoformat() + "Z"
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO insights (raw_item_id, data, analyzed_at) VALUES (?, ?, ?)",
                (raw_item_id, json.dumps(data, ensure_ascii=False), analyzed_at),
            )
            conn.commit()
            return cur.lastrowid

    def get_analyzed_raw_item_ids(self) -> set[int]:
        """Return set of raw_item_id that already have an insight (avoid re-analyzing)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT DISTINCT raw_item_id FROM insights").fetchall()
            return {r[0] for r in rows}

    def get_by_id(self, id: int) -> Insight | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM insights WHERE id = ?", (id,)).fetchone()
            if row is None:
                return None
            return Insight(
                id=row["id"],
                raw_item_id=row["raw_item_id"],
                data=json.loads(row["data"]),
                analyzed_at=row["analyzed_at"],
            )

    def list_since(self, since_iso: str | None = None, limit: int = 500) -> list[Insight]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if since_iso:
                rows = conn.execute(
                    "SELECT * FROM insights WHERE analyzed_at >= ? ORDER BY analyzed_at DESC LIMIT ?",
                    (since_iso, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM insights ORDER BY analyzed_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [
                Insight(
                    id=r["id"],
                    raw_item_id=r["raw_item_id"],
                    data=json.loads(r["data"]),
                    analyzed_at=r["analyzed_at"],
                )
                for r in rows
            ]
