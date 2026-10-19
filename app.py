# -*- coding: utf-8 -*-
"""Application Streamlit : lecture bilan + CPC, ratios, anomalies, synthèse.

Lancement :  streamlit run app.py
"""

from __future__ import annotations

import base64
import datetime as _dt
import os

import pandas as pd
import streamlit as st

from core import anomalies as an
from core import export as exp
from core import gabarit as gab
from core import parser
from core import pcg
from core import ratios as rat
from core import synthesis as syn

st.set_page_config(page_title="Analyse des états financiers", page_icon="📊",
                   layout="wide")

# ---------------------------------------------------------------------------
# Thème « Finance » : dégradé bleu nuit, accents or, cartes KPI
# ---------------------------------------------------------------------------

st.markdown("""
<style>
/* =========================================================
   DESIGN FINANCE — style « terminal de marché »
   Typographie petite, dense, professionnelle
   ========================================================= */

/* --- Typo globale : petite et condensée --- */
html, body, .stApp, p, li, label, div {
    font-family: "Source Sans Pro", "Segoe UI", "Arial Narrow", sans-serif !important;
    font-size: 0.83rem !important;      /* corps de texte réduit */
    letter-spacing: 0.2px;
    line-height: 1.45;
}

/* --- Fond : noir-bleu « salle des marchés » --- */
.stApp {
    background: linear-gradient(180deg, #070D14 0%, #0A121C 55%, #060A10 100%) !important;
    background-attachment: fixed;
}

/* --- Bandeau supérieur fin or (comme un ticker) --- */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #0D2B45, #C9A227 35%, #2ECC71 65%, #0D2B45);
    z-index: 999;
    pointer-events: none;
}

/* --- Titres : petits, fins, style rapport financier --- */
h1 {
    font-size: 1.35rem !important;
    font-weight: 600 !important;
    color: #E8EDF2 !important;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(201,162,39,0.45);
    padding-bottom: 6px;
    margin-top: 0.4rem;
}
h2 {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: #C9A227 !important;
    letter-spacing: 1px;
    text-transform: uppercase;
}
h3 {
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    color: #9FB3C8 !important;
}

/* --- Texte courant : gris-bleu clair --- */
[data-testid="stMarkdownContainer"], p, li, label, span {
    color: #C7D3DF !important;
}
b, strong { color: #E8EDF2 !important; }

/* --- Sidebar : panneau de contrôle, très compact --- */
[data-testid="stSidebar"] {
    background: #0A0F17 !important;
    border-right: 1px solid rgba(201,162,39,0.35);
}
[data-testid="stSidebar"] * { font-size: 0.78rem !important; }
[data-testid="stSidebar"] h1 {
    font-size: 1rem !important;
    color: #C9A227 !important;
    border-bottom: 1px solid rgba(201,162,39,0.4);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #8FA3B8 !important;
    font-size: 0.72rem !important;
}

/* --- KPI : cartes compactes type écran Bloomberg --- */
[data-testid="stMetric"] {
    background: #0D1622 !important;
    border: 1px solid rgba(201,162,39,0.3);
    border-top: 2px solid #C9A227;
    border-radius: 4px;
    padding: 8px 12px !important;
}
[data-testid="stMetricValue"] {
    color: #F5D67B !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    font-variant-numeric: tabular-nums;
}
[data-testid="stMetricLabel"] {
    color: #7F93A8 !important;
    font-size: 0.68rem !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
[data-testid="stMetricDelta"] { font-size: 0.72rem !important; }

/* --- Boutons : fins, style terminal --- */
.stButton > button {
    background: #101B2A !important;
    border: 1px solid rgba(201,162,39,0.5) !important;
    color: #C9A227 !important;
    font-size: 0.76rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    border-radius: 3px !important;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background: #C9A227 !important;
    color: #070D14 !important;
    border-color: #C9A227 !important;
}

/* --- Onglets : onglets de navigation plate --- */
[data-baseweb="tab-list"] { gap: 0 !important; background: transparent; }
[data-baseweb="tab"] {
    font-size: 0.78rem !important;
    color: #7F93A8 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 6px 16px !important;
    border-right: 1px solid rgba(127,147,168,0.2);
}
[data-baseweb="tab"][aria-selected="true"] {
    color: #F5D67B !important;
    background: rgba(201,162,39,0.08);
    border-bottom: 2px solid #C9A227 !important;
}

/* --- Tableaux / dataframes : lignes alternées type registre --- */
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border: 1px solid rgba(201,162,39,0.25) !important;
    border-radius: 3px;
}
[data-testid="stDataFrame"] table { font-size: 0.76rem !important; }

/* --- Expanders : panneaux quasi noirs, coins vifs --- */
[data-testid="stExpander"] {
    background: #0D1622 !important;
    border: 1px solid rgba(127,147,168,0.22) !important;
    border-radius: 4px !important;
}
[data-testid="stExpander"] summary {
    color: #C9A227 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

/* --- Alertes / anomalies : filet latéral codé par gravité --- */
[data-testid="stAlert"] {
    border-radius: 3px !important;
    border-left: 3px solid #C9A227 !important;
    background: #0D1622 !important;
    font-size: 0.78rem !important;
}

/* --- Blocs de code / markdown : encadrés --- */
[data-testid="stMarkdownContainer"] > p > em { color: #8FA3B8 !important; }

/* --- Séparateurs --- */
hr { border-color: rgba(127,147,168,0.25) !important; }

/* --- Barres de défilement discrètes --- */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #070D14; }
::-webkit-scrollbar-thumb { background: #1B2A3D; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #C9A227; }

/* --- Champs de saisie : style terminal --- */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    background: #0A121C !important;
    border: 1px solid rgba(127,147,168,0.3) !important;
    border-radius: 3px !important;
    color: #E8EDF2 !important;
    font-size: 0.78rem !important;
}

/* --- Téléchargeurs --- */
[data-testid="stDownloadButton"] { font-size: 0.76rem !important; }
</style>
""", unsafe_allow_html=True)

