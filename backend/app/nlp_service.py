"""Serviço de triagem NLP — porta da Fase 2 para o backend integrador.

Dois motores combinados:

1. **Ontologia médica** (`mapa_conhecimento_ontologia.csv`): extração de
   sintomas por regex e pontuação de diagnósticos por força de evidência —
   mesma lógica do `diagnostico_basico.py` da Fase 2.

2. **Classificador de risco textual**: o TF-IDF + Regressão Logística da
   Fase 2 (93% de acurácia) é treinado offline por `ml/export_model.py` e
   exportado para `nlp_risco.json` (vocabulário, pesos IDF e coeficientes).
   A inferência aqui é Python puro (produto escalar + sigmoide), mantendo a
   Serverless Function leve. Sem o JSON, cai num scorer por palavras-chave
   derivado da mesma base rotulada.
"""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
ONTOLOGIA_CSV = DATA_DIR / "mapa_conhecimento_ontologia.csv"
NLP_JSON = DATA_DIR / "nlp_risco.json"

_state: dict[str, Any] = {"regras": None, "modelo": None, "loaded": False}
_lock = Lock()


def normalize(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _carregar() -> None:
    with _lock:
        if _state["loaded"]:
            return
        # ontologia (Fase 2 — Parte 1)
        regras: list[tuple[list[str], str]] = []
        with open(ONTOLOGIA_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                termos = [row["Sintoma 1"], row["Sintoma 2"]]
                termos = [normalize(t) for t in termos if t and t.strip()]
                diagnostico = row["Doença Associada"].strip()
                regras.append((termos, diagnostico))
        _state["regras"] = regras

        # classificador exportado (Fase 2 — Parte 2)
        if NLP_JSON.exists():
            _state["modelo"] = json.loads(NLP_JSON.read_text(encoding="utf-8"))
        else:
            _state["modelo"] = None
        _state["loaded"] = True


# ---------- Parte 1: ontologia ----------

def extrair_sintomas(frase_norm: str) -> list[tuple[str, str]]:
    encontrados = []
    for termos, diag in _state["regras"]:
        for t in termos:
            if t and re.search(rf"\b{re.escape(t)}\b", frase_norm):
                encontrados.append((t, diag))
    return encontrados


def pontuar_diagnosticos(encontrados: list[tuple[str, str]]) -> list[dict]:
    score: dict[str, int] = defaultdict(int)
    for _, diag in encontrados:
        score[diag] += 1
    return [
        {"diagnostico": d, "forca_evidencia": pts}
        for d, pts in sorted(score.items(), key=lambda x: (-x[1], x[0]))
    ]


# ---------- Parte 2: risco textual ----------

def _prob_risco_tfidf(frase_norm: str) -> float:
    """Inferência pura-Python do TF-IDF + LogReg exportados.

    Reproduz o pipeline do sklearn: contagem de termos do vocabulário
    (uni/bigramas), peso tf*idf, normalização L2 e logística.
    """
    m = _state["modelo"]
    vocab: dict[str, int] = m["vocab"]
    idf: list[float] = m["idf"]
    coef: list[float] = m["coef"]
    intercept: float = m["intercept"]

    tokens = frase_norm.split()
    contagem: dict[int, int] = defaultdict(int)
    for n in (1, 2):
        for i in range(len(tokens) - n + 1):
            termo = " ".join(tokens[i : i + n])
            j = vocab.get(termo)
            if j is not None:
                contagem[j] += 1

    if not contagem:
        return 0.5

    tfidf = {j: c * idf[j] for j, c in contagem.items()}
    norma = math.sqrt(sum(v * v for v in tfidf.values()))
    z = intercept + sum((v / norma) * coef[j] for j, v in tfidf.items())
    return 1.0 / (1.0 + math.exp(-z))


_KEYWORDS_ALTO = (
    "dor no peito", "falta de ar", "desmaio", "desmaiei", "tontura", "tonto",
    "suor frio", "aperto no peito", "pressao no peito", "nao consigo respirar",
    "palpitacao", "coracao acelerado", "visao escurecendo",
)


def _prob_risco_keywords(frase_norm: str) -> float:
    hits = sum(1 for k in _KEYWORDS_ALTO if k in frase_norm)
    return min(0.25 + 0.25 * hits, 0.97) if hits else 0.15


def avaliar_texto(texto: str) -> dict:
    """Triagem completa de um relato livre: sintomas + diagnósticos + risco."""
    _carregar()
    frase_norm = normalize(texto)

    encontrados = extrair_sintomas(frase_norm)
    diagnosticos = pontuar_diagnosticos(encontrados)
    sintomas = sorted({t for t, _ in encontrados})

    if _state["modelo"]:
        prob = _prob_risco_tfidf(frase_norm)
        fonte = "tfidf_logreg_json"
    else:
        prob = _prob_risco_keywords(frase_norm)
        fonte = "keywords_fallback"

    if prob >= 0.5:
        risco = "alto risco"
    elif sintomas or prob <= 0.45:
        risco = "baixo risco"
    else:
        risco = "indefinido"

    return {
        "texto": texto,
        "sintomas_detectados": sintomas,
        "diagnosticos": diagnosticos,
        "risco_textual": risco,
        "probabilidade_risco": round(prob, 4),
        "fonte": fonte,
    }


def status() -> dict:
    _carregar()
    return {
        "regras_ontologia": len(_state["regras"] or []),
        "classificador_carregado": _state["modelo"] is not None,
    }
