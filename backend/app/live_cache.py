"""Cache em memória de leituras e predições recentes.

Na Vercel sem Postgres cada instância serverless usa SQLite em /tmp — os dados
gravados numa instância não aparecem noutra. Este cache não resolve isso entre
instâncias, mas evita perder dados na mesma instância entre leitura e escrita
e complementa o sticky state do frontend.
"""

from __future__ import annotations

from collections import deque
from threading import Lock

_LOCK = Lock()
_LEITURAS: deque[dict] = deque(maxlen=300)
_PREDICOES: deque[dict] = deque(maxlen=300)


def registrar_leitura(item: dict) -> None:
    with _LOCK:
        _LEITURAS.appendleft(item)


def registrar_predicao(item: dict) -> None:
    with _LOCK:
        _PREDICOES.appendleft(item)


def _mesclar(db_rows: list[dict], cache: deque[dict], limite: int) -> list[dict]:
    vistos: set[int] = set()
    merged: list[dict] = []
    for row in list(cache) + db_rows:
        rid = row.get("id")
        if rid is None or rid in vistos:
            continue
        vistos.add(rid)
        merged.append(row)
    merged.sort(key=lambda r: r.get("id", 0), reverse=True)
    return merged[:limite]


def mesclar_leituras(db_rows: list[dict], limite: int) -> list[dict]:
    with _LOCK:
        return _mesclar(db_rows, _LEITURAS, limite)


def mesclar_predicoes(db_rows: list[dict], limite: int) -> list[dict]:
    with _LOCK:
        return _mesclar(db_rows, _PREDICOES, limite)
