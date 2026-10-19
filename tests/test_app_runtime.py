# -*- coding: utf-8 -*-
"""Vérifie que app.py s'exécute sans exception (y compris le dashboard)."""
import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))

from streamlit.testing.v1 import AppTest  # noqa: E402

at = AppTest.from_file(os.path.join(os.path.dirname(BASE), "app.py"),
                       default_timeout=120)
at.session_state["use_sample"] = True
at.run()

errs = list(at.exception)
print(f"Exceptions : {len(errs)}")
for e in errs:
    print(" -", e.value if hasattr(e, "value") else e)

metrics = [m.label for m in at.metric]
print(f"KPIs affichés : {metrics}")
print("OK" if not errs else "ECHEC")

# --- Second passage : états financiers fournis en PDF ------------------------
import tempfile  # noqa: E402

from fpdf import FPDF  # noqa: E402

LAB_X, LAB_W, AMT_X, AMT_W, ROW_H = 40, 190, [230, 310], 80, 14
PAGES = [
    ("BILAN - ACTIF", ["2023", "2024"],
     [("Immobilisations corporelles", [180000, 205000]),
      ("Stocks de marchandises", [120000, 155000]),
      ("Clients et comptes rattaches", [95000, 118000]),
      ("Tresorerie", [45000, 38000])]),
    ("BILAN - PASSIF", None,
     [("Capital social", [80000, 80000]),
      ("Reserve legale", [20000, 25000]),
      ("Resultat de l'exercice", [30000, 46000]),
      ("Emprunts", [200000, 240000]),
      ("Dettes fournisseurs", [110000, 125000])]),
    ("COMPTE DE RESULTAT", ["2023", "2024"],
     [("Ventes de marchandises", [500000, 560000]),
      ("Achats de marchandises", [300000, 330000]),
      ("Charges de personnel", [100000, 110000]),
      ("Dotations aux amortissements", [20000, 24000]),
      ("Resultat de l'exercice", [120000, 96000])]),
]

pdf = FPDF(unit="pt", format="A4")
pdf.set_auto_page_break(False)
for titre, years, rows in PAGES:
    pdf.add_page()
    pdf.set_font("helvetica", size=9)
    y = 60.0
    pdf.set_xy(LAB_X, y)
    pdf.cell(LAB_W + 2 * AMT_W, ROW_H, titre)
    y += ROW_H + 4
    for label, vals in ([("", years)] if years else []) + rows:
        if label:
            pdf.set_xy(LAB_X, y)
            pdf.cell(LAB_W, ROW_H, label)
        for i, v in enumerate(vals):
            txt = v if isinstance(v, str) else f"{v:,.0f}".replace(",", " ")
            pdf.set_xy(AMT_X[i], y)
            pdf.cell(AMT_W, ROW_H, txt, align="R")
        y += ROW_H

chemin = os.path.join(tempfile.gettempdir(), "etats_financiers_test.pdf")
with open(chemin, "wb") as fh:
    fh.write(bytes(pdf.output()))

at2 = AppTest.from_file(os.path.join(os.path.dirname(BASE), "app.py"),
                        default_timeout=120)
at2.session_state["fixture_path"] = chemin
at2.run()

errs2 = list(at2.exception)
print(f"PDF — exceptions : {len(errs2)}")
for e in errs2:
    print(" -", e.value if hasattr(e, "value") else e)
m2 = [m.label for m in at2.metric]
print(f"PDF — KPIs : {m2}")
assert not errs2, errs2
assert any("Chiffre d'affaires" in l for l in m2), m2
assert any("Capitaux propres" in l for l in m2), m2
print("PDF — OK" if not errs2 else "PDF — ECHEC")
