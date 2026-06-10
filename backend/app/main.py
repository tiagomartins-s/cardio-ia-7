"""FastAPI app — entry point do CardioIA."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from . import ml_service, repository
from .agents import chat_agent
from .agents.orchestrator import executar_pipeline
from .db import init_db
from .schemas import (
    ChatTurnoIn,
    ChatTurnoOut,
    ModelMetrics,
    Paciente,
    PacienteIn,
    PredicaoOut,
    PredicaoRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    repository.seed_protocolos_se_vazio()
    # garante que o modelo seja pré-carregado
    ml_service.status()
    yield


app = FastAPI(
    title="CardioIA API",
    description=(
        "API do sistema preditivo multiagente CardioIA — Fase 6. "
        "Expõe endpoints de gestão (pacientes, protocolos, predições) e "
        "chatbot do paciente."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Saúde / metadados ----------

@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "modelo": ml_service.status(),
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


# ---------- Predição multiagente ----------

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


# ---------- Chatbot ----------

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
