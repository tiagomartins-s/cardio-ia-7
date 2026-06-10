"""Popula o banco com dados de demonstração (idempotente).

Em produção (Vercel) o seed roda automaticamente no bootstrap do app
(`app.main._bootstrap`). Este script existe para preparar o banco local
ou um Postgres recém-provisionado:

    python seeds/seed_pacientes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import _bootstrap  # noqa: E402
from app import repository  # noqa: E402

if __name__ == "__main__":
    _bootstrap()
    print(f"[ok] pacientes: {len(repository.listar_pacientes())}")
    print(f"[ok] protocolos: {len(repository.listar_protocolos())}")
