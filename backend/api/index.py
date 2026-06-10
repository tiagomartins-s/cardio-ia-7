"""Entry point para a Vercel — expõe o FastAPI como Serverless Function.

A Vercel detecta `api/index.py` e serve o app ASGI exportado em `app`.
O `vercel.json` redireciona todas as rotas para esta function.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402, F401
