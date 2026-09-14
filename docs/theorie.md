# Théorie — la matière à apprendre pendant le projet

Ce document n'est pas une révision de dernière minute. C'est ce qu'il faut apprendre **au fur et à mesure**, parce que chaque section débloque une partie du code à écrire.

Une notion apprise la veille d'en avoir besoin se retient, parce qu'on s'en sert le lendemain. La même notion révisée trois semaines plus tard ne se retient pas. L'ordre ci-dessous suit donc les phases du [plan de travail](plan-de-travail.md), pas la logique interne de la matière.

Chaque section donne l'essentiel, puis les liens vers la documentation de référence.

## Dans quel ordre apprendre

| Quand | Sections | Ce que ça débloque |
|---|---|---|
| **Avant de commencer** | §1 Flask · §3 Motifs de conception | La fabrique d'application, les blueprints, le registre de règles. Sans ça, tu recopies sans comprendre. |
| **Début de phase 1** | §4 Unicode · §5 Segmentation | La normalisation et les empans de caractères. Le piège se paie comptant. |
| **Milieu de phase 1** | §2 Persistance · §7 Tests | Les trois entités de base et la première suite de tests. |
| **Avant la phase 2** | §6 spaCy et dépendances | La détection du passif — la pièce maîtresse. À lire avant d'écrire la règle, pas pendant. |
| **Phase 3** | §8 Sécurité · §9 Python | Pendant le durcissement. |
| **25/09** | §10 Questions du jury | À voix haute. |

**Si tu ne lis que trois sections avant de commencer : §1, §3 et §4.** Les deux premières décrivent le code que tu écris tous les jours ; la troisième évite un bug qui coûte une journée entière.

Les sections ne se lisent pas d'une traite. Prends celle dont tu as besoin, écris le code correspondant, reviens. C'est le seul mode de lecture qui fonctionne pour ce genre de document.

---

## 1. Flask et le cycle d'une requête

> **Tu en as besoin pour écrire :** `app/__init__.py`, `app/config.py`, `app/routes/`.

### Ce qu'il faut savoir

**La fabrique d'application.** `create_app()` construit et renvoie une instance de `Flask` au lieu de la créer au niveau du module. Trois bénéfices, et il faut savoir les citer : on peut instancier plusieurs applications avec des configurations différentes (une pour les tests avec une base en mémoire, une pour la production) ; on évite les imports circulaires entre l'application et ses extensions ; et la configuration devient un paramètre plutôt qu'un état global.

**Les blueprints.** Un blueprint regroupe des routes, des gabarits et des fichiers statiques dans un module réutilisable, enregistré sur l'application au moment de la fabrique. Dans ce projet : `analyze` pour l'utilisateur, `admin` pour la configuration. Sans blueprints, toutes les routes s'entassent dans `__init__.py`.

**Les deux contextes.** Flask maintient un *contexte d'application* (portant `current_app` et `g`) et un *contexte de requête* (portant `request` et `session`). C'est ce qui permet à `request` d'être un objet importable globalement tout en étant différent pour chaque requête traitée. La question classique du jury : « comment `request` peut-il être une variable globale dans une application qui traite plusieurs requêtes ? » — réponse : c'est un mandataire (*proxy*) vers un objet propre au contexte courant.

**La configuration par variables d'environnement.** `app.config.from_object(Config)` où `Config` lit `os.environ`. Le principe : le code est identique partout, seule la configuration change. C'est ce qui rend une conteneurisation ultérieure presque gratuite.

**POST-Redirect-GET.** Après un POST qui modifie quelque chose, renvoyer une redirection plutôt qu'une page. Sinon un rafraîchissement du navigateur rejoue la soumission. À appliquer sur les écrans *Règles* et *Listes de mots*.

### Jinja2 — le moteur de gabarits

Flask utilise Jinja2 pour produire le HTML. Un gabarit (*template*) est un fichier HTML contenant des emplacements que Flask remplit avec des données Python au moment de la requête.

**Où sont les gabarits.** Flask les cherche dans le dossier `templates/` de l'application. Le chemin passé à `render_template` est relatif à ce dossier. Avec la structure `app/templates/analyze/index.html`, l'appel est `render_template("analyze/index.html")`.

**`render_template` — la fonction centrale.** Elle prend toujours **le chemin du fichier template en premier argument**, puis les variables à transmettre en arguments nommés :

