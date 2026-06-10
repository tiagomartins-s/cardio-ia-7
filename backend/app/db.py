"""Camada SQLite — minimalista, sem ORM, com migrações idempotentes."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(__file__).resolve().parent / "data" / "cardio_ia.sqlite3"


SCHEMA = """
CREATE TABLE IF NOT EXISTS pacientes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT    NOT NULL,
    idade           INTEGER NOT NULL,
    sexo            TEXT    NOT NULL DEFAULT 'O',
    documento       TEXT,
    telefone        TEXT,
    observacoes     TEXT,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS protocolos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT    NOT NULL UNIQUE,
    titulo          TEXT    NOT NULL,
    descricao       TEXT    NOT NULL,
    severidade      TEXT    NOT NULL,
    gatilhos_json   TEXT    NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS predicoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id     INTEGER REFERENCES pacientes(id) ON DELETE SET NULL,
    probabilidade   REAL    NOT NULL,
    classificacao   TEXT    NOT NULL,
    payload_json    TEXT    NOT NULL,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_mensagens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao_id       TEXT    NOT NULL,
    autor           TEXT    NOT NULL,
    conteudo        TEXT    NOT NULL,
    estado          TEXT,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chat_sessao ON chat_mensagens(sessao_id);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    # converte campos ISO-8601 conhecidos para datetime
    for k in ("criado_em",):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = datetime.fromisoformat(d[k])
            except ValueError:
                pass
    return d
