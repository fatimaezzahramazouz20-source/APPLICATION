# -*- coding: utf-8 -*-
"""Non-régression : liasse CGNC (Maroc) « modèle normal » fournie en PDF.

Le PDF est reconstitué avec fpdf2 dans la mise en page de la liasse :

* en-tête d'exercice fusionné (« EXERCICE » couvrant Brut / Amortissements /
  Net, puis « Exercice Précédent ») ;
* rubriques lettrées de (a) à (k) suivies de leur détail ;
* lignes de contrôle (« TOTAL II », « RESULTAT COURANT (III+VI) »…) ;
* libellés hors PCG : « Compte de négociation », « Titres et valeurs de
  placement », « Ecarts de conversion »…

Contrôles : total actif = total passif, aucun double comptage entre une
rubrique et son détail, aucune ligne perdue, et le CPC se reconstitue.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd  # noqa: E402
from fpdf import FPDF  # noqa: E402

from core import parser  # noqa: E402

LAB_X, LAB_W = 40, 270
AMT_X = [310, 380, 450, 520]
AMT_W = 70
ROW_H = 14

# --- Bilan actif : (brut, amortissements, net, net précédent) ---------------
ACTIF = [
    ("IMMOBILISATION EN NON VALEUR (a)", ["-", "-", "-", "-"]),
    ("IMMOBILISATIONS INCORPORELLES (b)", [1000, 400, 600, 500]),
    ("Logiciels", [1000, 400, 600, 500]),
    ("IMMOBILISATIONS CORPORELLES (c)", [1000, 400, 600, 500]),
    ("Mobilier, materiel de bureau", [1000, 400, 600, 500]),
    ("IMMOBILISATIONS FINANCIERES (d)", [200, "-", 200, 200]),
    ("Titres de participation", [200, "-", 200, 200]),
    ("STOCKS (f)", ["-", "-", "-", "-"]),
    ("CREANCES DE L'ACTIF CIRCULANT (g)", [6330, "-", 6330, 4700]),
    ("Clients et comptes rattaches", [630, "-", 630, 200]),
    ("Etat", [2000, "-", 2000, 1500]),
    ("Autres debiteurs", [3700, "-", 3700, 3000]),
    ("TITRES ET VALEURS DE PLACEMENT (i)", [1000, "-", 1000, 800]),
    ("Titres et valeurs de placement", [1000, "-", 1000, 800]),
    ("TRESORERIE - ACTIF (k)", [500, "-", 500, 400]),
    ("Banques, T.G & CP", [500, "-", 500, 400]),
    ("TOTAL GENERAL I+II+III", [14030, 800, 9230, 7100]),
]

# --- Bilan passif : (exercice, —, —, exercice précédent) --------------------
PASSIF = [
    ("CAPITAUX PROPRES (a)", [5800, None, None, 5500]),
    ("Capital social ou personnel (1)", [5000, None, None, 5000]),
    ("Reserve legale", [500, None, None, 500]),
    ("Report a nouveau (2)", [300, None, None, 0]),
    ("CAPITAUX PROPRES ASSIMILES (b)", ["-", None, None, "-"]),
    ("DETTES DE FINANCEMENT (c)", [500, None, None, 500]),
    ("Emprunts aupres des etablissements de credit", [500, None, None, 500]),
    ("PROVISIONS DURABLES POUR RISQUES ET CHARGES (d", ["-", None, None, "-"]),
    ("DETTES DU PASSIF CIRCULANT (g)", [2000, None, None, 1100]),
    ("Fournisseurs et comptes rattaches", [1200, None, None, 1000]),
    ("Etat", [600, None, None, 100]),
    ("Autres creanciers", [200, None, None, 0]),
    ("DEPOTS DE CLIENTELE (h)", ["-", None, None, "-"]),
    ("AUTRES PROVISIONS POUR RISQUES ET CHARGES (i)", [620, None, None, "-"]),
    ("ECARTS DE CONVERSION - PASSIF (j)( Elements circulants )",
     [10, None, None, "-"]),
    ("TRESORERIE PASSIF", [None, None, None, None]),
    ("Banques ( soldes crediteurs )", [300, None, None, "-"]),
    ("TOTAL I+II+III", [9230, None, None, 7100]),
]

# --- CPC : (exercice, —, —, exercice précédent) -----------------------------
CPC = [
    ("PRODUITS D'EXPLOITATION", [None, None, None, None]),
    ("* Ventes de marchandises", [1000, None, None, 900]),
    ("* Prestations de services", [500, None, None, 400]),
    ("Chiffre d'affaires", [1500, None, None, 1300]),
    ("* Autres produits d'exploitation", [100, None, None, 100]),
    ("Total I", [1600, None, None, 1400]),
    ("CHARGES D'EXPLOITATION", [None, None, None, None]),
    ("* Achats de marchandises", [600, None, None, 500]),
    ("* Impots et taxes", [50, None, None, 40]),
    ("* Charges de personnel", [400, None, None, 350]),
    ("Total II", [1050, None, None, 890]),
    ("RESULTAT D'EXPLOITATION (I-II)", [550, None, None, 510]),
    ("PRODUITS FINANCIERS", [None, None, None, None]),
    ("* Interets et autres produits financiers", [30, None, None, 20]),
    ("CHARGES FINANCIERES", [None, None, None, None]),
    ("* Charges d'interets", [10, None, None, 5]),
    ("RESULTAT COURANT (III+VI)", [570, None, None, 525]),
    ("PRODUITS NON COURANTS", [None, None, None, None]),
    ("* Produits non courants", [5, None, None, 3]),
    ("CHARGES NON COURANTES", [None, None, None, None]),
    ("* Charges non courantes", [2, None, None, 1]),
    ("RESULTAT NON COURANT (VIII-IX)", [3, None, None, 2]),
    ("RESULTAT AVANT IMPOTS (VII+X)", [573, None, None, 527]),
    ("IMPOTS SUR LES BENEFICES", [173, None, None, 127]),
    ("RESULTAT NET (XI-XII)", [400, None, None, 400]),
]

TITRE = ("SOGECAPITAL BOURSE SYNTHETIQUE (modele normal) "
         "Du 01/01/2021 au 31/12/2021")


def _page(pdf, titre, header, rows):
    pdf.add_page()
    pdf.set_font("helvetica", size=7)
    y = 50.0
    pdf.set_xy(LAB_X, y)
    pdf.cell(LAB_W + 4 * AMT_W, ROW_H, titre)
    y += ROW_H + 4
    for label, vals in [header] + list(rows):
        pdf.rect(LAB_X, y, LAB_W, ROW_H)
        for x in AMT_X:
            pdf.rect(x, y, AMT_W, ROW_H)
        if label:
            # Un libellé qui déborde empiète sur la colonne suivante et fausse
            # la lecture : on refuse tout débordement.
            assert pdf.get_string_width(label) <= LAB_W - 4, label
            pdf.set_xy(LAB_X, y)
            pdf.cell(LAB_W, ROW_H, label)
        for i, v in enumerate(vals):
            if v is None:
                continue
            assert pdf.get_string_width(str(v)) <= AMT_W - 4, v
            pdf.set_xy(AMT_X[i], y)
            pdf.cell(AMT_W, ROW_H, str(v), align="R")
        y += ROW_H


def _liasse() -> bytes:
    pdf = FPDF(unit="pt", format="A4")
    pdf.set_auto_page_break(False)
    entete = ["EXERCICE 2021", None, None, "Exercice Precedent"]
    _page(pdf, TITRE, ("ACTIF", entete), ACTIF)
    _page(pdf, TITRE, ("PASSIF", entete), PASSIF)
    _page(pdf, TITRE, ("NATURE", entete), CPC)
    return bytes(pdf.output())


# --- Lecture des montants collés dans une même cellule ----------------------
assert parser.parse_amount("0,00 11 833 103,15") == 11833103.15
assert parser.parse_amount("112 774,09 7 981 137,63") == 7981137.63
assert parser.parse_amount("11 833 103,15") == 11833103.15
assert parser.parse_amount("2 97 258,33") == 297258.33
assert parser.parse_amount("-") is None
print("Cellules fusionnees : OK")

# Le millésime du document est lu dans l'en-tête, jamais dans un montant qui
# ressemble à une année (« 2000 »).
_titre = pd.DataFrame({
    0: ["Liasse Du 01/01/2021 au 31/12/2021", "Produits financiers"],
    1: ["", "2000"],
})
assert parser._document_year(_titre) == 2021
_montants = pd.DataFrame({0: ["Ventes", "Produits financiers"],
                          1: ["", "2000"]})
assert parser._document_year(_montants) is None
print("Millesime du document : OK")

data = parser.parse_files([("liasse cgnc.pdf", _liasse())], None)
print("Annees :", data["years"])
assert data["years"] == [2020, 2021], data["years"]

for annee, total in ((2021, 9230), (2020, 7100)):
    b = data["bilan"][annee]
    assert b["total_actif"] == total, (annee, b["total_actif"])
    assert b["total_passif"] == total, (annee, b["total_passif"])
print("Bilan : actif = passif (9230 / 7100) : OK")

b21 = data["bilan"][2021]
# Une rubrique lettrée et son détail ne se cumulent pas.
assert b21["imm_incorp"] == 600, b21["imm_incorp"]
assert b21["imm_corp"] == 600, b21["imm_corp"]
assert b21["imm_fin"] == 200, b21["imm_fin"]
# « AUTRES PROVISIONS (i) » sans detail chiffre reste un poste.
assert b21["provisions_lt"] == 620, b21["provisions_lt"]
# Les ecarts de conversion passif ferment le bilan.
assert b21["dettes_non_courantes"] == 1120, b21["dettes_non_courantes"]
assert b21["dettes_expl"] == 2010, b21["dettes_expl"]
assert b21["autres_dettes_expl"] == 210, b21["autres_dettes_expl"]
assert b21["tresorerie_active"] == 1500, b21["tresorerie_active"]
print("Bilan : rubriques, provisions et ecarts de conversion : OK")

c21 = data["cpc"][2021]
# « Chiffre d'affaires » absorbe ses details (pas de double comptage).
assert c21["ca"] == 1500, c21["ca"]
assert c21["charges_exploitation"] == 1050, c21["charges_exploitation"]
assert c21["resultat_exploitation_calc"] == 550, c21["resultat_exploitation_calc"]
assert c21["produits_totaux"] == 1635, c21["produits_totaux"]
assert c21["charges_totaux"] == 1235, c21["charges_totaux"]
assert c21["resultat_net"] == 400, c21["resultat_net"]
assert c21["resultat_net_calc"] == 400, c21["resultat_net_calc"]
print("CPC : chiffre d'affaires, totaux et resultat : OK")

assert data["unmapped"].empty, data["unmapped"]
print("Aucune ligne non reconnue : OK")

print("\n✅ Liasse CGNC (PDF) : OK")
