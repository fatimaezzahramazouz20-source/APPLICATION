# -*- coding: utf-8 -*-
"""Application Streamlit : lecture bilan + CPC, ratios, anomalies, synthèse.

Lancement :  streamlit run app.py
"""

from __future__ import annotations

import datetime as _dt
import os

import pandas as pd
import streamlit as st

from core import anomalies as an
from core import export as exp
from core import gabarit as gab
from core import parser
from core import ratios as rat
from core import synthesis as syn

st.set_page_config(page_title="Analyse des états financiers", page_icon="📊",
                   layout="wide")

st.markdown("""
# 📈 Analyse des états financiers

**Cette application lit un bilan et un compte de produits et charges, calcule et vérifie les ratios financiers, repère les anomalies et rédige une synthèse.**

## Démarrage en 3 étapes

1. **Téléchargez le gabarit** (barre latérale ⬇️) — onglets `Bilan` et `CPC`,
   une colonne par exercice (`2023`, `2024`…).
2. **Remplissez-le** avec vos états financiers (montants en euros).
3. **Déposez le fichier** dans la zone ci-dessus, ou cliquez sur **🧪 Exemple**
   pour tester immédiatement avec un jeu de données sur 3 exercices.

> 💡 *Astuce : les colonnes peuvent porter une année (ex. `2024`) ou les
> étiquettes `N`, `N-1`, `N-2` ; l'année de référence se règle dans la barre
> latérale.*
""")

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(BASE, "sample", "exemple_bilan.xlsx")


# ---------------------------------------------------------------------------
# Pipeline (mis en cache)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def run_pipeline(files: list[tuple[str, bytes]],
                 ref_year: int | None) -> dict:
    return parser.parse_files(list(files), ref_year)


@st.cache_data(show_spinner=False)
def load_sample() -> bytes:
    if not os.path.exists(SAMPLE_PATH):
        from sample.generer_exemple import generer
        generer(SAMPLE_PATH)
    with open(SAMPLE_PATH, "rb") as fh:
        return fh.read()


@st.cache_data(show_spinner=False)
def template_bytes() -> bytes:
    return gab.generer_gabarit()


# ---------------------------------------------------------------------------
# Barre latérale
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("📊 Analyse financière")
    st.caption("Bilan + compte de produits et charges (PCG) → ratios, "
               "anomalies, synthèse.")

    uploads = st.file_uploader(
        "Déposez vos états financiers",
        type=["xlsx", "xlsm", "xls", "csv"],
        accept_multiple_files=True,
        help="Un classeur Excel avec onglets « Bilan » et « CPC », "
             "ou deux CSV (bilan.csv / cpc.csv).")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Gabarit Excel", data=template_bytes(),
                           file_name="gabarit_etats_financiers.xlsx",
                           mime=("application/vnd.openxmlformats-officedocument"
                                 ".spreadsheetml.sheet"),
                           use_container_width=True)
    with c2:
        if st.button("🧪 Exemple", use_container_width=True,
                     help="Charge un jeu d'exemple sur 3 exercices"):
            st.session_state["use_sample"] = True
            st.rerun()

    ref_year = st.number_input(
        "Année de référence (si colonnes « N », « N-1 »…)",
        min_value=1990, max_value=2100,
        value=_dt.date.today().year - 1, step=1)
    societe = st.text_input("Nom de l'entreprise (facultatif)",
                            value="L'entreprise")

    st.divider()
    with st.expander("🤖 Synthèse assistée par IA (optionnel)"):
        st.caption("Sans clé, la synthèse est produite par règles (hors ligne).")
        provider = st.selectbox("Fournisseur", list(syn.PROVIDERS))
        api_key = st.text_input(
            "Clé API", type="password",
            disabled=(provider == "Ollama (local)"))
        model = st.text_input(
            "Modèle", value=syn.PROVIDERS[provider]["model"],
            help="Laisser vide pour utiliser le modèle par défaut.")
        base_url = st.text_input(
            "URL (Ollama uniquement)",
            value=syn.PROVIDERS["Ollama (local)"]["url"],
            disabled=(provider != "Ollama (local)"))

    if st.session_state.get("use_sample"):
        if st.button("✖️ Effacer l'exemple"):
            st.session_state["use_sample"] = False
            st.rerun()

# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------

files: list[tuple[str, bytes]] = []
if st.session_state.get("use_sample"):
    files = [("exemple_bilan.xlsx", load_sample())]
elif uploads:
    files = [(f.name, f.getvalue()) for f in uploads]

if not files:
    st.markdown(
        """
# 👋 Bienvenue

Cette application **lit un bilan et un compte de produits et charges**,
**calcule et vérifie les ratios financiers**, **repère les anomalies**
puis **rédige une synthèse**.

### Pour commencer
1. **Téléchargez le gabarit Excel** (barre latérale) — onglets `Bilan` et `CPC`,
   une colonne par exercice (« 2023 », « 2024 »…).
2. Remplissez-le avec vos états financiers (montants en euros).
3. **Déposez le fichier** dans la zone ci-dessus, ou cliquez sur **🧪 Exemple**
   pour tester immédiatement avec un jeu d'essai sur 3 exercices.

| Onglet | Contenu |
|---|---|
| 📐 Ratios | Liquidité, endettement, rentabilité, BFR, délais — statuts 🟢🟡🔴 |
| 📊 Données | Agrégats normalisés, tables bilan/CPC, lignes non reconnues |
| 🚨 Anomalies | Contrôles de cohérence + dépassements de seuils |
| 📝 Synthèse | Synthèse rédigée (règles, ou IA si clé configurée) |
""")
    st.stop()

try:
    with st.spinner("Lecture et mappage des états financiers…"):
        data = run_pipeline(files, int(ref_year))
except Exception as exc:  # noqa: BLE001 — remontée utilisateur
    st.error(f"**Lecture impossible** : {exc}")
    st.stop()

computed = rat.compute_ratios(data)
anomalies = an.detect(data)
years = data["years"]
last, prev = years[-1], (years[-2] if len(years) > 1 else None)

bilan, cpc = data["bilan"], data["cpc"]
b = lambda y, k: float(bilan.get(y, {}).get(k, 0.0) or 0.0)
c = lambda y, k: float(cpc.get(y, {}).get(k, 0.0) or 0.0)
rv = computed["ratios_values"]

# ---------------------------------------------------------------------------
# En-tête + KPI
# ---------------------------------------------------------------------------

st.title(f"📈 {societe}")
st.caption(f"Exercices analysés : {', '.join(str(y) for y in years)}  ·  "
           f"Feuilles : " + ", ".join(s['nom'] for s in data['sheets']))

k1, k2, k3, k4, k5, k6 = st.columns(6)
ca = c(last, "ca_net")
ca_prev = c(prev, "ca_net") if prev else None
g_ca = ((ca - ca_prev) / abs(ca_prev)) if ca_prev else None
k1.metric(f"Chiffre d'affaires {last}", f"{ca:,.0f} €".replace(",", " "),
          delta=(f"{g_ca * 100:+.1f} %" if g_ca is not None else None),
          delta_color="inverse")
k2.metric(f"Résultat net {last}",
          f"{c(last, 'resultat_net'):,.0f} €".replace(",", " "))
k3.metric("Marge nette",
          rat.fmt(rv["marge_nette"][last], "%", 1))
k4.metric("Trésorerie nette",
          f"{b(last, 'tresorerie_nette'):,.0f} €".replace(",", " "))
k5.metric("BFR (jours de CA)", rat.fmt(rv["bfr_jours"][last], "j"))
crit = sum(1 for a in anomalies if a.gravite == "critique")
att = sum(1 for a in anomalies if a.gravite == "attention")
k6.metric("Anomalies",
          f"{crit} 🔴 / {att} 🟡",
          delta=None if not anomalies else f"{len(anomalies)} au total")

st.divider()

# ---------------------------------------------------------------------------
# Onglets
# ---------------------------------------------------------------------------

tab_r, tab_d, tab_a, tab_s = st.tabs(
    ["📐 Ratios", "📊 Données", "🚨 Anomalies", "📝 Synthèse"])

