"""Motor preditivo da Fase 6, adaptado para serverless (Vercel).

Em vez de carregar `model.joblib` com scikit-learn (que tornaria a Serverless
Function pesada demais — sklearn+scipy+numpy somam >150 MB), a Random Forest
treinada na Fase 6 foi **exportada para JSON** (`ml/export_model.py`) e a
inferência é feita aqui em **Python puro**: caminhamento das árvores de decisão
e média das probabilidades das folhas — exatamente o que o
`RandomForestClassifier.predict_proba` faz.

Se o JSON não existir, cai num scoring heurístico calibrado contra a mesma
função geradora da base sintética — o sistema permanece operacional.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from threading import Lock
from typing import Any

RF_JSON_PATH = Path(__file__).resolve().parent / "data" / "rf_model.json"

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

_state: dict[str, Any] = {"arvores": None, "metrics": None, "loaded": False, "fallback": False}
_lock = Lock()


def _carregar() -> None:
    with _lock:
        if _state["loaded"]:
            return
        if RF_JSON_PATH.exists():
            payload = json.loads(RF_JSON_PATH.read_text(encoding="utf-8"))
            _state["arvores"] = payload["arvores"]
            _state["metrics"] = payload.get("metrics")
            _state["fallback"] = False
        else:
            _state["arvores"] = None
            _state["metrics"] = None
            _state["fallback"] = True
        _state["loaded"] = True


def _coerce(v: Any) -> float:
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    return float(v)


def _prob_arvore(arvore: dict, x: list[float]) -> float:
    """Caminha uma árvore exportada (arrays paralelos do sklearn) até a folha
    e devolve a proporção da classe positiva."""
    feature = arvore["feature"]
    threshold = arvore["threshold"]
    left = arvore["left"]
    right = arvore["right"]
    value = arvore["value"]  # [neg, pos] por nó

    no = 0
    while feature[no] >= 0:  # -2 = folha no sklearn
        if x[feature[no]] <= threshold[no]:
            no = left[no]
        else:
            no = right[no]
    neg, pos = value[no]
    total = neg + pos
    return pos / total if total > 0 else 0.0


def _prob_floresta(sinais: dict) -> float:
    x = [_coerce(sinais[c]) for c in FEATURE_ORDER]
    arvores = _state["arvores"]
    return sum(_prob_arvore(a, x) for a in arvores) / len(arvores)


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
    return 1.0 / (1.0 + math.exp(-z))


def prever(sinais: dict) -> dict:
    """Retorna probabilidade, classificação e fonte do score."""
    _carregar()
    if _state["arvores"]:
        prob = float(_prob_floresta(sinais))
        fonte = "random_forest_json"
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
        "carregado": _state["arvores"] is not None,
        "fallback": _state["fallback"],
        "model_path": str(RF_JSON_PATH),
        "n_arvores": len(_state["arvores"]) if _state["arvores"] else 0,
    }
