"""Agente Analista de Risco — consulta o modelo ML e gera o score."""

from __future__ import annotations

from .. import ml_service
from .framework import Agent, Context, tool


@tool("prever_pico_risco", "Aplica o modelo treinado para gerar a probabilidade de pico de risco.")
def prever_pico_risco(sinais: dict) -> dict:
    return ml_service.prever(sinais)


@tool(
    "extrair_fatores_clinicos",
    "Identifica fatores clínicos relevantes a partir dos sinais vitais (regras objetivas).",
)
def extrair_fatores_clinicos(sinais: dict) -> list[str]:
    f: list[str] = []
    if sinais["frequencia_cardiaca"] >= 110:
        f.append(f"taquicardia (FC={sinais['frequencia_cardiaca']} bpm)")
    if sinais["frequencia_cardiaca"] <= 50:
        f.append(f"bradicardia (FC={sinais['frequencia_cardiaca']} bpm)")
    if sinais["spo2"] < 94:
        f.append(f"hipoxemia (SpO2={sinais['spo2']}%)")
    if sinais["pressao_sistolica"] >= 160:
        f.append(f"hipertensão grave (PAS={sinais['pressao_sistolica']})")
    if sinais["pressao_sistolica"] < 95:
        f.append(f"hipotensão (PAS={sinais['pressao_sistolica']})")
    if sinais["glicemia"] >= 250:
        f.append(f"hiperglicemia (gl={sinais['glicemia']})")
    if sinais["glicemia"] <= 60:
        f.append(f"hipoglicemia (gl={sinais['glicemia']})")
    if sinais.get("dor_toracica"):
        f.append("dor torácica em curso")
    if sinais.get("historico_arritmia"):
        f.append("histórico de arritmia")
    if sinais.get("historico_infarto"):
        f.append("histórico de infarto")
    if sinais["idade"] >= 65:
        f.append(f"idoso ({sinais['idade']} anos)")
    if sinais.get("tabagista"):
        f.append("tabagista")
    if sinais.get("diabetico"):
        f.append("diabético")
    if sinais["carga_sistema"] >= 0.7 and sinais["recursos_disponiveis"] <= 0.4:
        f.append("contexto operacional crítico (alta carga / poucos recursos)")
    return f


class RiskAnalyst(Agent):
    name = "AnalistaRisco"
    description = (
        "Analista de Risco. Consulta o modelo preditivo para calcular probabilidade "
        "de pico de risco e enumera fatores clínicos relevantes."
    )
    handoffs = ["EspecialistaProtocolos"]
    tools = [prever_pico_risco, extrair_fatores_clinicos]

    def run(self, ctx: Context) -> str | None:
        ctx.log(
            self.name,
            "thought",
            "Recebi os sinais vitais. Vou chamar o modelo preditivo e listar fatores.",
        )

        ctx.log(self.name, "tool_call", "prever_pico_risco(sinais)", {"sinais": ctx.sinais})
        score = self.prever_pico_risco(ctx.sinais)
        ctx.log(self.name, "tool_result", f"score={score['probabilidade']:.3f} ({score['classificacao']})", score)

        ctx.log(self.name, "tool_call", "extrair_fatores_clinicos(sinais)")
        fatores = self.extrair_fatores_clinicos(ctx.sinais)
        ctx.log(self.name, "tool_result", f"{len(fatores)} fatores", {"fatores": fatores})

        ctx.artefatos["risco"] = score
        ctx.artefatos["fatores"] = fatores

        ctx.log(
            self.name,
            "thought",
            f"Encaminhando ao Especialista em Protocolos com score {score['probabilidade']:.3f}.",
        )
        return "EspecialistaProtocolos"
