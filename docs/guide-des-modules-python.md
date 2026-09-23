# Guide des modules Python

*Pour l'explication ligne par ligne du code de l'import et du lien à la base, voir
`code-import-et-base.md`.*

État au 23 septembre 2026. Ce document décrit le code réellement présent dans
`app/`, sans couvrir les tests. Il distingue les modules actifs des emplacements
préparés pour les phases suivantes.

## La chaîne complète

```text
requête HTTP POST /
  -> routes/analyze.py : index()
  -> services/extraction/registry.py : extraire(nom, flux)   (si un fichier est déposé)
  -> services/ingestion/document.py : build_document(texte_brut, langue="fr")
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

La base intervient à un seul endroit de cette chaîne : pendant `run(document)`,
les règles lisent leurs listes de mots via `lexiques.py`, qui passe par le
repository. Une analyse affichée n'est enregistrée que si l'utilisateur le demande,
sous un nom, par un second formulaire (`POST /analyses/`).

---

## Les objets principaux

| Objet | Fichier | Rôle |
|---|---|---|
| `Token` | `services/ingestion/document.py` | Token grossier pour compter les mots ; porte un texte et un empan absolu. |
| `TokenLinguistique` | `services/ingestion/linguistics.py` | Projection d'un token spaCy : lemme, catégorie grammaticale, dépendance, gouverneur et empan absolu. |
| `Sentence` | `services/ingestion/document.py` | Phrase segmentée, avec ses `tokens` et son `analyse` linguistique. |
| `Paragraph` | `services/ingestion/document.py` | Paragraphe et liste de ses phrases. |
| `Document` | `services/ingestion/document.py` | Objet métier remis aux règles ; expose aussi les propriétés aplaties `phrases` et `tokens`. |
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
- Enregistre les blueprints `analyze` et `admin`, et la commande `flask seed`.
- Déclare `GET /health`, qui renvoie `{"status": "ok"}`.

La fabrique permet d'utiliser `TestConfig` pendant les tests sans modifier la
configuration de l'application lancée localement.

### `app/config.py`

- `Config` lit les variables d'environnement : `SECRET_KEY`, `DATABASE_URL`,
  `MAX_TEXT_LENGTH` et `MAX_UPLOAD_BYTES`.
- `MAX_CONTENT_LENGTH` est interprété par Flask avant que la route ne traite une
  requête avec fichier.
- `MAX_FORM_MEMORY_SIZE` est aligné sur `MAX_CONTENT_LENGTH`. Flask 3.1 plafonne
  à part les champs non-fichier, à 500 000 octets par défaut, et lève un 413
  avant la route : sans cet alignement, un texte collé trop long recevrait le
  message du dépassement de taille au lieu de celui de `MAX_TEXT_LENGTH`.
- `TestConfig(Config)` active `TESTING` et utilise une base SQLite en mémoire.

### `app/cli.py`

Porte la commande `flask seed`, enregistrée dans la fabrique par
`app.cli.add_command(seed)`. Sous Flask 3.1, une commande ajoutée à `app.cli`
reçoit d'office le contexte d'application : pas besoin de `@with_appcontext`.

- `AMORCE` est le chemin de `data/seeds/lexiques.json`, la source versionnée des
  listes de mots (D-12).
- `charger_amorce()` lit le JSON sous une forme unique,
  `{liste: {langue: {expression: remplacement}}}` : une liste JSON, comme celle
  des verbes, devient un dict sans remplacement grâce à `dict.fromkeys()`.
- `amorcer_lexiques()` passe chaque liste à `repositories.amorcer_liste()` et
  renvoie un bilan. `flask seed` l'affiche ; la fixture de test `base_amorcee`
  l'appelle aussi, si bien que les tests et l'application s'amorcent par le même
  chemin.

Lire un fichier n'est pas le travail du repository : c'est pourquoi le JSON est
lu ici, et seulement transmis au repository.

---

## Routes et interface

### `app/routes/analyze.py`

Le blueprint `bp` porte quatre routes et deux fonctions d'appui.

**`index()`**, sur `GET /` et `POST /`, analyse et affiche ; elle n'enregistre rien.

- En `GET`, elle affiche simplement le formulaire.
- En `POST`, elle prend le texte à la source la plus explicite : un fichier
  déposé s'il y en a un, sinon `request.form["texte"]`. Un fichier passe par
  `extraire(fichier.filename, fichier.stream)`.
- Chaque refus sort aussitôt par `return page(erreur=...)` : une `ExtractionError`,
  dont le message est affiché tel quel, un texte plus long que `MAX_TEXT_LENGTH`,
  ou un texte vide — « Aucun texte à analyser. »
- Sinon elle appelle `build_document(texte_brut, langue="fr")` et rend
  `page(document=document, findings=run(document), nom_fichier=...)`.

**`enregistrer()`**, sur `POST /analyses/`, enregistre sous un nom le texte qui vient
d'être analysé. Le formulaire renvoie le texte normalisé dans un champ caché, jamais
les signalements : la route relance `build_document()` et `run()`, pour ne pas se fier
à des empans venus du navigateur. Le nom est nettoyé (`" ".join(nom.split())`) et
limité à `NOM_MAX` caractères ; un nom vide réaffiche l'analyse avec un bandeau, un
champ caché vide ou trop long répond 400. Puis `repositories.enregistrer_analyse()`,
un `flash()` et une redirection vers `/analyses/<id>` : POST-Redirect-GET.

**`relire(analysis_id)`**, sur `GET /analyses/<id>`, reconstruit le `Document` depuis le
texte enregistré et rend la page avec les `FindingRecord`, sans relancer les règles.
Un `FindingRecord` porte les mêmes attributs qu'un `Finding` (D-6) : `surligner()` et
le gabarit le lisent tel quel. Identifiant inconnu : 404.

**`analyses()`**, sur `GET /analyses/`, rend la liste des analyses enregistrées.

**`resumer(findings, langue)`** compte les signalements par règle avec `Counter`, zéros
compris : la liste part de `regles(langue)`, pas des seules règles qui ont trouvé
quelque chose.

**`page(...)`** est le rendu unique de l'écran d'analyse. Elle calcule elle-même
`surligner(document.texte, findings)` et `resumer(...)` quand un document est fourni,
et ajoute toujours `extensions` et `nom_max`. Le paramètre `analyse` distingue une
analyse relue, qui affiche son nom, d'une analyse fraîche, qui propose de l'enregistrer.

`page()` existe aussi parce que les routes ne sont pas le seul chemin vers cet écran.
`envoi_trop_volumineux()`, décoré par `@bp.app_errorhandler(413)`, y passe aussi :
Flask refuse une requête trop lourde pendant la lecture de son corps, avant de la
router, donc `index()` n'est jamais appelée et aucun `try` ne pourrait l'attraper.
Le gestionnaire est déclaré `app_errorhandler` et non `errorhandler` — un 413 levé
avant le routage n'appartient à aucun blueprint — et il renvoie bien le code 413 :
rien n'a été analysé.

Entre les deux, la route vérifie `MAX_TEXT_LENGTH`. L'attribut `maxlength` du
gabarit n'existe que dans le navigateur ; un envoi direct le contourne.

La route ne connaît ni spaCy ni SQLAlchemy : elle orchestre les services et rend
le résultat. Elle ne connaît pas non plus les formats : la liste vient de
`extensions_supportees()`, et le gabarit s'en sert à la fois pour l'attribut
`accept` du champ de dépôt et pour la ligne qui énumère les formats.

### `app/routes/admin.py`

Le blueprint `admin`, préfixe `/listes`, enregistré dans la fabrique. Il sert
l'écran d'édition des listes de mots.

- `LISTES` associe à chaque nom de liste un libellé et un booléen : ses entrées
  portent-elles un remplacement ? C'est ce qui décide de la colonne affichée et
  de ce qui est obligatoire à l'ajout.
- `nettoyer(saisie)` applique `normalize()` puis réduit les espaces. Les règles
  cherchent les expressions dans le texte normalisé : une apostrophe courbe
  collée depuis un traitement de texte ne correspondrait jamais sans ce passage.
- `listes()` (`GET /listes/`) rend toutes les listes.
- `ajouter(liste_id)` (`POST /listes/<id>/entrees`) nettoie, met l'expression en
  minuscules — la règle ignore la casse, deux casses feraient un doublon —, puis
  refuse une expression vide, un remplacement manquant ou un doublon. Pour une
  liste sans remplacement, un remplacement envoyé est ignoré.
- `supprimer(entree_id)` (`POST /listes/entrees/<id>/supprimer`).

Les deux routes d'écriture répondent par `flash()` puis une redirection vers
`/listes/#liste-N` : POST-Redirect-GET, un rafraîchissement ne rejoue rien. Un
identifiant inconnu donne un 404. Comme `analyze.py`, la route ne touche jamais
`db.session` : tout passe par le repository.

