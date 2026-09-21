# Soutenance — aide-mémoire

Analyseur de langage clair. État au 21 septembre 2026, phase 3 en cours.
Documentation technique complète : `documentation.md` et `guide-des-modules-python.md`.

---

## 1. Le projet en trente secondes

Une application Flask qui reçoit un texte administratif et signale ce qui l'éloigne
des dix principes de rédaction claire des institutions européennes. Le texte revient
surligné, chaque signalement portant un empan de caractères, un message et, quand
c'est possible, une reformulation.

Ce que l'application **ne fait pas**, et c'est délibéré : pas de note sur 100 (D-10).
Un score invite à optimiser le chiffre ; on veut faire lire le texte.

---

## 2. La chaîne de traitement

```
saisie                fichier
  │                     └─ extraire()   un extracteur par extension
  └─────────┬───────────┘
texte brut
  └─ normalisation      BOM, CRLF, NFC, soft hyphen, apostrophes, insécables
      └─ segmentation   pysbd, sans franchir les paragraphes
          └─ tokenisation   \S+ avec offset
              └─ analyse spaCy   phrase par phrase -> Sentence.analyse
                  └─ Document   paragraphes · phrases · tokens · analyse
                      └─ règles   -> Finding
                          └─ surlignage   <mark> par empan
```

Un seul point d'entrée : `build_document(texte_brut, langue="fr")`. La normalisation
s'y fait une fois pour toutes (D-4) : il est impossible de fabriquer un `Document`
dont le texte ne serait pas le texte de référence.

Les deux chemins d'entrée se rejoignent avant la normalisation. Un extracteur rend du
texte **brut** : s'il normalisait lui-même, il y aurait deux textes de référence.

---

## 3. Le cœur technique : l'invariant des positions

**C'est le point à savoir défendre.** Chaque couche découpe une chaîne et *transporte*
sa position par addition ; elle ne la recalcule jamais.

```
bloc.start()      position du paragraphe dans le texte
+ span.start      position de la phrase dans le paragraphe
= phrase["start"] position de la phrase dans le texte    ─┐ passé en offset
+ match.start()   position du token dans la phrase       ─┘
= token["start"]  position du token dans le texte
```

L'invariant, testé dans `tests/test_positions.py` et réaffirmé sur les signalements
dans `tests/test_rules.py` :

```python
texte[fragment["start"]:fragment["end"]] == fragment["texte"]
```

### Les deux pièges, si on demande « pourquoi si compliqué ? »

- `texte.find(phrase)` pour retrouver une position : échoue dès qu'une phrase se répète
  dans le document — on retombe toujours sur la première occurrence.
- Cumuler les longueurs de fragments : dérive de 2 caractères par ligne vide entre
  paragraphes, invisible au début du texte, fatale à la fin.

### Le corollaire XSS

`surligner()` échappe le HTML **avant** d'insérer les balises, segment par segment entre
les frontières de signalements. Dans l'autre sens on échapperait ses propres balises.
Et l'échappement change les longueurs (`<` devient `&lt;`, 1 caractère → 4) : impossible
d'échapper d'abord le texte entier et de découper ensuite avec les mêmes positions.

Le découpage se fait aux frontières de *tous* les signalements : deux signalements qui
se chevauchent — une phrase trop longue contenant un connecteur lourd — produisent un
segment commun portant les deux classes CSS, et non deux `<mark>` imbriqués.

---

## 4. Architecture et décisions

