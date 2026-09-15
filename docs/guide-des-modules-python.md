# Guide des modules Python

État au 15 septembre 2026. Ce document décrit le code réellement présent dans
`app/`, sans couvrir les tests. Il distingue les modules actifs des emplacements
préparés pour les phases suivantes.

## La chaîne complète

```text
requête HTTP POST /
  -> routes/analyze.py : index()
  -> services/document.py : build_document(texte_brut, langue="fr")
       -> normalize()
       -> segment()
       -> tokenize()
       -> analyser_phrases() de linguistics.py
  -> rules/run(document)
  -> rendering/surligner(texte, findings)
  -> template HTML
```

La chaîne travaille toujours sur le texte normalisé. Les positions `start` et
`end` sont des index dans cette seule chaîne de référence :

```python
document.texte[start:end] == fragment.texte
```

Le chemin de persistance est volontairement séparé et n'est pas encore branché
à la route : les objets SQLAlchemy existent, mais une analyse affichée n'est pas
encore enregistrée en base.

---

## Les objets principaux

| Objet | Fichier | Rôle |
|---|---|---|
| `Token` | `services/document.py` | Token grossier pour compter les mots ; porte un texte et un empan absolu. |
| `TokenLinguistique` | `services/linguistics.py` | Projection d'un token spaCy : lemme, catégorie grammaticale, dépendance, gouverneur et empan absolu. |
| `Sentence` | `services/document.py` | Phrase segmentée, avec ses `tokens` et son `analyse` linguistique. |
| `Paragraph` | `services/document.py` | Paragraphe et liste de ses phrases. |
| `Document` | `services/document.py` | Objet métier remis aux règles ; expose aussi les propriétés aplaties `phrases` et `tokens`. |
| `Finding` | `services/rules/base.py` | Signalement de transport : règle, principe, sévérité, empan, message et suggestion éventuelle. |
| `DocumentRecord`, `Analysis`, `FindingRecord` | `models/` | Objets persistés par SQLAlchemy ; ils sont distincts des objets métier et de `Finding`. |

Toutes les dataclasses du document sont gelées (`frozen=True`). On ne les modifie
pas après construction : chaque étape fabrique donc des données cohérentes dès
le départ.

---

## Démarrage et configuration

### `app/__init__.py`

Ce module contient la fabrique `create_app(config_class=Config)`.

- Crée l'objet Flask.
- Charge la classe de configuration reçue.
- Initialise SQLAlchemy avec `db.init_app(app)` et les migrations avec
  `migrate.init_app(app, db)`.
- Enregistre le blueprint d'analyse.
- Déclare `GET /health`, qui renvoie `{"status": "ok"}`.

La fabrique permet d'utiliser `TestConfig` pendant les tests sans modifier la
configuration de l'application lancée localement.

### `app/config.py`

- `Config` lit les variables d'environnement : `SECRET_KEY`, `DATABASE_URL`,
  `MAX_TEXT_LENGTH` et `MAX_UPLOAD_BYTES`.
- `MAX_CONTENT_LENGTH` est interprété par Flask avant que la route ne traite une
  requête avec fichier.
- `TestConfig(Config)` active `TESTING` et utilise une base SQLite en mémoire.

### `app/cli.py`

Fichier préparé, actuellement vide. Il accueillera les commandes Flask telles
que l'amorce des listes de mots et la retokenisation.

---

## Routes et interface

### `app/routes/analyze.py`

Le blueprint `bp` porte la route `index()` sur `GET /` et `POST /`.

- En `GET`, elle affiche simplement le formulaire.
- En `POST`, elle lit `request.form["texte"]`, appelle
  `build_document(texte_brut, langue="fr")`, exécute `run(document)`, puis
  appelle `surligner(document.texte, findings)`.
- `Counter` calcule le nombre de signalements par règle, y compris zéro. La liste
  est fondée sur `regles(document.langue)`, pas seulement sur les règles qui ont
  trouvé quelque chose.
- Elle transmet `document`, `findings`, `texte_surligne` et `resume` à
  `render_template("analyze/index.html", ...)`.

La route ne connaît ni spaCy ni SQLAlchemy : elle orchestre les services et rend
le résultat.

### `app/routes/admin.py` et `app/routes/__init__.py`

Fichiers préparés et vides. `admin.py` accueillera les écrans de configuration
des règles, listes de mots et historique ; il n'est pas encore enregistré dans
la fabrique d'application.

---

## Construire le document analysable

### `app/services/normalization.py`

`normalize(texte: str) -> str` applique une seule fois les six transformations :

1. suppression du BOM initial ;
2. fins de ligne Windows ou Mac vers `\n` ;
3. normalisation Unicode NFC ;
4. suppression du trait d'union conditionnel ;
5. apostrophe courbe vers apostrophe droite ;
6. espaces insécables vers espaces ordinaires.

