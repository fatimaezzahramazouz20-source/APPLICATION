# -*- coding: utf-8 -*-
"""Génère le jeu d'exemple : `sample/exemple_bilan.xlsx`.

PME de distribution sur trois exercices (2023-2025) avec des écarts
volontaires destinés à déclencher des anomalies (stocks en hausse alors que
l'activité recule, endettement, délais fournisseurs, renouvellement du parc).

Usage :  python sample/generer_exemple.py
"""

from __future__ import annotations

import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

YEARS = [2023, 2024, 2025]

# ---------------------------------------------------------------------------
# Données (en euros)
# ---------------------------------------------------------------------------

BILAN = [
    ("SECTION", "ACTIF", None, None, None),
    ("Immobilisations en cours", "L", 20_000, 40_000, 25_000),
    ("Immobilisations incorporelles", "L", 15_000, 22_000, 26_000),
    ("Immobilisations corporelles", "L", 180_000, 205_000, 228_000),
    ("Immobilisations financières", "L", 10_000, 12_000, 12_000),
    ("Total immobilisations", "S", 225_000, 279_000, 291_000),
    ("Stocks et en-cours", "L", 120_000, 155_000, 205_000),
    ("Créances clients", "L", 95_000, 118_000, 152_000),
    ("Autres créances", "L", 18_000, 22_000, 30_000),
    ("dont créances sur l'État", "I", 8_000, 10_000, 14_000),
    ("Charges à payer", "L", 6_000, 8_000, 9_000),
    ("Trésorerie - Actif", "L", 45_000, 38_000, 35_000),
    ("Total actif", "T", 509_000, 620_000, 722_000),
    ("SECTION", "PASSIF", None, None, None),
    ("Capital social", "L", 80_000, 80_000, 80_000),
    ("Réserve légale", "L", 12_000, 14_000, 15_000),
    ("Autres réserves", "L", 10_000, 15_000, 15_000),
    ("Report à nouveau", "L", 5_000, 21_000, 83_000),
    ("Résultat de l'exercice", "L", 88_000, 118_000, 46_000),
    ("Total capitaux propres", "S", 195_000, 248_000, 239_000),
    ("Emprunts auprès des établissements de crédit", "L", 150_000, 190_000,
     230_000),
    ("Provisions pour risques et charges", "L", 12_000, 14_000, 15_000),
    ("Dettes fournisseurs et comptes rattachés", "L", 105_000, 118_000,
     180_000),
    ("Dettes fiscales et sociales", "L", 38_000, 42_000, 46_000),
    ("Autres dettes", "L", 9_000, 8_000, 10_000),
    ("Trésorerie - Passif", "L", None, None, 2_000),
    ("Total passif", "T", 509_000, 620_000, 722_000),
]

CPC = [
    ("SECTION", "PRODUITS", None, None, None),
    ("Ventes de marchandises", "L", 850_000, 970_000, 905_000),
    ("Prestations de services", "L", 250_000, 280_000, 275_000),
    ("Autres produits d'exploitation", "L", 18_000, 20_000, 22_000),
    ("Produits financiers", "L", 2_000, 2_000, 1_000),
    ("Total produits", "T", 1_120_000, 1_272_000, 1_203_000),
    ("SECTION", "CHARGES", None, None, None),
    ("Achats de marchandises", "L", 660_000, 742_000, 705_000),
    ("Variation des stocks (accroissement en négatif)", "L", -25_000,
     -35_000, -50_000),
    ("Autres charges d'exploitation", "L", 105_000, 118_000, 132_000),
    ("Charges de personnel", "L", 235_000, 262_000, 296_000),
    ("Dotations aux amortissements", "L", 36_000, 40_000, 44_000),
    ("Charges d'intérêts", "L", 14_000, 19_000, 24_000),
    ("Impôt sur les bénéfices", "L", 7_000, 8_000, 6_000),
    ("Total charges", "T", 1_032_000, 1_154_000, 1_157_000),
    ("SECTION", "RÉSULTAT", None, None, None),
    ("Résultat net de l'exercice", "L", 88_000, 118_000, 46_000),
]

SOCIETE = "SARL EXEMPLE DISTRIBUTION"


def _write_sheet(ws, header: str, rows: list[tuple]) -> None:
    bold = Font(bold=True)
    white_bold = Font(bold=True, color="FFFFFF")
    fond_titre = PatternFill("solid", fgColor="1F4E78")
    fond_section = PatternFill("solid", fgColor="DDEBF7")

    ws.cell(row=1, column=1, value=header).font = white_bold
    ws.cell(row=1, column=1).fill = fond_titre
    for j, y in enumerate(YEARS, start=2):
        cell = ws.cell(row=1, column=j, value=y)
        cell.font = white_bold
        cell.fill = fond_titre
        cell.alignment = Alignment(horizontal="center")
    ws.cell(row=2, column=1, value=SOCIETE).font = bold
    r = 3
    for label, kind, *vals in rows:
        if kind == "SECTION":
            cell = ws.cell(row=r, column=1, value=label)
            cell.font = bold
            cell.fill = fond_section
        else:
            ws.cell(row=r, column=1, value=label)
            if kind in {"S", "T"}:
                ws.cell(row=r, column=1).font = bold
            for j, v in enumerate(vals, start=2):
                if v is not None:
                    ws.cell(row=r, column=j, value=v)
        r += 1
    ws.column_dimensions["A"].width = 52
    for j in range(2, 2 + len(YEARS)):
        ws.column_dimensions[get_column_letter(j)].width = 15
    ws.freeze_panes = "B3"


def generer(path: str | None = None) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Bilan"
    _write_sheet(ws, "Poste du bilan (PCG)", BILAN)
    ws2 = wb.create_sheet("CPC")
    _write_sheet(ws2, "Compte de produits et charges (PCG)", CPC)
    path = path or os.path.join(os.path.dirname(__file__), "exemple_bilan.xlsx")
    wb.save(path)
    _verifier()
    return path


def _verifier() -> None:
    """Contrôle d'équilibrage et de cohérence du jeu d'exemple."""
    for idx, y in enumerate(YEARS, start=2):
        ta = next(v[idx - 2] for lab, k, *v in BILAN if lab == "Total actif")
        tp = next(v[idx - 2] for lab, k, *v in BILAN if lab == "Total passif")
        assert ta == tp, f"bilan non équilibré en {y}"
        prod = next(v[idx - 2] for lab, k, *v in CPC if lab == "Total produits")
        chg = next(v[idx - 2] for lab, k, *v in CPC if lab == "Total charges")
        rn = next(v[idx - 2] for lab, k, *v in CPC
                  if lab == "Résultat net de l'exercice")
        rn_bilan = next(v[idx - 2] for lab, k, *v in BILAN
                        if lab == "Résultat de l'exercice")
        assert prod - chg == rn == rn_bilan, f"résultat incohérent en {y}"


if __name__ == "__main__":
    print("Généré :", generer())
