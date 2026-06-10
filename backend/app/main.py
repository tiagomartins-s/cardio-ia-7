"""FastAPI app — núcleo integrador da CardioIA (Fase 7).

Une em uma única API os motores construídos nas fases anteriores:
  - Fase 2 → `/api/triagem-nlp` (ontologia + classificador de risco textual)
  - Fase 3 → `/api/iot/*` (ingestão de sinais do ESP32/MicroPython)
  - Fase 5 → `/api/chat` (chatbot por intents, ex-Watson)
  - Fase 6 → `/api/predicoes` (pipeline multiagente + Random Forest)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from . import iot_service, ml_service, nlp_service, repository
from .agents import chat_agent
from .agents.orchestrator import executar_pipeline
from .db import backend_info, init_db
from .schemas import (
    ChatTurnoIn,
    ChatTurnoOut,
    LeituraIotIn,
    LeituraIotOut,
    ModelMetrics,
    Paciente,
    PacienteIn,
    PredicaoOut,
    PredicaoRequest,
    TriagemNlpIn,
    TriagemNlpOut,
)

_BOOTSTRAPPED = False


def _bootstrap() -> None:
    """Inicialização idempotente — chamada no import (serverless pode não
    disparar o protocolo lifespan do ASGI) e no lifespan (uvicorn local)."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    init_db()
    repository.seed_protocolos_se_vazio()
    _seed_pacientes_demo()
    ml_service.status()
    nlp_service.status()
    _BOOTSTRAPPED = True


def _seed_pacientes_demo() -> None:
    """Em ambiente efêmero (Vercel + SQLite em /tmp) garante dados de demo."""
    if repository.listar_pacientes():
        return
    demos = [
        {"nome": "Maria Aparecida Souza", "idade": 71, "sexo": "F",
         "observacoes": "Hipertensa, em acompanhamento semestral."},
        {"nome": "João Carlos Pereira", "idade": 64, "sexo": "M",
         "observacoes": "Histórico de arritmia; usa marcapasso desde 2022."},
        {"nome": "Antônio Ferreira Lima", "idade": 58, "sexo": "M",
         "observacoes": "Tabagista, diabético tipo 2."},
        {"nome": "Helena Cristina Rocha", "idade": 47, "sexo": "F",
         "observacoes": "Assintomática; check-up anual."},
    ]
    for d in demos:
        repository.criar_paciente(d)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _bootstrap()
    yield


app = FastAPI(
    title="CardioIA API — Fase 7",
    description=(
        "Backend integrador da plataforma CardioIA. Conecta as interfaces Web "
        "(React+Vite) e Mobile (Expo) aos motores de IA: modelo preditivo e "
        "sistema multiagente (Fase 6), triagem NLP (Fase 2), chatbot (Fase 5) "
        "e ingestão IoT em MicroPython (Fase 3→7)."
    ),
    version="7.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_bootstrap()


# ---------- Saúde / metadados ----------

@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "ambiente": "vercel" if os.getenv("VERCEL") else "local",
        "banco": backend_info(),
        "modelo": ml_service.status(),
        "nlp": nlp_service.status(),
        "ts": datetime.utcnow().isoformat(),
    }


@app.get("/api/modelo/metrics", response_model=ModelMetrics | None)
def modelo_metrics():
    m = ml_service.metrics()
    if not m:
        return None
    return ModelMetrics(
        accuracy=m["accuracy"],
        roc_auc=m["roc_auc"],
        confusion_matrix=m["confusion_matrix"],
        feature_importance=m["feature_importance"],
    )


# ---------- Pacientes ----------

@app.get("/api/pacientes", response_model=list[Paciente])
def list_pacientes():
    return repository.listar_pacientes()


@app.post("/api/pacientes", response_model=Paciente, status_code=status.HTTP_201_CREATED)
def criar_paciente(p: PacienteIn):
    return repository.criar_paciente(p.model_dump())


@app.get("/api/pacientes/{paciente_id}", response_model=Paciente)
def obter_paciente(paciente_id: int):
    p = repository.obter_paciente(paciente_id)
    if not p:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    return p


@app.delete("/api/pacientes/{paciente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_paciente(paciente_id: int):
    if not repository.remover_paciente(paciente_id):
        raise HTTPException(status_code=404, detail="Paciente não encontrado")


# ---------- Protocolos ----------

@app.get("/api/protocolos")
def listar_protocolos():
    return repository.listar_protocolos()


# ---------- Predição multiagente (Fase 6) ----------

@app.post("/api/predicoes", response_model=PredicaoOut)
def predizer(req: PredicaoRequest):
    paciente = None
    if req.paciente_id is not None:
        paciente = repository.obter_paciente(req.paciente_id)
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente não encontrado")
    elif req.nome:
        paciente = {"nome": req.nome}

    saida = executar_pipeline(paciente, req.sinais.model_dump())
    repository.salvar_predicao(req.paciente_id, saida.model_dump(mode="json"))
    return saida


@app.get("/api/predicoes")
def listar_predicoes(paciente_id: int | None = None, limite: int = 50):
    return repository.listar_predicoes(paciente_id=paciente_id, limite=limite)


# ---------- Triagem NLP (Fase 2) ----------

@app.post("/api/triagem-nlp", response_model=TriagemNlpOut)
def triagem_nlp(req: TriagemNlpIn):
    return nlp_service.avaliar_texto(req.texto)


# ---------- IoT (Fase 3 → MicroPython) ----------

@app.post("/api/iot/leituras", response_model=LeituraIotOut, status_code=status.HTTP_201_CREATED)
def receber_leitura(leitura: LeituraIotIn):
    return iot_service.processar_leitura(leitura.model_dump())


@app.get("/api/iot/leituras", response_model=list[LeituraIotOut])
def listar_leituras(limite: int = 50, device_id: str | None = None):
    return repository.listar_leituras_iot(limite=limite, device_id=device_id)


# ---------- Chatbot (Fase 5) ----------

@app.post("/api/chat", response_model=ChatTurnoOut)
def chat(turno: ChatTurnoIn):
    return chat_agent.processar(
        mensagem=turno.mensagem,
        sessao_id=turno.sessao_id,
        paciente_id=turno.paciente_id,
    )


@app.get("/api/chat/{sessao_id}/historico")
def historico_chat(sessao_id: str):
    return repository.historico_chat(sessao_id)
