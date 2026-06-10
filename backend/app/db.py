"""Camada de dados com driver duplo — SQLite (dev/local) e Postgres (produção Vercel).

Por que driver duplo?
  O backend roda como Serverless Function na Vercel, onde o filesystem é
  efêmero (apenas /tmp é gravável e some entre cold starts). Para persistência
  durável em produção usa-se o Postgres gerenciado do Vercel Marketplace (Neon),
  detectado automaticamente pela env `POSTGRES_URL`. Sem ela, o backend cai em
  SQLite (arquivo local em dev; /tmp na Vercel), com seed automático no boot —
  suficiente para demonstrações.

A API exposta imita a do sqlite3 (`conn.execute(sql, params)`), com placeholders
`?` traduzidos para `%s` quando o destino é Postgres.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

POSTGRES_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
IS_PG = bool(POSTGRES_URL and POSTGRES_URL.startswith(("postgres://", "postgresql://")))

_DEFAULT_SQLITE = (
    Path("/tmp/cardio_ia.sqlite3")
    if os.getenv("VERCEL")
    else Path(__file__).resolve().parent / "data" / "cardio_ia.sqlite3"
)
SQLITE_PATH = Path(os.getenv("CARDIOIA_DB", str(_DEFAULT_SQLITE)))


def agora_iso() -> str:
    """Timestamp ISO-8601 UTC — gravado pela aplicação para manter o schema
    idêntico nos dois bancos (sem defaults específicos de dialeto)."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS pacientes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT    NOT NULL,
    idade           INTEGER NOT NULL,
    sexo            TEXT    NOT NULL DEFAULT 'O',
    documento       TEXT,
    telefone        TEXT,
    observacoes     TEXT,
    criado_em       TEXT    NOT NULL
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
    paciente_id     INTEGER,
    probabilidade   REAL    NOT NULL,
    classificacao   TEXT    NOT NULL,
    payload_json    TEXT    NOT NULL,
    criado_em       TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_mensagens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao_id       TEXT    NOT NULL,
    autor           TEXT    NOT NULL,
    conteudo        TEXT    NOT NULL,
    estado          TEXT,
    criado_em       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_sessao ON chat_mensagens(sessao_id);
CREATE TABLE IF NOT EXISTS chat_sessoes (
    sessao_id       TEXT PRIMARY KEY,
    estado_json     TEXT NOT NULL,
    atualizado_em   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leituras_iot (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id       TEXT    NOT NULL,
    bpm             INTEGER,
    temperatura_amb REAL,
    umidade         REAL,
    temperatura_pac REAL,
    status_edge     TEXT,
    alerta          INTEGER NOT NULL DEFAULT 0,
    avaliacao_json  TEXT,
    criado_em       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_iot_criado ON leituras_iot(criado_em);
"""

# Postgres: mesmas tabelas, dialetos de id ajustados
_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS pacientes (
    id              BIGSERIAL PRIMARY KEY,
    nome            TEXT    NOT NULL,
    idade           INTEGER NOT NULL,
    sexo            TEXT    NOT NULL DEFAULT 'O',
    documento       TEXT,
    telefone        TEXT,
    observacoes     TEXT,
    criado_em       TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS protocolos (
    id              BIGSERIAL PRIMARY KEY,
    codigo          TEXT    NOT NULL UNIQUE,
    titulo          TEXT    NOT NULL,
    descricao       TEXT    NOT NULL,
    severidade      TEXT    NOT NULL,
    gatilhos_json   TEXT    NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS predicoes (
    id              BIGSERIAL PRIMARY KEY,
    paciente_id     BIGINT,
    probabilidade   DOUBLE PRECISION NOT NULL,
    classificacao   TEXT    NOT NULL,
    payload_json    TEXT    NOT NULL,
    criado_em       TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_mensagens (
    id              BIGSERIAL PRIMARY KEY,
    sessao_id       TEXT    NOT NULL,
    autor           TEXT    NOT NULL,
    conteudo        TEXT    NOT NULL,
    estado          TEXT,
    criado_em       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_sessao ON chat_mensagens(sessao_id);
CREATE TABLE IF NOT EXISTS chat_sessoes (
    sessao_id       TEXT PRIMARY KEY,
    estado_json     TEXT NOT NULL,
    atualizado_em   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leituras_iot (
    id              BIGSERIAL PRIMARY KEY,
    device_id       TEXT    NOT NULL,
    bpm             INTEGER,
    temperatura_amb DOUBLE PRECISION,
    umidade         DOUBLE PRECISION,
    temperatura_pac DOUBLE PRECISION,
    status_edge     TEXT,
    alerta          INTEGER NOT NULL DEFAULT 0,
    avaliacao_json  TEXT,
    criado_em       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_iot_criado ON leituras_iot(criado_em);
"""


class Conn:
    """Wrapper fino que uniformiza sqlite3 e psycopg2 sob a mesma interface."""

    def __init__(self, raw: Any, is_pg: bool) -> None:
        self.raw = raw
        self.is_pg = is_pg

    def execute(self, sql: str, params: tuple = ()) -> Any:
        if self.is_pg:
            sql = sql.replace("?", "%s")
            cur = self.raw.cursor()
            cur.execute(sql, params)
            return cur
        return self.raw.execute(sql, params)

    def executescript(self, script: str) -> None:
        if self.is_pg:
            cur = self.raw.cursor()
            for stmt in script.split(";"):
                if stmt.strip():
                    cur.execute(stmt)
        else:
            self.raw.executescript(script)

    def insert_returning_id(self, sql: str, params: tuple = ()) -> int:
        """INSERT devolvendo o id gerado, abstraindo lastrowid × RETURNING."""
        if self.is_pg:
            cur = self.execute(sql + " RETURNING id", params)
            return int(cur.fetchone()["id"])
        cur = self.execute(sql, params)
        return int(cur.lastrowid)

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        self.raw.close()


def _connect() -> Conn:
    if IS_PG:
        import psycopg2
        import psycopg2.extras

        raw = psycopg2.connect(POSTGRES_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return Conn(raw, is_pg=True)

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(SQLITE_PATH)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return Conn(raw, is_pg=False)


@contextmanager
def get_conn() -> Iterator[Conn]:
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
        conn.executescript(_SCHEMA_PG if IS_PG else _SCHEMA_SQLITE)


def row_to_dict(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for k in ("criado_em", "atualizado_em"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = datetime.fromisoformat(d[k])
            except ValueError:
                pass
    return d


def backend_info() -> dict:
    return {
        "driver": "postgres" if IS_PG else "sqlite",
        "persistente": IS_PG or not os.getenv("VERCEL"),
        "caminho": "(gerenciado)" if IS_PG else str(SQLITE_PATH),
    }