### `app/routes/__init__.py`

Fichier vide, qui fait de `routes` un paquet.

---

## Construire le document analysable

Les cinq modules de cette partie vivent dans `app/services/ingestion/` : ensemble,
ils font d'un texte brut un `Document`. `__init__.py` est vide et ne réexporte
rien ; on importe chaque module par son chemin complet, par exemple
`from app.services.ingestion.document import build_document`.

### `app/services/ingestion/normalization.py`

`normalize(texte: str) -> str` applique une seule fois les six transformations :

1. suppression du BOM initial ;
2. fins de ligne Windows ou Mac vers `\n` ;
3. normalisation Unicode NFC ;
4. suppression du trait d'union conditionnel ;
5. apostrophe courbe vers apostrophe droite ;
6. espaces insécables vers espaces ordinaires.

Cette étape peut changer la longueur de la chaîne. C'est pourquoi les empans ne
sont calculés qu'après elle.

### `app/services/ingestion/segmentation.py`

`segment(texte: str) -> list[list[dict]]` sépare d'abord les paragraphes avec
une expression régulière, puis utilise une unique instance de `pysbd.Segmenter`
pour découper les phrases de chaque paragraphe.

Chaque dictionnaire de paragraphe porte `texte`, `start`, `end` et `phrases`.
Chaque dictionnaire de phrase porte aussi ces trois valeurs. Les positions de
pysbd, relatives au paragraphe, sont converties en positions absolues avec
`bloc.start() + span.start`.

