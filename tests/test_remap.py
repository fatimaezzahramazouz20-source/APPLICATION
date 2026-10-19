# -*- coding: utf-8 -*-
"""Cas concrets de rattachement des libellés :
- rubrique PASSIF non déclarée (le côté reste « Actif ») → repli automatique ;
- ligne d'agrégat « Capitaux propres » au lieu du détail ;
- recollement manuel (`overrides`) posé par l'utilisateur.
"""
from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

from core import parser, pcg  # noqa: E402


def _xlsx(sheets: dict[str, list[list]]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(w, sheet_name=name, header=False,
                                        index=False)
    return buf.getvalue()


CPC = [
    [None, 2024],
    ["PRODUITS", None],
    ["Ventes de marchandises", 200000],
    ["CHARGES", None],
    ["Achats de marchandises", 120000],
    ["Charges de personnel", 45000],
    ["Dotations aux amortissements", 11000],
    ["Résultat de l'exercice", 12000],
]

# --- 1) Pas d'en-tête « PASSIF » : le côté reste « Actif » ------------------
sans_passif = [
    [None, 2024],
    ["ACTIF", None],
    ["Immobilisations corporelles", 120000],
    ["Stocks", 35000],
    ["Créances clients", 45000],
    ["Trésorerie", 10000],
    ["Capital social", 50000],
    ["Réserves", 25000],
    ["Résultat de l'exercice", 12000],
    ["Emprunts", 50000],
    ["Dettes fournisseurs", 30000],
]
d = parser.parse_files([("sans_passif.xlsx",
                         _xlsx({"Bilan": sans_passif, "CPC": CPC}))], 2024)
b = d["bilan"][2024]
print("1) Passif non déclaré : capital =", b.get("capital"),
      "| réserves =", b.get("reserves"), "| emprunts =",
      b.get("dettes_fin_lt"), "| fournisseurs =", b.get("dettes_fournisseurs"))
assert b.get("capital") == 50000, b
assert b.get("reserves") == 25000, b
assert b.get("resultat") == 12000, b
assert b.get("dettes_fin_lt") == 50000, b
assert b.get("dettes_fournisseurs") == 30000, b
assert b.get("imm_corp") == 120000, b
assert d["unmapped"].empty, d["unmapped"]
print("1) OK — toutes les lignes rattachées malgré l'absence de rubrique PASSIF")

# --- 2) Ligne d'agrégat « Capitaux propres » (pas de détail capital/réserves)
aggregate = [
    [None, 2024],
    ["ACTIF", None],
    ["Immobilisations corporelles", 120000],
    ["Stocks", 35000],
    ["Créances clients", 45000],
    ["Trésorerie", 10000],
    ["PASSIF", None],
    ["Capitaux propres", 60000],
    ["Emprunts", 60000],
    ["Dettes fournisseurs", 50000],
]
d2 = parser.parse_files([("aggregate.xlsx",
                          _xlsx({"Bilan": aggregate, "CPC": CPC}))], 2024)
b2 = d2["bilan"][2024]
print("2) Capitaux propres déclarés :", b2.get("capitaux_propres"),
      "| ligne reconnue :", b2.get("capitaux_propres_declare"))
assert b2.get("capitaux_propres_declare") == 60000, b2
assert b2.get("capitaux_propres") == 60000, b2
assert "capitaux propre" not in [
    pcg.norm(x) for x in d2["unmapped"].get("Libellé", [])]
print("2) OK — l'agrégat « Capitaux propres » alimente les ratios")

# --- 3) Recollement manuel (overrides) -------------------------------------
ovr = {
    pcg.norm("Trésorerie"): "imm_fin",              # catégorie forcée
    pcg.norm("Réserves"): "__ignorer__",            # ligne exclue
}
d3 = parser.parse_files(
    [("sans_passif.xlsx", _xlsx({"Bilan": sans_passif, "CPC": CPC}))],
    2024, ovr)
b3 = d3["bilan"][2024]
print("3) Recollement : imm_fin =", b3.get("imm_fin"),
      "| réserves présentes :", "reserves" in b3)
assert b3.get("imm_fin") == 10000, b3
assert "reserves" not in b3, b3
assert b3.get("capital") == 50000, b3
assert d3["unmapped"].empty, d3["unmapped"]
print("3) OK — choix manuel appliqué (recatégorisation + exclusion)")

print("\n✅ Recollement des libellés : OK")
