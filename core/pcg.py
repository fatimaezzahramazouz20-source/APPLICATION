# -*- coding: utf-8 -*-
"""Référentiel PCG (Plan Comptable Général).

Normalise les libellés rencontrés dans les bilans et les comptes de produits
et charges (CPC), les rattache à des catégories normalisées, puis dérive les
agrégats nécessaires au calcul des ratios.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# Normalisation des libellés
# ---------------------------------------------------------------------------


def norm(text: object) -> str:
    """Normalise un libellé : sans accents, sans ponctuation, pluriels retirés."""
    if text is None:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    words = []
    for w in s.split():
        if len(w) > 3 and w.endswith(("s", "x")):
            w = w[:-1]
        words.append(w)
    return " ".join(words)


# ---------------------------------------------------------------------------
# Bilan : catégories normalisées (côté A = actif, P = passif)
# ---------------------------------------------------------------------------

BILAN_CATS: dict[str, tuple[str, list[str]]] = {
    # --- Actif -------------------------------------------------------------
    "imm_en_cours": ("A", ["immobilisation en cours", "avance et acompte",
                           "immobilisation en non valeur",
                           "frais preliminaire", "charge a repartir"]),
    "tresorerie_active": (
        "A",
        [
            "tresorerie actif", "tresorerie", "valeur mobilier", "placement",
            "titre et valeur", "banque", "caisse", "cheque", "vmp", "epargne",
            "livret",
        ],
    ),
    "imm_fin": (
        "A",
        [
            "immobilisation financiere", "creance rattach", "participation",
            "cautionnement", "pret", "titre de participation",
            "titre immobilise",
        ],
    ),
    "imm_incorp": (
        "A",
        [
            "immobilisation incorporelle", "brevet", "licence", "logiciel",
            "fond commercial", "droit au bail",
        ],
    ),
    "imm_corp": (
        "A",
        [
            "immobilisation corporelle", "terrain", "construction", "materiel",
            "machine", "mobilier", "ordinateur", "agencement", "installation",
            "vehicule", "moyen de transport", "outillage", "batiment",
        ],
    ),
    "clients": ("A", ["client", "commande"]),
    "charges_a_payer": ("A", ["charge a payer"]),
    "etat_actif": (
        "A",
        ["etat collectivite", "creance d etat", "credit d impot", "impot",
         "tva", "taxe", "redevance"],
    ),
    "personnel_actif": ("A", ["personnel", "salaire", "remuneration"]),
    "autres_creances": (
        "A", ["autre creance", "creance", "divers", "autre debiteur",
              "debiteur", "fourni debiteur", "compte de regularisation",
              "compte de negociation", "ecart de conversion"],
    ),
    "stocks": (
        "A",
        ["stock", "marchandise", "matiere premiere", "matiere et fourniture",
         "produit fini", "denree", "approvisionnement", "travaux en cours"],
    ),
    # --- Passif ------------------------------------------------------------
    "capitaux_propres_declare": ("P", ["capitau propre", "fond propre"]),
    "capital": ("P", ["capital social", "capital", "apport", "souscription"]),
    "reserves": (
        "P", ["reserve", "report a nouveau", "report nouveau",
              "resultat reporte", "benefice a nouveau", "benefice repartir"],
    ),
    "reserve_legale": ("P", ["reserve legale"]),
    "resultat": ("P", ["resultat de l exercice", "resultat net", "resultat de l exercice"]),
    "pertes": ("P", ["perte anterieure", "cumul des pertes", "perte"]),
    "subventions_invest": ("P", ["subvention d investissement"]),
    "amortissements_regl": ("P", ["provision reglementee", "amortissement differe"]),
    "produits_a_recevoir": ("P", ["produit a recevoir"]),
    "dettes_fin_ct": (
        "P",
        ["interet couru", "emprunt a court terme", "emprunt court terme",
         "credit a court terme", "credit d escompte",
         "credit de tresorerie"],
    ),
    "dettes_fin_lt": (
        "P",
        ["emprunt", "dettes rattach", "rachat d annuite", "obligation",
         "credit bail", "etablissement de credit", "pret",
         "credit bancaire", "dette bancaire", "dette de financement"],
    ),
    "provisions_lt": (
        "P",
        ["provision pour risque", "provision pour charge",
         "provision pour depreciation", "provision"],
    ),
    "dettes_fournisseurs": ("P", ["fournisseur"]),
    "dettes_personnel": (
        "P", ["dettes sur remuneration", "dettes personnel", "salaire a payer"],
    ),
    "dettes_etat": (
        "P",
        ["dettes fiscale", "dettes sociale", "tva a decaisser",
         "impot a payer", "dettes etat", "etat impot", "impot et taxe",
         "dette etat", "organisme sociaux"],
    ),
    "autres_dettes_expl": (
        "P",
        ["autre dette", "dette", "autre passif", "creancier",
         "compte de regularisation", "compte de negociation",
         "depot de clientele", "client crediteur", "ecart de conversion"],
    ),
    "tresorerie_passive": (
        "P",
        ["tresorerie passif", "tresorerie", "decouvert", "soldes debiteur",
         "compte de banque debiteur", "solde crediteur"],
    ),
}

# Libellés dont le rattachement dépend entièrement du côté du bilan : « Etat »
# est une créance à l'actif, une dette au passif (et non deux postes distincts).
_BILAN_EXACT: dict[str, tuple[str, str]] = {
    "etat": ("etat_actif", "dettes_etat"),
    "etat et collectivite publique": ("etat_actif", "dettes_etat"),
    "etat impot et taxe": ("etat_actif", "dettes_etat"),
}

# Ordre de priorité : les libellés spécifiques doivent être testés avant les
# libellés génériques (ex. « Créances clients » avant « Autres créances »).
BILAN_ORDER = [
    "imm_en_cours", "tresorerie_active", "imm_fin", "imm_incorp", "imm_corp",
    "charges_a_payer", "produits_a_recevoir", "clients",
    "dettes_fournisseurs", "dettes_personnel", "dettes_etat",
    "dettes_fin_ct", "dettes_fin_lt", "provisions_lt",
    "capitaux_propres_declare",
    "reserve_legale", "reserves", "capital", "subventions_invest",
    "amortissements_regl", "pertes", "resultat",
    "etat_actif", "personnel_actif", "autres_creances", "autres_dettes_expl",
    "stocks", "tresorerie_passive",
]

# ---------------------------------------------------------------------------
# Compte de produits et charges (CPC)
# ---------------------------------------------------------------------------

CPC_CATS: dict[str, list[str]] = {
    "ca": [
        "vente de marchandise", "prestation de service", "production vendue",
        "chiffre d affaire", "vente de produit",
        "commission des transaction", "commission sur activite",
    ],
    "production_stockee": ["production stockee", "destockage", "destocke"],
    "autres_produits_expl": (
        ["autre produit d exploitation", "subvention d exploitation",
         "reprise sur provision et depreciation", "produit d exploitation"]
    ),
    "achats_marchandises": ["achat de marchandise", "achat marchandise"],
    "achats_matieres": ["achat de matiere", "matiere premiere",
                        "achat consomme",
                        "achat de matiere et fourniture"],
    "var_stocks": ["variation de stock", "variation des stock",
                   "variation stock", "destockage"],
    "autres_charges_expl": [
        "autre charge d exploitation", "charge d exploitation",
        "achat et charge externe", "charge externe", "frai generau",
        "frai diver", "prestation de service", "impot et taxe",
        "impot taxe", "impot et taxe associe",
    ],
    "charges_personnel": ["charge de personnel", "remuneration du personnel"],
    "dotations": [
        "dotation aux amortissement", "dotation aux depreciation",
        "dotation aux provision", "dotation d exploitation",
        "reprise d exploitation", "reprise d amortissement",
        "reprise sur provision", "reprise d epargne",
    ],
    "resultats_expl": ["resultat d exploitation"],
    "charges_fin": ["charge d interet", "charge financiere", "interet d emprunt",
                    "frai financier", "perte sur cession", "perte de change",
                    "dotation financiere", "perte sur titre",
                    "autre charge financiere", "indemnite de remere"],
    "produits_fin": ["produit financier", "produit des titre", "gain de change",
                     "revenu et produit", "reprise financiere", "gain sur titre",
                     "interet et autre produit", "indemnite de remere"],
    "resultats_fin": ["resultat financier"],
    "impots": [
        "impot sur les benefice", "impot benefice", "impot courant",
        "impot sur le chiffre", "impot sur le resultat",
        "impot sur les societe",
    ],
    "produits_exc": ["produit exceptionnel", "produit hors activite",
                     "produit non courant"],
    "charges_exc": ["charge exceptionnel", "charge hors activite",
                    "charge non courante"],
    "resultat_net": ["resultat net", "resultat de l exercice",
                     "resultat du compte"],
}

CPC_ORDER = [
    "ca", "production_stockee", "autres_produits_expl",
    "achats_marchandises", "achats_matieres", "var_stocks",
    "autres_charges_expl", "charges_personnel", "dotations",
    "charges_fin", "produits_fin", "resultats_fin", "resultats_expl",
    "impots", "produits_exc", "charges_exc", "resultat_net",
]

# ---------------------------------------------------------------------------
# Léxico canonique (repli par similarité)
# ---------------------------------------------------------------------------

LEXICON = {
    "imm_en_cours": "Immobilisations en cours",
    "imm_incorp": "Immobilisations incorporelles",
    "imm_corp": "Immobilisations corporelles",
    "imm_fin": "Immobilisations financières",
    "stocks": "Stocks",
    "clients": "Créances clients",
    "charges_a_payer": "Charges à payer",
    "produits_a_recevoir": "Produits à recevoir",
    "etat_actif": "État, impôts et taxes",
    "personnel_actif": "Créances sur le personnel",
    "autres_creances": "Autres créances",
    "tresorerie_active": "Trésorerie - Actif",
    "capitaux_propres_declare": "Capitaux propres",
    "capital": "Capital social",
    "reserves": "Réserves",
    "reserve_legale": "Réserve légale",
    "resultat": "Résultat de l'exercice",
    "pertes": "Perte antérieure",
    "subventions_invest": "Subventions d'investissement",
    "amortissements_regl": "Provisions réglementées",
    "dettes_fin_lt": "Emprunts",
    "provisions_lt": "Provisions pour risques et charges",
    "dettes_fournisseurs": "Dettes fournisseurs",
    "dettes_personnel": "Dettes sur rémunérations",
    "dettes_etat": "Dettes fiscales et sociales",
    "autres_dettes_expl": "Autres dettes",
    "dettes_fin_ct": "Intérêts courus",
    "tresorerie_passive": "Trésorerie - Passif",
    "ca": "Ventes de marchandises",
    "production_stockee": "Production stockée",
    "autres_produits_expl": "Autres produits d'exploitation",
    "achats_marchandises": "Achats de marchandises",
    "achats_matieres": "Achats de matières premières",
    "var_stocks": "Variation des stocks",
    "autres_charges_expl": "Autres charges d'exploitation",
    "charges_personnel": "Charges de personnel",
    "dotations": "Dotations aux amortissements",
    "resultats_expl": "Résultat d'exploitation",
    "charges_fin": "Charges d'intérêts",
    "produits_fin": "Produits financiers",
    "resultats_fin": "Résultat financier",
    "impots": "Impôt sur les bénéfices",
    "produits_exc": "Produits exceptionnels",
    "charges_exc": "Charges exceptionnels",
    "resultat_net": "Résultat net",
}

_LEX_NORM_BILAN = {c: norm(LEXICON[c]) for c in BILAN_CATS}
_LEX_NORM_CPC = {c: norm(LEXICON[c]) for c in CPC_CATS}

# ---------------------------------------------------------------------------
# Lignes à ignorer
# ---------------------------------------------------------------------------

_SECTION_HEADERS = {
    "actif", "passif", "compte de produit et charge", "produit", "charge",
    "exploitation", "immobilisation", "actif circulant", "passif circulant",
    "tresorerie", "capitaux propre et ressource assimilee", "dette",
    "dette a plus d un an", "dette a court terme", "compte de resultat",
    "produit d exploitation", "charge d exploitation", "produit et charge",
    "resultat", "produit et charge hors activite courante",
    "immobilisation incorporelle corporelle et financiere",
}

_NUM_ONLY = re.compile(r"^[0-9 ]+$")

# Lignes de contrôle d'un CPC : agrégats intermédiaires (« RESULTAT COURANT
# (III+VI) ») sans poste correspondant dans les ratios.
_CONTROL_TOTAL_RE = re.compile(r"^resultat (courant|non courant|avant impot)\b")

# En-têtes de rubrique qui sont aussi des postes réels dès qu'ils portent un
# montant (« Trésorerie » = solde bancaire, fréquent dans les liasses).
_ACCOUNT_SECTIONS = {"tresorerie", "tresorerie actif", "tresorerie passif"}


def is_section_header(label: object, valued: bool = False) -> bool:
    """True si le libellé est un en-tête de rubrique (sans valeur utile)."""
    n = norm(label)
    if not n:
        return True
    if valued and n in _ACCOUNT_SECTIONS:
        return False
    if n in _SECTION_HEADERS:
        return True
    if n.startswith("total ") and "actif" not in n and "passif" not in n:
        return True  # sous-totaux (« Total immobilisations », « Total actif
        # circulant »…) : ne jamais les additionner aux postes détaillés.
    if re.search(r"\bdont\b", n):
        return True  # ventilations « dont … » : déjà comptées dans le total.
    if _NUM_ONLY.match(n):
        return True  # numéros de compte seuls
    return False


def is_control_total(label: object) -> bool:
    """True pour un agrégat de contrôle (« RESULTAT COURANT (III+VI) »…).

    Ces lignes additionnent des rubriques déjà lues (résultat d'exploitation,
    financier…) : les rattacher compterait deux fois, et les afficher comme
    « non reconnues » brouillerait le diagnostic.
    """
    return bool(_CONTROL_TOTAL_RE.match(norm(label)))


def detect_section(label: object) -> str | None:
    """Détecte les marqueurs de rubriques « ACTIF » / « PASSIF » / « CPC ».

    Renvoie « A » / « P » (côtés de bilan) ou « CP » / « CH » / « C »
    (rubriques produits / charges / CPC indifférencié).
    """
    n = norm(label)
    if n in {"actif", "total actif", "total bilan", "actif brut",
             "actif du bilan", "etat actif"}:
        return "A"
    if n in {"passif", "total passif", "total du passif", "passif du bilan",
             "passif brut", "passif total", "etat passif"}:
        return "P"
    if n in {"compte de produit et charge", "produit et charge", "cpc",
             "compte de resultat", "resultat"}:
        return "C"
    if n in {"produit", "produit d exploitation",
             "produit et charge hors activite courante"}:
        return "CP"
    if n in {"charge", "charge d exploitation"}:
        return "CH"
    # Libellés composés fréquents dans les PDF : « BILAN - ACTIF »,
    # « COMPTE DE RÉSULTAT (suite) », « ACTIF NET »… On ne le fait que sur des
    # libellés courts, pour ne pas confondre avec un poste détaillé.
    toks = n.split()
    if 2 <= len(toks) <= 3 and toks[0] in {"actif", "passif", "bilan",
                                           "compte", "total"}:
        if "passif" in toks:
            return "P"
        if "actif" in toks or "bilan" in toks:
            return "A"
        if "compte" in toks and ("resultat" in toks or "produit" in toks):
            return "C"
    return None


def _match_bilan(n: str, side: str | None) -> str | None:
    """Recherche par mots-clés puis par similarité, contrainte de côté.

    ``side`` est le côté déclaré (rubrique ACTIF / PASSIF). Le libellé peut
    lui-même indiquer son côté (« Trésorerie - Passif ») : on le respecte alors
    même que la rubrique aurait été mal détectée.
    """
    lbl_side = "P" if "passif" in n else ("A" if "actif" in n else None)

    def _ok(cat: str) -> bool:
        cat_side = BILAN_CATS[cat][0]
        if side and cat_side != side:
            return False
        if lbl_side and cat_side != lbl_side:
            return False
        return True

    for cat in BILAN_ORDER:
        if not _ok(cat):
            continue
        for kw in BILAN_CATS[cat][1]:
            if kw in n:
                if cat in ("total_actif", "total_passif"):
                    continue
                return cat
    # Repli : similarité avec le libellé canonique.
    best, score = None, 0.0
    for cat, canon in _LEX_NORM_BILAN.items():
        if not _ok(cat):
            continue
        r = SequenceMatcher(None, n, canon).ratio()
        if r > score:
            best, score = cat, r
    return best if score >= 0.82 else None


def categorize_bilan(label: object, side: str | None = None) -> str | None:
    """Rattache un libellé de bilan à une catégorie normalisée."""
    n = norm(label)
    if not n:
        return None
    exact = _BILAN_EXACT.get(n)
    if exact:
        return exact[1] if side == "P" else exact[0]
    cat = _match_bilan(n, side)
    if cat is not None:
        return cat
    # Repli : si la ligne de côté (Actif/Passif) était mal déclarée, on
    # retente sans filtre plutôt que de perdre le poste (ex. « Capital
    # social » alors que la rubrique PASSIF n'a pas été reconnue).
    if side:
        return _match_bilan(n, None)
    return None


def categorize_bilan_totals(label: object) -> str | None:
    """Reconnaît les lignes de totaux de bilan (TOTAL ACTIF / TOTAL PASSIF)."""
    n = norm(label)
    if not n.startswith("total"):
        return None
    if "circulant" in n or "immobilisation" in n or "intermediaire" in n:
        return None  # sous-totaux
    if "actif" in n:
        return "total_actif"
    if "passif" in n:
        return "total_passif"
    return None


def _match_cpc(n: str, side: str | None) -> str | None:
    produits = {"ca", "production_stockee", "autres_produits_expl",
                "produits_fin", "produits_exc", "resultats_expl",
                "resultat_net"}
    for cat in CPC_ORDER:
        if side == "P" and cat not in produits:
            continue
        if side == "C" and cat in produits:
            continue
        for kw in CPC_CATS[cat]:
            if kw in n:
                return cat
    best, score = None, 0.0
    for cat, canon in _LEX_NORM_CPC.items():
        r = SequenceMatcher(None, n, canon).ratio()
        if r > score:
            best, score = cat, r
    return best if score >= 0.82 else None


def categorize_cpc(label: object, side: str | None = None) -> str | None:
    """Rattache un libellé de CPC à une catégorie normalisée.

    ``side`` vaut « P » (rubrique produits), « C » (rubrique charges) ou None.
    """
    n = norm(label)
    if not n:
        return None
    cat = _match_cpc(n, side)
    if cat is not None:
        return cat
    # Repli : rubriques PRODUITS/CHARGES non repérées → on retente sans filtre
    # pour ne pas perdre la ligne.
    if side:
        return _match_cpc(n, None)
    return None


# ---------------------------------------------------------------------------
# Agrégats dérivés
# ---------------------------------------------------------------------------

def _sum(d: dict, *keys: str) -> float:
    return float(sum(float(d.get(k, 0.0) or 0.0) for k in keys))


def derive(bilan: dict[str, float], cpc: dict[str, float]) -> None:
    """Ajoute aux maps annuelles les agrégats nécessaires aux ratios."""
    # --- Bilan -------------------------------------------------------------
    bilan["immobilisations_total"] = _sum(
        bilan, "imm_en_cours", "imm_incorp", "imm_corp", "imm_fin")
    bilan["creances_circulantes"] = _sum(
        bilan, "clients", "etat_actif", "personnel_actif", "autres_creances",
        "charges_a_payer")
    bilan["stocks_total"] = float(bilan.get("stocks", 0.0) or 0.0)
    bilan["tresorerie_nette"] = _sum(bilan, "tresorerie_active") - _sum(
        bilan, "tresorerie_passive")
    comp_propres = (
        _sum(bilan, "capital", "reserve_legale", "reserves", "resultat",
             "subventions_invest", "amortissements_regl")
        - _sum(bilan, "pertes")
    )
    # Si le fichier donne seulement la ligne d'agrégat « Capitaux propres »
    # (capital + réserves + résultat en une seule ligne), on s'en sert.
    bilan["capitaux_propres"] = comp_propres or _sum(
        bilan, "capitaux_propres_declare")
    bilan["dettes_non_courantes"] = _sum(
        bilan, "dettes_fin_lt", "provisions_lt", "produits_a_recevoir")
    bilan["dettes_expl"] = _sum(
        bilan, "dettes_fournisseurs", "dettes_personnel", "dettes_etat",
        "autres_dettes_expl")
    bilan["dettes_fin_ct_total"] = float(bilan.get("dettes_fin_ct", 0.0) or 0.0)
    bilan["dettes_totales"] = (
        bilan["dettes_non_courantes"] + bilan["dettes_expl"]
        + bilan["dettes_fin_ct_total"])
    bilan["total_actif_calc"] = (
        bilan["immobilisations_total"] + bilan["stocks_total"]
        + bilan["creances_circulantes"] + _sum(bilan, "tresorerie_active"))
    bilan["total_passif_calc"] = (
        bilan["capitaux_propres"] + bilan["dettes_non_courantes"]
        + bilan["dettes_expl"] + bilan["dettes_fin_ct_total"]
        + _sum(bilan, "tresorerie_passive"))
    if not bilan.get("total_actif"):
        bilan["total_actif"] = bilan["total_actif_calc"]
    if not bilan.get("total_passif"):
        bilan["total_passif"] = bilan["total_passif_calc"]
    # Trésorerie nette théorique (identité : TN = FR - BFR + dettes fin. CT)
    bilan["fr"] = (bilan["capitaux_propres"] + bilan["dettes_non_courantes"]
                   - bilan["immobilisations_total"])
    bilan["bfr"] = (bilan["stocks_total"] + bilan["creances_circulantes"]
                    - bilan["dettes_expl"])
    bilan["trn_theorique"] = (bilan["fr"] - bilan["bfr"]
                              + bilan["dettes_fin_ct_total"])
    bilan.setdefault("investissements", 0.0)

    # --- CPC ---------------------------------------------------------------
    ca = float(cpc.get("ca", 0.0) or 0.0)
    stockee = float(cpc.get("production_stockee", 0.0) or 0.0)
    cpc["ca_net"] = ca + stockee
    cpc["produits_exploitation"] = cpc["ca_net"] + _sum(
        cpc, "autres_produits_expl")
    cpc["charges_exploitation"] = _sum(
        cpc, "achats_marchandises", "achats_matieres", "var_stocks",
        "autres_charges_expl", "charges_personnel", "dotations")
    cpc["resultat_exploitation_calc"] = (
        cpc["produits_exploitation"] - cpc["charges_exploitation"])
    cpc["achats_nets"] = _sum(cpc, "achats_marchandises", "achats_matieres",
                              "var_stocks")
    cpc["ebe"] = cpc["resultat_exploitation_calc"] + _sum(cpc, "dotations")
    cpc["produits_totaux"] = cpc["produits_exploitation"] + _sum(
        cpc, "produits_fin", "produits_exc")
    cpc["charges_totaux"] = cpc["charges_exploitation"] + _sum(
        cpc, "charges_fin", "impots", "charges_exc")
    cpc["resultat_net_calc"] = cpc["produits_totaux"] - cpc["charges_totaux"]
    if not cpc.get("resultat_net"):
        cpc["resultat_net"] = cpc["resultat_net_calc"]
    if not cpc.get("resultats_expl"):
        cpc["resultats_expl"] = cpc["resultat_exploitation_calc"]


def derive_years(bilan_by_year: dict, cpc_by_year: dict) -> None:
    """Dérive chaque exercice, puis calcule les investissements nets."""
    years = sorted(set(bilan_by_year) | set(cpc_by_year))
    for y in years:
        derive(bilan_by_year.setdefault(y, {}), cpc_by_year.setdefault(y, {}))
    # Investissements = variation des immobilisations nettes (2 exercices)
    if years:
        first = bilan_by_year[years[0]]
        first["investissements"] = 0.0
    for i in range(1, len(years)):
        prev = bilan_by_year[years[i - 1]]
        cur = bilan_by_year[years[i]]
        cur["investissements"] = (cur.get("immobilisations_total", 0.0)
                                  - prev.get("immobilisations_total", 0.0))
