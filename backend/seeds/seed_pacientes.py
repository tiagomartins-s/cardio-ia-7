"""Popula o banco com pacientes de exemplo (idempotente)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import init_db, get_conn
from app.repository import seed_protocolos_se_vazio, criar_paciente


PACIENTES_DEMO = [
    {"nome": "Maria Silva",        "idade": 67, "sexo": "F", "documento": "123.456.789-01", "telefone": "(11) 91234-5678"},
    {"nome": "João Pereira",       "idade": 58, "sexo": "M", "documento": "987.654.321-00", "telefone": "(11) 99876-5432"},
    {"nome": "Ana Souza",          "idade": 72, "sexo": "F", "documento": "456.789.123-22", "telefone": "(11) 95555-1212"},
    {"nome": "Carlos Mendes",      "idade": 45, "sexo": "M", "documento": "321.654.987-33", "telefone": "(11) 94444-3333"},
    {"nome": "Beatriz Lima",       "idade": 38, "sexo": "F", "documento": "159.753.456-44", "telefone": "(11) 93333-2222"},
    {"nome": "Roberto Castro",     "idade": 81, "sexo": "M", "documento": "753.951.852-55", "telefone": "(11) 92222-1111"},
]


def run() -> None:
    init_db()
    n_proto = seed_protocolos_se_vazio()
    print(f"protocolos: {n_proto} novos")

    with get_conn() as conn:
        existentes = conn.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
    if existentes > 0:
        print(f"pacientes: {existentes} já cadastrados, pulando seed")
        return

    for p in PACIENTES_DEMO:
        criado = criar_paciente(p)
        print(f"paciente criado: #{criado['id']} {criado['nome']}")


if __name__ == "__main__":
    run()
