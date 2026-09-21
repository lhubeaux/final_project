# Analyseur de langage clair — documentation technique

État au 21 septembre 2026, phase 3 en cours.
Document de référence : ce que le code fait aujourd'hui, et pourquoi il le fait ainsi.
Pour l'oral, voir plutôt `soutenance.md`, qui est un aide-mémoire de questions-réponses.

---

## 1. Objet du projet

Une application web qui reçoit un texte administratif en français et signale ce qui
l'éloigne des dix principes de rédaction claire des institutions européennes. Elle rend
le texte surligné : chaque signalement porte un empan de caractères, un message, et
quand c'est possible une reformulation.

Deux partis pris structurants :

- **Pas de note globale sur 100** (D-10). Un score invite à optimiser un chiffre ; on veut
  faire relire le texte.
- **Un signalement est un endroit, pas une statistique.** Tout ce qui suit découle de là :
  si un signalement désigne un endroit, ses positions doivent être exactes, toujours.

---

## 2. Installation

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1          # PowerShell
# source .venv/Scripts/activate     # Git Bash — Scripts/, pas bin/
pip install -r requirements.txt
Copy-Item .env.example .env         # puis renseigner SECRET_KEY
flask db upgrade                    # crée les tables
flask seed                          # charge les listes de mots en base
flask run                           # http://127.0.0.1:5000
pytest
```

Génération d'une clé : `python -c "import secrets; print(secrets.token_hex(32))"`

Le modèle spaCy `fr_core_news_sm` 3.8.0 est épinglé par URL dans `requirements.txt` ;
`pip install -r` suffit, aucun téléchargement séparé.

**Environnement cible :** Windows 11, Python 3.14, venv local, développement natif — le
dépôt reste sur `C:`, pas de WSL.

---

## 3. Architecture

```
app/
├── __init__.py            fabrique create_app()
├── config.py              Config / TestConfig, lues depuis l'environnement
├── models/                DocumentRecord · Analysis · FindingRecord · WordList · WordEntry
├── repositories.py        tout le SQL : amorcer_liste(), lire_liste()
├── cli.py                 flask seed : data/seeds/lexiques.json -> base
├── routes/
│   ├── analyze.py         GET/POST /
│   └── admin.py           /listes/ : écran des listes de mots
├── static/
│   ├── css/style.css      feuille unique, mode sombre
│   └── js/app.js          lien surlignage ↔ fiche
├── templates/analyze/index.html
└── services/
    ├── document.py        build_document() — le seul point d'entrée
    ├── normalization.py   six transformations, une seule fois
    ├── segmentation.py    paragraphes puis phrases (pysbd)
    ├── tokenization.py    \S+ avec report de position
    ├── rendering.py       surligner() — échappement puis balisage
    ├── linguistics.py     point de contact unique avec spaCy, TokenLinguistique
    ├── extraction/
    │   ├── registry.py    registre, extraire(), erreurs d'import
    │   ├── txt.py         décodage d'octets sans encodage déclaré
    │   ├── md.py          décodage txt puis retrait des marques
    │   ├── docx.py        paragraphes (python-docx)
    │   └── odt.py         paragraphes et titres dans l'ordre (odfpy)
    └── rules/
        ├── base.py        Finding (dataclass) + Rule (classe abstraite)
        ├── runner.py      registre plat, enregistrer / regles / run
        ├── seuils.py      données : seuils numériques par langue
        ├── lexiques.py    lit en base connecteurs et verbes conjugués avec être
        ├── fr.py          LongueurPhrase · ConnecteursLourds · Passif
        └── en.py          (vide)
