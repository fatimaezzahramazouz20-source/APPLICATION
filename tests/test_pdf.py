# -*- coding: utf-8 -*-
"""Vérifie la lecture des états financiers fournis en PDF.

Quatre mises en page sont simulées avec fpdf2 :

1. PDF sans filets (texte seul) : colonnes déduites des coordonnées ;
2. PDF à filets (tableau cadré) : cellules relues directement ;
3. PDF multipage : page de continuation sans ligne d'exercices ;
4. PDF « image » (aucun texte) : erreur explicite, fichier simplement signalé.
"""
from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402
from fpdf import FPDF  # noqa: E402

from core import parser, pdf as pdf_reader  # noqa: E402

LAB_X, LAB_W = 40, 190          # colonne des libellés : [40, 230]
AMT_X = [230, 310]              # colonnes de montants : [230,310] et [310,390]
AMT_W = 80
ROW_H = 14


def _amount(v: float) -> str:
    """« 180 000 » : les montants sont découpés en mots par le lecteur PDF."""
    return f"{v:,.0f}".replace(",", " ")


def _page(pdf, titre=None, years=None, rows=(), rules=False):
    pdf.add_page()
    pdf.set_font("helvetica", size=9)
    y = 60.0
    if titre:
        pdf.set_xy(LAB_X, y)
        pdf.cell(LAB_W + 2 * AMT_W, ROW_H, titre)
        y += ROW_H + 4
    corps = ([("", list(years))] if years else []) + list(rows)
    for label, vals in corps:
        if rules:
            pdf.rect(LAB_X, y, LAB_W, ROW_H)
            for x in AMT_X:
                pdf.rect(x, y, AMT_W, ROW_H)
        if label:
            pdf.set_xy(LAB_X, y)
            pdf.cell(LAB_W, ROW_H, label)
        for i, v in enumerate(vals):
            txt = v if isinstance(v, str) else _amount(v)
            pdf.set_xy(AMT_X[i], y)
            pdf.cell(AMT_W, ROW_H, txt, align="R")
        y += ROW_H


def _pdf(pages, **kw) -> bytes:
    pdf = FPDF(unit="pt", format="A4")
    pdf.set_auto_page_break(False)
    for p in pages:
        _page(pdf, **p)
    return bytes(pdf.output())


TITRE_ACTIF = "BILAN - ACTIF"
ACTIF_1 = [
    ("Immobilisations corporelles", [180000, 205000]),
    ("Stocks de marchandises", [120000, 155000]),
]
ACTIF_2 = [
    ("Clients et comptes rattaches", [95000, 118000]),
    ("Tresorerie", [45000, 38000]),
]
TITRE_PASSIF = "BILAN - PASSIF"
PASSIF = [
    ("Capital social", [80000, 80000]),
    ("Reserve legale", [20000, 25000]),
    ("Resultat de l'exercice", [30000, 46000]),
    ("Emprunts", [200000, 240000]),
    ("Dettes fournisseurs", [110000, 125000]),
]
CPC = [
    ("Ventes de marchandises", [500000, 560000]),
    ("Achats de marchandises", [300000, 330000]),
    ("Charges de personnel", [100000, 110000]),
    ("Dotations aux amortissements", [20000, 24000]),
    ("Resultat de l'exercice", [120000, 96000]),
]

PAGES = [
    {"titre": TITRE_ACTIF, "years": ["2023", "2024"],
     "rows": ACTIF_1 + ACTIF_2},
    {"titre": TITRE_PASSIF, "rows": PASSIF},                # continuation
    {"titre": "COMPTE DE RESULTAT", "years": ["2023", "2024"], "rows": CPC},
]


def _verifie(data, libelle):
    assert data["years"] == [2023, 2024], (libelle, data["years"])
    b24 = data["bilan"][2024]
    c24 = data["cpc"][2024]
    print(f"{libelle} - lecture :", data["diagnostic"][0]["colonnes_libelles"])
    assert b24.get("imm_corp") == 205000, b24.get("imm_corp")
    assert b24.get("stocks") == 155000, b24.get("stocks")
    assert b24.get("clients") == 118000, b24.get("clients")
    assert b24.get("tresorerie_active") == 38000, b24.get("tresorerie_active")
    assert b24.get("capital") == 80000, b24.get("capital")
    assert b24.get("reserve_legale") == 25000
    assert b24.get("resultat") == 46000, b24.get("resultat")
    assert b24.get("dettes_fin_lt") == 240000, b24.get("dettes_fin_lt")
    assert b24.get("dettes_fournisseurs") == 125000
    assert c24.get("ca") == 560000, c24.get("ca")
    assert c24.get("achats_marchandises") == 330000
    assert c24.get("charges_personnel") == 110000
    assert c24.get("resultat_net") == 96000, c24.get("resultat_net")


