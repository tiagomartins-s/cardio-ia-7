"""
Geração de base de dados sintética para o sistema CardioIA.

A base simula registros clínicos e operacionais coletados em um
consultório/clínica de cardiologia. O alvo `pico_risco` representa a
probabilidade de o paciente apresentar um evento cardíaco crítico nas
próximas horas — combinando sinais clínicos (idade, FC, SpO2, PA,
glicemia, sintomas, histórico) com sinais operacionais do consultório
(carga_sistema, recursos_disponiveis), permitindo que o sistema
multiagente articule risco clínico e capacidade de resposta.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


COLUMNS = [
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


def _logistic(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def gerar_dataset(n: int = 4000, seed: int = 42) -> pd.DataFrame:
    """Gera um DataFrame com `n` registros sintéticos rotulados."""
    rng = np.random.default_rng(seed)

    idade = rng.integers(20, 90, size=n)
    fc = rng.normal(loc=78, scale=18, size=n).clip(35, 200).round().astype(int)
    spo2 = rng.normal(loc=97, scale=2.2, size=n).clip(80, 100).round(1)
    pas = rng.normal(loc=130, scale=22, size=n).clip(80, 220).round().astype(int)
    pad = (pas - rng.normal(loc=45, scale=10, size=n)).clip(50, 130).round().astype(int)
    glicemia = rng.normal(loc=110, scale=35, size=n).clip(50, 400).round().astype(int)

    dor_toracica = rng.binomial(1, 0.18, size=n)
    hist_arritmia = rng.binomial(1, 0.15, size=n)
    hist_infarto = rng.binomial(1, 0.10, size=n)
    tabagista = rng.binomial(1, 0.22, size=n)
    diabetico = rng.binomial(1, 0.18, size=n)

    carga_sistema = rng.beta(2.0, 5.0, size=n).round(3)          # 0..1 (ocupação)
    recursos_disponiveis = rng.beta(5.0, 2.0, size=n).round(3)   # 0..1 (capacidade)

    # combinação linear que define a probabilidade de pico de risco
    z = (
        -3.0
        + 0.055 * (idade - 50)
        + 0.045 * np.maximum(fc - 100, 0)
        + 0.055 * np.maximum(40 - fc, 0)
        + 0.180 * np.maximum(94 - spo2, 0)
        + 0.035 * np.maximum(pas - 150, 0)
        + 0.040 * np.maximum(90 - pas, 0)
        + 0.018 * np.maximum(glicemia - 200, 0)
        + 0.022 * np.maximum(60 - glicemia, 0)
        + 1.60 * dor_toracica
        + 1.10 * hist_arritmia
        + 1.30 * hist_infarto
        + 0.55 * tabagista
        + 0.65 * diabetico
        + 1.10 * carga_sistema
        - 0.85 * recursos_disponiveis
    )
    p = _logistic(z)
    pico_risco = (rng.uniform(size=n) < p).astype(int)

    df = pd.DataFrame(
        {
            "idade": idade,
            "frequencia_cardiaca": fc,
            "spo2": spo2,
            "pressao_sistolica": pas,
            "pressao_diastolica": pad,
            "glicemia": glicemia,
            "dor_toracica": dor_toracica,
            "historico_arritmia": hist_arritmia,
            "historico_infarto": hist_infarto,
            "tabagista": tabagista,
            "diabetico": diabetico,
            "carga_sistema": carga_sistema,
            "recursos_disponiveis": recursos_disponiveis,
            "pico_risco": pico_risco,
        }
    )
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dataset sintético CardioIA.")
    parser.add_argument("--n", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).parent / "data" / "pacientes.csv",
    )
    args = parser.parse_args()

    df = gerar_dataset(n=args.n, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Dataset gerado: {args.out} ({len(df)} linhas)")
    print(f"Distribuicao do alvo: {df['pico_risco'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
