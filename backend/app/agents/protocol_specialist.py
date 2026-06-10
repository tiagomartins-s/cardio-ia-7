"""Agente Especialista em Protocolos — consulta a base e seleciona protocolos aplicáveis."""

from __future__ import annotations

from typing import Any

from .. import repository
from .framework import Agent, Context, tool


_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">":  lambda a, b: a >  b,
    ">=": lambda a, b: a >= b,
    "<":  lambda a, b: a <  b,
    "<=": lambda a, b: a <= b,
}


@tool(
    "buscar_protocolos",
    "Carrega todos os protocolos clínicos cadastrados no banco (com seus gatilhos).",
)
def buscar_protocolos() -> list[dict]:
    return repository.listar_protocolos()


@tool(
    "casar_protocolos",
    "Avalia gatilhos de cada protocolo contra os sinais e a probabilidade prevista.",
)
def casar_protocolos(
    protocolos: list[dict],
    sinais: dict,
    probabilidade: float,
) -> list[dict]:
    selecionados: list[dict] = []
    valores: dict[str, Any] = {**sinais, "probabilidade": probabilidade}
    for p in protocolos:
        for g in p["gatilhos"]:
            campo, op, valor = g["campo"], g["op"], g["valor"]
            atual = valores.get(campo)
            if atual is None:
                continue
            if isinstance(valor, bool):
                atual = bool(atual)
            if _OPS[op](atual, valor):
                selecionados.append(
                    {
                        "codigo": p["codigo"],
                        "titulo": p["titulo"],
                        "descricao": p["descricao"],
                        "severidade": p["severidade"],
                        "gatilho_atendido": f"{campo} {op} {valor}",
                    }
                )
                break
    # ordena por severidade (CRITICO -> BAIXO)
    ordem = {"CRITICO": 0, "ALTO": 1, "MODERADO": 2, "BAIXO": 3}
    selecionados.sort(key=lambda x: ordem.get(x["severidade"], 99))
    return selecionados


@tool(
    "definir_nivel_atencao",
    "Mapeia classificação de risco e protocolos em um nível operacional de atenção.",
)
def definir_nivel_atencao(classificacao: str, protocolos: list[dict]) -> str:
    severidades = {p["severidade"] for p in protocolos}
    if classificacao == "CRITICO" or "CRITICO" in severidades:
        return "emergencia"
    if classificacao == "ALTO" or "ALTO" in severidades:
        return "urgente"
    if classificacao == "MODERADO" or "MODERADO" in severidades:
        return "monitorar"
    return "rotina"


class ProtocolSpecialist(Agent):
    name = "EspecialistaProtocolos"
    description = (
        "Especialista em Protocolos. Cruza o score recebido com a base de protocolos "
        "clínicos e operacionais e devolve a lista priorizada por severidade."
    )
    handoffs = ["Orquestrador"]
    tools = [buscar_protocolos, casar_protocolos, definir_nivel_atencao]

    def run(self, ctx: Context) -> str | None:
        risco = ctx.artefatos["risco"]
        ctx.log(self.name, "thought", "Vou carregar protocolos e casar com sinais e probabilidade.")

        ctx.log(self.name, "tool_call", "buscar_protocolos()")
        protos = self.buscar_protocolos()
        ctx.log(self.name, "tool_result", f"{len(protos)} protocolos carregados")

        ctx.log(self.name, "tool_call", "casar_protocolos(...)")
        match = self.casar_protocolos(protos, ctx.sinais, risco["probabilidade"])
        ctx.log(
            self.name,
            "tool_result",
            f"{len(match)} protocolos aplicáveis: " + ", ".join(p["codigo"] for p in match),
            {"protocolos": match},
        )

        ctx.log(self.name, "tool_call", "definir_nivel_atencao(...)")
        nivel = self.definir_nivel_atencao(risco["classificacao"], match)
        ctx.log(self.name, "tool_result", f"nivel_atencao={nivel}")

        ctx.artefatos["protocolos"] = match
        ctx.artefatos["nivel_atencao"] = nivel

        ctx.log(self.name, "thought", "Devolvendo controle ao Orquestrador para resposta final.")
        return "Orquestrador"