```

Le détail de chaque module est dans `guide-des-modules-python.md`.

### Les trois frontières à ne pas franchir

1. **Aucune règle n'écrit de SQL.** Depuis le 21 septembre, les listes de mots sont en
   base et `lexiques.py` les lit via `repositories.lire_liste()` : le moteur dépend donc
   de la base, mais seulement à travers deux fonctions dont la signature n'a pas changé.
   Aucune règle n'importe `models`. Conséquence assumée : `test_rules.py` et
   `test_passif.py` tournent dans une application de test, base en mémoire amorcée.
2. **Le repository ne fait pas de linguistique.** Il traduit des objets en lignes de
   table, rien de plus. Tout le SQL du projet est là.
3. **Aucune règle n'importe spaCy** (D-7). Seul `services/linguistics.py` l'importe ; il
   traduit chaque token en `TokenLinguistique`, et les règles lisent `Sentence.analyse`.

---

## 4. La chaîne de traitement

```
saisie                fichier
  │                     └─ extraire()   registre par extension -> texte brut
  └─────────┬───────────┘
texte brut
  └─ normalisation      BOM · CRLF · NFC · soft hyphen · apostrophes · insécables
      └─ segmentation   paragraphes, puis phrases (pysbd), sans franchir les blocs
          └─ tokenisation   \S+, position reportée
              └─ analyse spaCy   chaque phrase séparément -> Sentence.analyse
                  └─ Document   paragraphes · phrases · tokens · analyse
                      └─ règles   -> liste de Finding
                          └─ surlignage   <mark> par empan
```

Un seul point d'entrée : `build_document(texte_brut, langue="fr")`. La normalisation s'y
fait une fois pour toutes (D-4) : il devient impossible de fabriquer un `Document` dont
le texte ne serait pas le texte de référence.

### Les deux chemins d'entrée

Une zone de texte, ou un fichier. Le fichier l'emporte quand les deux sont remplis : le
déposer est le geste le plus explicite.

`extraire(nom_fichier, flux)` choisit l'extracteur d'après la seule extension. Le nom
vient du client, il ne sert qu'à ce choix et jamais à écrire sur le disque.

| Format | Module | Ce qu'il fait |
|---|---|---|
| `.txt` | `txt.py` | UTF-8 d'abord — il est auto-vérifiant — puis `charset-normalizer` restreint à sept candidats — les encodages rencontrés dans l'Union. Un fichier indéchiffrable est refusé plutôt que rendu en mojibake : la segmentation et l'étiquetage porteraient sur des mots qui n'existent pas, sans lever la moindre erreur. |
| `.md` | `md.py` | Le décodage du `.txt`, puis six expressions régulières qui retirent titres, citations, puces, emphases, accents de code, et gardent le libellé des liens sans leur URL. Aucune dépendance ajoutée : Markdown est une convention d'écriture, pas un format de fichier. |
| `.docx` | `docx.py` | Les paragraphes via python-docx, joints par une ligne vide. |
| `.odt` | `odt.py` | Les paragraphes et titres via odfpy, parcourus en profondeur pour garder l'ordre de lecture — `getElementsByType()` grouperait tous les paragraphes puis tous les titres. |

La ligne vide entre deux blocs n'est pas cosmétique : c'est ce que `segment()` attend
pour délimiter un paragraphe.

**Un extracteur rend du texte brut et ne normalise jamais.** S'il normalisait, les deux
chemins d'entrée produiraient deux textes de référence différents et D-4 tomberait.

`.pdf` et `.doc` ont une entrée dédiée dans `_REFUS` : un message qui dit pourquoi vaut
mieux qu'un « format inconnu » (D-2). Les trois erreurs d'import — `FormatNonSupporte`,
`FichierIllisible`, et `ExtractionError` dont elles héritent — portent un message écrit
pour être montré tel quel ; la route ne le reformule pas.

### L'invariant des positions

Chaque couche découpe une chaîne et **transporte** sa position par addition ; elle ne la
recalcule jamais.

```
bloc.start()      position du paragraphe dans le texte
+ span.start      position de la phrase dans le paragraphe
= phrase["start"] position de la phrase dans le texte    ─┐ passé en offset
+ match.start()   position du token dans la phrase       ─┘
= token["start"]  position du token dans le texte
```

L'invariant, vérifié dans `tests/test_positions.py` :

```python
texte[fragment["start"]:fragment["end"]] == fragment["texte"]
```

Deux méthodes à ne jamais réintroduire :

- `texte.find(phrase)` pour retrouver une position — retombe sur la première occurrence
  dès qu'une phrase se répète.
- Cumuler les longueurs de fragments — dérive de 2 caractères par ligne vide entre
  paragraphes, invisible au début, fatale à la fin.

### Corollaire : l'échappement HTML

`surligner()` échappe segment par segment **avant** d'insérer les balises. Dans l'autre
sens, on échapperait ses propres `<mark>`. Et comme l'échappement change les longueurs
(`<` devient `&lt;`, un caractère en quatre), on ne peut pas échapper le texte entier
puis le découper avec les mêmes positions.

Le découpage se fait aux frontières de **tous** les signalements : deux signalements qui
se chevauchent produisent un segment commun portant les deux classes CSS, jamais deux
balises imbriquées.

---

## 5. Le moteur de règles

### Le contrat

`base.py` définit deux choses :

- **`Finding`** — dataclass gelée. Sept champs : `rule_id`, `hint`, `severity`,
  `char_start`, `char_end`, `message`, `suggestion`. C'est l'objet de transport, distinct
  de `FindingRecord` qui est l'objet de persistance (D-6).
- **`Rule`** — classe abstraite. Une règle concrète redéfinit `id`, `hint`, `severity`,
  puis implémente `check(document)`. Elle **ne garde aucun état sur `self`** : l'instance
  est partagée par toutes les requêtes.

### Le registre (D-8)

```python
@enregistrer
class MaRegle(Rule):
    ...