```python
render_template("analyze/index.html", texte=mon_texte, score=42)
#                ^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                1. quel fichier       2. variables accessibles dans le HTML
```

Sans le premier argument en chemin de fichier, Jinja essaie de trouver un template portant la valeur de la variable — d'où une erreur `TemplateNotFound` avec le contenu du texte comme nom de fichier.

**Afficher une variable : `{{ }}`**. Dans le template, `{{ texte }}` insère la valeur de la variable `texte`. Par défaut, Jinja **échappe le HTML** automatiquement — `<script>` devient `&lt;script&gt;`. C'est une protection contre les failles XSS (voir §8).

**Logique : `{% %}`**. Les blocs de contrôle permettent des conditions et des boucles :

```html
{% if texte %}
  <p>{{ texte }}</p>
{% endif %}

{% for item in liste %}
  <li>{{ item }}</li>
{% endfor %}
```

**Valeur par défaut.** Une variable non passée par `render_template` n'existe pas dans le template — y accéder provoque une erreur. Deux parades :

- Le filtre `or` : `{{ texte or '' }}` — si `texte` est vide, `None`, ou absent, ça donne une chaîne vide.
- Le test `defined` : `{% if texte is defined %}` — vérifie que la variable a été passée.

**L'héritage de gabarits.** Un gabarit de base (`base.html`) définit la structure commune (en-tête, pied de page) avec des blocs nommés. Les gabarits enfants étendent la base et ne remplissent que les blocs :

```html
{# base.html #}
<html>
<body>
  {% block contenu %}{% endblock %}
</body>
</html>

{# analyze/index.html #}
{% extends "base.html" %}
{% block contenu %}
  <form>...</form>
{% endblock %}
```

Tu n'en as pas besoin tout de suite, mais tu y viendras dès que tu auras deux pages qui partagent une mise en page.

**Le filtre `|safe`** — à manipuler avec précaution. Il désactive l'échappement automatique. Tu en auras besoin pour insérer les balises de surlignage dans le texte analysé, mais uniquement après avoir échappé toi-même le contenu utilisateur (voir §8, XSS et ordre des opérations).

### À lire

