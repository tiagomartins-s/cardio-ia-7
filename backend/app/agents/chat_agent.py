"""
Agente Chatbot do Paciente — Fase 5 + Fase 6 unificadas.

As intents modeladas no IBM Watson Assistant na Fase 5 (`watson.json`:
emergencia_cardiaca, agendar_exame, duvida_pressao, duvida_sintomas) foram
reimplementadas aqui como um motor local de NLU por palavras-chave/regex,
eliminando a dependência de credenciais IBM. As respostas dos dialog nodes
originais foram preservadas. Quando o paciente relata sintomas, o agente
faz a coleta guiada de sinais vitais e dispara o pipeline multiagente da
Fase 6 — o mesmo da tela de Predição.

O estado da sessão é persistido em banco (`chat_sessoes`): em serverless
cada requisição pode atender em uma instância diferente, então memória de
processo não é confiável.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from .. import repository
from ..schemas import ChatTurnoOut, PredicaoOut
from .orchestrator import executar_pipeline


# ---------- sessão persistida ----------

def _nova_sessao() -> dict:
    return {
        "sessao_id": uuid.uuid4().hex[:12],
        "estado": "saudacao",
        "paciente_id": None,
        "coleta": {},
        "contexto_paciente": None,
    }


def _obter(sessao_id: str | None) -> dict:
    if sessao_id:
        salva = repository.carregar_sessao_chat(sessao_id)
        if salva:
            return salva
    return _nova_sessao()


# ---------- NLU local (intents da Fase 5 + roteamento da Fase 6) ----------

def _normalizar(s: str) -> str:
    return s.strip().lower()


_EMERGENCIA = (
    "muita dor no peito", "dor forte no peito", "enfart", "infartando",
    "falta de ar grave", "braço formigando", "braco formigando",
    "peito apertando", "aperto no peito e", "dor no coração", "dor no coracao",
)
_SINTOMAS = (
    "dor", "tontura", "mal", "passando mal", "falta de ar", "palpit",
    "sintoma que estou", "peito", "desmaio", "tont", "ânsia", "ansia", "suor",
)
_EXAMES = (
    "eletrocardiograma", "ecocardiograma", "holter", "exame", "risco cirurgico",
    "risco cirúrgico", "mapa", "teste ergometrico", "teste ergométrico",
)
_AGENDAR = ("agendar", "marcar", "consulta", "horario", "horário")
_PRESSAO = ("pressão", "pressao", "hipertens", "por 9", "por 8", "x 9", "x 8", "14x", "15x")
_DUVIDA_SINTOMAS = (
    "quais os sintomas", "quais são os sinais", "quais sao os sinais",
    "como saber se", "como identificar", "o que a pessoa sente", "sinais de problema",
    "sintomas de um infarto", "sintomas de infarto", "sintoma de doença", "sintoma de doenca",
)


def detectar_intencao(texto: str) -> str:
    """Classifica a mensagem em uma intent — equivalente local do Watson NLU."""
    t = _normalizar(texto)
    if any(p in t for p in _EMERGENCIA):
        return "emergencia_cardiaca"
    if any(p in t for p in _DUVIDA_SINTOMAS):
        return "duvida_sintomas"
    if any(p in t for p in _PRESSAO):
        return "duvida_pressao"
    if any(p in t for p in _EXAMES) or any(p in t for p in _AGENDAR):
        return "agendar_exame"
    if any(p in t for p in _SINTOMAS):
        return "sintomas"
    if any(p in t for p in ("oi", "olá", "ola", "boa", "bom dia", "boa tarde", "boa noite")):
        return "saudacao"
    if any(p in t for p in ("obrigad", "valeu", "tchau", "encerrar")):
        return "encerrar"
    return "fallback"


# respostas herdadas dos dialog nodes do watson.json (Fase 5)
_RESP_WELCOME = (
    "Olá! Sou a assistente virtual da CardioIA. Posso te ajudar a:\n"
    "• Avaliar sintomas que você esteja sentindo\n"
    "• Agendar consultas e exames do coração (ECG, ecocardiograma, holter)\n"
    "• Tirar dúvidas sobre pressão arterial e sintomas cardíacos\n\n"
    "Como posso te ajudar hoje?"
)
_RESP_EMERGENCIA = (
    "⚠️ ALERTA: pelos sintomas que descreveu (dor/aperto no peito), isto pode ser "
    "uma EMERGÊNCIA médica. Procure IMEDIATAMENTE o pronto-socorro mais próximo "
    "ou ligue 192 (SAMU). Se quiser, posso fazer uma triagem rápida enquanto "
    "você se organiza — responda apenas se estiver em segurança."
)
_RESP_EXAMES = (
    "Para exames cardiológicos (Eletrocardiograma, Ecocardiograma ou Holter), "
    "nossa agenda está disponível. Tenho estes horários: amanhã 10h, amanhã 14h "
    "ou quinta 09h. Qual prefere?"
)
_RESP_PRESSAO = (
    "Variações na pressão arterial precisam de acompanhamento. Se a sua pressão "
    "estiver consistentemente acima de 14x9, deite-se, tente relaxar e meça "
    "novamente em 30 minutos. Se não baixar ou vier acompanhada de dor na nuca "
    "ou no peito, procure um pronto-atendimento. Deseja agendar uma consulta "
    "com o cardiologista para avaliar isso?"
)
_RESP_DUVIDA_SINTOMAS = (
    "Os sintomas mais comuns de problemas cardíacos incluem: dor ou aperto no "
    "peito, falta de ar inexplicável, palpitações fortes, tontura frequente ou "
    "inchaço nas pernas. Você está sentindo algum desses sintomas de forma "
    "intensa neste exato momento? Se sim, me avise."
)
_RESP_FALLBACK = (
    "Desculpe, não compreendi. Meu foco é saúde cardiovascular: posso avaliar "
    "sintomas, agendar exames ou tirar dúvidas sobre pressão arterial. "
    "Pode tentar com outras palavras?"
)


# ---------- coleta guiada de sinais (Fase 6) ----------

_FLUXO_TRIAGEM = [
    ("idade", "Para começar, qual a sua idade?"),
    ("frequencia_cardiaca", "Você consegue medir seu pulso? Quantos batimentos por minuto?"),
    ("spo2", "Tem oxímetro em casa? Qual a saturação (SpO2) em %? (digite 'nao' se não tiver — vou usar 97)"),
    ("pressao", "Qual sua pressão arterial agora? (formato 130/85, ou 'nao' se não souber)"),
    ("dor_toracica", "Você está sentindo dor no peito agora? (sim/nao)"),
    ("historico", "Tem histórico de arritmia ou infarto? (digite: arritmia, infarto, ambos, nenhum)"),
]


def _extrair_int(texto: str) -> int | None:
    m = re.search(r"\d{1,3}", texto)
    return int(m.group(0)) if m else None


def _extrair_pa(texto: str) -> tuple[int, int] | None:
    m = re.search(r"(\d{2,3})\s*[/x]\s*(\d{2,3})", texto)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _proxima_pergunta(sessao: dict) -> tuple[str, str] | None:
    coletados = sessao["coleta"].keys()
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


def _processar_resposta_triagem(sessao: dict, chave: str, mensagem: str) -> str | None:
    txt = _normalizar(mensagem)
    coleta = sessao["coleta"]

    if chave == "idade":
        v = _extrair_int(txt)
        if v is None or not 1 <= v <= 120:
            return "Não entendi sua idade. Pode informar em números, por favor?"
        coleta["idade"] = v

    elif chave == "frequencia_cardiaca":
        v = _extrair_int(txt)
        if v and 30 <= v <= 220:
            coleta["frequencia_cardiaca"] = v
        else:
            coleta["frequencia_cardiaca"] = 78
            return "Sem problema, vou usar valor médio (78 bpm). Vamos prosseguir."

    elif chave == "spo2":
        if "nao" in txt or "não" in txt:
            coleta["spo2"] = 97.0
        else:
            v = _extrair_int(txt)
            coleta["spo2"] = float(v) if v and 70 <= v <= 100 else 97.0

    elif chave == "pressao":
        if "nao" in txt or "não" in txt:
            coleta["pressao_sistolica"], coleta["pressao_diastolica"] = 130, 85
        else:
            pa = _extrair_pa(txt)
            if pa:
                coleta["pressao_sistolica"], coleta["pressao_diastolica"] = pa
            else:
                coleta["pressao_sistolica"], coleta["pressao_diastolica"] = 130, 85

    elif chave == "dor_toracica":
        coleta["dor_toracica"] = "sim" in txt or "tenho" in txt

    elif chave == "historico":
        coleta["historico_arritmia"] = "arritmia" in txt or "ambos" in txt
        coleta["historico_infarto"] = "infarto" in txt or "ambos" in txt

    return None


def _executar_triagem(sessao: dict) -> PredicaoOut:
    c = sessao["coleta"]
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
        "carga_sistema": 0.5,
        "recursos_disponiveis": 0.7,
    }
    return executar_pipeline(sessao.get("contexto_paciente"), sinais)


# ---------- helpers de resposta ----------

def _resposta(sessao: dict, msg: str, sugestoes: list[str] | None = None,
              triagem: PredicaoOut | None = None, intencao: str | None = None) -> ChatTurnoOut:
    repository.salvar_chat(sessao["sessao_id"], "bot", msg, sessao["estado"])
    repository.salvar_sessao_chat(sessao["sessao_id"], sessao)
    return ChatTurnoOut(
        sessao_id=sessao["sessao_id"],
        resposta=msg,
        estado=sessao["estado"],
        intencao=intencao,
        sugestoes=sugestoes or [],
        triagem=triagem,
    )


_SUGESTOES_PADRAO = [
    "Estou com dor no peito",
    "Quero agendar um eletrocardiograma",
    "Minha pressão está 15 por 9",
    "Quais os sintomas de um infarto?",
]


# ---------- processamento de um turno ----------

def processar(mensagem: str, sessao_id: str | None, paciente_id: int | None) -> ChatTurnoOut:
    sessao = _obter(sessao_id)
    if paciente_id and sessao.get("paciente_id") is None:
        sessao["paciente_id"] = paciente_id
        sessao["contexto_paciente"] = repository.obter_paciente(paciente_id)
    repository.salvar_chat(sessao["sessao_id"], "paciente", mensagem, sessao["estado"])

    estado = sessao["estado"]

    # estados "saudacao" e "duvida" roteiam por intenção (NLU local)
    if estado in ("saudacao", "duvida", "encerrado"):
        intencao = detectar_intencao(mensagem)

        if intencao == "emergencia_cardiaca":
            sessao["estado"] = "coletando_sintomas"
            sessao["coleta"]["dor_toracica"] = True
            kp = _proxima_pergunta(sessao)
            msg = _RESP_EMERGENCIA + ("\n\n" + kp[1] if kp else "")
            return _resposta(sessao, msg, intencao=intencao)

        if intencao == "sintomas":
            sessao["estado"] = "coletando_sintomas"
            kp = _proxima_pergunta(sessao)
            msg = (
                "Sinto muito que você esteja se sentindo assim. Vou fazer uma "
                "triagem rápida guiada pelo nosso sistema de IA. " + (kp[1] if kp else "")
            )
            return _resposta(sessao, msg, intencao=intencao)

        if intencao == "agendar_exame":
            sessao["estado"] = "agendamento"
            return _resposta(sessao, _RESP_EXAMES, intencao=intencao)

        if intencao == "duvida_pressao":
            sessao["estado"] = "duvida"
            return _resposta(
                sessao, _RESP_PRESSAO,
                sugestoes=["Quero agendar uma consulta", "Estou com dor no peito"],
                intencao=intencao,
            )

        if intencao == "duvida_sintomas":
            sessao["estado"] = "duvida"
            return _resposta(
                sessao, _RESP_DUVIDA_SINTOMAS,
                sugestoes=["Sim, estou sentindo", "Não, é só uma dúvida"],
                intencao=intencao,
            )

        if intencao == "encerrar":
            sessao["estado"] = "encerrado"
            return _resposta(sessao, "Tudo bem! Estou aqui se precisar. Cuide-se! 💙", intencao=intencao)

        if intencao == "saudacao":
            sessao["estado"] = "saudacao"
            return _resposta(sessao, _RESP_WELCOME, sugestoes=_SUGESTOES_PADRAO, intencao=intencao)

        # fallback (anything_else do Watson)
        sessao["estado"] = "saudacao"
        return _resposta(sessao, _RESP_FALLBACK, sugestoes=_SUGESTOES_PADRAO, intencao="fallback")

    if estado == "coletando_sintomas":
        atual = _proxima_pergunta(sessao)
        if atual is not None:
            erro = _processar_resposta_triagem(sessao, atual[0], mensagem)
            if erro:
                return _resposta(sessao, erro)

        prox = _proxima_pergunta(sessao)
        if prox is not None:
            return _resposta(sessao, prox[1])

        # coleta completa — dispara o pipeline multiagente (Fase 6)
        sessao["estado"] = "triando"
        triagem = _executar_triagem(sessao)
        repository.salvar_predicao(sessao.get("paciente_id"), triagem.model_dump(mode="json"))
        sessao["estado"] = "encaminhado"
        sessao["coleta"] = {}

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
                "Seus sintomas pedem monitorização. Sugiro agendar consulta nas "
                "próximas 48h. Posso te ajudar a marcar agora?"
            )
        else:
            base = (
                "Seus sintomas, no momento, parecem de baixo risco. "
                "Mas vale agendar uma avaliação preventiva. Quer que eu reserve um horário?"
            )
        base += f"\n\n(Probabilidade calculada: {triagem.probabilidade:.0%} | Classificação: {triagem.classificacao})"
        return _resposta(sessao, base, sugestoes=["Marcar consulta", "Voltar ao início"], triagem=triagem)

    if estado == "agendamento":
        txt = _normalizar(mensagem)
        if any(p in txt for p in ("amanha", "amanhã", "quinta", "10", "14", "09")):
            msg = (
                "Pronto! Seu horário está pré-reservado. A equipe entrará em contato "
                "para confirmar. Mais alguma coisa?"
            )
            sessao["estado"] = "saudacao"
        else:
            msg = "Não entendi o horário. Pode escolher entre amanhã 10h, amanhã 14h ou quinta 09h?"
        return _resposta(sessao, msg)

    if estado == "encaminhado":
        txt = _normalizar(mensagem)
        if "marc" in txt or "consulta" in txt or "agend" in txt:
            sessao["estado"] = "agendamento"
            msg = "Claro! Tenho amanhã 10h, amanhã 14h ou quinta 09h. Qual prefere?"
        else:
            sessao["estado"] = "saudacao"
            msg = "Sem problema. Posso te ajudar com mais alguma coisa?"
        return _resposta(sessao, msg)

    # fallback geral
    sessao["estado"] = "saudacao"
    return _resposta(sessao, _RESP_FALLBACK, sugestoes=_SUGESTOES_PADRAO)
