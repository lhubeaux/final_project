# Intégration de spaCy

*14 septembre 2026 — début de phase 2. Mesures faites avec `fr_core_news_sm` 3.8.0.*

**En une phrase :** pysbd découpe, spaCy analyse chaque phrase, `linguistics.py` traduit en objets maison, `build_document()` les rattache, les règles ne voient jamais spaCy.

---

## 1. Un seul fichier importe spaCy

`app/services/linguistics.py` (D-7). Deux rôles : charger le modèle, traduire sa sortie.

**Charger une seule fois** — environ 2 s mesurées. Au premier besoin, puis en cache :

```python
from functools import cache

@cache
def modele():
    return spacy.load("fr_core_news_sm", exclude=["ner"])
```

**Exclure `ner`** : la reconnaissance d'entités nommées ne sert à aucune règle. Composants du modèle : `tok2vec`, `morphologizer`, `parser`, `attribute_ruler`, `lemmatizer`, `ner`.

---

## 2. Analyser les phrases, pas le texte entier

Constat mesuré sur `"Titre du décret\n\nLa décision a été prise par le conseil. Elle est allée à Paris."` :

```
phrases spaCy : [(0, 56), (57, 80)]
phrases pysbd : [(0, 15), (17, 57), (57, 80)]
```

spaCy **fusionne le titre et la phrase suivante** par-dessus la ligne vide, et l'analyse est faussée : `prise` devient complément du nom de `Titre` (`nmod`) au lieu d'être la racine.

**Décision :** pysbd reste la seule autorité de segmentation. spaCy analyse chaque `Sentence` isolément, via `nlp.pipe(textes)` pour traiter par lots.

**Positions** — même addition que le reste de la chaîne :

```
position dans le texte = phrase.start + token.idx
```

Invariant `texte[start:end] == token.text` vérifié.

---

## 3. Projeter dans des objets maison

Laisser les règles lire `token.dep_` sur le `Doc` brut les rendrait dépendantes du modèle d'objets de spaCy, et D-7 ne tiendrait plus. `linguistics.py` projette donc chaque token dans une dataclass maison :

| Champ | Source spaCy | Exemple |
|---|---|---|
| `texte` | `token.text` | `"été"` |
| `lemme` | `token.lemma_` | `"être"` |
| `categorie` | `token.pos_` | `"AUX"` |
| `fonction` | `token.dep_` | `"aux:pass"` |
| `gouverneur` | `token.head.i` | indice du mot gouverneur |
| `start`, `end` | `phrase.start + token.idx` | positions absolues |

Le champ `Document.spacy_doc` est remplacé par cette analyse, rattachée à chaque `Sentence`. Remplacer spaCy ne toucherait que la projection.

---

## 4. Appeler l'analyse dans `build_document()`

Les objets sont gelés, donc l'analyse est fournie à la construction. Coût mesuré : **2,3 ms** par document court. Ni la route ni les règles existantes ne changent (D-3).

---

## 5. La règle du passif

Ce que produit l'analyse :

```
La décision a été prise par le conseil.
  décision nsubj:pass · été aux:pass · conseil obl:agent     → passif ✓

Elle est allée à Paris.
  Elle nsubj:pass · est aux:pass · allée (lemme aller)       → faux positif ✗
```

Logique :

1. Repérer un token `aux:pass`.
2. Son gouverneur est le participe.
3. **Heuristique** — lemme du participe dans la liste des verbes conjugués avec *être* (aller, venir, partir, arriver, rester, tomber, naître, mourir, devenir…) → pas un passif.
4. Aucun dépendant `obl:agent` → passif sans agent, sévérité plus haute.
5. Empan : de l'auxiliaire au participe.

Rappel (D-14) : `aux:pass` / `nsubj:pass` seuls obtiennent **2 sur 6** sur les phrases de référence. Les heuristiques portent la moitié du résultat. *La porte est ouverte* reste ambigu : limite à énoncer, pas bug à corriger.

---

## 6. Ordre de travail

1. **Jeu d'essai d'abord** — `tests/test_passif.py`, une vingtaine de phrases avec `@pytest.mark.parametrize`. Cas ambigus en `@pytest.mark.xfail`.
2. **Fixture de portée session** pour le modèle : `@pytest.fixture(scope="session")`.
3. **`linguistics.py`** — chargement et projection.
4. **Rattachement** dans `build_document()`.
5. **La règle**, puis mesure sur le jeu d'essai.
6. **Tester `fr_core_news_md`** — non installé, nouvelle dépendance à décider. Une ligne de `requirements.txt` si le gain est net.

**Jalon du 18/09 :** *la décision a été prise* est-elle distinguée de *elle est allée à Paris* ?
