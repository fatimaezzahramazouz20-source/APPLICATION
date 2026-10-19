# -*- coding: utf-8 -*-
"""Rédaction de la synthèse : mode par règles (hors ligne) et mode IA."""

from __future__ import annotations

import json

import requests

from .anomalies import Anomalie
from .ratios import fmt

# ---------------------------------------------------------------------------
# Utilitaires de rédaction
# ---------------------------------------------------------------------------


def _pct(v: float | None, sign: bool = True) -> str:
    if v is None:
        return "n.d."
    s = f"{v * 100:+.1f}" if sign else f"{v * 100:.1f}"
    return f"{s} %".replace(".", ",")


def _eur(v: float | None) -> str:
    if v is None:
        return "n.d."
    return f"{v:,.0f} €".replace(",", " ")


def _tendance(delta: float | None, seuil_pos: float = 0.02,
              seuil_neg: float = -0.02) -> str:
    if delta is None:
        return "non comparable"
    if delta > seuil_pos:
        return "en progression"
    if delta < seuil_neg:
        return "en repli"
    return "stable"


def _delta(a: float | None, b: float | None) -> float | None:
    if a is None or not b:
        return None
    return (a - b) / abs(b)


# ---------------------------------------------------------------------------
# Synthèse par règles
# ---------------------------------------------------------------------------

