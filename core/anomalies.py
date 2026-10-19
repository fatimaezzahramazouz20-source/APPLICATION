# -*- coding: utf-8 -*-
"""Contrôles de cohérence et détection d'anomalies financières."""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Seuils
# ---------------------------------------------------------------------------

SEUILS = {
    "equilibrage_pct": 0.005,        # 0,5 % du total de bilan
    "equilibrage_min": 500.0,        # tolérance plancher
    "rn_pct": 0.01,                  # cohérence résultat net (1 % du CA)
    "rn_min": 1_000.0,
    "trn_pct": 0.01,                 # cohérence TRN vs FR - BFR
    "liquidite_generale": 1.00,
    "liquidite_generale_warn": 1.20,
    "liquidite_reduite": 1.00,
    "endettement": 2.0,
    "endettement_critique": 3.0,
    "couverture_interets": 2.0,
    "couverture_interets_warn": 3.0,
    "ca_chute": -0.10,
    "ca_chute_forte": -0.20,
    "stocks_hausse": 0.20,
    "dso": 90.0,
    "dpo": 90.0,
    "bfr_jours": 90.0,
    "trsorerie_baisse": -0.30,
}


@dataclass
class Anomalie:
    gravite: str            # "critique" | "attention" | "info"
    exercice: int
    titre: str
    detail: str
    valeur: str = ""
    seuil: str = ""
    tags: list[str] = field(default_factory=list)


def _pct(v: float) -> str:
    return f"{v * 100:.1f} %".replace(".", ",")


def _eur(v: float) -> str:
    return f"{v:,.0f} €".replace(",", " ")


# ---------------------------------------------------------------------------
# Contrôles
# ---------------------------------------------------------------------------

