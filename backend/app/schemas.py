"""Pydantic schemas (entrada/saída validados em todos os endpoints e agentes)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------- Pacientes ----------

class PacienteIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    idade: int = Field(ge=0, le=120)
    sexo: Literal["F", "M", "O"] = "O"
    documento: Optional[str] = Field(default=None, max_length=40)
    telefone: Optional[str] = Field(default=None, max_length=40)
    observacoes: Optional[str] = Field(default=None, max_length=2000)


class Paciente(PacienteIn):
    id: int
    criado_em: datetime


# ---------- Sinais vitais / contexto operacional ----------

class SinaisVitais(BaseModel):
    idade: int = Field(ge=0, le=120)
    frequencia_cardiaca: int = Field(ge=20, le=260, description="bpm")
    spo2: float = Field(ge=50, le=100, description="saturacao em %")
    pressao_sistolica: int = Field(ge=60, le=260)
    pressao_diastolica: int = Field(ge=30, le=160)
    glicemia: int = Field(ge=20, le=600, description="mg/dL")
    dor_toracica: bool = False
    historico_arritmia: bool = False
    historico_infarto: bool = False
    tabagista: bool = False
    diabetico: bool = False
    carga_sistema: float = Field(ge=0, le=1, description="0=ocioso, 1=lotado")
    recursos_disponiveis: float = Field(
        ge=0, le=1, description="0=sem recursos, 1=plena capacidade"
    )

    @field_validator("pressao_diastolica")
    @classmethod
    def _diast_menor_que_sist(cls, v: int, info):
        sist = info.data.get("pressao_sistolica")
        if sist is not None and v >= sist:
            raise ValueError("pressao_diastolica deve ser menor que sistolica")
        return v


class PredicaoRequest(BaseModel):
    paciente_id: Optional[int] = None
    nome: Optional[str] = None
    sinais: SinaisVitais


# ---------- Saída do sistema multiagente ----------

class ProtocoloItem(BaseModel):
    codigo: str
    titulo: str
    descricao: str
    severidade: Literal["BAIXO", "MODERADO", "ALTO", "CRITICO"]


class TraceMensagem(BaseModel):
    agente: str
    papel: Literal["thought", "tool_call", "tool_result", "handoff", "final"]
    conteudo: str
    metadados: dict = Field(default_factory=dict)
    timestamp: datetime


class PredicaoOut(BaseModel):
    """Saída final validada do orquestrador."""

    paciente_id: Optional[int]
    nome: Optional[str]
    probabilidade: float = Field(ge=0, le=1)
    classificacao: Literal["BAIXO", "MODERADO", "ALTO", "CRITICO"]
    nivel_atencao: Literal["rotina", "monitorar", "urgente", "emergencia"]
    fatores_relevantes: list[str]
    protocolos: list[ProtocoloItem]
    recomendacao_final: str
    trace: list[TraceMensagem]
    gerado_em: datetime


# ---------- Chatbot do paciente (intents da Fase 5 + triagem da Fase 6) ----------

class ChatTurnoIn(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    sessao_id: Optional[str] = None
    paciente_id: Optional[int] = None


class ChatTurnoOut(BaseModel):
    sessao_id: str
    resposta: str
    estado: Literal[
        "saudacao",
        "coletando_sintomas",
        "triando",
        "encaminhado",
        "agendamento",
        "duvida",
        "encerrado",
    ]
    intencao: Optional[str] = None
    sugestoes: list[str] = Field(default_factory=list)
    triagem: Optional[PredicaoOut] = None


# ---------- Triagem NLP (Fase 2) ----------

class TriagemNlpIn(BaseModel):
    texto: str = Field(min_length=3, max_length=2000, description="relato livre do paciente")


class DiagnosticoSugerido(BaseModel):
    diagnostico: str
    forca_evidencia: int


class TriagemNlpOut(BaseModel):
    texto: str
    sintomas_detectados: list[str]
    diagnosticos: list[DiagnosticoSugerido]
    risco_textual: Literal["alto risco", "baixo risco", "indefinido"]
    probabilidade_risco: float = Field(ge=0, le=1)
    fonte: str


# ---------- IoT (Fase 3 → MicroPython) ----------

class LeituraIotIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=60)
    bpm: Optional[int] = Field(default=None, ge=0, le=300)
    temperatura_amb: Optional[float] = Field(default=None, ge=-10, le=60)
    umidade: Optional[float] = Field(default=None, ge=0, le=100)
    temperatura_pac: Optional[float] = Field(default=None, ge=25, le=45)
    status_edge: Optional[str] = Field(
        default=None, description="classificação local do dispositivo: NORMAL/ATENCAO/CRITICO"
    )
    # opcional: contexto do paciente monitorado para acionar o pipeline de IA
    paciente_id: Optional[int] = None
    executar_predicao: bool = False


class AvaliacaoIot(BaseModel):
    alerta: bool
    motivos: list[str]
    status_servidor: Literal["NORMAL", "ATENCAO", "CRITICO"]
    predicao: Optional[PredicaoOut] = None


class LeituraIotOut(BaseModel):
    id: int
    device_id: str
    bpm: Optional[int]
    temperatura_amb: Optional[float]
    umidade: Optional[float]
    temperatura_pac: Optional[float]
    status_edge: Optional[str]
    alerta: bool
    avaliacao: Optional[dict]
    criado_em: datetime


# ---------- Métricas do modelo ----------

class ModelMetrics(BaseModel):
    accuracy: float
    roc_auc: float
    confusion_matrix: list[list[int]]
    feature_importance: dict[str, float]