def synthese_par_regles(data: dict, computed: dict,
                        anomalies: list[Anomalie],
                        societe: str = "L'entreprise") -> str:
    years: list[int] = data["years"]
    bilan, cpc = data["bilan"], data["cpc"]
    last, prev = years[-1], (years[-2] if len(years) > 1 else None)

    def b(y, k): return float(bilan.get(y, {}).get(k, 0.0) or 0.0)
    def c(y, k): return float(cpc.get(y, {}).get(k, 0.0) or 0.0)

    rv = computed["ratios_values"]

    def r(cle, y): return rv.get(cle, {}).get(y)

    periode = (f"{years[0]} à {years[-1]}" if len(years) > 1
               else str(years[-1]))
    L: list[str] = []
    L.append(f"# Synthèse financière — {societe}")
    L.append("")
    L.append(f"**Période analysée :** {periode}  ")
    L.append(f"**Exercice de référence :** {last}  ")
    L.append("**Source :** bilan et compte de produits et charges (PCG)")
    L.append("")

    # --- 1. Activité et rentabilité --------------------------------------
    L.append("## 1. Activité et rentabilité")
    L.append("")
    ca, ca_prev = c(last, "ca_net"), (c(prev, "ca_net") if prev else None)
    rn = c(last, "resultat_net")
    g_ca = _delta(ca, ca_prev)
    phrase = f"Le chiffre d'affaires de l'exercice {last} s'établit à " \
             f"**{_eur(ca)}**"
    if g_ca is not None:
        phrase += f", {_tendance(g_ca)} de {_pct(abs(g_ca), sign=False)} " \
                  f"par rapport à {prev}"
    L.append(phrase + ".")
    L.append("")
    L.append(
        f"- **Résultat d'exploitation :** {_eur(c(last, 'resultat_exploitation_calc'))} "
        f"(marge {_pct(r('marge_exploitation', last), sign=False)})"
    )
    L.append(f"- **EBE :** {_eur(c(last, 'ebe'))} "
             f"(soit {_pct(c(last, 'ebe') / ca if ca else None, sign=False)} du CA)")
    L.append(f"- **Résultat net :** {_eur(rn)} "
             f"(marge nette {_pct(r('marge_nette', last), sign=False)})")
    if prev is not None:
        g_rn = _delta(rn, c(prev, "resultat_net"))
        if g_rn is not None:
            L.append(f"- **Évolution du résultat net :** {_pct(g_rn)} "
                     f"vs {prev} ({_tendance(g_rn)})")
    roe, roa = r("roe", last), r("roa", last)
    L.append(f"- **Rentabilité :** ROE {_pct(roe, sign=False)}, "
             f"ROA {_pct(roa, sign=False)}")
    L.append("")

    # --- 2. Structure financière -----------------------------------------
    L.append("## 2. Structure financière et solvabilité")
    L.append("")
    cp = b(last, "capitaux_propres")
    dettes = b(last, "dettes_totales")
    L.append(f"- **Capitaux propres :** {_eur(cp)} "
             f"({_pct(r('autonomie_financiere', last), sign=False)} du bilan)")
    L.append(f"- **Dettes totales :** {_eur(dettes)} "
             f"(dont {_eur(b(last, 'dettes_non_courantes'))} à + d'un an)")
    L.append(f"- **Fonds de roulement :** {_eur(b(last, 'fr'))}")
    endt = r("endettement", last)
    L.append(f"- **Taux d'endettement :** {fmt(endt, 'x', 2)} "
             f"(dettes / capitaux propres)")
    couv = r("couverture_interets", last)
    if couv is not None:
        L.append(f"- **Couverture des intérêts par l'EBE :** "
                 f"{fmt(couv, 'x', 1)}")
    # Lecture
    if cp <= 0:
        L.append("")
        L.append("> ⚠️ **Capitaux propres négatifs :** les ressources "
                 "permanentes sont épuisées, la situation appelle une "
                 "réorganisation du financement.")
    else:
        lect = []
        if endt is not None:
            lect.append(
                "endettement maîtrisé" if endt <= 1.5 else
                "endettement modéré" if endt <= 2 else
                "endettement élevé, à surveiller" if endt <= 3 else
                "endettement très élevé")
        auto = r("autonomie_financiere", last)
        if auto is not None:
            lect.append(
                "structure solide" if auto >= 0.3 else
                "structure équilibrée" if auto >= 0.2 else
                " autonomie financière limitée")
        L.append("")
        L.append(f"> **Lecture :** {' ; '.join(lect)}.")
    L.append("")

    # --- 3. BFR et trésorerie --------------------------------------------
    L.append("## 3. Cycle d'exploitation et trésorerie")
    L.append("")
    bfr, trn = b(last, "bfr"), b(last, "tresorerie_nette")
    L.append(f"- **BFR :** {_eur(bfr)} "
             f"({_pct(r('pouvoir_liberatoire_bfr', last), sign=False)} du CA, "
             f"{fmt(r('bfr_jours', last), 'j')} de chiffre d'affaires)")
    L.append(f"- **Trésorerie nette :** {_eur(trn)}")
    L.append(f"- **Délais :** clients {fmt(r('dso', last), 'j')} — "
             f"fournisseurs {fmt(r('dpo', last), 'j')}")
    if prev is not None:
        d_bfr = _delta(bfr, b(prev, "bfr"))
        d_ca = _delta(ca, ca_prev)
        if d_bfr is not None and d_ca is not None:
            L.append(f"- **Dynamique :** BFR {_pct(d_bfr)} vs CA {_pct(d_ca)} "
                     f"sur un an")
    lg = r("liquidite_generale", last)
    lr = r("liquidite_reduite", last)
    L.append(f"- **Liquidité générale :** {fmt(lg, 'x', 2)} — "
             f"**liquidité réduite :** {fmt(lr, 'x', 2)}")
    if trn < 0:
        L.append("")
        L.append("> ⚠️ **Trésorerie nette négative :** l'exploitation est "
                 "financée à court terme par des ressources extérieures.")
    L.append("")

    # --- 4. Points de vigilance ------------------------------------------
    L.append("## 4. Points de vigilance")
    L.append("")
    if anomalies:
        for grav in ("critique", "attention", "info"):
            items = [a for a in anomalies if a.gravite == grav]
            if not items:
                continue
            badge = {"critique": "🔴", "attention": "🟡", "info": "🔵"}[grav]
            titre = {"critique": "Critiques", "attention": "À surveiller",
                     "info": "Observations"}[grav]
            L.append(f"### {badge} {titre}")
            L.append("")
            for a in items:
                extra = f" — {a.valeur}" if a.valeur else ""
                seuil = f" (seuil : {a.seuil})" if a.seuil else ""
                L.append(f"- **{a.titre}** ({a.exercice}){extra}{seuil}. "
                         f"{a.detail}")
            L.append("")
    else:
        L.append("Aucune anomalie détectée au regard des seuils de "
                 "contrôle : les agrégats sont cohérents entre bilan et "
                 "CPC et les ratios restent dans les normes usuelles.")
        L.append("")

    # --- 5. Recommandations ----------------------------------------------
    L.append("## 5. Recommandations")
    L.append("")
    L.extend(_recommandations(data, computed, anomalies))
    L.append("")
    L.append("---")
    L.append("_Synthèse générée automatiquement à partir du bilan et du "
             "compte de produits et charges. Seuils de contrôle : liquidité "
             "générale 1,2 / endettement 2,0 / délais clients 90 j._")
    return "\n".join(L)