```
app/
├── __init__.py            create_app()
├── config.py              configuration par variables d'environnement
├── models/                DocumentRecord, Analysis, FindingRecord, WordList, WordEntry
├── repositories.py        tout le SQL — aucune linguistique
├── cli.py                 flask seed : data/seeds/lexiques.json -> base
├── routes/analyze.py      GET/POST /
├── routes/admin.py        /listes/ : écran des listes de mots
├── static/                css/style.css · js/app.js
├── templates/analyze/index.html
└── services/
    ├── document.py        build_document() — le seul point d'entrée
    ├── normalization.py · segmentation.py · tokenization.py
    ├── rendering.py       surligner()
    ├── linguistics.py     unique point de contact avec spaCy
    ├── extraction/        registry · txt · md · docx · odt
    └── rules/
        ├── base.py        Finding (dataclass) + Rule (ABC)
        ├── runner.py      registre plat + run()
        ├── seuils.py      données : seuils par langue
        ├── lexiques.py    lit les listes de mots en base
        └── fr.py · en.py
```

### Les décisions qu'on vous demandera de justifier

| Réf. | Décision | Argument en une phrase |
|---|---|---|
| D-3 | `check()` reçoit un `Document` maison | les règles ne dépendent ni de Flask ni de spaCy, donc leurs tests tournent seuls |
| D-4 | normaliser une seule fois, à l'entrée | une seule vérité de texte, donc des positions comparables partout |
| D-5 | toute règle renvoie un `Finding` portant un empan | le surlignage est générique, il ne connaît aucune règle |
| D-6 | `Finding` (transport) ≠ `FindingRecord` (persistance) | la dataclass ne traîne pas de session SQLAlchemy jusque dans le moteur |
| D-7 | spaCy isolé derrière `services/linguistics.py` | changer de modèle ou s'en passer ne touche aucune règle |
| D-8 | motif de registre, appliqué deux fois | ajouter une règle = une classe et un décorateur, zéro appelant modifié |
| D-10 | pas de score global | voir §1 |
| D-11 | seuils définis par langue | 25 mots en français, 21 en anglais : la longueur moyenne n'est pas la même |
| D-14 | passif = dépendances syntaxiques **+** heuristiques | mesuré : 2 formes sur 6 détectées avec `fr_core_news_sm` seul |

---

## 5. Le moteur de règles

Trois fichiers de code, plus deux fichiers de données (`seuils.py`, `lexiques.py`).

- **`base.py`** — `Finding`, dataclass gelée, et `Rule`, classe abstraite. Une règle
  concrète redéfinit `id`, `hint`, `severity`, puis implémente `check(document)`.
  Elle ne garde **aucun état sur `self`** : l'instance est partagée par toutes les requêtes.
- **`runner.py`** — le décorateur `@enregistrer` instancie la classe et la range dans un
  registre plat ; `run(document)` exécute les règles applicables et trie les signalements
  par position, parce que le surlignage parcourt le texte de gauche à droite.
- **`fr.py`** — les règles elles-mêmes.

### Pourquoi `langues` et pas le nom du fichier ?

Le registre est plat : une fois `fr.py` et `en.py` importés, plus rien ne dit d'où vient
une règle. Il faut donc que la règle porte elle-même l'information. Mieux encore, les deux
règles fondées sur des données ne déclarent pas de liste de langues : elles la déduisent
de leur donnée. Seule `Passif`, qui dépend de l'analyse grammaticale, déclare
`langues = ("fr",)`.

```python
def s_applique_a(self, langue: str) -> bool:
    return seuil(self.id, langue) is not None        # LongueurPhrase
    return bool(connecteurs_lourds(langue))          # ConnecteursLourds
```

Conséquence : ajouter une langue, c'est ajouter une entrée dans `seuils.py` ou
`lexiques.py`. Aucune ligne de code ne change. **C'est ce qui rend l'extension aux
24 langues de l'UE possible sans refonte.**

### Les trois règles livrées

| Règle | Principe | Sévérité | Mécanisme |
|---|---|---|---|
| `longueur_phrase` | P4 — faire court et simple | avertissement | compte les tokens de chaque phrase, compare au seuil de la langue |
| `connecteurs_lourds` | P5 — choisir des mots simples | info | seize locutions administratives, chacune avec sa reformulation |
| `passif` | P8 — préciser qui fait quoi | info avec agent / avertissement sans agent | `aux:pass` ou `cop`, participe `VERB`, heuristique des verbes avec *être*, recherche d'`obl:agent` |

