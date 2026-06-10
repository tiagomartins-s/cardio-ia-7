"""Acesso a dados — funções para pacientes, protocolos, predições e chat."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable

from .db import get_conn, row_to_dict
from .protocols_seed import PROTOCOLOS_SEED


# ---------- pacientes ----------

def listar_pacientes() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM pacientes ORDER BY criado_em DESC"
        ).fetchall()
    return [row_to_dict(r) for r in rows]


def obter_paciente(paciente_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pacientes WHERE id = ?", (paciente_id,)
        ).fetchone()
    return row_to_dict(row)


def criar_paciente(p: dict) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO pacientes (nome, idade, sexo, documento, telefone, observacoes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                p["nome"],
                p["idade"],
                p.get("sexo", "O"),
                p.get("documento"),
                p.get("telefone"),
                p.get("observacoes"),
            ),
        )
        novo_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM pacientes WHERE id = ?", (novo_id,)
        ).fetchone()
    return row_to_dict(row)


def remover_paciente(paciente_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM pacientes WHERE id = ?", (paciente_id,))
    return cur.rowcount > 0


# ---------- protocolos ----------

def seed_protocolos_se_vazio() -> int:
    """Insere os protocolos seed apenas se a tabela estiver vazia."""
    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM protocolos").fetchone()[0]
        if n > 0:
            return 0
        for p in PROTOCOLOS_SEED:
            conn.execute(
                """INSERT INTO protocolos (codigo, titulo, descricao, severidade, gatilhos_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    p["codigo"],
                    p["titulo"],
                    p["descricao"],
                    p["severidade"],
                    json.dumps(p["gatilhos"], ensure_ascii=False),
                ),
            )
    return len(PROTOCOLOS_SEED)


def listar_protocolos() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM protocolos ORDER BY "
            "CASE severidade "
            "  WHEN 'CRITICO' THEN 0 WHEN 'ALTO' THEN 1 "
            "  WHEN 'MODERADO' THEN 2 WHEN 'BAIXO' THEN 3 ELSE 4 END, "
            "codigo"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["gatilhos"] = json.loads(d.pop("gatilhos_json"))
        out.append(d)
    return out


# ---------- predições ----------

def salvar_predicao(paciente_id: int | None, payload: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO predicoes (paciente_id, probabilidade, classificacao, payload_json)
               VALUES (?, ?, ?, ?)""",
            (
                paciente_id,
                payload["probabilidade"],
                payload["classificacao"],
                json.dumps(payload, ensure_ascii=False, default=_json_default),
            ),
        )
    return cur.lastrowid


def listar_predicoes(paciente_id: int | None = None, limite: int = 50) -> list[dict]:
    with get_conn() as conn:
        if paciente_id is None:
            rows = conn.execute(
                "SELECT * FROM predicoes ORDER BY criado_em DESC LIMIT ?",
                (limite,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM predicoes WHERE paciente_id = ? "
                "ORDER BY criado_em DESC LIMIT ?",
                (paciente_id, limite),
            ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d.pop("payload_json"))
        out.append(d)
    return out


# ---------- chat ----------

def salvar_chat(sessao_id: str, autor: str, conteudo: str, estado: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO chat_mensagens (sessao_id, autor, conteudo, estado)
               VALUES (?, ?, ?, ?)""",
            (sessao_id, autor, conteudo, estado),
        )


def historico_chat(sessao_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_mensagens WHERE sessao_id = ? ORDER BY id ASC",
            (sessao_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------- helpers ----------

def _json_default(o: Any):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Tipo não serializável: {type(o)}")
