# -*- coding: utf-8 -*-
"""Test rapide du pipeline complet (sans Streamlit).

Usage :  python tests/test_pipeline.py
"""

from __future__ import annotations

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from core import anomalies as an          # noqa: E402
from core import parser                   # noqa: E402
from core import ratios as rat            # noqa: E402
from core import synthesis as syn         # noqa: E402
from core import gabarit as gab            # noqa: E402
from sample.generer_exemple import generer  # noqa: E402


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = generer()
    with open(path, "rb") as fh:
        raw = fh.read()
    data = parser.parse_files([("exemple_bilan.xlsx", raw)], 2025)

    assert data["years"] == [2023, 2024, 2025], data["years"]
    print("Exercices :", data["years"])
    print("\n== Bilan normalisé (extraits) ==")
    for y in data["years"]:
        bl = data["bilan"][y]
        print(f"  {y}: actif={bl['total_actif']:,.0f} "
              f"(calcul {bl['total_actif_calc']:,.0f}) · "
              f"CP={bl['capitaux_propres']:,.0f} · FR={bl['fr']:,.0f} · "
              f"BFR={bl['bfr']:,.0f} · TN={bl['tresorerie_nette']:,.0f} · "
              f"TRN théo={bl['trn_theorique']:,.0f}")
        assert abs(bl["total_actif"] - bl["total_actif_calc"]) < 1, y
        assert abs(bl["total_passif"] - bl["total_passif_calc"]) < 1, y
        assert abs(bl["tresorerie_nette"] - bl["trn_theorique"]) < 1, \
            f"identité FR-BFR échoue en {y}"
    for y in data["years"]:
        rn_cpc = data["cpc"][y]["resultat_net_calc"]
        rn_bilan = data["bilan"][y]["resultat"]
        print(f"  {y}: CA={data['cpc'][y]['ca_net']:,.0f} · "
              f"EBE={data['cpc'][y]['ebe']:,.0f} · RN={rn_cpc:,.0f}")
        assert abs(rn_cpc - rn_bilan) < 1, f"RN incohérent en {y}"

    unmapped = data["unmapped"]
    print(f"\nLignes non reconnues : {len(unmapped)}")
    if len(unmapped):
        print(unmapped.to_string(index=False))

    computed = rat.compute_ratios(data)
    print("\n== Ratios (exercice le plus récent) ==")
    print(computed["ratios"].to_string())

    anomalies = an.detect(data)
    print(f"\n== Anomalies ({len(anomalies)}) ==")
    for a in anomalies:
        print(f"  [{a.gravite}] {a.exercice} · {a.titre} · {a.valeur}")

    texte = syn.synthese_par_regles(data, computed, anomalies, "SARL EXEMPLE")
    print("\n== Synthèse (extrait) ==")
    print("\n".join(texte.splitlines()[:25]))
    assert len(texte) > 1000

    tpl = gab.generer_gabarit()
    assert len(tpl) > 5000
    # Le gabarit vierge doit être lisible (exercices détectés) mais refusé
    # faute de données : structure OK, contenu à remplir.
    try:
        parser.parse_files([("gabarit.xlsx", tpl)], 2025)
    except ValueError as exc:
        assert "bilan" in str(exc).lower(), exc
    else:
        raise AssertionError("le gabarit vide aurait dû être refusé")

    from core import export as exp
    xls = exp.export_excel(data, computed, anomalies)
    assert len(xls) > 5000

    print("\n✅ Tous les contrôles sont passés.")


if __name__ == "__main__":
    main()
