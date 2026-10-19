# -*- coding: utf-8 -*-
"""Non-régression du rattachement des libellés réels (variantes fréquentes)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from core import pcg  # noqa: E402

# (libellé, côté, catégorie attendue)
CAS_BILAN = [
    ("Capital social", None, "capital"),
    ("Capital social", "P", "capital"),
    ("Capital souscrit non appelé", None, "capital"),
    ("Capitaux propres", None, "capitaux_propres_declare"),
    ("Capitaux propres", "P", "capitaux_propres_declare"),
    ("Capitaux propres et ressources assimilées", "P",
     "capitaux_propres_declare"),
    ("Fonds propres", None, "capitaux_propres_declare"),
    ("Réserve légale", "P", "reserve_legale"),
    ("Report à nouveau", "P", "reserves"),
    ("Autres réserves", "P", "reserves"),
    ("Résultat de l'exercice", "P", "resultat"),
    ("Trésorerie", "A", "tresorerie_active"),
    ("Trésorerie", "P", "tresorerie_passive"),
    ("Trésorerie - Actif", "A", "tresorerie_active"),
    ("Trésorerie - Passif", "P", "tresorerie_passive"),
    ("Trésorerie - Passif", "A", "tresorerie_passive"),
    ("Banque", "A", "tresorerie_active"),
    ("Emprunts auprès des établissements de crédit", "P", "dettes_fin_lt"),
    ("Dettes bancaires", "P", "dettes_fin_lt"),
    ("Prêt à long terme", "P", "dettes_fin_lt"),
    ("Prêt accordé à une filiale", "A", "imm_fin"),
    ("Dettes fournisseurs et comptes rattachés", "P",
     "dettes_fournisseurs"),
    ("Dettes fiscales et sociales", "P", "autres_dettes_expl"),
    ("Provisions pour risques et charges", "P", "provisions_lt"),
]

CAS_CPC = [
    ("Ventes de marchandises", "P", "ca"),
    ("Prestations de services", "P", "ca"),
    ("Prestations de services", "C", "autres_charges_expl"),
    ("Chiffre d'affaires net", "P", "ca"),
    ("Autres achats et charges externes", "C", "autres_charges_expl"),
    ("Frais généraux", "C", "autres_charges_expl"),
    ("Impôts et taxes", "C", "impots"),
    ("Impôts, taxes et versements assimilés", "C", "impots"),
    ("Frais financiers", "C", "charges_fin"),
    ("Charges de personnel", "C", "charges_personnel"),
    ("Dotations aux amortissements", "C", "dotations"),
    ("Résultat de l'exercice", None, "resultat_net"),
]

echecs = []
for label, side, attendu in CAS_BILAN:
    obtenu = pcg.categorize_bilan(label, side)
    etat = "OK " if obtenu == attendu else "KO "
    print(f"{etat} bilan [{str(side):>4}] {label[:45]:47} → {obtenu} "
          f"(attendu {attendu})")
    if obtenu != attendu:
        echecs.append((label, side, attendu, obtenu))

for label, side, attendu in CAS_CPC:
    obtenu = pcg.categorize_cpc(label, side)
    etat = "OK " if obtenu == attendu else "KO "
    print(f"{etat} cpc   [{str(side):>4}] {label[:45]:47} → {obtenu} "
          f"(attendu {attendu})")
    if obtenu != attendu:
        echecs.append((label, side, attendu, obtenu))

# En-têtes : « Trésorerie » avec un montant est un poste, pas une rubrique
assert pcg.is_section_header("Trésorerie", valued=False) is True
assert pcg.is_section_header("Trésorerie", valued=True) is False
assert pcg.is_section_header("Trésorerie - Passif", valued=True) is False
for rubrique in ("ACTIF", "PASSIF", "Actif circulant", "Immobilisations",
                 "Total immobilisations", "dont stocks"):
    assert pcg.is_section_header(rubrique, valued=True) is True, rubrique

# L'agrégat « Capitaux propres et ressources assimilées » porteur d'un montant
# n'est PAS un en-tête : il alimente les capitaux propres déclarés.
assert pcg.is_section_header(
    "Capitaux propres et ressources assimilées", valued=True) is False
assert pcg.categorize_bilan(
    "Capitaux propres et ressources assimilées", "P") == \
    "capitaux_propres_declare"

assert not echecs, f"{len(echecs)} libellé(s) mal rattaché(s) : {echecs}"
print("\n✅ Libellés PCG : OK")
