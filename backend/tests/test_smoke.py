"""Smoke tests do backend integrador — exercitam todos os motores de IA."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# banco isolado por execução de teste
os.environ["CARDIOIA_DB"] = str(Path(tempfile.mkdtemp()) / "test.sqlite3")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

SINAIS_CRITICOS = {
    "idade": 68, "frequencia_cardiaca": 122, "spo2": 91.5,
    "pressao_sistolica": 168, "pressao_diastolica": 102, "glicemia": 215,
    "dor_toracica": True, "historico_arritmia": True, "historico_infarto": False,
    "tabagista": True, "diabetico": True,
    "carga_sistema": 0.72, "recursos_disponiveis": 0.35,
}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["modelo"]["carregado"] is True  # RF exportada em JSON
    assert body["nlp"]["classificador_carregado"] is True


def test_pacientes_crud():
    r = client.post("/api/pacientes", json={"nome": "Teste Silva", "idade": 60, "sexo": "M"})
    assert r.status_code == 201
    pid = r.json()["id"]

    r = client.get(f"/api/pacientes/{pid}")
    assert r.status_code == 200
    assert r.json()["nome"] == "Teste Silva"

    r = client.delete(f"/api/pacientes/{pid}")
    assert r.status_code == 204


def test_predicao_multiagente():
    r = client.post("/api/predicoes", json={"nome": "Anônimo", "sinais": SINAIS_CRITICOS})
    assert r.status_code == 200
    body = r.json()
    assert body["classificacao"] in ("ALTO", "CRITICO")
    assert body["nivel_atencao"] in ("urgente", "emergencia")
    assert len(body["trace"]) > 5
    assert body["protocolos"]


def test_triagem_nlp():
    r = client.post("/api/triagem-nlp", json={"texto": "sinto dor no peito e falta de ar"})
    assert r.status_code == 200
    body = r.json()
    assert body["risco_textual"] == "alto risco"
    assert "dor no peito" in body["sintomas_detectados"]
    assert any("Infarto" in d["diagnostico"] for d in body["diagnosticos"])


def test_iot_fluxo():
    # leitura normal
    r = client.post("/api/iot/leituras", json={
        "device_id": "wokwi-esp32", "bpm": 75,
        "temperatura_amb": 24.5, "umidade": 50.0, "status_edge": "NORMAL",
    })
    assert r.status_code == 201
    assert r.json()["alerta"] is False

    # leitura crítica — deve gerar alerta e disparar o pipeline multiagente
    r = client.post("/api/iot/leituras", json={
        "device_id": "wokwi-esp32", "bpm": 145,
        "temperatura_amb": 24.5, "umidade": 50.0, "status_edge": "CRITICO",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["alerta"] is True
    assert body["avaliacao"]["status_servidor"] == "CRITICO"
    assert body["avaliacao"]["predicao"] is not None  # IA acionada automaticamente

    r = client.get("/api/iot/leituras?limite=10")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_chat_intents_fase5():
    # intent: duvida_sintomas (Watson da Fase 5)
    r = client.post("/api/chat", json={"mensagem": "Quais os sintomas de um infarto?"})
    assert r.status_code == 200
    body = r.json()
    assert body["intencao"] == "duvida_sintomas"
    sessao = body["sessao_id"]

    # intent: duvida_pressao
    r = client.post("/api/chat", json={"mensagem": "Minha pressão está 15 por 9", "sessao_id": sessao})
    assert r.json()["intencao"] == "duvida_pressao"

    # intent: agendar_exame
    r = client.post("/api/chat", json={"mensagem": "Quero agendar um ecocardiograma", "sessao_id": sessao})
    assert r.json()["intencao"] == "agendar_exame"
    assert r.json()["estado"] == "agendamento"


def test_chat_triagem_completa():
    """Fluxo fim-a-fim: emergência → coleta guiada → pipeline multiagente."""
    r = client.post("/api/chat", json={"mensagem": "Estou com muita dor no peito"})
    body = r.json()
    assert body["intencao"] == "emergencia_cardiaca"
    assert body["estado"] == "coletando_sintomas"
    sessao = body["sessao_id"]

    respostas = ["68", "120", "92", "170/100", "sim", "ambos"]
    for resp in respostas:
        r = client.post("/api/chat", json={"mensagem": resp, "sessao_id": sessao})
        body = r.json()
        if body["estado"] == "encaminhado":
            break

    assert body["estado"] == "encaminhado"
    assert body["triagem"] is not None
    assert body["triagem"]["classificacao"] in ("ALTO", "CRITICO")