`_motif()` compile une expression du lexique en expression régulière tolérante :
`\s+` entre les mots (double espace, retour à la ligne), `re.IGNORECASE` (majuscule de
début de phrase), `\b` aux deux bouts (pas de correspondance au milieu d'un mot), et
un « de » final qui attrape aussi sa forme élidée « d' ».

```python
_motif("afin de").pattern       # \bafin\s+d(?:e\b|')
_motif("nonobstant").pattern    # \bnonobstant\b
```

---

## 6. La démonstration

```powershell
.venv\Scripts\Activate.ps1
flask run
```

Texte à coller — deux paragraphes, choisis pour montrer les deux règles et leur
chevauchement :

```
Dans le cadre de la mise en œuvre du dispositif, et conformément à la décision du comité, il convient de transmettre au moyen de la plateforme dédiée l'ensemble des pièces justificatives préalablement à l'examen du dossier par les services compétents, nonobstant les délais annoncés.

Afin d'assurer le suivi, une notice est publiée. En ce qui concerne les recours, le demandeur est susceptible d'obtenir un délai supplémentaire au titre d'une clause dérogatoire. S'agissant  de la procédure, la demande est rejetée par le biais d'une notification.
```

Ce qu'il faut faire remarquer :

1. **Paragraphe 1** — une seule phrase de 44 tokens : les deux règles se superposent.
   Ouvrir l'inspecteur : les `<mark>` portent `r-longueur_phrase r-connecteurs_lourds`,
   sans imbrication. C'est le découpage aux frontières.
2. **Paragraphe 2** — trois phrases courtes, aucun signalement de longueur. Il montre
   les tolérances du motif : élision (*Afin d'*, *au titre d'une*), majuscule de début
   de phrase, et la double espace de « S'agissant  de » que seul le `\s+` rattrape.
3. **Le volet « Structure du texte »** — le tableau de diagnostic affiche
   `texte[start:end]` à côté de chaque fragment. C'est l'invariant, visible à l'œil nu.

Puis, pour le passif — le moment fort :

```
La décision a été prise par le conseil.   -> passif avec agent (info)
La décision a été prise.                  -> passif sans agent (avertissement)
Elle est allée à Paris.                   -> rien : « aller » se conjugue avec être
```

Une regex `être + participe` signalerait les trois ; l'analyse en dépendances et
l'heuristique les distinguent. Annoncer le chiffre : 2 sur 6 avec les dépendances seules.

Puis l'écran des listes — la démonstration que les données pilotent les règles :

1. Coller « À cet égard, le dossier est complet. » : aucun connecteur signalé.
2. Menu → *Listes de mots*, ajouter « à cet égard » → « sur ce point ».
3. Revenir sur *Analyse*, relancer : « À cet égard » est surligné, avec sa proposition.

Aucun redémarrage : les règles relisent la base à chaque analyse. Faire remarquer
que la saisie est passée par `normalize()` — c'est l'invariant de D-4 appliqué à
l'autre bout.

Puis l'import, avec les fichiers de `exemples/` — le même texte dans les quatre
formats :

```
notification.txt    cp1252, pas UTF-8 : la détection d'encodage travaille
notification.md     les marques sont retirées, les libellés de liens gardés
notification.docx   paragraphes joints par une ligne vide
notification.odt    paragraphes et titres, dans l'ordre de lecture
```

Montrer que les quatre donnent les **mêmes** signalements : c'est la démonstration que
l'extraction est bien en amont de la chaîne et ne la contamine pas. Puis déposer un
`.pdf` : le message dit pourquoi le format est refusé, il ne dit pas « format inconnu ».

Enfin, sans serveur et sans toucher la base réelle — la fixture monte une base en
mémoire, amorcée par la même fonction que `flask seed` :

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_rules.py tests/test_passif.py -v
```

Et le parcours d'erreur, qui passe lui par la route :

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_validation.py -v
```

---

## 7. Questions probables, et ce qu'on répond

**« Pourquoi pas une bibliothèque de lisibilité existante, Flesch ou autre ? »**
Un indice de lisibilité rend un chiffre, pas un endroit. Ici chaque signalement pointe
un empan précis et propose une reformulation. Et les formules classiques comptent les
syllabes, ce qui les rend peu transposables d'une langue à l'autre.

**« Pourquoi une regex plutôt que spaCy pour les connecteurs ? »**
Une locution figée est une suite de mots, pas une structure syntaxique. Passer par l'analyse
spaCy n'apporterait rien pour ce cas. Elle est réservée à ce qui l'exige vraiment : la
détection du passif.

**« Pourquoi spaCy ne découpe-t-il pas les phrases ? »**
Mesuré : sur un titre suivi d'une ligne vide, spaCy fusionne le titre et la phrase
suivante, et l'analyse devient fausse. pysbd reste la seule autorité de segmentation ;
spaCy analyse chaque phrase isolément, et ses positions sont reportées par
`phrase.start + token.idx`.

**« Pourquoi pas `fr_core_news_md` ? »**
Comparé sur sept phrases de référence : aucun résultat différent. Le modèle léger suffit.

**« Que se passe-t-il pour une langue non couverte ? »**
Rien, et c'est testé. `s_applique_a()` interroge la donnée, donc une règle sans seuil ni
lexique pour cette langue n'est simplement pas exécutée. C'était un vrai bug au départ :
la version précédente lisait `self.seuils[document.langue]` et levait un `KeyError`.

**« Et l'injection HTML, si je colle un `<script>` ? »**
Échappement avant balisage, segment par segment. Voir §3.

**« Les listes sont dans un JSON et en base : pourquoi les deux ? »**
Le JSON, `data/seeds/lexiques.json`, est la source versionnée (D-12) : git ne suit pas
la base. La base est la copie d'exécution, et `flask seed` la reconstruit à tout moment.
L'amorce n'ajoute que ce qui manque et n'écrase jamais rien : on peut la relancer, et
elle ne détruit pas les ajouts faits depuis l'écran des listes.

**« Passer les listes en base, ça a obligé à réécrire les règles ? »**
Non, et c'est le point à faire remarquer. Les règles appelaient déjà
`connecteurs_lourds(document.langue)` et `verbes_conjugues_avec_etre(document.langue)`.
Seul l'intérieur de ces deux fonctions a changé : elles lisent maintenant la base via
`repositories.lire_liste()`. Le prix, je l'assume : le moteur dépend de la base, donc ses
tests tournent dans une application de test avec une base en mémoire. La frontière a
bougé — elle passe désormais entre les règles et le SQL, qui reste confiné au repository.

**« Un utilisateur peut taper n'importe quoi dans l'écran des listes : et si c'était du regex ? »**
L'expression saisie finit bien dans une expression régulière, mais `_motif()` passe
chaque mot par `re.escape` : « a.b » cherche un point, pas n'importe quel caractère.
Et la saisie est d'abord normalisée comme le texte — apostrophes, espaces, casse —,
sinon une apostrophe courbe collée depuis Word ne correspondrait jamais.

**« Que se passe-t-il si je dépose un fichier de 50 Mo ? »**
Flask le refuse pendant la lecture du corps de la requête, via `MAX_CONTENT_LENGTH` :
la route n'est jamais appelée, donc aucun `try` ne pourrait l'attraper. C'est
`@bp.app_errorhandler(413)` qui répond, et il rend la même page que la route — le
formulaire avec son bandeau d'erreur — en conservant le code 413, parce que rien n'a
été analysé. Le rendu est partagé par une fonction `page()` : une page d'erreur reste
une page d'analyse.

**« Pourquoi un extracteur est-il une fonction, alors qu'une règle est une classe ? »**
Parce qu'un extracteur n'a rien à porter : pas d'identifiant, pas de sévérité, pas de
principe de rattachement. Une règle porte les quatre, et le gabarit les affiche. Le
registre suit la même différence : une liste parcourue en entier pour les règles, un
dictionnaire indexé par extension pour les extracteurs, puisqu'on en cherche un seul.

**« Comment devinez-vous l'encodage d'un `.txt` ? »**
On essaie l'UTF-8 d'abord : il est dominant et auto-vérifiant, des octets qui n'en sont
pas échouent au lieu de produire un faux texte. Sinon `charset-normalizer` tranche, mais
sur une liste restreinte à sept candidats, les encodages rencontrés dans l'Union — sur un texte court, son heuristique
peut élire un encodage asiatique. Si rien ne convient, on refuse le fichier. Rendre du
mojibake serait pire : la segmentation et l'étiquetage porteraient sur des mots qui
n'existent pas, sans lever la moindre erreur. `exemples/notification.txt` est enregistré
en cp1252 exprès.

**« Pourquoi `.pdf` est-il refusé ? »**
Un PDF n'a pas de structure de paragraphes fiable : l'extraction produit des coupures de
ligne arbitraires qui feraient mentir la segmentation, donc les positions, donc le
surlignage. Mieux vaut refuser que signaler au mauvais endroit (D-2).

---

## 8. Limites assumées

À dire soi-même plutôt qu'à se faire dire :

- « s'agissant **des** pièces » n'est pas détecté — `des` n'est ni `de` ni `d'`.
  Le lexique traite les locutions figées, pas la morphologie.
- La tokenisation est un simple `\S+` : la ponctuation reste collée au mot. Suffisant
  pour compter des mots ; la tokenisation fine reste à faire.
- Le lexique compte seize entrées. C'est un échantillon représentatif, pas un inventaire.
- Un seul texte à la fois, pas d'historique, pas d'export : phase 3.
- Sur une base migrée mais non amorcée, rien ne plante : la règle des connecteurs
  disparaît et le passif perd son exclusion des verbes avec *être*. Une liste absente
  donne un dict vide — c'est voulu pour une langue non couverte, et c'est le revers du
  même mécanisme. D'où `flask seed` dans les étapes d'installation.
- L'écran des listes n'a ni CSRF ni authentification : application locale,
  mono-utilisateur. Flask-WTF réglerait le CSRF, au prix d'une dépendance.
- Une entrée d'origine supprimée à l'écran revient au prochain `flask seed`. Le remède —
  marquer l'entrée supprimée au lieu de l'effacer — demande une colonne et une migration.
- L'import lit le corps du document : les tableaux d'un `.docx` et les notes de bas de page sont ignorés.
- Le choix de l'extracteur se fait sur l'extension, pas sur les octets d'en-tête. Un `.pdf` renommé en `.docx` est refusé par python-docx, donc avec le bon résultat mais pour la mauvaise raison.
- Les analyses ne sont pas encore enregistrées en base ; les tables et la migration existent.
- « La porte est ouverte » et « Il est convaincu » restent signalés : la frontière entre état et passif est ambiguë. Le premier cas est documenté par un test `xfail`. Score : 4 sur 6 sur les phrases de référence, contre 2 sur 6 avec les dépendances seules.
- Les attributs adjectivaux (« est susceptible de ») ne sont plus signalés depuis le 15/09 : la règle exige un participe étiqueté `VERB`.

---

## 9. Commandes utiles

```powershell
.venv\Scripts\Activate.ps1                  # activer l'environnement
pip install -r requirements.txt             # inclut le modèle spaCy, épinglé par URL
Copy-Item .env.example .env                 # puis renseigner SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
flask db upgrade                            # crée les tables
flask seed                                  # charge les listes de mots ; relançable

flask run                                   # http://127.0.0.1:5000
.venv\Scripts\python.exe -m pytest -p no:cacheprovider                         # toute la suite
.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_rules.py -v  # le moteur seul

python -c "import app.services.rules"       # silence = registre sain
```

Si PowerShell refuse le script d'activation :
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
