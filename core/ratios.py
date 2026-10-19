# -*- coding: utf-8 -*-
"""Calcul des agrégats et des ratios financiers (PCG)."""

from __future__ import annotations

import math

import pandas as pd

# ---------------------------------------------------------------------------
# Seuils d'appréciation (conventions usuelles — ajustables)
# ---------------------------------------------------------------------------
# « higher » : plus la valeur est grande, mieux c'est (bornes : vert, rouge)
# « lower »  : l'inverse (bornes : vert, rouge)

SEUILS: dict[str, tuple[float, float]] = {
    "liquidite_generale": (1.20, 1.00),
    "liquidite_reduite": (1.00, 0.80),
    "coefficient_tresorerie": (0.15, 0.00),
    "endettement": (2.00, 3.00),
    "autonomie_financiere": (0.30, 0.15),
    "couverture_interets": (3.00, 1.50),
    "croissance_ca": (0.00, -0.10),
    "marge_exploitation": (0.08, 0.00),
    "marge_nette": (0.05, 0.00),
    "pouvoir_liberatoire_bfr": (0.10, 0.20),
    "bfr_jours": (60, 90),
    "dso": (60, 90),
    "dpo": (60, 90),
    "rotation_stocks_jours": (60, 90),
    "roe": (0.12, 0.00),
    "roa": (0.05, 0.00),
}

RATIOS: list[dict] = [
    # (clé, libellé, sens, unité, décimales)
    ("liquidite_generale", "Liquidité générale (actif circulant / dettes CT)",
     "higher", "x", 2),
    ("liquidite_reduite", "Liquidité réduite (hors stocks / dettes CT)",
     "higher", "x", 2),
    ("coefficient_tresorerie", "Coefficient de trésorerie (TRN / dettes CT)",
     "higher", "x", 2),
    ("endettement", "Taux d'endettement (dettes totales / capitaux propres)",
     "lower", "x", 2),
    ("autonomie_financiere", "Autonomie financière (CP / total actif)",
     "higher", "%", 1),
    ("couverture_interets", "Couverture des intérêts (EBE / charges fin.)",
     "higher", "x", 1),
    ("croissance_ca", "Croissance du chiffre d'affaires",
     "higher", "%", 1),
    ("marge_exploitation", "Marge d'exploitation (RE / CA)",
     "higher", "%", 1),
    ("marge_nette", "Marge nette (résultat net / CA)",
     "higher", "%", 1),
    ("roe", "Rentabilité des capitaux propres (ROE)",
     "higher", "%", 1),
    ("roa", "Rentabilité des actifs (ROA)",
     "higher", "%", 1),
    ("pouvoir_liberatoire_bfr", "Pouvoir libératoire du BFR (BFR / CA)",
     "lower", "%", 1),
    ("bfr_jours", "BFR en jours de chiffre d'affaires",
     "lower", "j", 0),
    ("dso", "Délai clients (jours de chiffre d'affaires)",
     "lower", "j", 0),
    ("dpo", "Délai fournisseurs (jours d'achats)",
     "lower", "j", 0),
    ("rotation_stocks_jours", "Rotation des stocks (jours d'achats)",
     "lower", "j", 0),
]


def _safe_div(a: float, b: float) -> float | None:
    if b in (0, 0.0) or b is None or a is None:
        return None
    return float(a) / float(b)


def statut(cle: str, valeur: float | None) -> str:
    """Statut 🟢 / 🟡 / 🔴 d'un ratio selon les seuils."""
    if valeur is None:
        return "—"
    sens = next((r[2] for r in RATIOS if r[0] == cle), "higher")
    vert, rouge = SEUILS.get(cle, (0.0, 0.0))
    if sens == "higher":
        if valeur >= vert:
            return "🟢"
        if valeur >= rouge:
            return "🟡"
        return "🔴"
    if valeur <= vert:
        return "🟢"
    if valeur <= rouge:
        return "🟡"
    return "🔴"