```

Le décorateur instancie la classe et la range dans une liste de module. `run(document)`
parcourt cette liste, écarte les règles inapplicables, concatène les signalements et les
trie par position — parce que le surlignage parcourt le texte de gauche à droite.

Conséquence : **ajouter une règle ne modifie aucun appelant.** Ni la route, ni le
template, ni le runner. La seule trace d'une règle ailleurs dans l'application est sa
ligne de couleur dans `style.css`.

### Les langues, et l'extension aux 24 langues de l'UE

Le registre est plat : une fois `fr.py` et `en.py` importés, plus rien ne dit d'où vient
une règle. `Rule.s_applique_a(langue)` porte donc l'information. Les deux règles fondées
sur des données ne déclarent aucune liste de langues, elles la déduisent de leur donnée :

```python
return seuil(self.id, langue) is not None        # LongueurPhrase
return bool(connecteurs_lourds(langue))          # ConnecteursLourds
```

Ajouter une langue, c'est ajouter une entrée dans `seuils.py`, ou une langue dans
`data/seeds/lexiques.json` suivie de `flask seed`. Aucune ligne de code ne change. C'est aussi ce qui rend le `KeyError` structurellement
impossible : une règle ne peut pas s'exécuter sur une langue dont elle n'a pas la donnée.

La règle `Passif`, elle, dépend de l'analyse grammaticale : elle déclare explicitement
`langues = ("fr",)` et le comportement par défaut de `s_applique_a()` suffit.

### Les trois règles livrées

| Règle | Principe | Sévérité | Mécanisme |
|---|---|---|---|
| `longueur_phrase` | P4 — faire court et simple | avertissement | compte les tokens de chaque phrase, compare au seuil de la langue (25 en français, 21 en anglais) |
| `connecteurs_lourds` | P5 — choisir des mots simples | info | seize locutions administratives, chacune avec sa reformulation |
| `passif` | P8 — préciser qui fait quoi | info avec agent, avertissement sans agent | `aux:pass` ou `cop` dans `Sentence.analyse`, exclusion des verbes conjugués avec *être*, recherche d'un `obl:agent` |

`_motif()` compile une expression du lexique en expression régulière tolérante :
`\s+` entre les mots, `re.IGNORECASE`, `\b` aux deux bouts, et un « de » final qui
attrape aussi sa forme élidée « d' ».

```python
_motif("afin de").pattern       # \bafin\s+d(?:e\b|')
_motif("nonobstant").pattern    # \bnonobstant\b
```

### La règle du passif

1. Parcourir `phrase.analyse` et retenir un token `aux:pass`, ou `cop` : sans complément
   d'agent, le modèle étiquette souvent ainsi l'auxiliaire du passif.
2. Son gouverneur est le participe. S'il n'est pas étiqueté `VERB`, c'est un attribut
   (« est **susceptible** », « est **nécessaire** », « est **médecin** ») : pas un passif.
3. Si le lemme du participe figure dans `verbes_conjugues_avec_etre(document.langue)`
   (*aller*, *venir*, *partir*…), ce n'est pas un passif.
4. Chercher un dépendant `obl:agent` du participe : présent, sévérité `info` ; absent,
   sévérité `avertissement`, parce que le lecteur ne sait pas qui agit.
5. L'empan va du premier auxiliaire du participe jusqu'au participe : « a été prise ».

Mesure de référence (D-14), sur les six phrases de référence : les dépendances seules
obtiennent 2 sur 6, la règle actuelle 4 sur 6. Les deux échecs restants sont « La porte
est ouverte » et « Il est convaincu », où spaCy étiquette le participe `VERB`.
`fr_core_news_md` n'a montré aucun gain sur sept phrases.

---

## 6. Modèle de données

Cinq entités, pas sept : `RuleSet` et `RuleConfig` n'existent pas, faute d'écran de
configuration des règles.

| Table | Rôle | Points notables |
|---|---|---|
| `documents` | un texte soumis | `texte` est le texte **normalisé** ; `source` vaut `saisie` ou `fichier` ; `version_tokeniseur` prépare la commande `retokenize` |
| `analyses` | une exécution du moteur sur un document | horodatée ; un document peut en avoir plusieurs |
| `findings` | un signalement persisté | reflet de la dataclass `Finding`, mêmes champs, nom distinct (D-6) |
| `word_lists` | une liste de mots nommée, pour une langue | unique sur (`nom`, `langue`) : `connecteurs_lourds` / `fr` |
| `word_entries` | une entrée de liste | unique dans sa liste ; `remplacement` vide pour les verbes, qui n'ont pas de reformulation |

Deux migrations : les trois premières tables (`7b70f94273c6`), puis les listes de mots
(`346c000e5787`).

**Les listes de mots sont remplies par `flask seed`.** La source versionnée reste
`data/seeds/lexiques.json` (D-12) ; la base n'en est que la copie d'exécution.
`amorcer_liste()` n'ajoute que les entrées absentes et n'écrase jamais rien : relancer
l'amorce est sans risque, y compris depuis que les listes sont éditables à l'écran.

**Les trois premières tables restent vides** : la route n'enregistre pas encore les
analyses.

Quand ce sera branché : la route appellera `repositories.enregistrer_analyse(...)`, jamais
`db.session` directement, et c'est là — et nulle part ailleurs — que se fera la traduction
`Finding` → `FindingRecord`.

---

## 7. L'interface

Deux pages, reliées par un menu commun. `templates/base.html` porte l'en-tête, la
feuille de style et le menu ; `analyze/index.html` et `admin/listes.html` en héritent
par `{% extends %}`. Le lien de la page courante reçoit la classe `actif` d'après
`request.blueprint`.

### La page d'analyse

`templates/analyze/index.html`, servie en `GET` et en `POST`.

- **Le formulaire** — une `textarea`, `maxlength="20000"`, et un champ de dépôt de
  fichier. L'attribut `accept` et la liste des formats affichée sont tous deux produits
  par `extensions_supportees()` : enregistrer un extracteur de plus suffit à les mettre
  à jour. Après analyse, la zone réaffiche `document.texte`, c'est-à-dire le texte
  **normalisé** : l'utilisateur récupère ses apostrophes redressées. C'est cohérent
  avec D-4 et assumé.
- **Le bandeau d'erreur** — un `<p class="erreur">` au-dessus des résultats, alimenté
  par le message de l'`ExtractionError`, par le dépassement de `MAX_TEXT_LENGTH`, ou
  par « Aucun texte à analyser. » quand la saisie est vide.
- **Un rendu unique** — `page()` dans `routes/analyze.py`. La route et le gestionnaire
  d'erreur y passent tous deux, si bien qu'une page d'erreur reste une page d'analyse :
  le formulaire est toujours là, la liste des formats aussi.
- **Colonne de gauche** — le texte surligné. Chaque `<mark>` porte ses classes
  (`signalement r-longueur_phrase`) et un `data-findings="0,3"` listant les rangs des
  signalements qui le couvrent.
- **Colonne de droite** — le compte par règle, zéros compris, puis une fiche par
  signalement avec `id="signalement-N"`.
- **`app.js`** relie les deux sens : cliquer un passage ouvre sa fiche, cliquer une fiche
  ramène à son passage. Rien d'autre ne dépend de JavaScript — la page reste lisible
  sans lui.
- **En bas, replié** — le diagnostic technique des positions : pour chaque phrase, son
  `start`, son `end`, ce qu'elle transporte et `texte[start:end]` recalculé, en rouge en
  cas d'écart. C'est un outil de vérification, pas une fonctionnalité.

### L'écran des listes de mots

`templates/admin/listes.html`, servi par le blueprint `admin` sous `/listes/`.

- **Une section par liste**, avec son libellé, sa langue et son nombre d'entrées, un
  tableau trié par expression, un bouton *Supprimer* par ligne et un formulaire
  d'ajout. Le libellé et la présence d'une colonne *Remplacement* viennent du tableau
  `LISTES` de `admin.py` ; une liste qui n'y figure pas s'affiche sous son nom brut.
- **La saisie est normalisée comme le texte analysé** : `nettoyer()` applique
  `normalize()` puis réduit les espaces, et l'expression passe en minuscules. Sans ça,
  une apostrophe courbe collée depuis Word ne correspondrait jamais au texte, qui est
  toujours normalisé — l'invariant de D-4, appliqué à l'autre bout.
- **Refus** : expression vide, doublon (y compris « Afin DE » face à « afin de »),
  remplacement manquant pour une liste qui en demande un. Chaque refus ou succès
  revient par `flash()`, sous forme de bandeau `.erreur` ou `.succes`.
- **POST-Redirect-GET** : ajout et suppression renvoient une redirection vers
  `/listes/#liste-N`. Rafraîchir la page ne rejoue pas l'opération, et l'ancre ramène
  à la liste modifiée.
