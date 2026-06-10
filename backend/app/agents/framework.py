"""
Mini-framework de agentes — inspirado no padrão OpenAI Agents SDK
(handoffs, tools, message history, output validation), reescrito de forma
enxuta e determinística para esta entrega acadêmica.

Os blocos principais:
  - `tool(...)` : decorator para registrar funções como ferramentas
  - `Agent`     : agente especializado com prompt-papel, tools e handoffs
  - `Context`   : estado compartilhado e histórico de mensagens
  - `Runner`    : executa a sequência de agentes a partir do orquestrador
  - `Trace`     : lista validada de TraceMensagem para auditoria/exibição

A "inteligência" de cada agente é codificada em métodos `run(...)` que
chamam tools internas e decidem handoffs com base em regras explícitas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, ValidationError


# -------- Tools --------

@dataclass
class Tool:
    name: str
    description: str
    fn: Callable[..., Any]

    def __call__(self, *args, **kwargs) -> Any:
        return self.fn(*args, **kwargs)


def tool(name: str, description: str = "") -> Callable[[Callable[..., Any]], Tool]:
    def deco(fn: Callable[..., Any]) -> Tool:
        return Tool(name=name, description=description or fn.__doc__ or name, fn=fn)
    return deco


# -------- Mensagens / Contexto --------

@dataclass
class Message:
    agente: str
    papel: str  # 'thought' | 'tool_call' | 'tool_result' | 'handoff' | 'final'
    conteudo: str
    metadados: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Context:
    """Estado compartilhado entre agentes durante uma execução."""

    paciente: dict
    sinais: dict
    artefatos: dict = field(default_factory=dict)
    historico: list[Message] = field(default_factory=list)

    def log(self, agente: str, papel: str, conteudo: str, metadados: dict | None = None) -> None:
        self.historico.append(
            Message(
                agente=agente,
                papel=papel,
                conteudo=conteudo,
                metadados=metadados or {},
            )
        )

    def to_trace(self) -> list[dict]:
        return [
            {
                "agente": m.agente,
                "papel": m.papel,
                "conteudo": m.conteudo,
                "metadados": m.metadados,
                "timestamp": m.timestamp,
            }
            for m in self.historico
        ]


# -------- Agente base --------

class Agent:
    name: str = "Agent"
    description: str = ""
    handoffs: list[str] = []
    tools: list[Tool] = []

    def __init__(self) -> None:
        # registra tools como atributos pelo nome
        for t in self.tools:
            setattr(self, t.name, t)

    def run(self, ctx: Context) -> str | None:
        """Executa o passo do agente. Retorna o nome do próximo agente
        (handoff) ou ``None`` quando finaliza."""
        raise NotImplementedError


# -------- Validação de saída --------

def validar_saida(modelo: type[BaseModel], dados: dict) -> BaseModel:
    """Valida e devolve um BaseModel; reúne erros num formato amigável."""
    try:
        return modelo.model_validate(dados)
    except ValidationError as e:
        raise ValueError(f"Saída inválida: {e.errors()}") from e


# -------- Runner --------

class Runner:
    def __init__(self, agentes: dict[str, Agent], inicial: str) -> None:
        self.agentes = agentes
        self.inicial = inicial

    def run(self, ctx: Context, max_handoffs: int = 8) -> Context:
        atual = self.inicial
        for _ in range(max_handoffs):
            agente = self.agentes[atual]
            proximo = agente.run(ctx)
            if proximo is None:
                return ctx
            ctx.log(agente.name, "handoff", f"-> {proximo}", {"para": proximo})
            atual = proximo
        ctx.log("Runner", "final", "limite de handoffs atingido")
        return ctx