### `app/services/ingestion/tokenization.py`

`tokenize(phrase: str, offset: int = 0) -> list[dict]` utilise `re.finditer(r"\S+", phrase)`.
Il s'agit volontairement d'une tokenisation grossière : la ponctuation peut
rester attachée à un mot. `offset` reporte les positions de la phrase vers le
texte complet.

### `app/services/ingestion/linguistics.py`

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

### `app/services/ingestion/document.py`

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

La liste `REGLES` contient une instance partagée de chaque règle, écrite en
clair, dans l'ordre d'affichage du résumé. Une instance et non une classe : une
règle ne garde aucun état sur `self`, elle est donc partagée par toutes les
requêtes.

- `regles(langue=None)` renvoie une copie de toutes les règles, ou seulement
  celles applicables à une langue.
- `run(document, desactivees=frozenset())` exécute les règles applicables, écarte
  les identifiants désactivés, rassemble les findings et les trie par position.

Le tri final est nécessaire au rendu de gauche à droite. Ajouter une règle, c'est
une classe dans le module de sa langue et une ligne dans `REGLES` : ni la route
ni `run()` ne changent.

### `app/services/rules/__init__.py`

Réexporte `Finding`, `Rule`, `REGLES`, `regles` et `run`. Le module `en.py` est
vide pour l'instant : l'import de ses classes et leurs lignes dans `REGLES` seront
les seules modifications de `runner.py`.

### `app/services/rules/seuils.py`

`SEUILS` est la donnée numérique par règle et par langue. `seuil(rule_id, langue)`
renvoie un entier ou `None`, ce qui permet à une règle de ne pas s'exécuter sur
une langue non couverte sans lever de `KeyError`.

### `app/services/rules/lexiques.py`

Ne contient plus de données depuis le 21 septembre : il lit la base.

- `connecteurs_lourds(langue)` renvoie `lire_liste("connecteurs_lourds", langue)`,
  un dictionnaire `{expression: remplacement}`.
- `verbes_conjugues_avec_etre(langue)` renvoie
  `frozenset(lire_liste("verbes_conjugues_avec_etre", langue))`.

Les deux signatures sont celles d'avant le passage en base : aucune règle n'a eu
à changer. Une langue sans liste donne un dictionnaire ou un ensemble vide, jamais
une `KeyError`.

Le module passe par le repository plutôt que par les modèles : tout le SQL reste
dans `repositories.py`. Les règles dépendent donc de la base, mais seulement à
travers ces deux fonctions ; elles s'exécutent dans un contexte d'application —
celui de la requête, ou celui de la fixture `base_amorcee` en test.

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

## Persistance : listes de mots et analyses enregistrées

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

