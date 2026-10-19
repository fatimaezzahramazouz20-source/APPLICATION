# -*- coding: utf-8 -*-
"""Lecture des fichiers d'états financiers (Excel / CSV) et mapping PCG."""

from __future__ import annotations

import io
import math
import re
from typing import Any

import pandas as pd

from . import pcg

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_N_RE = re.compile(r"\bn\s*-?\s*(\d)\b")

_ETAT_LABELS = {"actif", "passif", "bilan", "cpc", "produits", "charges",
                "produit et charge", "etat", "section", "type",
                "etat financier"}

_BILAN_MARKERS = [
    "capital social", "immobilisation", "total actif", "tresorerie",
    "creance client", "emprunt", "reserve", "passif",
]
_CPC_MARKERS = [
    "vente de marchandise", "prestation de service", "chiffre d affaire",
    "charge de personnel", "resultat d exploitation", "achats de marchandise",
    "resultat net", "produit",
]


# ---------------------------------------------------------------------------
# Lecture brute
# ---------------------------------------------------------------------------

def read_files(files: list[tuple[str, bytes]]) -> list[tuple[str, pd.DataFrame]]:
    """Lit chaque fichier et renvoie une liste (nom, DataFrame brut)."""
    out: list[tuple[str, pd.DataFrame]] = []
    for name, content in files:
        lower = name.lower()
        buf = io.BytesIO(content)
        if lower.endswith((".xlsx", ".xlsm")):
            sheets = pd.read_excel(buf, sheet_name=None, header=None)
            for sheet_name, df in sheets.items():
                out.append((f"{name} — {sheet_name}", df))
        elif lower.endswith(".xls"):
            sheets = pd.read_excel(buf, sheet_name=None, header=None,
                                   engine="xlrd")
            for sheet_name, df in sheets.items():
                out.append((f"{name} — {sheet_name}", df))
        else:
            df = _read_csv(buf)
            out.append((name, df))
    return out


def _read_csv(buf: io.BytesIO) -> pd.DataFrame:
    raw = buf.read()
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover
        text = raw.decode("utf-8", errors="replace")
    sep = ";" if text.count(";") > text.count(",") else ","
    return pd.read_csv(io.StringIO(text), sep=sep, header=None)


# ---------------------------------------------------------------------------
# Nombres au format français
# ---------------------------------------------------------------------------

def parse_number(value: Any) -> float | None:
    """Convertit une cellule en float (« 1 234,56 », « (500) », « -30 »…)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    s = str(value).strip()
    if not s or s.lower() in {"-", "n/a", "na", "nan", "x", ""}:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    s = s.replace("\u00a0", " ").replace("\u202f", " ")
    s = s.replace("€", "").replace("eur", "").strip().replace(" ", "")
    if s.endswith("-"):
        neg, s = True, s[:-1]
    if s.startswith("-"):
        neg, s = True, s[1:]
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        decimals = len(s.split(",")[-1])
        s = s.replace(",", ".") if 0 < decimals <= 2 else s.replace(",", "")
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x


# ---------------------------------------------------------------------------
# Détection de la structure d'une feuille
# ---------------------------------------------------------------------------

def _header_year(cell: Any) -> tuple[str, int] | None:
    """« 2024 » -> ('Y', 2024) ; « Exercice N-1 » -> ('N', 1)."""
    if cell is None or (isinstance(cell, float) and math.isnan(cell)):
        return None
    if isinstance(cell, (int, float)):
        y = int(cell)
        return ("Y", y) if 1990 <= y <= 2100 else None
    text = str(cell)
    m = _YEAR_RE.search(text)
    if m:
        return ("Y", int(m.group(0)))
    n = pcg.norm(text)
    m = _N_RE.search(n)
    if m:
        return ("N", int(m.group(1)))
    if n in {"n", "annee n", "annee", "exercice n", "exercice"}:
        return ("N", 0)
    return None


def _find_header_row(df: pd.DataFrame, scan: int = 8) -> int:
    for i in range(min(scan, len(df))):
        for cell in df.iloc[i, 1:]:
            if _header_year(cell) is not None:
                return i
    return 0


def _classify_sheet(name: str, df: pd.DataFrame) -> str:
    """Classe une feuille : 'bilan' ou 'cpc' (par le nom puis le contenu)."""
    n_name = pcg.norm(name)
    if any(k in n_name for k in ("cpc", "produit et charge", "produit",
                                 "charge", "compte de resultat", "trep",
                                 "resultat")):
        return "cpc"
    if "bilan" in n_name:
        return "bilan"
    sample = " ".join(pcg.norm(v) for v in df.iloc[:, 0].head(60)
                      if isinstance(v, str))
    b_score = sum(1 for k in _BILAN_MARKERS if k in sample)
    c_score = sum(1 for k in _CPC_MARKERS if k in sample)
    return "cpc" if c_score > b_score else "bilan"


def _detect_etat_column(df: pd.DataFrame) -> int | None:
    """Repère une éventuelle colonne « État » (actif/passif/cpc) d'un CSV."""
    for col in range(min(3, df.shape[1])):
        header = pcg.norm(df.iat[0, col]) if len(df) else ""
        if header not in _ETAT_LABELS or not header:
            continue
        values = {pcg.norm(v) for v in df.iloc[1:, col].dropna().head(50)}
        known = {"actif", "passif", "bilan", "cpc", "produits", "charges"}
        if values and values <= known | {"cpc", "bilan"}:
            return col
    return None


