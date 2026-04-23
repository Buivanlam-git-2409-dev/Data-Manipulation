from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable

from .logger import get_logger


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class ArticleRecord:
    title: str
    abstract: str
    author: str
    url: str
    content_path: str
    image_path: str
    published_date: str


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                abstract TEXT,
                author TEXT,
                url TEXT UNIQUE,
                content_path TEXT,
                image_path TEXT,
                published_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    conn.close()


def upsert_article(db_path: str, record: ArticleRecord) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO articles (
                title, abstract, author, url, content_path, image_path, published_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                abstract=excluded.abstract,
                author=excluded.author,
                content_path=excluded.content_path,
                image_path=excluded.image_path,
                published_date=excluded.published_date
            """,
            (
                record.title,
                record.abstract,
                record.author,
                record.url,
                record.content_path,
                record.image_path,
                record.published_date,
            ),
        )
    conn.close()


def fetch_articles(
    db_path: str,
    keyword: str = "",
    field: str = "title",
) -> list[sqlite3.Row]:
    conn = get_connection(db_path)
    query = "SELECT * FROM articles"
    params: list[str] = []
    if keyword:
        query += f" WHERE {field} LIKE ?"
        params.append(f"%{keyword}%")
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def count_articles(db_path: str) -> int:
    conn = get_connection(db_path)
    row = conn.execute("SELECT COUNT(*) AS total FROM articles").fetchone()
    conn.close()
    return int(row["total"]) if row else 0


def top_authors(db_path: str, limit: int = 5) -> list[sqlite3.Row]:
    conn = get_connection(db_path)
    rows = conn.execute(
        """
        SELECT author, COUNT(*) AS total
        FROM articles
        WHERE author != ''
        GROUP BY author
        ORDER BY total DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return rows
