"""Wrapper sobre o modelo treinado (Random Forest serializado em joblib).

Expõe `prever()` como interface única, usada pelo agente Analista de Risco.
Se o modelo treinado não estiver disponível, cai num scoring heurístico
calibrado contra a mesma função geradora — assim o sistema permanece
operacional em demonstrações sem o joblib presente.
"""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

import joblib
import numpy as np

MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "model.joblib"

FEATURE_ORDER = [
    "idade",
    "frequencia_cardiaca",
    "spo2",
    "pressao_sistolica",
    "pressao_diastolica",
    "glicemia",
    "dor_toracica",
    "historico_arritmia",
    "historico_infarto",
    "tabagista",
    "diabetico",
    "carga_sistema",
    "recursos_disponiveis",
]

_state: dict[str, Any] = {"model": None, "metrics": None, "loaded": False, "fallback": False}
_lock = Lock()


def _carregar() -> None:
    with _lock:
        if _state["loaded"]:
            return
        if MODEL_PATH.exists():
            payload = joblib.load(MODEL_PATH)
            _state["model"] = payload["model"]
            _state["metrics"] = payload.get("metrics")
            _state["fallback"] = False
        else:
            _state["model"] = None
            _state["metrics"] = None
            _state["fallback"] = True
        _state["loaded"] = True


def _vetorizar(sinais: dict) -> np.ndarray:
    return np.array([[float(_coerce(sinais[c])) for c in FEATURE_ORDER]])


def _coerce(v: Any) -> float:
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    return float(v)


def _heuristica(sinais: dict) -> float:
    """Logística calibrada contra `gerar_dataset` — fallback determinístico."""
    s = {k: _coerce(v) for k, v in sinais.items()}
    z = (
        -3.0
        + 0.055 * (s["idade"] - 50)
        + 0.045 * max(s["frequencia_cardiaca"] - 100, 0)
        + 0.055 * max(40 - s["frequencia_cardiaca"], 0)
        + 0.180 * max(94 - s["spo2"], 0)
        + 0.035 * max(s["pressao_sistolica"] - 150, 0)
        + 0.040 * max(90 - s["pressao_sistolica"], 0)
        + 0.018 * max(s["glicemia"] - 200, 0)
        + 0.022 * max(60 - s["glicemia"], 0)
        + 1.60 * s["dor_toracica"]
        + 1.10 * s["historico_arritmia"]
        + 1.30 * s["historico_infarto"]
        + 0.55 * s["tabagista"]
        + 0.65 * s["diabetico"]
        + 1.10 * s["carga_sistema"]
        - 0.85 * s["recursos_disponiveis"]
    )
    return 1.0 / (1.0 + np.exp(-z))


def prever(sinais: dict) -> dict:
    """Retorna probabilidade, classificação e fonte do score."""
    _carregar()
    if _state["model"] is not None:
        x = _vetorizar(sinais)
        prob = float(_state["model"].predict_proba(x)[0, 1])
        fonte = "random_forest"
    else:
        prob = float(_heuristica(sinais))
        fonte = "heuristica_fallback"

    classificacao = _classificar(prob)
    return {
        "probabilidade": prob,
        "classificacao": classificacao,
        "fonte": fonte,
    }


def _classificar(prob: float) -> str:
    if prob >= 0.70:
        return "CRITICO"
    if prob >= 0.40:
        return "ALTO"
    if prob >= 0.20:
        return "MODERADO"
    return "BAIXO"


def metrics() -> dict | None:
    _carregar()
    return _state["metrics"]


def status() -> dict:
    _carregar()
    return {
        "carregado": _state["model"] is not None,
        "fallback": _state["fallback"],
        "model_path": str(MODEL_PATH),
    }
