# -*- coding: utf-8 -*-
"""Test : lecture via CSV (bilan.csv + cpc.csv) et colonnes « N / N-1 »."""

from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd  # noqa: E402

from core import parser  # noqa: E402
from sample.generer_exemple import BILAN, CPC, generer  # noqa: E402


def _df(rows, header_label):
    header = [header_label, "Exercice N-2", "Exercice N-1", "Exercice N"]
    data = [header]
    for label, kind, *vals in rows:
        data.append([label] + ["" if v is None else v for v in vals])
    return pd.DataFrame(data[1:], columns=data[0])


def main() -> None:
    # 1) Export CSV du jeu d'exemple (colonnes N / N-1 / N-2)
    generer()
    b_csv = _df(BILAN, "Poste du bilan").to_csv(
        index=False, sep=";").encode("utf-8")
    c_csv = _df(CPC, "Poste du CPC").to_csv(
        index=False, sep=";").encode("utf-8")

    data = parser.parse_files([("bilan.csv", b_csv), ("cpc.csv", c_csv)],
                              ref_year=2025)
    print("Années (colonnes N/N-1) :", data["years"])
    assert data["years"] == [2023, 2024, 2025], data["years"]
    assert abs(data["bilan"][2025]["total_actif"] - 722_000) < 1
    assert abs(data["cpc"][2025]["ca_net"] - 1_180_000) < 1
    assert len(data["unmapped"]) == 0, data["unmapped"]

    # 2) Même contenu en un seul CSV avec colonne « État »
    b = _df(BILAN, "Poste")
    c = _df(CPC, "Poste")
    b.insert(0, "État", "bilan")
    c.insert(0, "État", "cpc")
    single = pd.concat([b, c]).to_csv(index=False, sep=";").encode("utf-8")
    data2 = parser.parse_files([("etats.csv", single)], ref_year=2025)
    print("Années (CSV unique + colonne État) :", data2["years"])
    assert data2["years"] == [2023, 2024, 2025], data2["years"]
    assert abs(data2["bilan"][2025]["total_passif"] - 722_000) < 1
    assert abs(data2["cpc"][2025]["resultat_net_calc"] - 46_000) < 1

    # 3) Nombres au format français
    assert parser.parse_number("1 234,56") == 1234.56
    assert parser.parse_number("(500)") == -500
    assert parser.parse_number("-12,5") == -12.5
    assert parser.parse_number("1.234,5") == 1234.5
    assert parser.parse_number("") is None

    print("✅ CSV et formats numériques : OK")


if __name__ == "__main__":
    main()
