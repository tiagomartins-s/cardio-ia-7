"""
Agente Chatbot do Paciente.

Em produção, este chatbot ficaria na app pública e estaria desacoplado
da plataforma de gestão. Para fins de demonstração, está exposto na
mesma stack — porém apenas conversa com o paciente; quando há suspeita
clínica, dispara o pipeline multiagente como um cliente externo.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any

from .. import repository
from ..schemas import ChatTurnoOut, PredicaoOut
from .orchestrator import executar_pipeline


@dataclass
class _Sessao:
    sessao_id: str
    estado: str = "saudacao"
    paciente_id: int | None = None
    coleta: dict[str, Any] = field(default_factory=dict)
    perguntas_pendentes: list[str] = field(default_factory=list)
    contexto_paciente: dict | None = None


_SESSOES: dict[str, _Sessao] = {}
_LOCK = Lock()


# perguntas guiadas para coletar sinais vitais auto-relatados
_FLUXO_TRIAGEM = [
    ("idade", "Para começar, qual a sua idade?"),
    ("frequencia_cardiaca", "Você consegue medir seu pulso? Quantos batimentos por minuto?"),
    ("spo2", "Tem oxímetro em casa? Qual a saturação (SpO2) em %? (digite 'nao' se não tiver — vou usar 97)"),
    ("pressao", "Qual sua pressão arterial agora? (formato 130/85, ou 'nao' se não souber)"),
    ("dor_toracica", "Você está sentindo dor no peito agora? (sim/nao)"),
    ("historico", "Tem histórico de arritmia ou infarto? (digite: arritmia, infarto, ambos, nenhum)"),
]


def _nova_sessao() -> _Sessao:
    s = _Sessao(sessao_id=uuid.uuid4().hex[:12])
    _SESSOES[s.sessao_id] = s
    return s


def _obter(sessao_id: str | None) -> _Sessao:
    if sessao_id and sessao_id in _SESSOES:
        return _SESSOES[sessao_id]
    return _nova_sessao()


def _normalizar(s: str) -> str:
    return s.strip().lower()


def _extrair_int(texto: str) -> int | None:
    m = re.search(r"\d{1,3}", texto)
    return int(m.group(0)) if m else None


def _extrair_pa(texto: str) -> tuple[int, int] | None:
    m = re.search(r"(\d{2,3})\s*[/x]\s*(\d{2,3})", texto)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _resposta(estado: str, msg: str, sugestoes: list[str] | None = None,
              triagem: PredicaoOut | None = None, sessao: _Sessao | None = None) -> ChatTurnoOut:
    return ChatTurnoOut(
        sessao_id=sessao.sessao_id if sessao else "",
        resposta=msg,
        estado=estado,
        sugestoes=sugestoes or [],
        triagem=triagem,
    )


def _persistir(sessao: _Sessao, autor: str, conteudo: str) -> None:
    repository.salvar_chat(sessao.sessao_id, autor, conteudo, sessao.estado)


def _executar_triagem(sessao: _Sessao) -> PredicaoOut:
    c = sessao.coleta
    sinais = {
        "idade": c.get("idade", 50),
        "frequencia_cardiaca": c.get("frequencia_cardiaca", 78),
        "spo2": c.get("spo2", 97.0),
        "pressao_sistolica": c.get("pressao_sistolica", 130),
        "pressao_diastolica": c.get("pressao_diastolica", 85),
        "glicemia": c.get("glicemia", 110),
        "dor_toracica": c.get("dor_toracica", False),
        "historico_arritmia": c.get("historico_arritmia", False),
        "historico_infarto": c.get("historico_infarto", False),
        "tabagista": c.get("tabagista", False),
        "diabetico": c.get("diabetico", False),
        "carga_sistema": 0.5,           # contexto operacional do consultório
        "recursos_disponiveis": 0.7,
    }
    paciente = sessao.contexto_paciente
    return executar_pipeline(paciente, sinais)


def _proxima_pergunta(sessao: _Sessao) -> tuple[str, str] | None:
    coletados = sessao.coleta.keys()
    for chave, pergunta in _FLUXO_TRIAGEM:
        if chave == "pressao":
            if "pressao_sistolica" in coletados:
                continue
        elif chave == "historico":
            if "historico_arritmia" in coletados:
                continue
        elif chave in coletados:
            continue
        return chave, pergunta
    return None


def _processar_resposta_triagem(sessao: _Sessao, chave: str, mensagem: str) -> str | None:
    """Atualiza `sessao.coleta` com base na resposta. Devolve mensagem opcional."""
    txt = _normalizar(mensagem)

    if chave == "idade":
        v = _extrair_int(txt)
        if v is None or not 1 <= v <= 120:
            return "Não entendi sua idade. Pode informar em números, por favor?"
        sessao.coleta["idade"] = v

    elif chave == "frequencia_cardiaca":
        v = _extrair_int(txt)
        if v and 30 <= v <= 220:
            sessao.coleta["frequencia_cardiaca"] = v
        else:
            sessao.coleta["frequencia_cardiaca"] = 78  # padrão
            return "Sem problema, vou usar valor médio (78 bpm). Vamos prosseguir."

    elif chave == "spo2":
        if "nao" in txt or "não" in txt:
            sessao.coleta["spo2"] = 97.0
        else:
            v = _extrair_int(txt)
            if v and 70 <= v <= 100:
                sessao.coleta["spo2"] = float(v)
            else:
                sessao.coleta["spo2"] = 97.0

    elif chave == "pressao":
        if "nao" in txt or "não" in txt:
            sessao.coleta["pressao_sistolica"] = 130
            sessao.coleta["pressao_diastolica"] = 85
        else:
            pa = _extrair_pa(txt)
            if pa:
                sessao.coleta["pressao_sistolica"] = pa[0]
                sessao.coleta["pressao_diastolica"] = pa[1]
            else:
                sessao.coleta["pressao_sistolica"] = 130
                sessao.coleta["pressao_diastolica"] = 85

    elif chave == "dor_toracica":
        sessao.coleta["dor_toracica"] = "sim" in txt or "tenho" in txt

    elif chave == "historico":
        sessao.coleta["historico_arritmia"] = "arritmia" in txt or "ambos" in txt
        sessao.coleta["historico_infarto"] = "infarto" in txt or "ambos" in txt

    return None


def _intencao(texto: str) -> str:
    t = _normalizar(texto)
    palavras_sintomas = (
        "dor", "tontura", "mal", "passando mal", "falta de ar", "palpit",
        "pressão", "pressao", "sintoma", "peito", "coração", "coracao",
        "desmaio", "tont", "ânsia", "ansia",
    )
    if any(p in t for p in palavras_sintomas):
        return "sintomas"
    if any(p in t for p in ("agendar", "marcar", "consulta", "horario", "horário")):
        return "agendamento"
    if any(p in t for p in ("oi", "olá", "ola", "boa", "bom dia", "boa tarde", "boa noite")):
        return "saudacao"
    if any(p in t for p in ("obrigad", "valeu", "tchau", "encerrar")):
        return "encerrar"
    return "duvida"


def processar(mensagem: str, sessao_id: str | None, paciente_id: int | None) -> ChatTurnoOut:
    with _LOCK:
        sessao = _obter(sessao_id)
        if paciente_id and sessao.paciente_id is None:
            sessao.paciente_id = paciente_id
            sessao.contexto_paciente = repository.obter_paciente(paciente_id)
        _persistir(sessao, "paciente", mensagem)

        # roteamento por estado
        if sessao.estado == "saudacao":
            intencao = _intencao(mensagem)
            if intencao == "sintomas":
                sessao.estado = "coletando_sintomas"
                kp = _proxima_pergunta(sessao)
                resp = (
                    "Sinto muito que você esteja se sentindo assim. Vou fazer uma triagem rápida "
                    "guiada pelo nosso sistema de IA. " + (kp[1] if kp else "")
                )
            elif intencao == "agendamento":
                sessao.estado = "agendamento"
                resp = (
                    "Claro! Para agendar uma consulta, posso te oferecer estes horários: "
                    "amanhã 10h, amanhã 14h ou quinta 09h. Qual prefere?"
                )
            elif intencao == "encerrar":
                sessao.estado = "encerrado"
                resp = "Tudo bem! Estou aqui se precisar."
            else:
                resp = (
                    "Olá! Sou a assistente virtual da CardioIA. Posso te ajudar a:\n"
                    "• Avaliar sintomas que você esteja sentindo\n"
                    "• Agendar uma consulta\n"
                    "• Tirar dúvidas sobre seu acompanhamento\n\n"
                    "Como posso te ajudar hoje?"
                )
            _persistir(sessao, "bot", resp)
            return _resposta(
                sessao.estado, resp,
                sugestoes=["Estou com dor no peito", "Quero marcar uma consulta", "Tenho uma dúvida"],
                sessao=sessao,
            )

        if sessao.estado == "coletando_sintomas":
            atual = _proxima_pergunta(sessao)
            if atual is None:
                # já temos tudo
                pass
            else:
                erro = _processar_resposta_triagem(sessao, atual[0], mensagem)
                if erro:
                    _persistir(sessao, "bot", erro)
                    return _resposta(sessao.estado, erro, sessao=sessao)

            prox = _proxima_pergunta(sessao)
            if prox is not None:
                _persistir(sessao, "bot", prox[1])
                return _resposta(sessao.estado, prox[1], sessao=sessao)

            # acabou a coleta — roda triagem
            sessao.estado = "triando"
            triagem = _executar_triagem(sessao)
            sessao.estado = "encaminhado"

            urg = triagem.nivel_atencao
            if urg == "emergencia":
                base = (
                    "⚠️ ATENÇÃO: seus sintomas indicam risco ALTO. Procure imediatamente "
                    "uma emergência ou ligue 192 (SAMU). Já notifiquei a equipe da clínica."
                )
            elif urg == "urgente":
                base = (
                    "Os sintomas relatados sugerem necessidade de atendimento URGENTE. "
                    "Recomendo dirigir-se ao pronto-atendimento ainda hoje. "
                    "Vou registrar sua triagem para a equipe médica."
                )
            elif urg == "monitorar":
                base = (
                    "Seus sintomas pedem monitorização. Sugiro agendar consulta nas próximas 48h. "
                    "Posso te ajudar a marcar agora?"
                )
            else:
                base = (
                    "Seus sintomas, no momento, parecem de baixo risco. "
                    "Mas vale agendar uma avaliação preventiva. Quer que eu reserve um horário?"
                )
            base += f"\n\n(Probabilidade calculada: {triagem.probabilidade:.0%} | Classificação: {triagem.classificacao})"
            _persistir(sessao, "bot", base)
            return _resposta(
                sessao.estado, base,
                sugestoes=["Marcar consulta", "Voltar ao início"],
                triagem=triagem, sessao=sessao,
            )

        if sessao.estado == "agendamento":
            txt = _normalizar(mensagem)
            if any(p in txt for p in ("amanha", "amanhã", "quinta", "10", "14", "09")):
                resp = (
                    "Pronto! Sua consulta está pré-reservada. A equipe entrará em contato "
                    "para confirmar. Mais alguma coisa?"
                )
                sessao.estado = "saudacao"
            else:
                resp = "Não entendi o horário. Pode escolher entre amanhã 10h, amanhã 14h ou quinta 09h?"
            _persistir(sessao, "bot", resp)
            return _resposta(sessao.estado, resp, sessao=sessao)

        if sessao.estado == "encaminhado":
            txt = _normalizar(mensagem)
            if "marc" in txt or "consulta" in txt or "agend" in txt:
                sessao.estado = "agendamento"
                resp = "Claro! Tenho amanhã 10h, amanhã 14h ou quinta 09h. Qual prefere?"
            else:
                sessao.estado = "saudacao"
                resp = "Sem problema. Posso te ajudar com mais alguma coisa?"
            _persistir(sessao, "bot", resp)
            return _resposta(sessao.estado, resp, sessao=sessao)

        # fallback
        sessao.estado = "saudacao"
        resp = "Pode reformular? Posso ajudar com sintomas, agendamento ou dúvidas."
        _persistir(sessao, "bot", resp)
        return _resposta(sessao.estado, resp, sessao=sessao)