Cette étape peut changer la longueur de la chaîne. C'est pourquoi les empans ne
sont calculés qu'après elle.

### `app/services/segmentation.py`

`segment(texte: str) -> list[list[dict]]` sépare d'abord les paragraphes avec
une expression régulière, puis utilise une unique instance de `pysbd.Segmenter`
pour découper les phrases de chaque paragraphe.

Chaque dictionnaire de paragraphe porte `texte`, `start`, `end` et `phrases`.
Chaque dictionnaire de phrase porte aussi ces trois valeurs. Les positions de
pysbd, relatives au paragraphe, sont converties en positions absolues avec
`bloc.start() + span.start`.

### `app/services/tokenization.py`

`tokenize(phrase: str, offset: int = 0) -> list[dict]` utilise `re.finditer(r"\S+", phrase)`.
Il s'agit volontairement d'une tokenisation grossière : la ponctuation peut
rester attachée à un mot. `offset` reporte les positions de la phrase vers le
texte complet.

### `app/services/linguistics.py`

Ce module est l'unique import de spaCy dans l'application.

- `TokenLinguistique` est une dataclass indépendante de spaCy. Ses champs sont
  `texte`, `lemme`, `categorie`, `fonction`, `gouverneur`, `start` et `end`.
- `modele() -> Language`, décorée par `@cache`, charge `fr_core_news_sm` une
  seule fois et exclut le composant `ner`, inutile ici.
- `analyser_phrases(phrases: list[tuple[str, int]])` reçoit les phrases avec
  leur offset absolu. Elle les traite par lot via `modele().pipe(textes)`, puis
  projette chaque token spaCy en `TokenLinguistique`.

Le `gouverneur` est l'indice du token gouverneur dans l'analyse de la phrase ;
les positions, elles, sont absolues grâce à `offset + token.idx`.

### `app/services/document.py`

Ce fichier rassemble les objets métier `Token`, `Sentence`, `Paragraph` et
`Document`, puis fournit l'unique point d'entrée :

```python
build_document(texte_brut: str, langue: str = "fr") -> Document
```

La fonction normalise le texte, segmente tous les paragraphes, demande en une
fois l'analyse spaCy de toutes les phrases, tokenise chaque phrase et construit
les dataclasses imbriquées. `Sentence.analyse` reçoit la liste de
`TokenLinguistique` correspondante.

Les propriétés `Document.phrases` et `Document.tokens` aplatissent la hiérarchie
pour les règles qui n'ont pas besoin de connaître les paragraphes. Le champ
`spacy_doc` reste présent pour compatibilité de conception mais n'est pas utilisé :
les règles lisent uniquement `Sentence.analyse`.

---

## Moteur de règles

### `app/services/rules/base.py`

`Finding` est une dataclass gelée qui circule entre les règles, le rendu et, plus
tard, le repository. Elle ne dépend pas de la base de données.

`Rule` est une classe abstraite. Une sous-classe définit `id`, `hint`,
`severity` et éventuellement `langues`, puis implémente :

```python
check(document: Document) -> list[Finding]
```

- `s_applique_a(langue)` contrôle par défaut l'appartenance à `langues`.
- `signaler(char_start, char_end, message, suggestion=None, severity=None)`
  fabrique un `Finding` en reprenant l'identité de la règle. La sévérité fournie
  permet une exception ponctuelle, utilisée par la règle du passif sans agent.

### `app/services/rules/runner.py`

Le registre `_registre` contient une instance partagée de chaque règle.

- `@enregistrer` instancie une classe de règle et l'ajoute au registre au moment
  de l'import.
- `regles(langue=None)` renvoie une copie de toutes les règles, ou seulement
  celles applicables à une langue.
- `run(document, desactivees=frozenset())` exécute les règles applicables, écarte
  les identifiants désactivés, rassemble les findings et les trie par position.

Le tri final est nécessaire au rendu de gauche à droite. Ajouter une règle ne
modifie donc ni la route ni le runner.

### `app/services/rules/__init__.py`

Réexporte `Finding`, `Rule`, `enregistrer`, `regles` et `run`. L'import de `fr`
et `en` déclenche l'enregistrement des règles. Le module anglais est vide pour
l'instant, mais son import prépare l'extension.

### `app/services/rules/seuils.py`

`SEUILS` est la donnée numérique par règle et par langue. `seuil(rule_id, langue)`
renvoie un entier ou `None`, ce qui permet à une règle de ne pas s'exécuter sur
une langue non couverte sans lever de `KeyError`.

### `app/services/rules/lexiques.py`

Contient les données linguistiques versionnées :

- `CONNECTEURS_LOURDS` associe chaque expression administrative à une
  reformulation plus simple ; `connecteurs_lourds(langue)` renvoie le dictionnaire
  de la langue ou un dictionnaire vide.