- **Effet immédiat** : les règles relisent la base à chaque analyse, il n'y a aucun
  cache. Une expression ajoutée est surlignée dès le texte suivant, sans redémarrage.

Une expression saisie finit dans une expression régulière, mais `_motif()` passe chaque
mot par `re.escape` : aucune injection de motif n'est possible.

---

## 8. Tests

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider                          # toute la suite
.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_rules.py -v   # le moteur seul
.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_passif.py -v  # le passif seul
```

| Fichier | Ce qu'il garantit |
|---|---|
| `test_positions.py` | l'invariant sur les paragraphes, les phrases et les tokens ; le cas du texte vide |
| `test_rules.py` | longueur de phrase et connecteurs lourds, l'empan de chaque signalement, l'absence de faux positif au milieu d'un mot, l'enregistrement des trois règles, le tri des signalements par position, et qu'une langue non couverte ne fait rien planter |
| `test_smoke.py` | la route `/health` répond |
| `test_admin.py` | l'écran des listes, par la route : affichage et menu, ajout pris en compte dès l'analyse suivante, redirection POST-Redirect-GET, saisie normalisée (apostrophe courbe), doublon refusé même en majuscules, remplacement obligatoire, expression vide, verbe sans remplacement, suppression prise en compte, 404 sur un identifiant inconnu |
| `test_validation.py` | le parcours d'erreur, vu depuis la route : dépassement de 2 Mo (413), texte trop long, texte vide, refus `.pdf` et `.doc` avec leur raison, extension inconnue, `.docx` corrompu, `.txt` en cp1252 décodé, et la priorité du fichier sur la zone de texte |
| `test_passif.py` | les passifs avec ou sans agent (empan et sévérité), le passif au futur, les faux positifs « Elle est allée » et attributs adjectivaux (« est susceptible », « est nécessaire »), l'invariant des positions sur `Sentence.analyse`, et le cas ambigu « La porte est ouverte » en `xfail` ; le modèle spaCy est chargé par une fixture de portée `session` |

Depuis que les listes de mots sont en base, `test_rules.py` et `test_passif.py` se
déclarent `pytestmark = pytest.mark.usefixtures("base_amorcee")`. La fixture, dans
`conftest.py`, crée une application de test, une base SQLite en mémoire, et l'amorce
avec `amorcer_lexiques()` — la fonction même qu'utilise `flask seed`. Aucun test ne
touche la base réelle. `client` s'appuie sur la même fixture : les tests de la route
voient donc les mêmes listes que le moteur.

État au 21 septembre : 39 tests passent, plus le `xfail` assumé, en moins de 3 secondes.

**Manque encore** : `test_normalization.py`, qui doit couvrir les six transformations de
`normalize()`.

Les fichiers de `exemples/` servent la démonstration, pas les tests : un texte de
notification administrative dans les quatre formats acceptés. Le `.txt` est enregistré
en cp1252, ce qui exerce la détection d'encodage au lieu de la contourner.

---

## 9. État d'avancement

**Phase 0 — socle** ✅ dépôt, venv, dépendances, `create_app()`, `/health`.

**Phase 1 — la chaîne complète en version minimale** (→ ven 11/09)
- ✅ normalisation, segmentation, tokenisation avec positions absolues
- ✅ route `POST /`, diagnostic des positions
- ✅ `models/` : trois entités et leur migration
- ✅ objet `Document` maison, `rules/base.py`, `rules/runner.py`
- ✅ deux règles : longueur de phrase, connecteurs lourds
- ✅ écran de résultats : surlignage, fiches, compte par règle, lien dans les deux sens
- ⬜ tests de la normalisation

**Phase 2 — close le ven 18/09** : spaCy et détection du passif *(priorité absolue)*,
import de fichiers, tokenisation fine, deux règles de plus.
- ✅ spaCy analyse les phrases séparées par `pysbd` et projette ses tokens dans `Sentence.analyse`
- ✅ règle `passif`, affichée par le mécanisme générique de surlignage
- ✅ jeu d'essai du passif complété ; attributs adjectivaux exclus
- ✅ comparaison `fr_core_news_sm` / `md` : aucun gain, `sm` conservé
- ✅ import de fichiers : registre d'extracteurs, `.txt`, `.md`, `.docx`, `.odt`, refus
  explicites de `.pdf` et `.doc`, quatre textes de démonstration dans `exemples/`
- ⬜ tokenisation fine, deux règles de plus

Les points 1 à 3 sont tenus. Restent la tokenisation fine, les deux règles
supplémentaires et le script d'amorce : ils entrent dans l'ordre de sacrifice ci-dessous.

**Phase 3 — en cours** (lun 21 → ven 25/09) : durcissement, puis connexion à la base.
- ✅ texte vide refusé côté serveur ; format non pris en charge, fichier corrompu et
  encodage non reconnu affichés dans le bandeau d'erreur
- ✅ erreur 413 : `app_errorhandler` rend la page du formulaire avec son bandeau
- ✅ `MAX_TEXT_LENGTH` vérifié côté serveur
- ✅ `tests/test_validation.py` — neuf cas du parcours d'erreur
- ✅ `MAX_FORM_MEMORY_SIZE` aligné sur `MAX_CONTENT_LENGTH` dans `config.py`
- ⬜ `tests/test_normalization.py`
- ✅ documentation technique et diaporama de soutenance (`docs/soutenance.pptx`)
- ⬜ enregistrement des analyses : `DocumentRecord`, `Analysis`, `FindingRecord`
- ✅ connecteurs lourds et verbes conjugués avec *être* en base, amorcés par `flask seed`
- ✅ écran des listes de mots : afficher, ajouter, supprimer ; menu commun

Le durcissement étant bouclé le 21/09, le reste de la semaine va à la connexion à la
base. Ce choix avance deux lignes de l'ordre de sacrifice — la partie stockage de
l'historique, et les listes de mots — au détriment de la quatrième règle, devenue
facultative.

Gel des fonctionnalités : vendredi 25 septembre au soir. Soutenance : lundi 28 septembre 2026.

### Ordre de sacrifice si le retard s'installe

Conteneurisation → export et historique → jeu de règles anglais → écrans de configuration
→ quatrième règle et au-delà → tokenisation fine.

*L'import `.odt` et `.docx` a quitté cette liste : il est fait.*

**Jamais sacrifié :** normalisation, segmentation, moteur de règles, les trois règles
livrées, surlignage, détection du passif, durcissement, répétition.

---

## 10. Limites connues

- « s'agissant **des** pièces » n'est pas détecté — `des` n'est ni `de` ni `d'`. Le lexique
  traite des locutions figées, pas la morphologie.