- [Application Factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/) — le motif, en vingt lignes
- [Blueprints](https://flask.palletsprojects.com/en/stable/blueprints/)
- [Configuration Handling](https://flask.palletsprojects.com/en/stable/config/)
- [The Application Context](https://flask.palletsprojects.com/en/stable/appcontext/) et [The Request Context](https://flask.palletsprojects.com/en/stable/reqcontext/) — les deux pages qui expliquent le mandataire
- [Jinja — Template Designer Documentation](https://jinja.palletsprojects.com/en/stable/templates/)
- [Méthodes HTTP](https://developer.mozilla.org/fr/docs/Web/HTTP/Methods) et [codes de statut](https://developer.mozilla.org/fr/docs/Web/HTTP/Status) — savoir pourquoi tu renvoies 400 plutôt que 500 sur un fichier refusé

---

## 2. Persistance : ORM, sessions, migrations

> **Tu en as besoin pour écrire :** `app/models.py`, `app/repositories.py`, et pour lancer les migrations.

### Ce qu'il faut savoir

**Ce qu'est un ORM.** Une correspondance entre des classes Python et des tables relationnelles. Tu manipules des objets, la bibliothèque produit le SQL. L'intérêt : pas de SQL concaténé à la main, donc pas d'injection SQL, et un modèle de données lisible dans le code. Le coût : une couche d'indirection, et des requêtes parfois moins efficaces que du SQL écrit à la main.

**La session SQLAlchemy.** Elle tient une *unité de travail* : elle accumule les modifications d'objets et les écrit en base au `commit()`. Elle assure aussi l'*identity map* — deux requêtes sur la même ligne renvoient le même objet Python. Savoir expliquer `add`, `commit`, `rollback`, et pourquoi un objet lu reste attaché à sa session.

**Le problème N+1.** Charger 100 documents puis accéder à `document.analyses` pour chacun déclenche 101 requêtes. La solution est le chargement anticipé (`selectinload`, `joinedload`). C'est la question de performance que pose un jury qui connaît les ORM.

**Les migrations.** Alembic (via Flask-Migrate) compare tes modèles à l'état de la base et génère un script de migration. Chaque migration est versionnée et réversible. Point important à comprendre : la génération automatique ne détecte pas tout (renommages de colonnes, contraintes complexes) — il faut relire le script produit.

**Pourquoi SQLite ici.** Zéro configuration, un fichier, parfait pour une démonstration locale. Ses limites, à assumer : un seul écrivain à la fois, et un typage souple. Pour ce projet mono-utilisateur, aucune de ces limites ne se manifeste.

### À lire

- [Flask-SQLAlchemy](https://flask-sqlalchemy.readthedocs.io/en/stable/)
- [SQLAlchemy ORM Quick Start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html) — la syntaxe 2.0, celle que tu utilises
- [Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) — à lire vraiment, c'est le concept le plus mal compris de SQLAlchemy
- [Flask-Migrate](https://flask-migrate.readthedocs.io/en/latest/) et [le tutoriel Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

---

## 3. Les motifs de conception du projet

> **Tu en as besoin pour écrire :** `services/rules/base.py`, `services/rules/runner.py`, `services/extraction/registry.py`. C'est aussi la section la plus rentable en soutenance.

Cette section est **la plus rentable en soutenance**. Un jury évalue la conception davantage que le nombre de fonctionnalités, et ton projet applique volontairement quelques motifs bien identifiés.

### Le registre (*registry*)

Une interface commune, plusieurs implémentations, et un dictionnaire qui associe une clé à l'implémentation. Ajouter un cas = ajouter une classe et une ligne d'enregistrement, sans toucher au code appelant.

Le projet l'applique **deux fois** : les extracteurs de format (`services/extraction/`) et les règles (`services/rules/`). Savoir dire que c'est la même idée employée à deux endroits vaut mieux que de décrire les deux séparément.

Le principe sous-jacent porte un nom : le **principe ouvert/fermé** — ouvert à l'extension, fermé à la modification.

### L'inversion de dépendance

`services/linguistics.py` est le seul fichier qui importe spaCy. Les règles dépendent de *ton* interface, pas de la bibliothèque. Conséquence concrète et démontrable : changer de modèle, ou remplacer spaCy, ne touche qu'un fichier. C'est le seul isolement du projet qui rapporte vraiment quelque chose — et il faut savoir expliquer pourquoi les autres n'en valaient pas la peine.

### Le motif *repository*

`repositories.py` concentre l'accès aux données. Les services ne connaissent pas SQLAlchemy, les *repositories* ne connaissent pas la linguistique. L'argument à faire valoir : **le moteur de règles se teste sans base de données**, donc sa suite de tests s'exécute en direct devant le jury en une fraction de seconde.

### La *dataclass* comme objet de transport

`Finding` est une `dataclass` : une structure de données sans comportement, qui circule entre les couches. Toutes les règles renvoient la même forme, quelle que soit leur granularité — d'où une couche d'affichage qui ne change plus quand on ajoute une règle.

Attention au piège de nommage : tu auras probablement **deux** `Finding`, la `dataclass` de transport et l'entité persistée en base. Nomme-les distinctement (`Finding` / `FindingRecord`) ou documente clairement la différence, sinon la question tombera en soutenance et l'hésitation se verra.

### À lire

- [dataclasses](https://docs.python.org/3/library/dataclasses.html) et [PEP 557](https://peps.python.org/pep-0557/)
- [abc — Abstract Base Classes](https://docs.python.org/3/library/abc.html) — pour la classe de base `Rule`
- [typing](https://docs.python.org/3/library/typing.html) et [PEP 484](https://peps.python.org/pep-0484/) — `check(document) -> list[Finding]` se lit tout seul

---

## 4. Texte, encodages et Unicode

> **Tu en as besoin pour écrire :** `services/normalization.py` — et pour ne pas décaler tous tes surlignages.

C'est la partie invisible du projet, et celle qui produit les bugs les plus coûteux.

### Ce qu'il faut savoir

**Encodage contre jeu de caractères.** Unicode attribue un numéro à chaque caractère ; UTF-8, UTF-16, CP1252 sont des façons de coder ces numéros en octets. Un fichier n'annonce pas son encodage : on le devine. D'où `charset-normalizer`.

**Le BOM.** Trois octets en tête d'un fichier UTF-8 écrit par certains outils Windows. Non retirés, ils deviennent un caractère invisible collé au premier mot, qui fausse le premier token de chaque document.

**La normalisation Unicode — le point à vraiment comprendre.** « é » s'écrit de deux façons : un caractère précomposé (U+00E9), ou « e » suivi d'un accent combinant (U+0065 U+0301). Visuellement identiques, différents pour Python. Sans normalisation NFC, `"été" == "été"` peut être faux et tes décomptes de fréquence se dédoublent.

**Le piège qui va te coûter une journée si tu ne le vois pas venir.** La normalisation **change la longueur de la chaîne**. Vérifié dans ce projet :

| Opération | Longueur avant → après |
|---|---|
| NFC sur `e` + accent combinant | 6 → 5 |
| Suppression du trait d'union conditionnel (U+00AD) | 8 → 7 |
| Apostrophe courbe U+2019 → U+0027 | 7 → 7 |

Or tes `Finding` portent des empans de caractères (`char_start`, `char_end`). **Conclusion opérationnelle : normalise une seule fois, à l'entrée, stocke le texte normalisé comme texte de référence, et calcule tous les empans dessus.** Ne conserve jamais le texte d'origine pour l'affichage tout en calculant les positions sur le texte normalisé : les surlignages se décaleraient d'un caractère par accent décomposé, et tu chercherais la cause pendant des heures.

### À lire

- [Unicode HOWTO](https://docs.python.org/3/howto/unicode.html) — la meilleure introduction, en français dans l'esprit sinon dans la lettre
- [unicodedata](https://docs.python.org/3/library/unicodedata.html) — `normalize()`, `category()`
- [UAX #15 — Unicode Normalization Forms](https://unicode.org/reports/tr15/) — la référence, à survoler pour comprendre NFC/NFD/NFKC/NFKD
- [charset-normalizer](https://charset-normalizer.readthedocs.io/en/latest/)

---

## 5. Segmentation et tokenisation

> **Tu en as besoin pour écrire :** `services/segmentation.py` et `services/tokenization.py`.

### Ce qu'il faut savoir

**Segmenter n'est pas découper sur le point.** « M. Dupont a versé 3,14 M€ le 1er janv. 2026. » contient un seul point final et quatre points internes. D'où `pysbd`, qui embarque les règles d'abréviation par langue.

**Contrainte propre au projet :** la segmentation ne doit jamais franchir une frontière de paragraphe. Un titre sans point final suivi d'un paragraphe produirait sinon une phrase de 80 mots — et ta règle principale est justement la longueur de phrase. Le faux positif serait spectaculaire en démonstration.

**Tokeniser en français.** Les cas à traiter, et à savoir énumérer :

- **Élisions** (`l'`, `d'`, `qu'`, `n'`, `jusqu'`) — à séparer, sinon chaque déterminant fusionne avec son nom et le décompte lexical est faux.
- **Traits d'union** — à séparer pour les clitiques (`est-ce`, `dit-il`, `celui-ci`), à conserver pour les composés (`week-end`, `arc-en-ciel`). **Il n'existe pas de règle formelle** : une liste d'exceptions est inévitable. C'est un bon exemple à présenter — une tâche qui semble mécanique et qui ne l'est pas.
- **Abréviations et nombres** (`M.`, `etc.`, `3,14`, `1er`).

**Deux décisions de conception à savoir défendre :**

1. *La ponctuation est conservée*, marquée par un indicateur plutôt que supprimée. Le texte reste reconstructible, et les décomptes filtrent quand ils en ont besoin. Supprimer serait une perte d'information irréversible.
2. *Forme brute et forme normalisée sont stockées toutes les deux.* On bascule entre sensible et insensible à la casse sans repasser sur le texte.

**Le numéro de version du tokeniseur.** Ton tokeniseur *va* changer en cours de projet. Sans numéro de version par document et sans commande de retokenisation, tu te retrouves avec une base mêlant deux découpages incompatibles. C'est une précaution qui se remarque en soutenance : elle montre que tu as anticipé ta propre évolution.

### À lire

- [pySBD](https://github.com/nipunsadvilkar/pySBD) — lire le README, il explique bien le problème
- [spaCy — Linguistic Features : Tokenization](https://spacy.io/usage/linguistic-features) — la section sur les exceptions de tokenisation

---

## 6. spaCy et l'analyse en dépendances

> **Tu en as besoin pour écrire :** `services/linguistics.py` et la détection du passif dans `services/rules/fr.py`.

C'est la section technique du projet, et **le passage de la soutenance qui te distinguera**. À maîtriser sérieusement.

### Ce qu'il faut savoir

**Ce qu'est un pipeline spaCy.** `nlp(texte)` fait passer le texte par une suite de composants — tokeniseur, étiqueteur morpho-syntaxique, analyseur en dépendances, lemmatiseur, reconnaisseur d'entités — chacun enrichissant le même objet `Doc`. Savoir que le modèle est un réseau de neurones entraîné sur un corpus annoté, et non un ensemble de règles.

**Charger le modèle une seule fois**, au démarrage de l'application. `spacy.load()` occupe quelques centaines de mégaoctets et prend plusieurs secondes ; l'appeler par requête rendrait l'application inutilisable.

**Les attributs d'un token** : `text` (forme de surface), `lemma_` (forme canonique), `pos_` (catégorie grammaticale universelle), `dep_` (fonction syntaxique), `head` (le token dont il dépend), `morph` (traits morphologiques). Le tiret bas signifie « la version lisible » — sans lui, tu obtiens un identifiant numérique.

**L'analyse en dépendances.** Chaque token pointe vers son gouverneur avec une étiquette de relation. Les étiquettes suivent la nomenclature *Universal Dependencies*, commune à toutes les langues — ce qui est précisément ce qui rend ton projet extensible.

**Les étiquettes qui t'intéressent :**

| Étiquette | Sens |
|---|---|
| `aux:pass` | auxiliaire de passif |
| `nsubj:pass` | sujet d'un verbe au passif |
| `obl:agent` | complément d'agent (« **par** le conseil ») |
| `cop` | copule (« la porte **est** ouverte ») |

**Pourquoi une expression régulière échoue.** Une regex `être + participe passé` ne peut pas distinguer :

- *La décision a été prise* — passif véritable
- *Elle est allée à Paris* — passé composé avec l'auxiliaire *être*
- *La porte est ouverte* — description d'un état
- *Il est convaincu* — adjectif

C'est l'exemple à montrer en soutenance. Trois phrases où la regex se trompe, la même analyse grammaticale qui tranche.

### Résultats mesurés sur ce projet — à connaître avant d'y compter

Test effectué avec `fr_core_news_sm` 3.8.0 sur les six phrases citées dans la synthèse, en ne retenant que le critère `aux:pass` / `nsubj:pass` :

| Phrase | Attendu | Détecté |
|---|---|---|
| La décision a été prise par le conseil. | passif | ✅ passif |
| La décision a été prise. | passif | ❌ non détecté |
| Le rapport sera publié demain. | passif | ✅ passif |
| Elle est allée à Paris. | pas passif | ❌ passif |
| La porte est ouverte. | pas passif | ❌ passif |
| Il est convaincu de son bon droit. | pas passif | ❌ passif |

**2 sur 6.** Ce résultat n'invalide pas l'approche, mais il change ce que tu dois prévoir :

- **Le complément d'agent est une béquille du modèle.** Même phrase avec « par le conseil » : `aux:pass` correct. Sans lui : `été` est étiqueté `cop` et le passif disparaît. Le modèle s'appuie fortement sur le « par ».
- **« Elle est allée » est un faux positif propre à corriger** : `lemma_` vaut `aller`. Une liste des verbes intransitifs conjugués avec *être* (aller, venir, partir, arriver, rester, tomber, naître, mourir, devenir…) élimine toute cette famille en quelques lignes.
- **« La porte est ouverte » est un cas honnêtement ambigu** — la synthèse le reconnaît. Ce n'est pas une erreur à corriger, c'est une limite à assumer et à savoir énoncer.
- **Les heuristiques ne sont pas un ornement.** La synthèse évoque l'analyse en dépendances « complétée par des heuristiques » : en réalité, elles portent la moitié du résultat. Prévois-en le temps.

Conséquence pratique : le plan prévoit en phase 2 de **constituer le jeu d'essai avant d'écrire la règle**. Ce test confirme que c'est indispensable et pas une coquetterie méthodologique.

Premier réflexe en phase 2 : tester le modèle `fr_core_news_md` sur le même jeu d'essai. S'il fait nettement mieux, une ligne de `requirements.txt` change et tu gagnes des heures d'heuristiques.

### À lire

- [spaCy 101](https://spacy.io/usage/spacy-101) — à lire en entier, c'est court
- [Linguistic Features](https://spacy.io/usage/linguistic-features) — la section *Dependency Parse* en particulier
- [Processing Pipelines](https://spacy.io/usage/processing-pipelines)
- [API : Token](https://spacy.io/api/token) — la liste complète des attributs
- [Universal Dependencies — relations](https://universaldependencies.org/u/dep/) et [spécificités du français](https://universaldependencies.org/fr/)

---

## 7. Tests

> **Tu en as besoin pour écrire :** `tests/conftest.py` et toute la suite de tests.

### Ce qu'il faut savoir

**Unitaire contre intégration.** Un test unitaire vérifie une fonction isolée, sans base ni réseau — tes règles et ta normalisation. Un test d'intégration traverse plusieurs couches — une requête HTTP jusqu'à la base. Les premiers sont rapides et nombreux, les seconds lents et peu nombreux.

**Les fixtures pytest.** Une fonction décorée par `@pytest.fixture` produit un objet que les tests reçoivent en paramètre par simple correspondance de nom. Elles gèrent la préparation et le nettoyage. Savoir expliquer la portée (`function`, `module`, `session`) : le chargement du modèle spaCy mérite une fixture de portée `session`, sinon la suite de tests devient interminable.

**Le client de test Flask.** `app.test_client()` émet des requêtes sans lancer de serveur. C'est ce qui rend tes tests de routes rapides et déterministes.

**Test-driven sur la règle du passif.** Le plan fixe cet ordre en phase 2 : le jeu d'essai d'abord, la règle ensuite. Ce n'est pas dogmatique — c'est que sans jeu d'essai, tu n'as aucun moyen de savoir si ta dernière heuristique a amélioré ou dégradé l'ensemble. Le tableau de la section 6 est le début de ce jeu d'essai.

### À lire

- [pytest — Get Started](https://docs.pytest.org/en/stable/getting-started.html)
- [pytest — Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [Flask — Testing Flask Applications](https://flask.palletsprojects.com/en/stable/testing/)

---

## 8. Sécurité

> **Tu en as besoin pour écrire :** le rendu surligné de l'écran de résultats, et l'extraction de fichiers.

Un jury pose presque toujours une question de sécurité. Ces quatre points suffisent, et ils sont tous réellement présents dans ton code.

### Ce qu'il faut savoir

**XSS et ordre des opérations.** Tu affiches un texte fourni par l'utilisateur, dans lequel tu insères des balises de surlignage. **Échapper d'abord, insérer les balises ensuite.** Dans l'autre sens, tu échappes tes propres balises (page cassée) ou tu laisses passer celles de l'utilisateur (faille). Jinja échappe automatiquement, mais `|safe` désactive cette protection — et tu en auras besoin pour le surlignage, donc tu es responsable de l'échappement à cet endroit précis.

**Corollaire à ne pas manquer :** l'échappement change la longueur du texte (`<` devient `&lt;`, quatre caractères de plus). Tes empans deviennent faux si tu échappes tout puis insères. La méthode correcte : découper le texte aux frontières de signalements, échapper chaque segment, puis assembler avec les balises.

**XML et fichiers de bureau.** `.docx` et `.odt` sont des archives ZIP contenant du XML. Un XML hostile peut faire exploser la mémoire par expansion d'entités (« bombe XML », dite *milliard de rires*). D'où `defusedxml`, qui désactive ces fonctionnalités.

**Validation des fichiers déposés.** Trois contrôles, dans cet ordre : taille maximale (`MAX_CONTENT_LENGTH`, appliqué par Flask lui-même avant que ton code ne voie quoi que ce soit), octets d'en-tête plutôt qu'extension (une extension se renomme), et nom de fichier assaini si tu l'écris sur le disque.

**Secrets.** `SECRET_KEY` signe les cookies de session. Elle vit dans `.env`, jamais dans le dépôt — d'où le couple `.env` / `.env.example`. Savoir dire ce qu'un attaquant ferait s'il l'obtenait : forger des sessions.

### À lire

- [OWASP — XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [defusedxml](https://pypi.org/project/defusedxml/) — le README décrit chaque attaque, c'est de la bonne matière de soutenance
- [Flask — Uploading Files](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
- [python-docx](https://python-docx.readthedocs.io/en/latest/)

---

## 9. Python, le langage

> **Transverse.** À reprendre quand une syntaxe du projet reste opaque.

### Ce qu'il faut savoir

**Paquets et modules.** Un dossier contenant `__init__.py` est un paquet. `from app.services.rules import base` suit l'arborescence. Savoir expliquer pourquoi `app/__init__.py` contient la fabrique : c'est le point d'entrée du paquet, et `FLASK_APP=app` suffit alors à ce que Flask trouve `create_app` tout seul.

**Classes de base abstraites.** `Rule` définit `check()` sans l'implémenter. Toute règle en hérite et doit fournir sa version. C'est le contrat que le registre exploite.

**Annotations de type.** `def check(self, document: Document) -> list[Finding]:` documente et se vérifie. Elles ne sont pas contrôlées à l'exécution — question fréquente, et la bonne réponse est « non, sauf outil dédié ».

**Environnements virtuels.** `.venv` isole les dépendances du projet de l'installation système. `requirements.txt` les liste. Savoir dire pourquoi le modèle spaCy y est épinglé par URL : il devient une dépendance ordinaire, installée par un simple `pip install -r`, en local comme dans l'image Docker.

### À lire

- [PEP 8](https://peps.python.org/pep-0008/) — le style, et ruff l'applique pour toi
- [PEP 484](https://peps.python.org/pep-0484/) — annotations de type
- [abc](https://docs.python.org/3/library/abc.html)

---

## 10. Questions probables du jury

Prépare une réponse de deux phrases à chacune. C'est le meilleur rapport temps investi / points gagnés de toute cette liste.

> **Sers-t'en aussi comme contrôle d'acquis, dès maintenant.** Après avoir écrit une partie du code, reviens ici et cherche la question qui la concerne. Si tu ne sais pas y répondre en deux phrases, c'est que la section correspondante n'est pas acquise — et il vaut mieux le découvrir le jour où tu écris le code que trois semaines plus tard.

**Sur la conception**

1. Pourquoi une fabrique d'application plutôt qu'une instance globale ?
2. Vous avez le même motif à deux endroits. Lequel, et pourquoi ce choix ?
3. Comment ajoute-t-on un format de fichier ? Une langue ? Une règle ?
4. Pourquoi `Finding` porte-t-il toujours un empan de caractères, même pour une règle qui mesure un pourcentage ?
5. Pourquoi isoler spaCy derrière un seul fichier, alors que vous n'avez pas isolé SQLAlchemy ?

**Sur les choix assumés**

6. Pourquoi refuser le PDF ? *(l'extraction casse les paragraphes, donc la segmentation, donc la mesure de longueur de phrase — le cœur de l'outil)*
7. Pourquoi pas de score global sur 100 ? *(toute formule serait arbitraire et indéfendable ; des décomptes par principe se justifient)*
8. Pourquoi ne pas faire réécrire le texte par un modèle de langue ? *(cela déplacerait tout le travail intéressant hors du code présenté)*

**Sur la technique**

9. Montrez une phrase où une expression régulière se trompe et où votre règle réussit.
10. Quel est le taux d'erreur de votre détection du passif ? *(tu as un chiffre mesuré — le donner franchement vaut infiniment mieux que d'esquiver)*
11. Comment évitez-vous les failles XSS sur du texte fourni par l'utilisateur ?
12. Que se passe-t-il si je dépose un fichier de 500 Mo ? Un `.docx` corrompu ? Un texte vide ?
13. Pourquoi normaliser en NFC, et qu'est-ce que cela change pour vos positions de caractères ?

**Sur les limites**

14. Qu'est-ce qui ne marche pas dans votre projet ? — **prépare vraiment cette réponse.** Une limite énoncée spontanément et précisément inspire davantage confiance qu'une liste de réussites.
15. Que feriez-vous avec trois semaines de plus ?

---

*Documents liés : [synthese-projet-langage-clair.md](synthese-projet-langage-clair.md) pour les décisions de conception, [plan-de-travail.md](plan-de-travail.md) pour le calendrier, [setup-projet-vscode.md](setup-projet-vscode.md) pour l'environnement.*