- `VERBES_CONJUGUES_AVEC_ETRE` liste les lemmes qui emploient normalement *être* ;
  `verbes_conjugues_avec_etre(langue)` renvoie le `frozenset` concerné ou un
  ensemble vide.

Déplacer ces listes dans ce module permet d'ajouter une langue par des données,
sans modifier la logique des règles.

### `app/services/rules/fr.py`

Ce fichier contient les règles françaises enregistrées.

- `LongueurPhrase` applique le seuil obtenu avec `seuil("longueur_phrase", langue)`
  à `len(phrase.tokens)`. Elle signale la phrase entière si le seuil est dépassé.
- `_motif(expression)` transforme une entrée de lexique en expression régulière
  tolérante : espaces multiples, casse ignorée, frontières de mots et élision de
  `de` en `d'`.
- `ConnecteursLourds` recherche les expressions les plus longues d'abord. L'ensemble
  `occupes` empêche deux signalements concurrents sur les mêmes caractères.
- `Passif` parcourt `phrase.analyse`. Il cherche `aux:pass` et le cas `cop` observé
  par spaCy lorsque l'agent est absent, écarte les gouverneurs qui ne sont pas
  des `VERB` (attributs comme « est susceptible »), écarte les verbes de
  `verbes_conjugues_avec_etre(document.langue)`, puis cherche un dépendant
  `obl:agent`. Un agent explicite produit une information ; son absence produit
  un avertissement. L'empan couvre le groupe auxiliaire et le participe.

### `app/services/rules/en.py`

Fichier vide, réservé aux règles anglaises.

---

## Rendu HTML sûr

### `app/services/rendering.py`

`surligner(texte: str, findings: list[Finding]) -> Markup` prépare le texte pour
le template.

1. Elle collecte toutes les frontières d'empans.
2. Elle construit les segments entre deux frontières successives.
3. Elle échappe chaque segment avec `escape()` avant de créer une balise HTML.
4. Un segment couvert devient `<mark class="signalement r-...">` et reçoit les
   rangs de ses findings dans `data-findings`.

Cette stratégie prévient l'injection HTML et gère les chevauchements sans créer
de balises `<mark>` imbriquées. Le JavaScript de l'interface utilise ensuite les
attributs `data-findings` pour relier le surlignage aux fiches de détails.

---

## Persistance : présente, pas encore utilisée

### `app/models/base.py`

Déclare `Base`, la base déclarative SQLAlchemy, et `db`, l'extension
`SQLAlchemy(model_class=Base)`. `maintenant()` retourne l'heure UTC au moment de
l'insertion ; la fonction est passée comme valeur par défaut, et non son résultat.

### `app/models/document.py`

`DocumentRecord` représente un texte enregistré. Ses champs principaux sont le
texte normalisé, la langue, la source (`saisie` ou `fichier`), le nom de fichier,
la version du tokeniseur et la date de création. La relation `analyses` supprime
ses analyses enfants si le document est supprimé.

### `app/models/analysis.py`

`Analysis` représente une exécution datée du moteur. Elle appartient à un
`DocumentRecord` et possède une collection de `FindingRecord`.

### `app/models/finding.py`

`FindingRecord` est le reflet SQLAlchemy d'un `Finding`. Il porte les mêmes
informations utiles au rendu, mais aussi `analysis_id` qui le rattache à son
analyse. La séparation évite de faire circuler une session SQLAlchemy dans le
moteur de règles.

### `app/models/__init__.py`

Réexporte `db`, `Base`, `maintenant` et les trois modèles afin que la fabrique et
les migrations puissent les importer depuis `app.models`.

### `app/repositories.py`

Fichier préparé et vide. Il accueillera les fonctions qui traduiront un
`Document` et ses `Finding` en `DocumentRecord`, `Analysis` et `FindingRecord`.
Les règles ne devront jamais l'importer.

---

## Extraction de fichiers : structure préparée

Le dossier `app/services/extraction/` contient actuellement des fichiers vides :
`registry.py`, `txt.py`, `md.py`, `docx.py`, `odt.py` et `__init__.py`.

Ils sont réservés à la phase d'import : un registre choisira un extracteur par
format, puis chaque extracteur renverra du texte avant son passage obligatoire
dans `build_document(texte_brut, langue="fr")`. Les formats ciblés sont `.txt`,
`.md`, `.docx` et `.odt`; `.pdf` et `.doc` resteront refusés.

---

## Frontières à respecter

- Une route orchestre ; elle ne fait ni linguistique ni SQL brut.
- `build_document(...)` est le seul point d'entrée de la chaîne linguistique.
- `linguistics.py` est le seul module qui importe spaCy.
- Une règle reçoit un `Document` et renvoie des `Finding`; elle ne connaît ni
  Flask, ni les templates, ni SQLAlchemy.
- Les repositories, lorsqu'ils seront écrits, feront de la persistance mais pas
  de linguistique.