def detect(data: dict) -> list[Anomalie]:
    years: list[int] = data["years"]
    bilan, cpc = data["bilan"], data["cpc"]
    last, prev = years[-1], (years[-2] if len(years) > 1 else None)
    out: list[Anomalie] = []

    def b(y, k): return float(bilan.get(y, {}).get(k, 0.0) or 0.0)
    def c(y, k): return float(cpc.get(y, {}).get(k, 0.0) or 0.0)

    # --- 1. Équilibrage du bilan -----------------------------------------
    for y in years:
        tol = max(SEUILS["equilibrage_min"],
                  SEUILS["equilibrage_pct"] * abs(b(y, "total_actif")))
        ecart = b(y, "total_actif") - b(y, "total_passif")
        if abs(ecart) > tol:
            out.append(Anomalie(
                "critique", y,
                "Bilan non équilibré",
                "Le total de l'actif ne correspond pas au total du passif : "
                "postes probablement mal classés ou ligne manquante.",
                valeur=f"écart {_eur(ecart)}",
                seuil=f"tolérance {_eur(tol)}",
                tags=["cohérence"]))

    # --- 2. Cohérence résultat net (CPC vs bilan) ------------------------
    for y in years:
        rn_cpc, rn_bilan = c(y, "resultat_net"), b(y, "resultat")
        if rn_cpc and rn_bilan:
            tol = max(SEUILS["rn_min"], SEUILS["rn_pct"] * abs(rn_cpc))
            if abs(rn_cpc - rn_bilan) > tol:
                out.append(Anomalie(
                    "critique", y,
                    "Résultat net incohérent entre bilan et CPC",
                    "Le résultat net du bilan diffère du résultat net calculé "
                    "sur le compte de produits et charges.",
                    valeur=f"bilan {_eur(rn_bilan)} / CPC {_eur(rn_cpc)}",
                    seuil=f"tolérance {_eur(tol)}",
                    tags=["cohérence"]))

    # --- 3. Cohérence TRN (identité FR - BFR) ----------------------------
    for y in years:
        tn = b(y, "tresorerie_nette")
        theo = b(y, "trn_theorique")
        tol = max(SEUILS["equilibrage_min"],
                  SEUILS["trn_pct"] * abs(b(y, "total_actif")))
        if abs(tn - theo) > tol:
            out.append(Anomalie(
                "attention", y,
                "Trésorerie non conciliable avec le FR - BFR",
                "L'identité « trésorerie nette = FR - BFR (+ dettes fin. court "
                "terme) » n'est pas vérifiée : poste mal rattaché probablement.",
                valeur=f"bilan {_eur(tn)} / calcul {_eur(theo)}",
                seuil=f"tolérance {_eur(tol)}",
                tags=["cohérence"]))

    # --- 4. Résultats / capitaux propres ---------------------------------
    for y in years:
        rn = c(y, "resultat_net")
        if rn < 0:
            consecutive = prev is not None and c(prev, "resultat_net") < 0
            out.append(Anomalie(
                "critique" if consecutive else "attention", y,
                "Perte nette sur l'exercice",
                ("Deux exercices consécutifs déficitaires : le fonds propre "
                 "est grignoté." if consecutive else
                 "L'exercice se solde par une perte."),
                valeur=_eur(rn), tags=["rentabilité"]))
        if b(y, "capitaux_propres") < 0:
            out.append(Anomalie(
                "critique", y, "Capitaux propres négatifs",
                "Les ressources permanentes sont inférieures aux dettes : "
                "situation de dépôt de bilan potentiel.",
                valeur=_eur(b(y, "capitaux_propres")), tags=["structure"]))

    # --- 5. Liquidité ----------------------------------------------------
    for y in years:
        dc = b(y, "dettes_expl") + b(y, "dettes_fin_ct_total")
        ac = b(y, "stocks_total") + b(y, "creances_circulantes")
        if dc <= 0:
            continue
        lg, lr = ac / dc, b(y, "creances_circulantes") / dc
        if lg < SEUILS["liquidite_generale"]:
            out.append(Anomalie(
                "critique", y, "Liquidité générale inférieure à 1",
                "L'actif court terme ne couvre plus les dettes court terme : "
                "risque de tensions de trésorerie.",
                valeur=f"{lg:.2f}".replace(".", ","),
                seuil="≥ 1,00", tags=["liquidité"]))
        elif lg < SEUILS["liquidite_generale_warn"]:
            out.append(Anomalie(
                "attention", y, "Liquidité générale faible",
                "Marge de sécurité limitée sur les dettes court terme.",
                valeur=f"{lg:.2f}".replace(".", ","),
                seuil="≥ 1,20", tags=["liquidité"]))
        if lr < SEUILS["liquidite_reduite"]:
            out.append(Anomalie(
                "attention", y, "Liquidité réduite inférieure à 1",
                "Hors stocks, les créances ne couvrent plus les dettes court "
                "terme : tout encaissement retardé peut devenir critique.",
                valeur=f"{lr:.2f}".replace(".", ","),
                seuil="≥ 1,00", tags=["liquidité"]))

    # --- 6. Endettement / couverture des intérêts ------------------------
    for y in years:
        cp = b(y, "capitaux_propres")
        if cp > 0:
            endt = b(y, "dettes_totales") / cp
            if endt > SEUILS["endettement_critique"]:
                out.append(Anomalie(
                    "critique", y, "Endettement très élevé",
                    "Les dettes dépassent de loin les capitaux propres : "
                    "capacité de financement et solvabilité affaiblies.",
                    valeur=f"{endt:.2f}".replace(".", ","),
                    seuil="≤ 3,00", tags=["structure"]))
            elif endt > SEUILS["endettement"]:
                out.append(Anomalie(
                    "attention", y, "Endettement élevé",
                    "Dettes supérieures aux deux fois les capitaux propres.",
                    valeur=f"{endt:.2f}".replace(".", ","),
                    seuil="≤ 2,00", tags=["structure"]))
        cf = c(y, "charges_fin")
        if cf > 0:
            couv = c(y, "ebe") / cf
            if couv < SEUILS["couverture_interets"]:
                out.append(Anomalie(
                    "critique", y, "Charge d'intérêts difficilement couverte",
                    "L'EBE ne couvre plus qu'une faible part des intérêts : "
                    "risque de défaut de paiement.",
                    valeur=f"{couv:.1f}".replace(".", ","),
                    seuil="≥ 3,00", tags=["structure"]))
            elif couv < SEUILS["couverture_interets_warn"]:
                out.append(Anomalie(
                    "attention", y, "Couverture des intérêts faible",
                    "Marge de manœuvre réduite pour absorber la dette.",
                    valeur=f"{couv:.1f}".replace(".", ","),
                    seuil="≥ 3,00", tags=["structure"]))

    # --- 7. Dynamique de l'activité --------------------------------------
    if prev is not None:
        ca, ca0 = c(last, "ca_net"), c(prev, "ca_net")
        if ca0:
            g = (ca - ca0) / abs(ca0)
            if g <= SEUILS["ca_chute_forte"]:
                out.append(Anomalie(
                    "critique", last, "Forte baisse du chiffre d'affaires",
                    "Le chiffre d'affaires recule fortement sur un an : "
                    "rebondir sur la rentabilité et la trésorerie.",
                    valeur=_pct(g), seuil="≥ -10 %", tags=["activité"]))
            elif g <= SEUILS["ca_chute"]:
                out.append(Anomalie(
                    "attention", last, "Baisse du chiffre d'affaires",
                    "Le chiffre d'affaires recule sur un an.",
                    valeur=_pct(g), seuil="≥ -10 %", tags=["activité"]))
        # Effondrement du résultat net
        rn_l, rn_p = c(last, "resultat_net"), c(prev, "resultat_net")
        if rn_p > 0 and rn_l >= 0:
            g_rn = (rn_l - rn_p) / abs(rn_p)
            if g_rn <= -0.40:
                out.append(Anomalie(
                    "attention", last, "Fort recul du résultat net",
                    "Le résultat net chute de plus de 40 % sur un an alors "
                    "que l'entreprise reste bénéficiaire.",
                    valeur=_pct(g_rn), seuil="≥ -40 %",
                    tags=["rentabilité"]))
        # Stocks en hausse alors que l'activité recule
        st, st0 = b(last, "stocks_total"), b(prev, "stocks_total")
        if st0 and ca0 and g < 0:
            gst = (st - st0) / abs(st0)
            if gst >= SEUILS["stocks_hausse"] and g < 0:
                out.append(Anomalie(
                    "attention", last,
                    "Stocks en hausse alors que le chiffre d'affaires baisse",
                    "Les stocks progressent alors que l'activité recule : "
                    "risque de stocks immobilisés et de dépréciations.",
                    valeur=f"stocks {_pct(gst)} / CA {_pct(g)}",
                    seuil=f"stocks ≤ +{_pct(SEUILS['stocks_hausse'])}",
                    tags=["activité", "stocks"]))
        # Investissements < dotations : renouvellement insuffisant
        dot = c(last, "dotations")
        inv = b(last, "investissements")
        if dot > 0 and inv < dot * 0.5:
            out.append(Anomalie(
                "info", last, "Renouvellement du parc insuffisant",
                "Les investissements nets sont nettement inférieurs aux "
                "dotations d'amortissement : vieillissement de l'outillage "
                "à moyen terme.",
                valeur=f"invest. {_eur(inv)} / dotations {_eur(dot)}",
                seuil="≥ 50 % des dotations", tags=["investissement"]))
        # Trésorerie en baisse
        trn, trn0 = b(last, "tresorerie_nette"), b(prev, "tresorerie_nette")
        if trn0 > 0:
            gt = (trn - trn0) / abs(trn0)
            if gt <= SEUILS["trsorerie_baisse"]:
                out.append(Anomalie(
                    "attention", last, "Trésorerie nette en nette baisse",
                    "La trésorerie se détériore fortement sur un an.",
                    valeur=_pct(gt), seuil="≥ -30 %", tags=["trésorerie"]))

    # --- 8. BFR / délais -------------------------------------------------
    for y in years:
        ca, achats = c(y, "ca_net"), c(y, "achats_nets")
        if ca:
            bfr_j = b(y, "bfr") / ca * 365
            if bfr_j > SEUILS["bfr_jours"]:
                out.append(Anomalie(
                    "attention", y, "BFR très élevé en jours d'activité",
                    "Le cycle d'exploitation immobilise beaucoup de fonds : "
                    "besoin de financement croissant.",
                    valeur=f"{bfr_j:.0f} j".replace(".", ","),
                    seuil="≤ 90 j", tags=["BFR"]))
        if ca:
            dso = b(y, "clients") / ca * 365
            if dso > SEUILS["dso"]:
                out.append(Anomalie(
                    "attention", y, "Délais clients longs",
                    "Les créances représentent plus de 90 jours de ventes : "
                    "trésorerie décaissée au profit des clients.",
                    valeur=f"{dso:.0f} j".replace(".", ","),
                    seuil="≤ 90 j", tags=["BFR"]))
        if achats:
            dpo = b(y, "dettes_fournisseurs") / achats * 365
            if dpo > SEUILS["dpo"]:
                out.append(Anomalie(
                    "attention", y, "Délais fournisseurs dépassant 90 jours",
                    "Dette fournisseuse très longue : signe possible de "
                    "tensions de trésorerie ou de retards de paiement.",
                    valeur=f"{dpo:.0f} j".replace(".", ","),
                    seuil="≤ 90 j", tags=["BFR"]))
        if b(y, "tresorerie_nette") < 0:
            out.append(Anomalie(
                "critique", y, "Trésorerie nette négative",
                "L'entreprise est financée à court terme par ses créances "
                "d'exploitation : découvert bancaire ou retards de paiement.",
                valeur=_eur(b(y, "tresorerie_nette")),
                tags=["trésorerie"]))

    # Tri : critiques d'abord, puis par exercice décroissant
    order = {"critique": 0, "attention": 1, "info": 2}
    out.sort(key=lambda a: (order.get(a.gravite, 3), -a.exercice))
    return out
