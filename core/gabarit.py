# -*- coding: utf-8 -*-
"""Génération du gabarit Excel d'import (bilan PCG + CPC)."""

from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

_TITRE = Font(bold=True, color="FFFFFF")
_FOND_TITRE = PatternFill("solid", fgColor="1F4E78")
_FOND_SECTION = PatternFill("solid", fgColor="DDEBF7")
_GRAS = Font(bold=True)

_BILAN = [
    ("SECTION", "ACTIF"),
    ("immobilisation en cours", "A"),
    ("Immobilisations incorporelles", "A"),
    ("Immobilisations corporelles", "A"),
    ("Immobilisations financières", "A"),
    ("Total immobilisations", "S"),
    ("Stocks et en-cours", "A"),
    ("Créances clients", "A"),
    ("Autres créances", "A"),
    ("dont créances sur l'État", "I"),
    ("Charges à payer", "A"),
    ("Trésorerie - Actif", "A"),
    ("Total actif", "T"),
    ("SECTION", "PASSIF"),
    ("Capital social", "A"),
    ("Réserve légale", "A"),
    ("Autres réserves", "A"),
    ("Report à nouveau", "A"),
    ("Résultat de l'exercice", "A"),
    ("Subventions d'investissement", "A"),
    ("Total capitaux propres et assimilés", "S"),
    ("Emprunts auprès des établissements de crédit", "A"),
    ("Provisions pour risques et charges", "A"),
    ("Produits à recevoir", "A"),
    ("Dettes à plus d'un an", "S"),
    ("Dettes fournisseurs et comptes rattachés", "A"),
    ("Dettes fiscales et sociales", "A"),
    ("Autres dettes", "A"),
    ("Trésorerie - Passif", "A"),
    ("Total passif", "T"),
]

_CPC = [
    ("SECTION", "PRODUITS"),
    ("Ventes de marchandises", "A"),
    ("Prestations de services", "A"),
    ("Production stockée / déstockée", "A"),
    ("Autres produits d'exploitation", "A"),
    ("Subventions d'exploitation", "A"),
    ("Produits financiers", "A"),
    ("Produits exceptionnels", "A"),
    ("Total produits", "T"),
    ("SECTION", "CHARGES"),
    ("Achats de marchandises", "A"),
    ("Achats de matières premières", "A"),
    ("Variation des stocks (accroissement en négatif)", "A"),
    ("Autres charges d'exploitation", "A"),
    ("Charges de personnel", "A"),
    ("Dotations aux amortissements et provisions", "A"),
    ("Charges d'intérêts", "A"),
    ("Impôt sur les bénéfices", "A"),
    ("Charges exceptionnelles", "A"),
    ("Total charges", "T"),
    ("SECTION", "RÉSULTAT"),
    ("Résultat net de l'exercice", "A"),
]

_README = [
    "GABARIT D'IMPORT — BILAN ET COMPTE DE PRODUITS ET CHARGES (PCG)",
    "",
    "1. Remplissez les deux feuilles : « Bilan » et « CPC ».",
    "2. Une colonne par exercice ; l'intitulé de colonne doit être une année",
    "   (ex. « 2024 ») ou « N », « N-1 », « N-2 » avec l'année de référence",
    "   indiquée dans l'application.",
    "3. Montants en euros, sans symbole. Format accepté : 1234,5 ou 1 234,5",
    "   (négatif : -50 ou (50)).",
    "4. Vous pouvez ajouter/renommer des lignes : l'application rapproche les",
    "   libellés du plan comptable général (mots-clés + similarité).",
    "5. Les lignes « Total … » et les ventilations « dont … » sont ignorées",
    "   automatiquement (sauf Total actif / Total passif, contrôlés).",
    "6. Variation des stocks : laisser le signe du fichier (accroissement en",
    "   négatif dans les charges).",
    "7. Laisser vide les postes non concernés.",
]


def generer_gabarit(years: list[int] | None = None) -> bytes:
    """Construit le classeur de référence (bytes)."""
    if not years:
        years = [2023, 2024, 2025]
    wb = Workbook()

    # --- Feuille Bilan ----------------------------------------------------
    ws = wb.active
    ws.title = "Bilan"
    _fill_sheet(ws, "Poste du bilan (PCG)", years, _BILAN)

    # --- Feuille CPC ------------------------------------------------------
    ws2 = wb.create_sheet("CPC")
    _fill_sheet(ws2, "Poste du compte de produits et charges (PCG)",
                years, _CPC)

    # --- Lisez-moi --------------------------------------------------------
    ws3 = wb.create_sheet("Lisez-moi")
    for i, line in enumerate(_README, start=1):
        ws3.cell(row=i, column=1, value=line)
        if i == 1:
            ws3.cell(row=i, column=1).font = _GRAS
    ws3.column_dimensions["A"].width = 72

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fill_sheet(ws, header: str, years: list[int], rows: list[tuple]) -> None:
    ws.cell(row=1, column=1, value=header)
    ws.cell(row=1, column=1).font = _TITRE
    ws.cell(row=1, column=1).fill = _FOND_TITRE
    for j, y in enumerate(years, start=2):
        cell = ws.cell(row=1, column=j, value=y)
        cell.font = _TITRE
        cell.fill = _FOND_TITRE
        cell.alignment = Alignment(horizontal="center")
    r = 2
    for label, kind in rows:
        if kind == "SECTION":
            cell = ws.cell(row=r, column=1, value=label)
            cell.font = _GRAS
            cell.fill = _FOND_SECTION
        else:
            ws.cell(row=r, column=1, value=label)
            if kind in {"S", "T"}:
                ws.cell(row=r, column=1).font = _GRAS
        r += 1
    ws.column_dimensions["A"].width = 56
    for j in range(2, 2 + len(years)):
        ws.column_dimensions[get_column_letter(j)].width = 16
    ws.freeze_panes = "B2"
