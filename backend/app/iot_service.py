"""Serviço IoT — recepção e avaliação dos sinais vindos do dispositivo MicroPython.

Fluxo (Fase 3 evoluída para a Fase 7):
  ESP32 (Wokwi, MicroPython) lê DHT22 + pulsos do botão (BPM), classifica
  localmente (edge) e envia HTTP POST para `/api/iot/leituras`. Aqui o servidor:

  1. Reavalia a leitura com regras clínicas (segunda opinião do edge);
  2. Persiste a leitura com a avaliação;
  3. Opcionalmente dispara o pipeline multiagente da Fase 6, convertendo a
     leitura em sinais vitais — fechando o ciclo Sensor → IA → recomendação.
"""

from __future__ import annotations

from typing import Any

from . import repository
from .agents.orchestrator import executar_pipeline

# Faixas clínicas de referência (mesmas premissas da Fase 3, ampliadas)
BPM_BAIXO_CRITICO = 40
BPM_BAIXO = 50
BPM_ALTO = 100
BPM_ALTO_CRITICO = 130
TEMP_PAC_FEBRE = 37.8
TEMP_PAC_FEBRE_ALTA = 39.0
TEMP_PAC_HIPOTERMIA = 35.0
TEMP_AMB_MIN, TEMP_AMB_MAX = 18.0, 30.0
UMID_MIN, UMID_MAX = 40.0, 60.0


def avaliar_leitura(leitura: dict) -> dict:
    """Aplica as regras de alerta no servidor e devolve a avaliação."""
    motivos: list[str] = []
    nivel = 0  # 0=NORMAL, 1=ATENCAO, 2=CRITICO

    bpm = leitura.get("bpm")
    if bpm is not None:
        if bpm <= BPM_BAIXO_CRITICO or bpm >= BPM_ALTO_CRITICO:
            motivos.append(f"BPM crítico ({bpm})")
            nivel = max(nivel, 2)
        elif bpm <= BPM_BAIXO or bpm >= BPM_ALTO:
            motivos.append(f"BPM fora da faixa ideal ({bpm})")
            nivel = max(nivel, 1)

    tpac = leitura.get("temperatura_pac")
    if tpac is not None:
        if tpac >= TEMP_PAC_FEBRE_ALTA or tpac <= TEMP_PAC_HIPOTERMIA:
            motivos.append(f"temperatura do paciente crítica ({tpac}°C)")
            nivel = max(nivel, 2)
        elif tpac >= TEMP_PAC_FEBRE:
            motivos.append(f"febre ({tpac}°C)")
            nivel = max(nivel, 1)

    tamb = leitura.get("temperatura_amb")
    if tamb is not None and not (TEMP_AMB_MIN <= tamb <= TEMP_AMB_MAX):
        motivos.append(f"temperatura ambiente fora da faixa de UTI ({tamb}°C)")
        nivel = max(nivel, 1)

    umid = leitura.get("umidade")
    if umid is not None and not (UMID_MIN <= umid <= UMID_MAX):
        motivos.append(f"umidade fora da faixa de UTI ({umid}%)")
        nivel = max(nivel, 1)

    status = ("NORMAL", "ATENCAO", "CRITICO")[nivel]
    return {
        "alerta": nivel >= 1,
        "motivos": motivos,
        "status_servidor": status,
    }


def _leitura_para_sinais(leitura: dict, paciente: dict | None) -> dict:
    """Converte a leitura IoT em `SinaisVitais` para o pipeline multiagente.

    Campos não medidos pelo dispositivo recebem valores de referência neutros;
    a idade vem do cadastro do paciente quando disponível.
    """
    return {
        "idade": (paciente or {}).get("idade", 60),
        "frequencia_cardiaca": leitura.get("bpm") or 78,
        "spo2": 97.0,
        "pressao_sistolica": 130,
        "pressao_diastolica": 85,
        "glicemia": 110,
        "dor_toracica": False,
        "historico_arritmia": False,
        "historico_infarto": False,
        "tabagista": False,
        "diabetico": False,
        "carga_sistema": 0.5,
        "recursos_disponiveis": 0.7,
    }


def processar_leitura(payload: dict) -> dict:
    """Avalia, persiste e (opcionalmente) prediz. Devolve a leitura gravada."""
    avaliacao: dict[str, Any] = avaliar_leitura(payload)

    paciente = None
    if payload.get("paciente_id"):
        paciente = repository.obter_paciente(payload["paciente_id"])

    # dispara o pipeline multiagente quando solicitado ou em leitura crítica
    if payload.get("executar_predicao") or avaliacao["status_servidor"] == "CRITICO":
        saida = executar_pipeline(paciente, _leitura_para_sinais(payload, paciente))
        repository.salvar_predicao(payload.get("paciente_id"), saida.model_dump(mode="json"))
        avaliacao["predicao"] = saida.model_dump(mode="json")

    return repository.salvar_leitura_iot(payload, avaliacao)