`Analysis` représente une analyse que l'utilisateur a choisi d'enregistrer. Elle
porte un `nom` obligatoire et une date `cree_le` en UTC, appartient à un
`DocumentRecord` et possède une collection de `FindingRecord`. La relation
`findings` déclare `order_by="FindingRecord.id"` : relus, les signalements
reviennent dans l'ordre de `run()`, celui des rangs de `data-findings`.

### `app/models/finding.py`

`FindingRecord` est le reflet SQLAlchemy d'un `Finding`. Il porte les mêmes
informations utiles au rendu, mais aussi `analysis_id` qui le rattache à son
analyse. La séparation évite de faire circuler une session SQLAlchemy dans le
moteur de règles.

### `app/models/lexique.py`

Deux modèles liés, réunis dans un fichier parce qu'ils ne vont pas l'un sans
l'autre.

- `WordList` — une liste nommée pour une langue, table `word_lists`, unique sur
  (`nom`, `langue`). Sa relation `entrees` supprime ses entrées avec elle.
- `WordEntry` — une entrée, table `word_entries`, unique dans sa liste sur
  `expression`. `remplacement` reste vide pour les verbes conjugués avec *être* :
  une seule table sert les listes avec et sans reformulation.

Les contraintes d'unicité ne sont pas décoratives : ce sont elles qui empêchent
un doublon, maintenant que les listes sont éditables à l'écran.

### `app/models/__init__.py`

Réexporte `db`, `Base`, `maintenant` et les cinq modèles afin que la fabrique et
les migrations puissent les importer depuis `app.models`. C'est parce que
`WordList` et `WordEntry` y sont importés que `flask db migrate` les a détectés.

### `app/repositories.py`

Tout le SQL du projet. Aucune linguistique : le repository range et relit, il
ne décide rien.

- `amorcer_liste(nom, langue, entrees)` crée la liste si besoin, ajoute les
  entrées absentes, puis valide la transaction. Elle n'écrase et ne supprime
  jamais rien, et renvoie le nombre d'entrées ajoutées : relancer l'amorce est
  sans risque.
- `lire_liste(nom, langue)` renvoie `{expression: remplacement}` par une
  jointure `word_entries` → `word_lists`. Une liste absente donne un dict vide,
  ce qui est voulu pour une langue non couverte — mais masque aussi une base
  qu'on aurait oublié d'amorcer.

Quatre fonctions servent l'écran d'édition :

- `toutes_les_listes()` — les listes, triées par nom puis par langue.
- `trouver_liste(liste_id)` — une liste ou `None`.
- `ajouter_entree(liste, expression, remplacement)` — renvoie `False` si
  l'expression est déjà dans la liste, sans rien écrire.
- `supprimer_entree(entree_id)` — renvoie l'expression et l'id de la liste, ou
  `None`. Les deux valeurs sont lues avant `commit()` : après validation, l'objet
  supprimé ne peut plus être relu.

Trois fonctions servent les analyses enregistrées :

- `enregistrer_analyse(nom, document, findings, nom_fichier=None)` — crée le
  `DocumentRecord`, l'`Analysis` et ses `FindingRecord` en une transaction, et
  renvoie l'id. C'est la seule traduction `Finding` → `FindingRecord` du projet :
  `FindingRecord(**asdict(finding))`, possible parce que les deux types ont les
  mêmes champs. La `source` se déduit de `nom_fichier`. Le HTML n'est jamais
  stocké.
- `lire_analyse(analysis_id)` — une analyse ou `None`.
- `toutes_les_analyses()` — la plus récente d'abord.

`Document` et `Finding` ne sont importés que sous `if TYPE_CHECKING:`, pour les
annotations : un import réel créerait le cycle `rules` → `lexiques` →
`repositories` → `rules`.

---

## Extraction de fichiers

### `app/services/extraction/base.py`

Le contrat, et rien d'autre : le type `Extracteur`, c'est-à-dire
`Callable[[BinaryIO], str]` — un extracteur est une fonction, pas une classe, il
n'a aucun état à porter — et les trois exceptions.

Toutes filles d'`ExtractionError`, toutes porteuses d'un message écrit pour être
affiché tel quel : `FormatNonSupporte` quand l'extension n'a pas d'extracteur,
`FichierIllisible` quand le fichier a la bonne extension mais ne s'ouvre pas.

Ce module n'importe rien du projet. C'est ce qui permet à `registry.py`
d'importer les extracteurs, et aux extracteurs d'importer leurs exceptions, sans
cycle d'import. Même rôle que `rules/base.py` pour les règles.

