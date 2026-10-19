# -*- coding: utf-8 -*-
"""Lecture des états financiers fournis en PDF.

Deux stratégies complémentaires :

1. **tableaux à filets** (cadres tracés) : pdfplumber relit chaque cellule et sa
   position — c'est la voie la plus fidèle ;
2. **PDF sans filets** : les mots sont regroupés en lignes (même ordonnée) puis
   en colonnes grâce à leurs coordonnées horizontales (les colonnes de montants
   sont alignées dans un état financier).

Les pages de continuation (page 2 du bilan, sans ligne d'exercices) sont
rattachées à la page précédente quand la géométrie des colonnes correspond :
les montants restent ainsi rattachés au bon exercice.

Un PDF **image** (scan) ne contient aucun texte extractible : une erreur
explicite ``PdfNoTextError`` est levée, l'utilisateur est invité à fournir la
version numérique ou un fichier Excel/CSV.
"""

from __future__ import annotations

import bisect
import io
import re
import unicodedata
from typing import Any

import pandas as pd

_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_N_RE = re.compile(r"(?:^|\s)n(?:\s*-?\s*\d)?(?:\s|$)", re.IGNORECASE)
# En-tête d'exercice écrit en toutes lettres : « Exercice N-1 », « Clos le
# 31/12/2024 », « Au 31.12.23 »… Il est aligné comme les montants (à droite).
_DATEISH = re.compile(
    r"^(?:[a-z\u00e0-\u00ff.']+[\s.]+)*"
    r"(?:\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{4}|n(?:\s*-?\s*\d)?)$",
    re.IGNORECASE)
_NUM = re.compile(r"^\(?-?\d[\d\s\u00a0\u202f.,]*\)?-?$")

# Écart horizontal (points) sous lequel deux fragments sont recollés : les
# montants écrits « 180 000 » ou « (1 234,56) » sont découpés en plusieurs mots
# par le lecteur PDF, il faut les réunir avant de répartir en colonnes.
_JOIN_GAP = 3.0
_SIGNS = {"-", "(", ")", "\u2013", "\u2212", "+"}

# Regroupement en colonnes : les libellés sont rapprochés (indentation), les
# montants sont alignés à droite (tolérance serrée).
_LABEL_GAP = 8.0    # écart séparant deux blocs de texte d'une même ligne
_LABEL_TOL = 40.0   # tolérance de regroupement des libellés
_NUM_TOL = 6.0      # tolérance de regroupement des montants


class PdfNoTextError(ValueError):
    """PDF sans texte extractible (scan) ou illisible."""


def _is_number(text: Any) -> bool:
    t = str(text).strip()
    return bool(t) and bool(_NUM.match(t))


# Premiers mots d'un en-tête d'exercice : « Exercice 2024 », « Année N-1 »,
# « Au 31/12/2024 »… Ils se collent à l'année qui suit pour former une cellule.
_PREFIXES = re.compile(
    r"(exercices?|annees?|an|au|le|clos|arretes?|situation|periode?s?|du|de"
    r"|des|fin|jusqu|aujourd)")


def _is_header_prefix(text: str) -> bool:
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().strip()
    return bool(s) and bool(_PREFIXES.fullmatch(s))


def _has_year(cells: list) -> bool:
    for c in cells:
        t = str(c).strip()
        if not t:
            continue
        if _YEAR.search(t) or _N_RE.search(t):
            return True
    return False


def _cluster(values: list[float], tol: float = 8.0) -> list[float]:
    """Regroupe des abscisses proches et renvoie leur moyenne."""
    vals = sorted(values)
    out: list[float] = []
    cur: list[float] = []
    for v in vals:
        if cur and v - cur[-1] > tol:
            out.append(sum(cur) / len(cur))
            cur = []
        cur.append(v)
    if cur:
        out.append(sum(cur) / len(cur))
    return out


def _nearest(columns: list[float], pos: float) -> int:
    """Indice de la colonne la plus proche d'une abscisse (colonnes triées)."""
    idx = bisect.bisect_right(columns, pos)
    if idx <= 0:
        return 0
    if idx >= len(columns):
        return len(columns) - 1
    before, after = columns[idx - 1], columns[idx]
    return idx - 1 if (pos - before) <= (after - pos) else idx


def _joinable(a: str, b: str) -> bool:
    """Deux fragments d'un même nombre (« 180 » + « 000 », « ( » + « 500 »)."""
    a, b = a.strip(), b.strip()
    if not a or not b:
        return False
    if a in _SIGNS or b in _SIGNS:
        return True
    return _is_number(a) and _is_number(b)