# ---------------------------------------------------------------------------
# Extraction année par année
# ---------------------------------------------------------------------------

class SheetData:
    def __init__(self, name: str, df: pd.DataFrame):
        self.name = name
        self.kind = _classify_sheet(name, df)
        self.rows: list[dict] = []          # libellé + valeurs par exercice
        self.unmapped: list[dict] = []
        self.years: set[int] = set()
        self._parse(df)

    # -- parsing ---------------------------------------------------------
    def _parse(self, df: pd.DataFrame) -> None:
        if df.empty or df.shape[1] < 2:
            return
        etat_col = _detect_etat_column(df)
        h = _find_header_row(df)
        label_col = 0 if etat_col != 0 else 1
        # Colonnes d'exercices
        col_year: dict[int, tuple[str, int]] = {}
        for c in range(df.shape[1]):
            if c in (label_col, etat_col):
                continue
            hy = _header_year(df.iat[h, c])
            if hy is not None:
                col_year[c] = hy
        if not col_year:
            return
        ref_year = self._infer_ref_year(col_year, df, h)
        year_cols: dict[int, int] = {}
        for c, (kind, val) in col_year.items():
            if kind == "Y":
                year_cols[c] = val
            elif ref_year:
                year_cols[c] = ref_year - val
        self.year_cols = year_cols
        self.years |= set(year_cols.values())
        # Lignes
        side = None      # « A »/« P » (bilan), « CP »/« CH » (CPC)
        section = None   # « BILAN » | « CPC »
        for i in range(h + 1, len(df)):
            label = df.iat[i, label_col]
            if label is None or (isinstance(label, float) and math.isnan(label)):
                continue
            label = str(label).strip()
            if not label:
                continue
            # 1) Totaux de bilan : lignes de contrôle (Total actif / passif)
            tot = pcg.categorize_bilan_totals(label)
            if tot and section != "CPC":
                values, has_value = self._row_values(df, i, year_cols)
                if has_value:
                    self._record(label, tot, values, "bilan")
                continue
            # 2) Marqueurs de rubriques (ACTIF / PASSIF / PRODUITS / …)
            sec = pcg.detect_section(label)
            if sec:
                if sec in ("A", "P"):
                    side, section = sec, "BILAN"
                elif sec == "C":
                    side, section = None, "CPC"
                else:
                    side, section = sec, "CPC"
                continue
            # 3) Éventuelle colonne « État » d'un CSV
            etat = pcg.norm(df.iat[i, etat_col]) if etat_col is not None else None
            if etat in {"actif", "passif"}:
                side = "A" if etat == "actif" else "P"
                section = "BILAN"
            elif etat in {"cpc", "bilan", "produits", "charges",
                          "produit et charge"}:
                section = "BILAN" if etat == "bilan" else "CPC"
                side = (None if etat in {"cpc", "bilan", "produit et charge"}
                        else ("CP" if etat == "produits" else "CH"))
            if pcg.is_section_header(label):
                continue
            values, has_value = self._row_values(df, i, year_cols)
            if not has_value:
                continue
            kind = self.kind
            if section == "BILAN":
                kind = "bilan"
            elif section == "CPC":
                kind = "cpc"
            if kind == "bilan":
                cat = pcg.categorize_bilan(
                    label, side if side in ("A", "P") else None)
            else:
                cat = pcg.categorize_cpc(
                    label, {"CP": "P", "CH": "C"}.get(side))
                if cat == "dotations" and "reprise" in pcg.norm(label):
                    values = {c: -v for c, v in values.items()}
            self._record(label, cat, values, kind)

    def _row_values(self, df: pd.DataFrame, i: int,
                    year_cols: dict[int, int]) -> tuple[dict[int, float], bool]:
        values: dict[int, float] = {}
        has_value = False
        for c in year_cols:
            if c >= df.shape[1]:
                continue
            v = parse_number(df.iat[i, c])
            if v is not None:
                has_value = True
                values[c] = v
        return values, has_value

    def _record(self, label: str, cat: str | None, values: dict, kind: str):
        entry = {"libelle": label, "categorie": cat, "values": values,
                 "kind": kind}
        self.rows.append(entry)
        if cat is None:
            self.unmapped.append(entry)

    @staticmethod
    def _infer_ref_year(col_year: dict, df: pd.DataFrame,
                        h: int) -> int | None:
        """Année de référence si les colonnes sont nommées « N », « N-1 »…"""
        if not any(kind == "N" for kind, _ in col_year.values()):
            return None
        found = [v for kind, v in col_year.values() if kind == "Y"]
        if found:
            return max(found)
        return pd.Timestamp.today().year - 1

    # -- agrégation ------------------------------------------------------
    def build(self, years: list[int]) -> tuple[dict, dict]:
        bilan = {y: {} for y in years}
        cpc = {y: {} for y in years}
        for row in self.rows:
            cat = row["categorie"]
            if cat is None:
                continue
            target = bilan if row["kind"] == "bilan" else cpc
            for c, v in row["values"].items():
                y = getattr(self, "year_cols", {}).get(c)
                if y is None:
                    continue
                bucket = target.setdefault(y, {})
                bucket[cat] = float(bucket.get(cat, 0.0)) + float(v)
        return bilan, cpc

    def value_of(self, row: dict, year: int) -> float | None:
        for c, v in row["values"].items():
            if getattr(self, "year_cols", {}).get(c) == year:
                return v
        return None


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def parse_files(files: list[tuple[str, bytes]],
                ref_year: int | None = None) -> dict:
    """Parse les fichiers et renvoie un dictionnaire normalisé."""
    sheets_raw = read_files(files)
    sheets = [SheetData(name, df) for name, df in sheets_raw
              if not df.empty]
    if not sheets:
        raise ValueError("Aucune donnée exploitable dans le fichier fourni.")

    years: set[int] = set()
    for s in sheets:
        years |= s.years
    if not years:
        raise ValueError(
            "Aucun exercice détecté : les colonnes doivent porter une année "
            "(ex. « 2024 ») ou être nommées « N », « N-1 »…")
    year_list = sorted(years)

    bilan_by_year: dict[int, dict] = {y: {} for y in year_list}
    cpc_by_year: dict[int, dict] = {y: {} for y in year_list}
    unmapped_rows: list[dict] = []

    for s in sheets:
        b, c = s.build(year_list)
        for y in year_list:
            for k, v in b.get(y, {}).items():
                bilan_by_year[y][k] = bilan_by_year[y].get(k, 0.0) + v
            for k, v in c.get(y, {}).items():
                cpc_by_year[y][k] = cpc_by_year[y].get(k, 0.0) + v
        for row in s.unmapped:
            unmapped_rows.append({
                "Feuille": s.name,
                "État": "Bilan" if row["kind"] == "bilan" else "CPC",
                "Libellé": row["libelle"],
                **{str(y): s.value_of(row, y) for y in year_list},
            })

    has_bilan = any(any(vals.values()) for vals in bilan_by_year.values())
    has_cpc = any(any(vals.values()) for vals in cpc_by_year.values())
    if not has_bilan:
        raise ValueError(
            "Aucune ligne de bilan reconnue. Vérifiez que le fichier "
            "contient un onglet « Bilan » avec les postes (Actif / Passif).")
    if not has_cpc:
        raise ValueError(
            "Aucun poste de produits et charges reconnu. Vérifiez que le "
            "fichier contient un onglet « CPC » (ventes, achats, charges…).")

    pcg.derive_years(bilan_by_year, cpc_by_year)

    def _table(mapping: dict) -> pd.DataFrame:
        rows = []
        for cat in sorted({k for y in mapping for k in mapping[y]}):
            rows.append({"Catégorie": _CAT_LABELS.get(cat, cat),
                         **{str(y): mapping[y].get(cat, 0.0) for y in year_list}})
        return pd.DataFrame(rows)

    return {
        "years": year_list,
        "bilan": bilan_by_year,
        "cpc": cpc_by_year,
        "bilan_table": _table(bilan_by_year),
        "cpc_table": _table(cpc_by_year),
        "unmapped": pd.DataFrame(unmapped_rows),
        "sheets": [{"nom": s.name, "type": s.kind} for s in sheets],
    }