# --- Ratios ----------------------------------------------------------------
with tab_r:
    st.subheader("Ratios financiers — seuils de contrôle par exercice")
    st.dataframe(computed["ratios"], use_container_width=True, height=520)
    st.caption("🟢 conforme · 🟡 limite · 🔴 hors seuil — statut calculé sur "
               "l'exercice le plus récent. « Écart N/N-1 » = évolution de "
               "l'exercice N par rapport à N-1.")
    with st.expander("Signification des ratios"):
        st.markdown(
            "| Ratio | Lecture usuelle |\n|---|---|\n"
            "| Liquidité générale | ≥ 1,2 : les dettes court terme sont "
            "couvertes par l'actif circulant |\n"
            "| Liquidité réduite | ≥ 1,0 : idem hors stocks |\n"
            "| Taux d'endettement | ≤ 2 : dettes maîtrisées par rapport aux "
            "capitaux propres |\n"
            "| Autonomie financière | ≥ 30 % : part des ressources propres "
            "dans le bilan |\n"
            "| Couverture des intérêts | ≥ 3 : l'EBE couvre largement les "
            "intérêts |\n"
            "| BFR en jours | ≤ 60 j : cycle d'exploitation rapide |\n"
            "| DSO / DPO | jours de ventes clients / jours d'achats "
            "fournisseurs |\n"
            "| ROE / ROA | rendement des capitaux propres / des actifs |")

# --- Données ---------------------------------------------------------------
with tab_d:
    st.subheader("Agrégats normalisés (€)")
    st.dataframe(computed["aggregats"], use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Bilan normalisé**")
        st.dataframe(data["bilan_table"], use_container_width=True,
                     height=420)
    with c2:
        st.markdown("**Compte de produits et charges normalisé**")
        st.dataframe(data["cpc_table"], use_container_width=True, height=420)
    unmapped = data["unmapped"]
    if not unmapped.empty:
        with st.expander(f"⚠️ Lignes non reconnues ({len(unmapped)}) — "
                         "à vérifier, elles ne sont pas comptées"):
            st.dataframe(unmapped, use_container_width=True)
    else:
        st.success("Toutes les lignes ont été rattachées à une catégorie "
                   "du plan comptable.")

# --- Anomalies -------------------------------------------------------------
with tab_a:
    st.subheader("Contrôles et anomalies détectées")
    if not anomalies:
        st.success("Aucune anomalie : bilan équilibré, CPC cohérent avec le "
                   "résultat du bilan et ratios dans les seuils usuels.")
    for a in anomalies:
        badge = {"critique": "🔴", "attention": "🟡", "info": "🔵"}[a.gravite]
        extra = f" — **{a.valeur}**" if a.valeur else ""
        seuil = f" · seuil : {a.seuil}" if a.seuil else ""
        message = f"{badge} **{a.titre}** ({a.exercice}){extra}{seuil}  \n{a.detail}"
        if a.gravite == "critique":
            st.error(message)
        elif a.gravite == "attention":
            st.warning(message)
        else:
            st.info(message)

# --- Synthèse --------------------------------------------------------------
with tab_s:
    st.subheader("Synthèse rédigée")
    texte = syn.synthese_par_regles(data, computed, anomalies, societe)
    st.markdown(texte)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("⬇️ Synthèse (Markdown)", data=texte,
                           file_name=f"synthese_{last}.md",
                           mime="text/markdown",
                           use_container_width=True)
    with col2:
        st.download_button("⬇️ Analyse complète (Excel)",
                           data=exp.export_excel(data, computed, anomalies),
                           file_name=f"analyse_financiere_{last}.xlsx",
                           mime=("application/vnd.openxmlformats-officedocument"
                                 ".spreadsheetml.sheet"),
                           use_container_width=True)
    with col3:
        ia_dispo = provider == "Ollama (local)" or bool(api_key.strip())
        if st.button("✨ Enrichir avec l'IA", use_container_width=True,
                     disabled=not ia_dispo,
                     help="Clé API requise (sidebar)" if not ia_dispo else ""):
            with st.spinner("Rédaction de la synthèse par l'IA…"):
                try:
                    st.session_state["synth_ia"] = syn.synthese_ia(
                        data, computed, anomalies, societe, provider,
                        api_key, model, base_url)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Appel IA impossible : {exc}")

    if st.session_state.get("synth_ia"):
        st.divider()
        st.markdown("### ✨ Synthèse assistée par IA")
        st.markdown(st.session_state["synth_ia"])
        st.download_button("⬇️ Synthèse IA (Markdown)",
                           data=st.session_state["synth_ia"],
                           file_name=f"synthese_ia_{last}.md",
                           mime="text/markdown")

# ---------------------------------------------------------------------------
# Dashboard entreprise (résumé global)
# ---------------------------------------------------------------------------
with st.expander("📊 Dashboard entreprise", expanded=False):
    st.markdown(f"**Période :** {years[0]} → {last}  |  **Exercice de référence :** {last}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Chiffre d'affaires", f"{ca:,.0f} €", delta=(f"+{g_ca*100:.1f} %" if g_ca else None))
    with c2:
        st.metric("Résultat net", f"{c(last, 'resultat_net'):,.0f} €")
    with c3:
        st.metric("Capitaux propres", f"{b(last, 'capitaux_propres'):,.0f} €")
    with c4:
        endt = rv["endettement"][last]
        st.metric("Taux endettement", fmt(endt, "x", 2), delta="🟡 si > 1,5")
    st.markdown("---")
    st.markdown("**Évolution CA & Résultat Net**")
    if prev is not None:
        ca0 = c(prev, "ca_net")
        rn0 = c(prev, "resultat_net")
        g_ca_pct = ((ca - ca0) / abs(ca0) * 100) if ca0 else None
        g_rn_pct = ((c(last, "resultat_net") - rn0) / abs(rn0) * 100) if rn0 else None
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"CA : {_pct(g_ca_pct, sign=False)} vs {prev}")
            st.line_chart(pd.DataFrame({"CA": [ca0, ca]}, index=[prev, last]))
        with c2:
            st.caption(f"Résultat net : {_pct(g_rn_pct, sign=False)} vs {prev}")
            st.line_chart(pd.DataFrame({"RN": [rn0, c(last, "resultat_net")]}, index=[prev, last]))
    # Liquidité dans le temps
    st.markdown("**Liquidité (actif circulant / dettes CT) dans le temps**")
    lg_vals = {str(y): rv["liquidite_generale"].get(y) for y in years}
    st.line_chart(pd.DataFrame(lg_vals, index=[last] if len(years) == 1 else years))
    st.caption("🟢 ≥ 1,2 • 🟡 1,0 à 1,2 • 🔴 < 1,0")
    # BFR dans le temps
    st.markdown("**BFR en jours de CA dans le temps**")
    bfr_j_vals = {str(y): rv["bfr_jours"].get(y) for y in years}
    st.line_chart(pd.DataFrame(bfr_j_vals, index=[last] if len(years) == 1 else years))
    st.caption("🟢 ≤ 60 j • 🟡 60-90 j • 🔴 > 90 j")

