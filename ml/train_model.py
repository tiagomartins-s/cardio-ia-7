"""
Treina e serializa o modelo preditivo de pico de risco cardíaco.
Saída: ml/model.joblib (consumido pelo backend FastAPI).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from generate_data import COLUMNS, gerar_dataset


HERE = Path(__file__).parent


def treinar(df: pd.DataFrame, seed: int = 42):
    X = df[COLUMNS].values
    y = df["pico_risco"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=4,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
        "feature_importance": dict(
            sorted(
                zip(COLUMNS, model.feature_importances_.tolist()),
                key=lambda kv: kv[1],
                reverse=True,
            )
        ),
    }
    return model, metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=HERE / "data" / "pacientes.csv")
    parser.add_argument("--out", type=Path, default=HERE / "model.joblib")
    parser.add_argument("--metrics", type=Path, default=HERE / "metrics.json")
    parser.add_argument("--n", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.data.exists():
        df = pd.read_csv(args.data)
        print(f"Dataset carregado: {args.data} ({len(df)} linhas)")
    else:
        print("Dataset nao encontrado; gerando sintetico...")
        df = gerar_dataset(n=args.n, seed=args.seed)
        args.data.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.data, index=False)

    model, metrics = treinar(df, seed=args.seed)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": model, "feature_order": COLUMNS, "metrics": metrics}
    joblib.dump(payload, args.out)

    args.metrics.write_text(json.dumps(metrics, indent=2, ensure_ascii=False))

    print(f"Modelo salvo em: {args.out}")
    print(f"Acuracia: {metrics['accuracy']:.4f}  |  AUC: {metrics['roc_auc']:.4f}")
    print("Matriz de confusao:")
    print(np.array(metrics["confusion_matrix"]))
    print("Top 5 features:")
    for k, v in list(metrics["feature_importance"].items())[:5]:
        print(f"  {k:<24} {v:.4f}")


if __name__ == "__main__":
    main()