def compute_ratios(data: dict) -> dict:
    """Renvoie {aggregats, ratios} sous forme de DataFrames index/exercices."""
    years: list[int] = data["years"]
    bilan = data["bilan"]
    cpc = data["cpc"]

    def b(y: int, key: str) -> float:
        return float(bilan.get(y, {}).get(key, 0.0) or 0.0)

    def c(y: int, key: str) -> float:
        return float(cpc.get(y, {}).get(key, 0.0) or 0.0)

    # --- Agrégats ---------------------------------------------------------
    agg_defs: list[tuple[str, str, int]] = [
        ("ca_net", "Chiffre d'affaires net", 0),
        ("ebe", "Excédent brut d'exploitation (EBE)", 0),
        ("resultat_exploitation_calc", "Résultat d'exploitation", 0),
        ("resultat_net", "Résultat net", 0),
        ("capitaux_propres", "Capitaux propres (bilan)", 0),
        ("dettes_totales", "Dettes totales (bilan)", 0),
        ("fr", "Fonds de roulement (FR)", 0),
        ("bfr", "Besoin en fonds de roulement (BFR)", 0),
        ("tresorerie_nette", "Trésorerie nette", 0),
        ("investissements", "Investissements (variation immob. nettes)", 0),
    ]
    agg_rows = {}
    for key, label, dec in agg_defs:
        src = cpc if key in {"ca_net", "ebe", "resultat_exploitation_calc",
                             "resultat_net"} else bilan
        if key == "resultat_net":
            vals = {y: c(y, "resultat_net") for y in years}
        else:
            vals = {y: float(src.get(y, {}).get(key, 0.0) or 0.0)
                    for y in years}
        agg_rows[label] = vals
    # Délai BFR en jours, ajouté aux agrégats
    agg_rows["Trésorerie nette (FR - BFR)"] = {
        y: b(y, "fr") - b(y, "bfr") for y in years}

    aggregats = pd.DataFrame(
        {str(y): {lab: round(v[y], 0) for lab, v in agg_rows.items()}
         for y in years})

    # --- Ratios -----------------------------------------------------------
    ratios: dict[str, dict[int, float | None]] = {}
    cp_prev: dict[int, float] = {}
    for i, y in enumerate(years):
        cp_prev[y] = (b(years[i - 1], "capitaux_propres") + b(y, "capitaux_propres")) / 2 \
            if i > 0 else b(y, "capitaux_propres")

    for i, y in enumerate(years):
        dc = b(y, "dettes_expl") + b(y, "dettes_fin_ct_total")
        ac = b(y, "stocks_total") + b(y, "creances_circulantes")
        cp = b(y, "capitaux_propres")
        ca = c(y, "ca_net")
        achats = c(y, "achats_nets")
        charges_fin = c(y, "charges_fin")
        values = {
            "liquidite_generale": _safe_div(ac, dc),
            "liquidite_reduite": _safe_div(b(y, "creances_circulantes"), dc),
            "coefficient_tresorerie": _safe_div(b(y, "tresorerie_nette"), dc),
            "endettement": (_safe_div(b(y, "dettes_totales"), cp)
                            if cp > 0 else None),
            "autonomie_financiere": _safe_div(cp, b(y, "total_actif")),
            "couverture_interets": (_safe_div(c(y, "ebe"), charges_fin)
                                    if charges_fin > 0 else None),
            "croissance_ca": (
                ((ca - c(years[i - 1], "ca_net"))
                 / abs(c(years[i - 1], "ca_net")))
                if i > 0 and c(years[i - 1], "ca_net") else None),
            "marge_exploitation": _safe_div(
                c(y, "resultat_exploitation_calc"), ca),
            "marge_nette": _safe_div(c(y, "resultat_net"), ca),
            "roe": _safe_div(c(y, "resultat_net"), cp_prev[y]),
            "roa": _safe_div(c(y, "resultat_net"), b(y, "total_actif")),
            "pouvoir_liberatoire_bfr": _safe_div(b(y, "bfr"), ca),
            "bfr_jours": (_safe_div(b(y, "bfr"), ca) * 365) if ca else None,
            "dso": (_safe_div(b(y, "clients"), ca) * 365) if ca else None,
            "dpo": (_safe_div(b(y, "dettes_fournisseurs"), achats) * 365)
                   if achats else None,
            "rotation_stocks_jours": (_safe_div(b(y, "stocks_total"), achats)
                                      * 365) if achats else None,
        }
        for cle, val in values.items():
            ratios.setdefault(cle, {})[y] = val

    # Mise en forme du DataFrame
    last, prev = years[-1], (years[-2] if len(years) > 1 else None)
    rows = {}
    order = [r[0] for r in RATIOS]
    meta = {r[0]: r for r in RATIOS}
    for cle in order:
        _, label, _, unite, dec = meta[cle]
        line = {}
        for y in years:
            v = ratios[cle].get(y)
            if v is None:
                line[str(y)] = None
            else:
                line[str(y)] = round(v * 100 if unite == "%" else v, dec)
        if prev is not None:
            v1, v0 = ratios[cle].get(last), ratios[cle].get(prev)
            if v1 is None or v0 is None:
                line["Écart N/N-1"] = None
            else:
                d = v1 - v0
                line["Écart N/N-1"] = round(d * 100 if unite == "%" else d, dec)
        line["Unité"] = {"%": "%", "x": "×", "j": "jours"}[unite]
        line["Statut"] = statut(cle, ratios[cle].get(last))
        rows[f"{label} [{unite}]"] = line
    ratios_df = pd.DataFrame(rows).T
    ratios_df = ratios_df[[str(y) for y in years]
                          + (["Écart N/N-1"] if prev is not None else [])
                          + ["Unité", "Statut"]]

    return {"aggregats": aggregats, "ratios": ratios_df,
            "ratios_values": ratios, "meta": meta}


def fmt(v: float | None, unite: str = "", dec: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n.d."
    if unite == "%":
        return f"{v * 100:,.{dec}f} %".replace(",", " ").replace(".", ",")
    if unite == "x":
        return f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
    if unite == "j":
        return f"{v:,.0f} j".replace(",", " ")
    return f"{v:,.0f}".replace(",", " ")
