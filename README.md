# 📊 Analyse des états financiers (Streamlit)

Application **Streamlit** qui :

1. **lit un bilan et un compte de produits et charges** (Excel ou CSV) ;
2. **calcule et vérifie les ratios financiers** sur plusieurs exercices (PCG) ;
3. **repère les anomalies** (incohérences + dépassements de seuils, tendances) ;
4. **rédige une synthèse** — par règles (hors ligne, par défaut) ou avec une
   IA optionnelle (OpenAI / Anthropic / Ollama).

---

## Démarrage rapide

```powershell
# 1. Environnement (une seule fois)
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 2. Lancement
.\.venv\Scripts\streamlit run app.py
# puis ouvrir http://localhost:8501
```

> Sur ce poste, Python 3.12 est installé et l'environnement `.venv` est déjà
> créé : il suffit de lancer `.\.venv\Scripts\streamlit run app.py`.

**Tester immédiatement :** cliquer sur **🧪 Exemple** dans la barre latérale
(PME de distribution sur 3 exercices, 2023-2025, avec des anomalies volontaires).

---

## Format des données

### Classeur Excel (recommandé)

Télécharger le **gabarit** via la barre latérale (`gabarit_etats_financiers.xlsx`) :

| Onglet | Contenu |
|---|---|
| `Bilan` | Postes Actif / Passif, **une colonne par exercice** |
| `CPC` | Produits / Charges / Résultat, une colonne par exercice |
| `Lisez-moi` | Rappels de saisie |

- En-têtes de colonnes : une **année** (`2023`, `2024`…) **ou** `N`, `N-1`,
  `N-2` (l'année de référence se règle dans la sidebar).
- Montants en euros : `1234,5` / `1 234,5` / `(500)` / `-12,5` acceptés.
- Les lignes `Total …` (hors *Total actif / Total passif*) et les
  ventilations `dont …` sont **ignorées automatiquement**.
- Les onglets peuvent être nommés librement (le classement se fait par le nom
  puis par le contenu, enfin par la colonne « État » si elle existe).

### CSV

- **Deux fichiers** : `bilan.csv` + `cpc.csv`, ou
- **Un seul fichier** avec une colonne `État` (`bilan` / `cpc` / `actif` /
  `passif` / `produits` / `charges`).
- Séparateur `;` ou `,` détecté automatiquement (UTF-8 ou Windows-1252).

### Mapping des libellés

Les libellés sont rapprochés du **Plan Comptable Général** en trois étapes :
rubriques `ACTIF` / `PASSIF` / `PRODUITS` / `CHARGES` repérées dans la
première colonne → mots-clés normalisés (accents/pluriels) → similarité avec
les libellés canoniques. **Les lignes non reconnues sont listées** dans l'onglet
📊 *Données* : elles n'entrent dans aucun ratio.

---

## Onglets de l'application

| Onglet | Contenu |
|---|---|
| **📐 Ratios** | 16 ratios par exercice, écart N/N-1, statut 🟢🟡🔴 + aide mémoire |
| **📊 Données** | Agrégats normalisés (CA, EBE, FR, BFR, trésorerie…), tables bilan/CPC, lignes non reconnues |
| **🚨 Anomalies** | Contrôles de cohérence + dépassements de seuils, triés par gravité |
| **📝 Synthèse** | Synthèse Markdown (téléchargeable) + export Excel complet + enrichissement IA optionnel |

### Ratios calculés

Liquidité générale et réduite · coefficient de trésorerie · taux
d'endettement · autonomie financière · couverture des intérêts · croissance
du CA · marges d'exploitation et nette · ROE · ROA · pouvoir libératoire du
BFR · BFR en jours · délais clients (DSO) et fournisseurs (DPO) · rotation
des stocks.

### Contrôles / anomalies

- **Cohérence** : bilan équilibré (actif = passif), résultat net du bilan =
  résultat du CPC, identité `trésorerie nette = FR − BFR (+ dettes fin. CT)`.
- **Solvabilité** : capitaux propres négatifs, endettement > 2 / > 3,
  liquidité < 1,2 / < 1, couverture des intérêts < 3 / < 2.
- **Activité** : chute du CA > 10 % / 20 %, recul du résultat net > 40 %,
  stocks en hausse alors que le CA baisse, renouvellement du parc < 50 % des
  dotations.
- **Exploitation** : BFR > 90 jours, DSO > 90 j, DPO > 90 j, trésorerie
  nette négative ou en baisse > 30 %.

Seuils modifiables : `core/ratios.py → SEUILS` et
`core/anomalies.py → SEUILS`.

---

## Synthèse

- **Mode par règles (par défaut, hors ligne)** : rédige 5 sections
  (activité, structure, BFR/trésorerie, vigilance, recommandations) à partir
  des ratios et anomalies — aucun service externe.
- **Mode IA (optionnel)** : dans la sidebar → *🤖 Synthèse assistée*, choisir
  **OpenAI** (clé API), **Anthropic** (clé API) ou **Ollama** (local,
  `http://localhost:11434`), puis bouton **✨ Enrichir avec l'IA**. Le digest
  JSON envoyé contient uniquement agrégats, ratios et anomalies.

---

## Structure du projet

```
app.py                 # interface Streamlit
requirements.txt
core/
  pcg.py               # référentiel PCG : normalisation, catégories, agrégats
  parser.py            # lecture Excel/CSV, détection d'exercices, mapping
  ratios.py            # calcul des ratios + statuts (seuils)
  anomalies.py         # contrôles de cohérence + règles d'anomalie
  synthesis.py         # synthèse par règles + appels LLM (optionnels)
  gabarit.py           # génération du classeur vierge
  export.py            # export Excel des résultats
sample/
  generer_exemple.py   # jeu d'exemple 2023-2025 (généré, vérifié)
tests/
  test_pipeline.py     # bout en bout (bilan, ratios, anomalies, synthèse, export)
  test_csv.py          # CSV, colonnes N/N-1, formats numériques
```

### Tests

```powershell
.\.venv\Scripts\python tests\test_pipeline.py
.\.venv\Scripts\python tests\test_csv.py
```

---

## Notes et limites

- Les délais (DSO/DPO) sont calculés en base **CA HT / achats HT** : ils
  sous-estiment légèrement les délais réels si le fichier ne fournit pas les
  montants TTC.
- `Variation des stocks` : conserver le signe du fichier (accroissement en
  négatif dans les charges).
- L'EBE est reconstitué (`résultat d'exploitation + dotations`), le BFR au
  format simplifié `(stocks + créances d'exploitation) − dettes
  d'exploitation`.
- Les seuils sont des conventions usuelles : à ajuster selon le secteur
  (`core/ratios.py`, `core/anomalies.py`).