_CAT_LABELS = {
    "imm_en_cours": "Immobilisations en cours",
    "imm_incorp": "Immobilisations incorporelles",
    "imm_corp": "Immobilisations corporelles",
    "imm_fin": "Immobilisations financières",
    "immobilisations_total": "→ Immobilisations nettes (total)",
    "stocks": "Stocks",
    "stocks_total": "→ Stocks",
    "clients": "Créances clients",
    "etat_actif": "Créances fiscales / État",
    "personnel_actif": "Créances sur personnel",
    "autres_creances": "Autres créances",
    "charges_a_payer": "Charges à payer",
    "creances_circulantes": "→ Créances d'exploitation (total)",
    "tresorerie_active": "Trésorerie - Actif",
    "tresorerie_passive": "Trésorerie - Passif",
    "tresorerie_nette": "→ Trésorerie nette",
    "total_actif": "TOTAL ACTIF (déclaré)",
    "total_actif_calc": "→ Total actif (calculé)",
    "total_passif": "TOTAL PASSIF (déclaré)",
    "total_passif_calc": "→ Total passif (calculé)",
    "capital": "Capital social / apports",
    "reserve_legale": "Réserve légale",
    "reserves": "Réserves, report à nouveau…",
    "resultat": "Résultat de l'exercice",
    "pertes": "Perte antérieure (retranchée)",
    "subventions_invest": "Subventions d'investissement",
    "amortissements_regl": "Provisions réglementées",
    "capitaux_propres": "→ Capitaux propres",
    "dettes_fin_lt": "Emprunts et dettes rattachées",
    "provisions_lt": "Provisions pour risques et charges",
    "produits_a_recevoir": "Produits à recevoir",
    "dettes_non_courantes": "→ Dettes à + d'un an",
    "dettes_fournisseurs": "Dettes fournisseurs",
    "dettes_personnel": "Dettes sur rémunérations",
    "dettes_etat": "Dettes fiscales et sociales",
    "autres_dettes_expl": "Autres dettes d'exploitation",
    "dettes_expl": "→ Dettes d'exploitation",
    "dettes_fin_ct": "Emprunts / intérêts court terme",
    "dettes_totales": "→ Dettes totales",
    "fr": "→ Fonds de roulement (FR)",
    "bfr": "→ Besoin en fonds de roulement (BFR)",
    "trn_theorique": "→ Trésorerie nette théorique (FR-BFR)",
    "investissements": "Investissements (variation immob. nettes)",
    "ca": "Ventes & production vendue",
    "production_stockee": "Production stockée / déstockée",
    "ca_net": "→ Chiffre d'affaires net",
    "autres_produits_expl": "Autres produits d'exploitation",
    "achats_marchandises": "Achats de marchandises",
    "achats_matieres": "Achats de matières premières",
    "var_stocks": "Variation des stocks",
    "achats_nets": "→ Achats nets (CAH indicatif)",
    "autres_charges_expl": "Autres charges d'exploitation",
    "charges_personnel": "Charges de personnel",
    "dotations": "Dotations aux amortissements",
    "resultats_expl": "Résultat d'exploitation (déclaré)",
    "resultat_exploitation_calc": "→ Résultat d'exploitation (calculé)",
    "ebe": "→ Excédent brut d'exploitation (EBE)",
    "produits_fin": "Produits financiers",
    "produits_exc": "Produits exceptionnels",
    "charges_fin": "Charges d'intérêts",
    "impots": "Impôt sur les bénéfices",
    "charges_exc": "Charges exceptionnelles",
    "resultat_net": "Résultat net",
    "resultat_net_calc": "→ Résultat net (calculé)",
}