**Un extracteur rend du texte brut.** La normalisation reste le travail de
`build_document()` : un extracteur qui normaliserait lui-même donnerait un second
texte de référence, et l'invariant des positions ne tiendrait plus.

### `app/services/extraction/registry.py`

Le second registre du projet, bâti sur le même motif que celui des règles : une
table écrite en clair.

- `REGISTRE` associe une extension à la fonction qui sait la lire. Le jeu de
  formats est arrêté par décision (D-2), donc l'énumérer se lit mieux qu'un
  enregistrement automatique : tout ce que le programme accepte tient dans
  quatre lignes.
- `extensions_supportees()` renvoie les extensions triées. Le gabarit s'en sert
  pour l'attribut `accept` et pour la ligne des formats : ajouter un extracteur
  met l'interface à jour sans y toucher.
- `extraire(nom_fichier, flux)` choisit d'après la seule extension. Le nom vient
  du client : il ne sert qu'à ce choix, jamais à écrire sur le disque.

Le dictionnaire `_REFUS` traite à part `.pdf` et `.doc` (D-2) : ils ne sont pas
absents du registre par hasard, ils sont refusés pour une raison, et le message
la donne. Le test des refus passe avant la recherche dans `REGISTRE`.

### `app/services/extraction/txt.py`

`decoder(donnees: bytes) -> str` est le cœur du module, et il est partagé avec
`md.py`.

L'encodage n'est écrit nulle part dans un fichier texte : il faut le deviner.
UTF-8 est essayé d'abord — via `utf_8_sig`, qui retire le BOM éventuel — parce
qu'il est dominant et auto-vérifiant : des octets qui n'en sont pas échouent au
lieu de produire un faux texte. Sinon `charset-normalizer` tranche, mais sur une
liste restreinte (`cp1252`, `iso8859_15`, `cp1250`, `cp1251`, `cp1253`,
`utf_16`) : sur un texte court, son heuristique peut élire un encodage asiatique
et rendre des idéogrammes.

Si rien ne convient, `FichierIllisible` est levée. Refuser vaut mieux que rendre
des « Ã© » : sur du mojibake, la segmentation et l'étiquetage seraient faux sans
lever la moindre erreur.

### `app/services/extraction/md.py`

Markdown n'est pas un format de fichier mais une convention d'écriture : le
décodage est celui d'un `.txt`. Six expressions régulières retirent ensuite les
marques — titres, citations, puces, accents de code, emphases — pour qu'elles ne
soient pas comptées comme des mots, et gardent le libellé d'un lien en jetant son
URL. Volontairement minimal, et sans dépendance nouvelle.

### `app/services/extraction/docx.py` et `odt.py`

Les deux formats sont des archives ZIP contenant du XML où l'encodage est
déclaré : aucune devinette. Les deux extracteurs joignent les blocs par une ligne
vide, parce que c'est ce que `segment()` attend pour délimiter un paragraphe.

- `docx.py` lit `docx.paragraphs` via python-docx. Le texte des tableaux est
  ignoré.
- `odt.py` descend l'arbre en profondeur avec `_parcourir()` et retient les
  balises `text:p` et `text:h`. `getElementsByType()` aurait groupé tous les
  paragraphes puis tous les titres : l'ordre de lecture serait perdu.

Les deux enveloppent l'ouverture dans un `try` large — les bibliothèques lèvent
des types variés sur un fichier corrompu — et relèvent `FichierIllisible`.

### `app/services/extraction/__init__.py`

Réexporte l'interface publique : les exceptions et le type venus de `base.py`,
`REGISTRE`, `extensions_supportees()` et `extraire()` venus de `registry.py`.
Même rôle que `rules/__init__.py`.

---

## Frontières à respecter

- Une route orchestre ; elle ne fait ni linguistique ni SQL brut.
- Un extracteur rend du texte brut ; il ne normalise pas, ne segmente pas et
  ne connaît pas Flask.
- `build_document(...)` est le seul point d'entrée de la chaîne linguistique.
- `linguistics.py` est le seul module qui importe spaCy.
- Une règle reçoit un `Document` et renvoie des `Finding`; elle ne connaît ni
  Flask, ni les templates, ni SQLAlchemy.
- Le repository fait de la persistance, jamais de linguistique ; c'est le seul
  module qui écrit du SQL. Une règle y accède indirectement, par `lexiques.py`,
  jamais en important `models`.