- La tokenisation est un `\S+` : la ponctuation reste collée au mot. Suffisant pour
  compter ; la tokenisation fine reste à faire.
- « La porte est ouverte » et « Il est convaincu » peuvent être signalés comme passifs :
  spaCy étiquette le participe `VERB`, et état et passif restent ambigus pour cette
  heuristique.
- La route n'enregistre pas les analyses en base.
- **Base migrée mais non amorcée : aucune erreur, des signalements en moins.**
  `lire_liste()` renvoie un dict vide pour une liste absente — c'est ce qui protège une
  langue non couverte du `KeyError`. Mais sur une base où l'on a oublié `flask seed`, le
  même mécanisme fait disparaître `connecteurs_lourds` des règles actives, et `Passif`
  perd son exclusion des verbes avec *être* : « Elle est allée » redevient un faux
  positif. Vérifié. Sans la migration, en revanche, l'erreur est bruyante :
  `OperationalError: no such table: word_entries`.
- L'écran des listes n'a ni protection CSRF ni authentification : acceptable pour
  une application locale mono-utilisateur, à dire à l'oral. Flask-WTF réglerait le
  CSRF, mais c'est une nouvelle dépendance.
- Une entrée d'origine supprimée depuis l'écran revient au prochain `flask seed`,
  qui reprend les entrées manquantes. Les ajouts de l'utilisateur ne sont jamais
  touchés.
- On ne modifie pas un remplacement sur place : on supprime l'entrée, puis on la
  rajoute.
- `docx.paragraphs` ignore le texte des tableaux, et l'extracteur `.odt` ne lit que les
  paragraphes et les titres. Le corps du document, pas ses annexes.
- `defusedxml` est bien utilisé, mais par odfpy et non par le code du projet : `odf/opendocument.py` fait `from defusedxml.sax import make_parser`. Le `.odt` est donc lu par un parseur durci, le `.docx` par lxml. La ligne de `requirements.txt` est techniquement redondante, odfpy tirant la dépendance ; elle est **gardée volontairement**, parce qu'elle rend visible dans le fichier des dépendances que le XML des fichiers de bureau est lu par un parseur durci, et qu'elle protège d'un changement de parseur côté odfpy.
- Le champ `Document.spacy_doc` subsiste mais n'est pas utilisé : les règles lisent
  `Sentence.analyse`.
- Le surlignage n'est cliquable qu'à la souris. Le rendre accessible au clavier demande un
  `tabindex` posé dans `rendering.py`.
- Le lexique compte seize connecteurs et dix-sept verbes : un échantillon représentatif,
  pas un inventaire.