def _recommandations(data: dict, computed: dict,
                     anomalies: list[Anomalie]) -> list[str]:
    recs: list[str] = []
    seen: set[str] = set()

    def add(key: str, text: str):
        if key not in seen:
            seen.add(key)
            recs.append(text)

    tags = {t for a in anomalies for t in a.tags}

    if "liquidité" in tags or "trésorerie" in tags:
        add("tresorerie",
            "**Trésorerie :** sécuriser une ligne de financement court terme "
            "(découvert garanti, escompte) et échelonner le remboursement "
            "des dettes les plus coûteuses avant tout nouvel investissement.")
    if "BFR" in tags:
        add("bfr",
            "**BFR :** négocier des délais fournisseurs, renforcer le suivi "
            "des créances (relance à 30 jours, escompte/nantissement des "
            "créances) et piloter les stocks au plus près de la demande "
            "(notamment les articles en surplus).")
    if "activité" in tags:
        add("activite",
            "**Activité :** travailler la mix commerciale et les prix "
            "(marge), cibler les segments rentables et analyser les pertes "
            "de clients avant d'engager des dépenses fixes supplémentaires.")
    if "structure" in tags:
        add("structure",
            "**Endettement :** reconstituer les capitaux propres "
            "(apport, mise en réserve du résultat) et privilégier les "
            "fonds propres ou la lease-back sur les prochaines "
            "immobilisations.")
    if "investissement" in tags:
        add("invest",
            "**Investissements :** programmer un plan de renouvellement du "
            "parc aligné sur les dotations d'amortissement, en privilégiant "
            "les solutions locatives pour préserver la trésorerie.")
    if "rentabilité" in tags:
        add("rentabilite",
            "**Rentabilité :** agir sur la structure de coût (charges "
            "d'exploitation, masse salariale au ratio CA) et sur le "
            "pilotage de la marge par ligne d'activité.")
    if "cohérence" in tags:
        add("coherence",
            "**Données :** corriger les écarts de classement entre bilan et "
            "CPC (postes mal rattachés, totaux erronés) avant toute décision "
            "— les ratios en dépendent.")
    if not recs:
        recs.append(
            "**Pérennité :** conserver le niveau de trésorerie, poursuivre "
            "les investissements et maintenir le suivi mensuel des ratios "
            "pour préserver la trajectoire actuelle.")
    return [f"- {t}" for t in recs]


# ---------------------------------------------------------------------------
# Synthèse assistée par IA (optionnelle)
# ---------------------------------------------------------------------------

PROVIDERS = {
    "OpenAI": {"model": "gpt-4o-mini",
               "url": "https://api.openai.com/v1/chat/completions"},
    "Anthropic": {"model": "claude-3-5-sonnet-latest",
                  "url": "https://api.anthropic.com/v1/messages"},
    "Ollama (local)": {"model": "llama3.1",
                       "url": "http://localhost:11434/api/chat"},
}

_SYSTEM = (
    "Tu es analyste financier senior. Tu rédiges, en français, une synthèse "
    "financière professionnelle à partir de données comptables normalisées "
    "(PCG). Tu t'appuies UNIQUEMENT sur les chiffres fournis, tu es précis "
    "sur les ordres de grandeur, tu cites les anomalies détectées et tu "
    "termine par des recommandations concrètes. Format : Markdown, 5 sections "
    "(1. Activité et rentabilité, 2. Structure financière, 3. BFR et "
    "trésorerie, 4. Points de vigilance, 5. Recommandations), 400 à 600 mots. "
    "Aucune invention de chiffre."
)


def _digest(data: dict, computed: dict, anomalies: list[Anomalie],
            societe: str) -> str:
    years = data["years"]
    payload = {
        "societe": societe,
        "exercices": years,
        "aggregats": computed["aggregats"].to_dict(),
        "ratios": computed["ratios"].to_dict(),
        "anomalies": [
            {"gravite": a.gravite, "exercice": a.exercice,
             "titre": a.titre, "detail": a.detail, "valeur": a.valeur,
             "seuil": a.seuil}
            for a in anomalies],
    }
    return json.dumps(payload, ensure_ascii=False, default=str)


def synthese_ia(data: dict, computed: dict, anomalies: list[Anomalie],
                societe: str, provider: str, api_key: str, model: str,
                base_url: str = "") -> str:
    """Appelle le LLM choisi et renvoie la synthèse Markdown."""
    cfg = PROVIDERS.get(provider, PROVIDERS["OpenAI"])
    url = base_url.strip() or cfg["url"]
    model = (model or "").strip() or cfg["model"]
    prompt = (
        f"{_SYSTEM}\n\nDonnées (JSON) :\n"
        f"{_digest(data, computed, anomalies, societe)}")

    if provider == "Anthropic":
        resp = requests.post(
            url,
            headers={"x-api-key": api_key,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": model, "max_tokens": 1600,
                  "system": _SYSTEM, "messages": [
                      {"role": "user",
                       "content": _digest(data, computed, anomalies,
                                          societe)}]},
            timeout=90)
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "\n".join(bl.get("text", "") for bl in blocks)

    payload: dict = {
        "model": model,
        "messages": [{"role": "system", "content": _SYSTEM},
                     {"role": "user", "content": prompt}],
    }
    if provider != "Ollama (local)":
        payload["temperature"] = 0.3
        headers = {"Authorization": f"Bearer {api_key}",
                   "Content-Type": "application/json"}
    else:
        payload["stream"] = False
        headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
