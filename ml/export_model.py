"""Exporta os modelos de ML para JSON de inferência pura-Python.

Por que: o backend roda como Serverless Function na Vercel, e empacotar
scikit-learn + scipy + numpy estouraria o tamanho/tempo de cold start da
function. Este script roda OFFLINE (no ambiente de desenvolvimento) e:

1. Converte a Random Forest da Fase 6 (`ml/model.joblib`) em
   `backend/app/data/rf_model.json` — arrays das árvores (feature, threshold,
   filhos, contagens por folha) que o `app/ml_service.py` percorre em
   Python puro, reproduzindo `predict_proba`.

2. Treina o classificador de risco textual da Fase 2 (TF-IDF + Regressão
   Logística sobre `frases_risco.csv`) e exporta vocabulário, IDF e
   coeficientes em `backend/app/data/nlp_risco.json` para o
   `app/nlp_service.py` (produto escalar + sigmoide).

Uso:
    pip install scikit-learn joblib numpy pandas
    python ml/export_model.py
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
MODEL_JOBLIB = ROOT / "ml" / "model.joblib"
METRICS_JSON = ROOT / "ml" / "metrics.json"
DATA_DIR = ROOT / "backend" / "app" / "data"
RF_OUT = DATA_DIR / "rf_model.json"
NLP_OUT = DATA_DIR / "nlp_risco.json"
FRASES_CSV = DATA_DIR / "frases_risco.csv"


# ---------- 1. Random Forest (Fase 6) → JSON ----------

def exportar_random_forest() -> None:
    payload = joblib.load(MODEL_JOBLIB)
    model = payload["model"]
    metrics = payload.get("metrics")
    if metrics is None and METRICS_JSON.exists():
        metrics = json.loads(METRICS_JSON.read_text(encoding="utf-8"))

    arvores = []
    for est in model.estimators_:
        t = est.tree_
        arvores.append(
            {
                "feature": t.feature.tolist(),
                "threshold": [round(float(x), 6) for x in t.threshold],
                "left": t.children_left.tolist(),
                "right": t.children_right.tolist(),
                "value": [[float(v[0][0]), float(v[0][1])] for v in t.value],
            }
        )

    out = {"n_arvores": len(arvores), "arvores": arvores, "metrics": metrics}
    RF_OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    tam = RF_OUT.stat().st_size / 1024 / 1024
    print(f"[ok] Random Forest exportada: {len(arvores)} arvores -> {RF_OUT} ({tam:.1f} MB)")

    # confere paridade predict_proba × inferência pura-Python
    sys.path.insert(0, str(ROOT / "backend"))
    from app import ml_service

    exemplo = {
        "idade": 68, "frequencia_cardiaca": 122, "spo2": 91.5,
        "pressao_sistolica": 168, "pressao_diastolica": 102, "glicemia": 215,
        "dor_toracica": True, "historico_arritmia": True, "historico_infarto": False,
        "tabagista": True, "diabetico": True,
        "carga_sistema": 0.72, "recursos_disponiveis": 0.35,
    }
    x = np.array([[float(ml_service._coerce(exemplo[c])) for c in ml_service.FEATURE_ORDER]])
    p_sklearn = float(model.predict_proba(x)[0, 1])
    ml_service._state["loaded"] = False  # força recarga do JSON novo
    p_puro = ml_service.prever(exemplo)["probabilidade"]
    delta = abs(p_sklearn - p_puro)
    print(f"[ok] paridade predict_proba: sklearn={p_sklearn:.6f} puro={p_puro:.6f} (delta={delta:.2e})")
    assert delta < 1e-9, "inferência pura-Python divergiu do sklearn!"


# ---------- 2. Classificador de risco textual (Fase 2) → JSON ----------

def _normalize(s: str) -> str:
    """Idêntica à `nlp_service.normalize` — precisa casar com a inferência."""
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def exportar_nlp() -> None:
    df = pd.read_csv(FRASES_CSV)
    X_txt = [_normalize(t) for t in df["frase"]]
    y = (df["situacao"].str.strip() == "alto risco").astype(int)

    # tokenizer=split casa com a inferência pura (n-gramas sobre tokens de espaço)
    vec = TfidfVectorizer(ngram_range=(1, 2), tokenizer=str.split, lowercase=False,
                          token_pattern=None)
    X = vec.fit_transform(X_txt)

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(Xtr, ytr)
    acc = accuracy_score(yte, clf.predict(Xte))

    # re-treina com toda a base para o artefato final (base pequena: 99 frases)
    clf_full = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf_full.fit(X, y)

    out = {
        "vocab": {t: int(i) for t, i in vec.vocabulary_.items()},
        "idf": [round(float(v), 6) for v in vec.idf_],
        "coef": [round(float(v), 6) for v in clf_full.coef_[0]],
        "intercept": round(float(clf_full.intercept_[0]), 6),
        "acuracia_holdout": round(float(acc), 4),
        "n_amostras": int(len(df)),
    }
    NLP_OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] Classificador NLP exportado -> {NLP_OUT} (acuracia holdout={acc:.1%})")

    # paridade sklearn × inferência pura
    sys.path.insert(0, str(ROOT / "backend"))
    from app import nlp_service

    nlp_service._state["loaded"] = False
    frase = "sinto dor no peito e falta de ar"
    p_sk = float(clf_full.predict_proba(vec.transform([_normalize(frase)]))[0, 1])
    p_puro = nlp_service.avaliar_texto(frase)["probabilidade_risco"]
    print(f"[ok] paridade NLP: sklearn={p_sk:.4f} puro={p_puro:.4f}")
    assert abs(p_sk - p_puro) < 1e-3, "inferência NLP pura divergiu do sklearn!"


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    exportar_random_forest()
    exportar_nlp()
    print("[done] artefatos prontos para o deploy serverless.")
