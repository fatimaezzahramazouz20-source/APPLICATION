# -*- coding: utf-8 -*-
"""Test de fumée de l'interface de recollement manuel (onglet 📊 Données).

Charge un classeur contenant des libellés non reconnus, vérifie que l'app
s'exécute sans exception, que les selectboxes de rattachement apparaissent,
puis rejoue avec un recollement appliqué.
"""
from __future__ import annotations

import os
import sys
import tempfile

os.environ["PYTHONIOENCODING"] = "utf-8"
BASE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(BASE)
sys.path.insert(0, PROJ)
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from core import pcg  # noqa: E402

EXOTIQUE = "Poste exotique à rattacher"

BILAN = [
    [None, 2024],
    ["ACTIF", None],
    ["Immobilisations corporelles", 120000],
    ["Stocks", 35000],
    ["Créances clients", 45000],
    [EXOTIQUE, 7000],                     # ← non reconnu : à rattacher
    ["Trésorerie", 10000],
    ["PASSIF", None],
    ["Capital social", 50000],
    ["Réserves", 25000],
    ["Emprunts", 60000],
    ["Dettes fournisseurs", 30000],
]
CPC = [
    [None, 2024],
    ["PRODUITS", None],
    ["Ventes de marchandises", 200000],
    ["CHARGES", None],
    ["Achats de marchandises", 120000],
    ["Charges de personnel", 45000],
    ["Frais généraux divers", 23000],
    ["Résultat de l'exercice", 12000],
]

tmp = tempfile.mkdtemp(prefix="remap_ui_")
path = os.path.join(tmp, "essai_remap.xlsx")
with pd.ExcelWriter(path, engine="openpyxl") as w:
    pd.DataFrame(BILAN).to_excel(w, sheet_name="Bilan", header=False,
                                 index=False)
    pd.DataFrame(CPC).to_excel(w, sheet_name="CPC", header=False, index=False)


def _run(overrides: dict | None = None):
    at = AppTest.from_file(os.path.join(PROJ, "app.py"), default_timeout=120)
    at.session_state["fixture_path"] = path
    if overrides:
        at.session_state["remap"] = overrides
    at.run()
    errs = [e.value if hasattr(e, "value") else str(e) for e in at.exception]
    return at, errs


at, errs = _run()
print(f"1) Exécution brute — exceptions : {len(errs)}")
for e in errs:
    print("   -", e)
assert not errs, errs
boxes = [s for s in at.selectbox if "Rattacher" in str(s.label or "")]
print(f"1) Selectboxes de rattachement affichées : {len(boxes)}")
assert len(boxes) >= 1, "aucune selectbox de recollement"

# Membres proposés : catégories de bilan et de CPC + les deux choix neutres
opts = list(boxes[0].options)
print("1) Nb d'options proposées :", len(opts))
assert any(o.startswith("Bilan ·") for o in opts), opts[:5]
assert any(o.startswith("CPC ·") for o in opts)
assert opts[0].startswith("—") and opts[1].startswith("❌")

# 2) Recollement appliqué : la ligne exotique est rattachée à « Créances clients »
at2, errs2 = _run({pcg.norm(EXOTIQUE): "clients"})
print(f"2) Recollement appliqué — exceptions : {len(errs2)}")
assert not errs2, errs2
boxes2 = [s for s in at2.selectbox if "Rattacher" in str(s.label or "")]
print(f"2) Ligne non reconnue encore proposée : {len(boxes2)}")
assert len(boxes2) == 0, "la ligne rattachée ne doit plus être proposée"

# 3) Ligne explicitement ignorée
at3, errs3 = _run({pcg.norm(EXOTIQUE): "__ignorer__"})
print(f"3) Ligne ignorée — exceptions : {len(errs3)}")
assert not errs3, errs3
assert not [s for s in at3.selectbox if "Rattacher" in str(s.label or "")]

print("\n✅ Interface de recollement : OK")