st.divider()

# --- Export complet --------------------------------------------------------
st.markdown("### Export complet")
c1, c2 = st.columns(2)
with c1:
    st.download_button("⬇️ Synthèse (Markdown)", data=texte,
                       file_name=f"synthese_{last}.md",
                       mime="text/markdown", use_container_width=True)
with c2:
    st.download_button("⬇️ Analyse complète (Excel)",
                       data=exp.export_excel(data, computed, anomalies),
                       file_name=f"analyse_financiere_{last}.xlsx",
                       mime=("application/vnd.openxmlformats-officedocument"
                             ".spreadsheetml.sheet"),
                       use_container_width=True)
with col3:
    ia_dispo = provider == "Ollama (local)" or bool(api_key.strip())
    if st.button("✨ Enrichir avec l'IA", use_container_width=True,
                 disabled=not ia_dispo,
                 help="Clé API requise (sidebar)" if not ia_dispo else ""):
        with st.spinner("Rédaction de la synthèse par l'IA…"):
            try:
                st.session_state["synth_ia"] = syn.synthese_ia(
                    data, computed, anomalies, societe, provider,
                    api_key, model, base_url)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Appel IA impossible : {exc}")

    if st.session_state.get("synth_ia"):
        st.divider()
        st.markdown("### ✨ Synthèse assistée par IA")
        st.markdown(st.session_state["synth_ia"])
        st.download_button("⬇️ Synthèse IA (Markdown)",
                           data=st.session_state["synth_ia"],
                           file_name=f"synthese_ia_{last}.md",
                           mime="text/markdown")