# --- Fond photo « salle des marchés » (voile sombre pour la lisibilité) ---
_BG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "assets", "background.jpg")
try:
    with open(_BG_PATH, "rb") as _fh:
        _BG_B64 = base64.b64encode(_fh.read()).decode()
    st.markdown(f"""
<style>
.stApp, [data-testid="stAppViewContainer"] {{
    background:
        linear-gradient(rgba(6,10,16,0.82), rgba(6,10,16,0.90)),
        url("data:image/jpeg;base64,{_BG_B64}")
        center / cover no-repeat fixed !important;
}}
/* photo aussi dans la barre latérale (voile plus dense) */
[data-testid="stSidebar"] {{
    background:
        linear-gradient(rgba(5,8,13,0.92), rgba(5,8,13,0.96)),
        url("data:image/jpeg;base64,{_BG_B64}")
        center / cover no-repeat fixed !important;
}}
</style>
""", unsafe_allow_html=True)
except OSError:
    pass  # image absente → le fond dégradé du thème s'applique

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
                 ref_year: int | None,
                 overrides: dict | None = None) -> dict:
    return parser.parse_files(list(files), ref_year, dict(overrides or {}))


def _bump_remap_stamp() -> None:
    """Change l'horodatage des widgets de recollement : les anciennes valeurs
    devenant obsolètes, les selectboxes repartent des choix enregistrés."""
    st.session_state["remap_stamp"] = st.session_state.get("remap_stamp", 0) + 1


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
                           width="stretch")
    with c2:
        if st.button("🧪 Exemple", width="stretch",
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
_fixture = st.session_state.get("fixture_path")
if st.session_state.get("use_sample"):
    files = [("exemple_bilan.xlsx", load_sample())]
elif _fixture and os.path.exists(_fixture):
    # Jeu d'essai externe (tests automatisés, diagnostic).
    with open(_fixture, "rb") as _fh:
        files = [(os.path.basename(_fixture), _fh.read())]
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
        data = run_pipeline(files, int(ref_year),
                            st.session_state.get("remap"))
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
    st.dataframe(computed["ratios"], width="stretch", height=520)
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
    diag = data.get("diagnostic") or []
    if diag:
        with st.expander("🔎 Diagnostic de lecture (feuilles, colonnes, "
                         "exercices détectés)"):
            st.dataframe(pd.DataFrame(diag), width="stretch")
            st.caption("Colonnes numérotées à partir de 1 (1 = colonne A). "
                       "« lignes_non_reconnues » = libellés non rattachés au "
                       "plan comptable.")
    st.subheader("Agrégats normalisés (€)")
    st.dataframe(computed["aggregats"], width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Bilan normalisé**")
        st.dataframe(data["bilan_table"], width="stretch",
                     height=420)
    with c2:
        st.markdown("**Compte de produits et charges normalisé**")
        st.dataframe(data["cpc_table"], width="stretch", height=420)
    unmapped = data["unmapped"]
    remap = dict(st.session_state.get("remap") or {})
    pending = dict(remap)
    if not unmapped.empty:
        st.warning(
            f"**{len(unmapped)} ligne(s) non reconnue(s)** : elles sont "
            "exclues des agrégats. Rattachez-les manuellement ci-dessous "
            "(capital social, capitaux propres, postes atypiques…).")
        with st.expander(f"✍️ Rattacher {len(unmapped)} ligne(s) à une "
                         "catégorie PCG", expanded=True):
            opts = ["— Laisser non reconnue —",
                    "❌ Ignorer cette ligne (hors analyse)"]
            disp2cat: dict[str, str] = {}
            for k in list(pcg.BILAN_ORDER) + list(pcg.CPC_ORDER):
                grp = "Bilan" if k in pcg.BILAN_CATS else "CPC"
                d = f"{grp} · {parser._CAT_LABELS.get(k, k)}"
                disp2cat[d] = k
                opts.append(d)

            for idx, (_, row) in enumerate(unmapped.iterrows()):
                lib = str(row.get("Libellé", "")).strip()
                etat = str(row.get("État", ""))
                nkey = pcg.norm(lib)
                cur = pending.get(nkey)
                if cur == "__ignorer__":
                    cur_disp = opts[1]
                elif cur:
                    grp = "Bilan" if cur in pcg.BILAN_CATS else "CPC"
                    cur_disp = (f"{grp} · "
                                f"{parser._CAT_LABELS.get(cur, cur)}")
                else:
                    cur_disp = opts[0]
                if cur_disp not in opts:
                    cur_disp = opts[0]
                cl, cs = st.columns([3, 2])
                cl.markdown(f"<span class='chip'>{etat}</span> {lib}",
                            unsafe_allow_html=True)
                choice = cs.selectbox(
                    "Rattacher", opts, index=opts.index(cur_disp),
                    key=f"remap_w{st.session_state.get('remap_stamp', 0)}_{idx}",
                    label_visibility="collapsed")
                if choice == opts[0]:
                    pending.pop(nkey, None)
                elif choice == opts[1]:
                    pending[nkey] = "__ignorer__"
                else:
                    pending[nkey] = disp2cat[choice]

            a1, a2 = st.columns(2)
            if a1.button("✅ Appliquer et recalculer", key="btn_remap_apply"):
                st.session_state["remap"] = pending
                _bump_remap_stamp()
                st.rerun()
            if a2.button("🗑️ Réinitialiser les recollements",
                         key="btn_remap_reset"):
                st.session_state["remap"] = {}
                _bump_remap_stamp()
                st.rerun()

        st.dataframe(unmapped, width="stretch")
    else:
        st.success("Toutes les lignes ont été rattachées à une catégorie "
                   "du plan comptable.")
    if remap:
        st.caption(f"📌 {len(remap)} recollement(s) manuel(aux) appliqué(s) "
                   "à cette analyse.")

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
                           width="stretch", key="dl_synth_tab")
    with col2:
        st.download_button("⬇️ Analyse complète (Excel)",
                           data=exp.export_excel(data, computed, anomalies),
                           file_name=f"analyse_financiere_{last}.xlsx",
                           mime=("application/vnd.openxmlformats-officedocument"
                                 ".spreadsheetml.sheet"),
                           width="stretch", key="dl_xlsx_tab")
    with col3:
        ia_dispo = provider == "Ollama (local)" or bool(api_key.strip())
        if st.button("✨ Enrichir avec l'IA", width="stretch",
                     disabled=not ia_dispo,
                     help="Clé API requise (sidebar)" if not ia_dispo else "",
                     key="btn_ia_tab"):
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
                           mime="text/markdown", key="dl_ia_tab")

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
        st.metric("Taux endettement", rat.fmt(endt, "x", 2), delta="🟡 si > 1,5")
    st.markdown("---")
    st.markdown("**Évolution CA & Résultat Net**")
    if prev is not None:
        ca0 = c(prev, "ca_net")
        rn0 = c(prev, "resultat_net")
        g_ca_pct = ((ca - ca0) / abs(ca0) * 100) if ca0 else None
        g_rn_pct = ((c(last, "resultat_net") - rn0) / abs(rn0) * 100) if rn0 else None
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"CA : {syn._pct(g_ca_pct, sign=False)} vs {prev}")
            st.line_chart(pd.DataFrame({"CA": [ca0, ca]}, index=[prev, last]))
        with c2:
            st.caption(f"Résultat net : {syn._pct(g_rn_pct, sign=False)} vs {prev}")
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
                       mime="text/markdown", width="stretch",
                       key="dl_synth_export")
with c2:
    st.download_button("⬇️ Analyse complète (Excel)",
                       data=exp.export_excel(data, computed, anomalies),
                       file_name=f"analyse_financiere_{last}.xlsx",
                       mime=("application/vnd.openxmlformats-officedocument"
                             ".spreadsheetml.sheet"),
                       width="stretch")
with col3:
    ia_dispo = provider == "Ollama (local)" or bool(api_key.strip())
    if st.button("✨ Enrichir avec l'IA", width="stretch",
                 disabled=not ia_dispo,
                 help="Clé API requise (sidebar)" if not ia_dispo else "",
                 key="btn_ia_export"):
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
                           mime="text/markdown", key="dl_ia_export")