# --- Cas 1 : PDF sans filets (texte + coordonnées) --------------------------
data = parser.parse_files([("etats.pdf", _pdf(PAGES))], 2024)
_verifie(data, "Cas 1 (sans filets)")
assert not data.get("avertissements")
print("Cas 1 : OK")

# --- Cas 2 : PDF à filets (tableau cadré) -----------------------------------
PAGES_RULES = [dict(p, rules=True) for p in PAGES]
data2 = parser.parse_files([("etats_cadres.pdf", _pdf(PAGES_RULES))], 2024)
_verifie(data2, "Cas 2 (avec filets)")
print("Cas 2 : OK")

# --- Cas 3 : page de continuation isolée ------------------------------------
suite = [
    {"titre": TITRE_ACTIF, "years": ["2023", "2024"], "rows": ACTIF_1},
    {"rows": ACTIF_2},
    {"titre": TITRE_PASSIF, "rows": PASSIF},
    {"titre": "COMPTE DE RESULTAT", "years": ["2023", "2024"], "rows": CPC},
]
data3 = parser.parse_files([("suite.pdf", _pdf(suite))], 2024)
_verifie(data3, "Cas 3 (continuation)")
feuilles = [d["feuille"] for d in data3["diagnostic"]]
print("Cas 3 - feuilles :", feuilles)
assert len(feuilles) == 2, feuilles       # bilan (p.1+p.2) et CPC (p.3)
print("Cas 3 : OK")

# --- Cas 4 : PDF image (aucun texte) ----------------------------------------
pdf = FPDF(unit="pt", format="A4")
pdf.add_page()
pdf.set_line_width(0.5)
pdf.rect(40, 40, 400, 600)          # cadre vide : aucun texte extractible
scan = bytes(pdf.output())

try:
    parser.parse_files([("scan.pdf", scan)], 2024)
except ValueError as exc:
    assert "scann" in str(exc).lower(), exc
    print("Cas 4 - message :", str(exc)[:90], "…")
else:
    raise AssertionError("un PDF sans texte aurait dû être refusé")

# ... et signalé (sans tout bloquer) quand il accompagne un fichier lisible.
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    pd.DataFrame([[None, None, 2024],
                  ["Immobilisations corporelles", None, 10000]]).to_excel(
        w, sheet_name="Bilan", header=False, index=False)
    pd.DataFrame([[None, None, 2024],
                  ["Ventes de marchandises", None, 30000]]).to_excel(
        w, sheet_name="CPC", header=False, index=False)

data4 = parser.parse_files([("scan.pdf", scan),
                            ("bilan.xlsx", buf.getvalue())], 2024)
assert len(data4["avertissements"]) == 1, data4["avertissements"]
print("Cas 4 - avertissement :", data4["avertissements"][0][:70], "…")
assert data4["bilan"][2024].get("imm_corp") == 10000
print("Cas 4 : OK (scan signalé, Excel lu)")

# --- Cas 5 : en-têtes d'exercice « en toutes lettres » ----------------------
for etiquette, entetes in (
        ("Exercice 2024", ["Exercice 2023", "Exercice 2024"]),
        ("dates", ["31/12/2023", "31/12/2024"]),
        ("N / N-1", ["Exercice N-1", "Exercice N"]),
        ("colonnes 2023", ["2023", "2024"]),
):
    pages = [dict(PAGES[0], years=entetes),
             dict(PAGES[1]),
             dict(PAGES[2], years=entetes)]
    d = parser.parse_files([(f"entetes_{etiquette}.pdf", _pdf(pages))], 2024)
    _verifie(d, f"Cas 5 ({etiquette})")
    print(f"Cas 5 ({etiquette}) : OK")

# --- Cas 6 : PdfNoTextError exposée -----------------------------------------
assert issubclass(pdf_reader.PdfNoTextError, ValueError)
print("\n✅ Lecture des PDF : OK")
