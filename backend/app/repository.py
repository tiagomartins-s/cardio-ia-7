"""Acesso a dados — pacientes, protocolos, predições, chat e leituras IoT.

Compatível com SQLite e Postgres via camada `db.Conn` (placeholders `?`,
contagens com alias, ids via `insert_returning_id`).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .db import agora_iso, get_conn, row_to_dict
from .live_cache import mesclar_leituras, mesclar_predicoes, registrar_leitura, registrar_predicao
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
        novo_id = conn.insert_returning_id(
            """INSERT INTO pacientes (nome, idade, sexo, documento, telefone, observacoes, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                p["nome"],
                p["idade"],
                p.get("sexo", "O"),
                p.get("documento"),
                p.get("telefone"),
                p.get("observacoes"),
                agora_iso(),
            ),
        )
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
        n = conn.execute("SELECT COUNT(*) AS n FROM protocolos").fetchone()["n"]
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

def _predicao_out(row: Any) -> dict:
    d = row_to_dict(row)
    d["payload"] = json.loads(d.pop("payload_json"))
    return d


def salvar_predicao(paciente_id: int | None, payload: dict) -> int:
    with get_conn() as conn:
        novo_id = conn.insert_returning_id(
            """INSERT INTO predicoes (paciente_id, probabilidade, classificacao, payload_json, criado_em)
               VALUES (?, ?, ?, ?, ?)""",
            (
                paciente_id,
                payload["probabilidade"],
                payload["classificacao"],
                json.dumps(payload, ensure_ascii=False, default=_json_default),
                agora_iso(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM predicoes WHERE id = ?", (novo_id,)
        ).fetchone()
    out = _predicao_out(row)
    registrar_predicao(out)
    return novo_id


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
    out = [_predicao_out(r) for r in rows]
    if paciente_id is None:
        return mesclar_predicoes(out, limite)
    return out


# ---------- chat (mensagens + estado de sessão persistido) ----------

def salvar_chat(sessao_id: str, autor: str, conteudo: str, estado: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO chat_mensagens (sessao_id, autor, conteudo, estado, criado_em)
               VALUES (?, ?, ?, ?, ?)""",
            (sessao_id, autor, conteudo, estado, agora_iso()),
        )


def historico_chat(sessao_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_mensagens WHERE sessao_id = ? ORDER BY id ASC",
            (sessao_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def carregar_sessao_chat(sessao_id: str) -> dict | None:
    """Estado da sessão persistido em banco — obrigatório em serverless, onde
    cada requisição pode cair em uma instância diferente (sem memória comum)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT estado_json FROM chat_sessoes WHERE sessao_id = ?", (sessao_id,)
        ).fetchone()
    if row is None:
        return None
    return json.loads(dict(row)["estado_json"])


def salvar_sessao_chat(sessao_id: str, estado: dict) -> None:
    payload = json.dumps(estado, ensure_ascii=False)
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE chat_sessoes SET estado_json = ?, atualizado_em = ? WHERE sessao_id = ?",
            (payload, agora_iso(), sessao_id),
        )
        if cur.rowcount == 0:
            conn.execute(
                "INSERT INTO chat_sessoes (sessao_id, estado_json, atualizado_em) VALUES (?, ?, ?)",
                (sessao_id, payload, agora_iso()),
            )


# ---------- leituras IoT ----------

def salvar_leitura_iot(leitura: dict, avaliacao: dict | None) -> dict:
    with get_conn() as conn:
        novo_id = conn.insert_returning_id(
            """INSERT INTO leituras_iot
               (device_id, bpm, temperatura_amb, umidade, temperatura_pac,
                status_edge, alerta, avaliacao_json, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                leitura["device_id"],
                leitura.get("bpm"),
                leitura.get("temperatura_amb"),
                leitura.get("umidade"),
                leitura.get("temperatura_pac"),
                leitura.get("status_edge"),
                1 if (avaliacao or {}).get("alerta") else 0,
                json.dumps(avaliacao, ensure_ascii=False, default=_json_default)
                if avaliacao
                else None,
                agora_iso(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM leituras_iot WHERE id = ?", (novo_id,)
        ).fetchone()
    out = _leitura_out(row)
    registrar_leitura(out)
    return out


def listar_leituras_iot(limite: int = 50, device_id: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if device_id:
            rows = conn.execute(
                "SELECT * FROM leituras_iot WHERE device_id = ? ORDER BY id DESC LIMIT ?",
                (device_id, limite),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM leituras_iot ORDER BY id DESC LIMIT ?", (limite,)
            ).fetchall()
    out = [_leitura_out(r) for r in rows]
    if device_id is None:
        return mesclar_leituras(out, limite)
    return out


def _leitura_out(row: Any) -> dict:
    d = row_to_dict(row)
    raw = d.pop("avaliacao_json", None)
    d["avaliacao"] = json.loads(raw) if raw else None
    d["alerta"] = bool(d.get("alerta"))
    return d


# ---------- helpers ----------

def _json_default(o: Any):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"Tipo não serializável: {type(o)}")