def _glue(line: list[dict]) -> list[dict]:
    """Recolle les fragments d'un montant séparés par une espace fine."""
    out: list[dict] = []
    for w in line:
        if (out and float(w["x0"]) - float(out[-1]["x1"]) <= _JOIN_GAP
                and _joinable(str(out[-1]["text"]), str(w["text"]))):
            prev = dict(out[-1])
            prev["text"] = str(prev["text"]) + str(w["text"])
            prev["x1"] = w["x1"]
            out[-1] = prev
            continue
        out.append(dict(w))
    return out


def _push_text(cells: list, anchors_lbl: list, anchors_num: list,
               texte: str, pos: float | None, x1: float | None) -> None:
    """Range un bloc de texte : en-tête d'exercice ou libellé.

    Un en-tête tel que « Exercice N-1 » ou « 31/12/2024 » se trouve au-dessus
    de la colonne de montants (alignée à droite) : on l'ancre donc sur sa fin,
    comme les nombres, sinon ses montants ne seraient jamais rattachés.
    """
    if not texte:
        return
    if x1 is not None and _DATEISH.match(texte):
        cells.append((float(x1), texte))
        anchors_num.append(float(x1))
    else:
        cells.append((float(pos), texte))
        anchors_lbl.append(float(pos))


def _same_layout(a: list[float], b: list[float], tol: float = 12.0) -> bool:
    """Vrai si deux pages présentent les mêmes colonnes (à la tolérance près)."""
    if not a or not b or len(a) != len(b):
        return False
    return all(abs(x - y) <= tol for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# Stratégie 1 : tableaux à filets
# ---------------------------------------------------------------------------

def _grids_from_tables(page) -> list[tuple[list[list[str]], list[float],
                                            list[float]]]:
    grids: list[tuple[list[list[str]], list[float], list[float]]] = []
    try:
        tables = page.find_tables()
    except Exception:  # noqa: BLE001 — PDF exotique : on passe au plan B
        return grids
    for table in tables:
        try:
            data = table.extract()
        except Exception:  # noqa: BLE001
            continue
        boxes = [c for row in table.rows for c in row.cells if c]
        if not boxes or len(data) < 2:
            continue
        starts = _cluster([float(c[0]) for c in boxes], tol=10.0)
        if len(starts) < 2:
            continue
        bounds = [(starts[i] + starts[i + 1]) / 2.0
                  for i in range(len(starts) - 1)]
        rows: list[list[str]] = []
        for bbox_row, text_row in zip(table.rows, data):
            line = [""] * len(starts)
            for bbox, txt in zip(bbox_row.cells, text_row):
                if txt is None:
                    continue
                txt = " ".join(str(txt).split())
                if not txt:
                    continue
                if bbox is None:            # cellule fusionnée
                    line[0] = (line[0] + " " + txt).strip()
                    continue
                cx = (float(bbox[0]) + float(bbox[2])) / 2.0
                idx = min(bisect.bisect_left(bounds, cx), len(starts) - 1)
                line[idx] = (line[idx] + " " + txt).strip()
            rows.append(line)
        grids.append((rows, starts, starts))
    return grids


# ---------------------------------------------------------------------------
# Stratégie 2 : mots + coordonnées
# ---------------------------------------------------------------------------

def _grid_from_words(page) -> tuple[list[list[str]], list[float], list[float]]:
    """Grille reconstruite à partir des mots et de leurs coordonnées.

    Les libellés sont alignés à gauche (et peuvent être indentés), les montants
    à droite : on réunit donc les mots d'une même ligne en **blocs de texte**
    (écart faible) et on ancre les colonnes sur les départs de texte et les fins
    de nombre. C'est ce qui permet de distinguer deux blocs côte à côte
    (Actif / PASSIF) et de ne pas couper « Ventes de marchandises ».

    Renvoie ``(lignes, colonnes, signature)`` : la signature est la position des
    colonnes de montants, qui sert à savoir si une page est la suite d'une autre.
    """
    try:
        words = page.extract_words(x_tolerance=2, y_tolerance=2,
                                   keep_blank_chars=False,
                                   use_text_flow=False)
    except Exception:  # noqa: BLE001
        return [], [], []
    if not words:
        return [], [], []
    words = sorted(words, key=lambda w: (float(w["top"]), float(w["x0"])))
    # 1) regroupement en lignes (même ordonnée, tolérance 3 pt)
    lines: list[list[dict]] = []
    tops: list[float] = []
    for w in words:
        top = float(w["top"])
        if lines and abs(top - tops[-1]) <= 3.0:
            lines[-1].append(w)
        else:
            lines.append([w])
            tops.append(top)
    for line in lines:
        line.sort(key=lambda w: float(w["x0"]))
    lines = [_glue(line) for line in lines]
    # 2) cellules : un bloc de texte = un libellé (ou un en-tête d'exercice),
    #    un mot numérique = un montant
    cells_by_line: list[list[tuple[float, str]]] = []
    anchors_lbl: list[float] = []
    anchors_num: list[float] = []
    for line in lines:
        cells: list[tuple[float, str]] = []
        texte, pos, last_x1 = "", None, None
        for w in line:
            x0, x1 = float(w["x0"]), float(w["x1"])
            if _is_number(w["text"]):
                if texte and _is_header_prefix(texte):
                    # « Exercice 2024 » : un seul en-tête, aligné à droite
                    cells.append((x1, f"{texte} {w['text']}".strip()))
                else:
                    _push_text(cells, anchors_lbl, anchors_num, texte, pos,
                               last_x1)
                    cells.append((x1, str(w["text"])))
                anchors_num.append(x1)
                texte, pos = "", None
            else:
                if texte and last_x1 is not None and x0 - last_x1 > _LABEL_GAP:
                    _push_text(cells, anchors_lbl, anchors_num, texte, pos,
                               last_x1)
                    texte, pos = "", None
                if not texte:
                    pos = x0
                texte = (texte + " " + str(w["text"])).strip()
            last_x1 = x1
        _push_text(cells, anchors_lbl, anchors_num, texte, pos, last_x1)
        cells_by_line.append(cells)
    # 3) colonnes : libellés (départs) + montants (fins), quasi confondus fusionnés
    signature = _cluster(anchors_num, tol=_NUM_TOL)
    positions = sorted(_cluster(anchors_lbl, tol=_LABEL_TOL) + signature)
    columns: list[float] = []
    for p in positions:
        if columns and p - columns[-1] <= _NUM_TOL:
            columns[-1] = (columns[-1] + p) / 2.0
        else:
            columns.append(p)
    rows: list[list[str]] = []
    for cells in cells_by_line:
        line_cells = [""] * len(columns)
        for pos, txt in cells:
            idx = _nearest(columns, pos)
            line_cells[idx] = (line_cells[idx] + " " + txt).strip()
        rows.append(line_cells)
    return rows, columns, signature


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def pdf_to_sheets(name: str, content: bytes) -> list[tuple[str, pd.DataFrame]]:
    """Convertit un PDF en « feuilles » (nom, DataFrame brut sans en-tête)."""
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover
        raise PdfNoTextError(
            "La lecture des PDF nécessite la bibliothèque « pdfplumber » "
            "(ajoutez-la aux dépendances).") from exc

    blocks: list[dict] = []
    pages_ok = 0
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for pno, page in enumerate(pdf.pages, start=1):
                grids = _grids_from_tables(page)
                if grids:
                    rows, _cols, signature = max(
                        grids, key=lambda g: len(g[0]) * max(1, len(g[1])))
                else:
                    rows, _cols, signature = _grid_from_words(page)
                rows = [r for r in rows if any(str(c).strip() for c in r)]
                if not rows:
                    continue
                pages_ok += 1
                has_year = any(_has_year(r) for r in rows[:8])
                if (blocks and not has_year
                        and _same_layout(blocks[-1]["signature"], signature)):
                    blocks[-1]["rows"].extend(rows)
                    continue
                blocks.append({"rows": rows, "signature": signature,
                               "page": pno})
    except PdfNoTextError:
        raise
    except Exception as exc:  # noqa: BLE001 — PDF protégé / corrompu
        raise PdfNoTextError(
            f"PDF « {name} » illisible ({exc}). Réenregistrez-le ou fournissez "
            "un fichier Excel/CSV.") from None

    if not pages_ok or not blocks:
        raise PdfNoTextError(
            f"Le PDF « {name} » ne contient aucun texte extractible : il "
            "s'agit probablement d'un document scanné (image). Fournissez la "
            "version numérique du PDF, un Excel ou un CSV.")

    out: list[tuple[str, pd.DataFrame]] = []
    for b in blocks:
        width = max(len(r) for r in b["rows"])
        padded = [list(r) + [""] * (width - len(r)) for r in b["rows"]]
        out.append((f"{name} — p.{b['page']}", pd.DataFrame(padded)))
    return out
