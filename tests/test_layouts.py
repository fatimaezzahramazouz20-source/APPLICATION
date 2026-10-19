# -*- coding: utf-8 -*-
"""Vérifie la lecture de mises en page réelles :
- bilan Actif à gauche / Passif à droite sur une même feuille ;
- bloc de présentation (en-tête long) + colonne de numéros de comptes.
"""
from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

from core import parser  # noqa: E402


def _xlsx(sheets: dict[str, list[list]]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(w, sheet_name=name, header=False,
                                        index=False)
    return buf.getvalue()


# --- Cas 1 : bilan Actif (gauche) / Passif (droite) côte à côte ------------
lignes = [
    [None, None, 2024, 2025, None, None, 2024, 2025],
    ["ACTIF", None, None, None, "PASSIF", None, None, None],
    ["Immobilisations corporelles", None, 100000, 120000, "Capital social",
     None, 50000, 50000],
    ["Stocks", None, 30000, 35000, "Réserves", None, 20000, 25000],
    ["Créances clients", None, 40000, 45000, "Résultat de l'exercice", None,
     10000, 12000],
    ["Trésorerie", None, 15000, 10000, "Emprunts", None, 60000, 50000],
    ["Dettes fournisseurs", None, 25000, 30000, "Dettes fournisseurs", None,
     20000, 22000],
]
CPC = [
    [None, None, 2024, 2025],
    ["PRODUITS", None, None, None],
    ["Ventes de marchandises", None, 200000, 220000],
    ["CHARGES", None, None, None],
    ["Achats de marchandises", None, 120000, 130000],
    ["Charges de personnel", None, 40000, 45000],
    ["Dotations aux amortissements", None, 10000, 11000],
    ["Résultat de l'exercice", None, 10000, 12000],
]
CPC_2324 = [
    [None, None, 2023, 2024],
    ["PRODUITS", None, None, None],
    ["Ventes de marchandises", None, 180000, 200000],
    ["CHARGES", None, None, None],
    ["Achats de marchandises", None, 110000, 120000],
    ["Charges de personnel", None, 38000, 40000],
    ["Dotations aux amortissements", None, 9000, 10000],
    ["Résultat de l'exercice", None, 9000, 10000],
]



data = parser.parse_files(
    [("bilan_cote_a_cote.xlsx",
      _xlsx({"Bilan": lignes, "CPC": CPC}))], 2025)
assert data["years"] == [2024, 2025], data["years"]
b24 = data["bilan"][2024]
b25 = data["bilan"][2025]
print("Cas 1 - années :", data["years"])
print("Cas 1 - actif 2025 :", b25.get("total_actif"),
      "| passif 2025 :", b25.get("total_passif"))
print("Cas 1 - capital 2025 :", b25.get("capital"),
      "| emprunts LT :", b25.get("dettes_fin_lt"))
assert b25.get("imm_corp") == 120000
assert b25.get("capital") == 50000
assert b25.get("stocks") == 35000
assert b25.get("dettes_fin_lt") == 50000
assert b25.get("total_actif") == sum(
    v for k, v in b25.items() if k in
    ("imm_corp", "stocks", "clients", "tresorerie_active"))
print("Cas 1 : OK (actif ET passif lus sur la même feuille)")

# --- Cas 2 : en-tête long + colonne de numéros de comptes ------------------
entete = [
    ["SARL DEMO", None, None, None],
    ["Bilan au 31/12/2024", None, None, None],
    [None, None, None, None],
    ["Compte", "Libellé", "2023", "2024"],
]
corps = [
    ["211000", "Immobilisations corporelles", 80000, 90000],
    ["300000", "Stocks de marchandises", 20000, 25000],
    ["411000", "Clients et comptes rattachés", 30000, 32000],
    ["512000", "Banque", 12000, 9000],
    ["101000", "Capital social", 60000, 60000],
    ["164000", "Emprunts auprès des établissements de crédit", 40000, 35000],
    ["401000", "Fournisseurs", 15000, 18000],
]
data2 = parser.parse_files(
    [("bilan_entete_long.xlsx",
      _xlsx({"Bilan": entete + corps, "CPC": CPC_2324}))], 2024)
print("Cas 2 - années :", data2["years"],
      "| diagnostic :", data2["diagnostic"][0]["colonnes_libelles"])
assert data2["years"] == [2023, 2024], data2["years"]
assert data2["bilan"][2024].get("imm_corp") == 90000
assert data2["bilan"][2024].get("capital") == 60000
assert data2["bilan"][2024].get("tresorerie_active") == 9000
print("Cas 2 : OK (en-tête long + colonne de comptes ignorée)")

print("\n✅ Mises en page réelles : OK")
