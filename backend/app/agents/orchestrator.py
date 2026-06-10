"""Agente Orquestrador — inicia o fluxo e consolida a resposta final validada."""

from __future__ import annotations

from datetime import datetime

from ..schemas import PredicaoOut, ProtocoloItem, TraceMensagem
from .framework import Agent, Context, Runner, tool, validar_saida
from .protocol_specialist import ProtocolSpecialist
from .risk_analyst import RiskAnalyst


@tool(
    "compor_recomendacao",
    "Compõe a recomendação textual final integrando risco, fatores e protocolos.",
)
def compor_recomendacao(
    classificacao: str,
    probabilidade: float,
    fatores: list[str],
    protocolos: list[dict],
    nivel_atencao: str,
) -> str:
    nivel_txt = {
        "rotina": "acompanhamento de rotina",
        "monitorar": "monitorização periódica",
        "urgente": "atendimento URGENTE",
        "emergencia": "atendimento de EMERGÊNCIA imediato",
    }[nivel_atencao]

    cabecalho = (
        f"Risco {classificacao} (probabilidade {probabilidade:.0%}). "
        f"Encaminhamento sugerido: {nivel_txt}."
    )
    if fatores:
        cabecalho += " Fatores: " + ", ".join(fatores) + "."
    if protocolos:
        cabecalho += " Protocolos: " + ", ".join(
            f"{p['codigo']} ({p['severidade']})" for p in protocolos[:4]
        ) + "."
    return cabecalho


class Orchestrator(Agent):
    name = "Orquestrador"
    description = (
        "Orquestrador. Inicia o fluxo, delega ao Analista de Risco, recebe os "
        "achados via Especialista em Protocolos e produz a saída final validada."
    )
    handoffs = ["AnalistaRisco"]
    tools = [compor_recomendacao]

    def run(self, ctx: Context) -> str | None:
        if "risco" not in ctx.artefatos:
            ctx.log(
                self.name,
                "thought",
                "Sem score ainda. Iniciando handoff para AnalistaRisco.",
            )
            return "AnalistaRisco"

        risco = ctx.artefatos["risco"]
        protocolos = ctx.artefatos["protocolos"]
        fatores = ctx.artefatos["fatores"]
        nivel = ctx.artefatos["nivel_atencao"]

        ctx.log(self.name, "tool_call", "compor_recomendacao(...)")
        recomendacao = self.compor_recomendacao(
            classificacao=risco["classificacao"],
            probabilidade=risco["probabilidade"],
            fatores=fatores,
            protocolos=protocolos,
            nivel_atencao=nivel,
        )
        ctx.log(self.name, "tool_result", recomendacao)

        ctx.artefatos["recomendacao_final"] = recomendacao
        ctx.log(
            self.name,
            "final",
            "Saída consolidada. Encerrando o pipeline multiagente.",
            {"classificacao": risco["classificacao"]},
        )
        return None


def montar_runner() -> Runner:
    agentes = {
        "Orquestrador": Orchestrator(),
        "AnalistaRisco": RiskAnalyst(),
        "EspecialistaProtocolos": ProtocolSpecialist(),
    }
    return Runner(agentes=agentes, inicial="Orquestrador")


def executar_pipeline(paciente: dict | None, sinais: dict) -> PredicaoOut:
    """Executa o pipeline e devolve a saída validada via Pydantic."""
    runner = montar_runner()
    ctx = Context(paciente=paciente or {}, sinais=sinais)
    runner.run(ctx)

    risco = ctx.artefatos["risco"]
    protocolos = [
        ProtocoloItem(
            codigo=p["codigo"],
            titulo=p["titulo"],
            descricao=p["descricao"],
            severidade=p["severidade"],
        )
        for p in ctx.artefatos["protocolos"]
    ]
    trace = [TraceMensagem(**m) for m in ctx.to_trace()]

    saida = {
        "paciente_id": (paciente or {}).get("id"),
        "nome": (paciente or {}).get("nome"),
        "probabilidade": risco["probabilidade"],
        "classificacao": risco["classificacao"],
        "nivel_atencao": ctx.artefatos["nivel_atencao"],
        "fatores_relevantes": ctx.artefatos["fatores"],
        "protocolos": [p.model_dump() for p in protocolos],
        "recomendacao_final": ctx.artefatos["recomendacao_final"],
        "trace": [t.model_dump() for t in trace],
        "gerado_em": datetime.utcnow(),
    }
    return validar_saida(PredicaoOut, saida)
