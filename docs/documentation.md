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
├── models/                DocumentRecord · Analysis · FindingRecord
├── repositories.py        accès aux données — aucune linguistique     (vide)
├── cli.py                 commandes seed, retokenize                  (vide)
├── routes/
│   ├── analyze.py         GET/POST /
│   └── admin.py           écrans de configuration                     (vide)
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
        ├── lexiques.py    données : connecteurs, verbes conjugués avec être
        ├── fr.py          LongueurPhrase · ConnecteursLourds · Passif
        └── en.py          (vide)
```

Le détail de chaque module est dans `guide-des-modules-python.md`.

### Les trois frontières à ne pas franchir

1. **Le moteur de règles ne connaît pas la base.** Aucun import de `models` ni de
   `repositories` sous `services/rules/`. C'est ce qui permet de lancer
   `pytest tests/test_rules.py` sans base de données ni serveur.
2. **Le repository ne fait pas de linguistique.** Il traduit des objets en lignes de
   table, rien de plus.
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

Ajouter une langue, c'est ajouter une entrée dans `seuils.py` ou `lexiques.py`. Aucune
ligne de code ne change. C'est aussi ce qui rend le `KeyError` structurellement
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

Trois entités, pas sept.

| Table | Rôle | Points notables |
|---|---|---|
| `documents` | un texte soumis | `texte` est le texte **normalisé** ; `source` vaut `saisie` ou `fichier` ; `version_tokeniseur` prépare la commande `retokenize` |
| `analyses` | une exécution du moteur sur un document | horodatée ; un document peut en avoir plusieurs |
| `findings` | un signalement persisté | reflet de la dataclass `Finding`, mêmes champs, nom distinct (D-6) |

Les trois tables existent et la migration est écrite. **Rien ne les remplit aujourd'hui** :
la route ne persiste pas, `repositories.py` est vide. L'historique relève de la phase 3.

Quand ce sera branché : la route appellera `repositories.enregistrer_analyse(...)`, jamais
`db.session` directement, et c'est là — et nulle part ailleurs — que se fera la traduction
`Finding` → `FindingRecord`.

---

## 7. L'interface

Une seule page, `templates/analyze/index.html`, servie en `GET` et en `POST`.

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
| `test_validation.py` | le parcours d'erreur, vu depuis la route : dépassement de 2 Mo (413), texte trop long, texte vide, refus `.pdf` et `.doc` avec leur raison, extension inconnue, `.docx` corrompu, `.txt` en cp1252 décodé, et la priorité du fichier sur la zone de texte |
| `test_passif.py` | les passifs avec ou sans agent (empan et sévérité), le passif au futur, les faux positifs « Elle est allée » et attributs adjectivaux (« est susceptible », « est nécessaire »), l'invariant des positions sur `Sentence.analyse`, et le cas ambigu « La porte est ouverte » en `xfail` ; le modèle spaCy est chargé par une fixture de portée `session` |

`test_rules.py` n'importe ni `create_app` ni `db` : c'est la démonstration concrète que le
moteur est isolé de la base.

État au 21 septembre : 28 tests passent, plus le `xfail` assumé, en moins de 3 secondes.

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

**Phase 3 — en cours** (lun 21 → jeu 24/09) : durcissement, documentation, écrans de
configuration, puis historique / export / anglais / conteneurisation.
- ✅ texte vide refusé côté serveur ; format non pris en charge, fichier corrompu et
  encodage non reconnu affichés dans le bandeau d'erreur
- ✅ erreur 413 : `app_errorhandler` rend la page du formulaire avec son bandeau
- ✅ `MAX_TEXT_LENGTH` vérifié côté serveur
- ✅ `tests/test_validation.py` — neuf cas du parcours d'erreur
- ⬜ `MAX_FORM_MEMORY_SIZE` aligné sur `MAX_CONTENT_LENGTH` dans `config.py`
- ⬜ `tests/test_normalization.py`
- ✅ documentation technique et diaporama de soutenance (`docs/soutenance.pptx`)

L'import de fichiers étant livré avec la phase 2, la phase 3 n'a plus qu'un objet : le
durcissement. C'est ce que demande le jalon du 24/09 — un inconnu manipule l'application
dix minutes sans la casser.

Gel des fonctionnalités : jeudi 24 septembre. Soutenance : lundi 28 septembre 2026.

### Ordre de sacrifice si le retard s'installe

Conteneurisation → export et historique → jeu de règles anglais → écrans de configuration
→ règles au-delà des quatre premières → tokenisation fine.

*L'import `.odt` et `.docx` a quitté cette liste : il est fait.*

**Jamais sacrifié :** normalisation, segmentation, moteur de règles, quatre règles,
surlignage, détection du passif, durcissement, journée de répétition.

---

## 10. Limites connues

- Flask 3.1 plafonne les champs non-fichier à `MAX_FORM_MEMORY_SIZE`, 500 000 octets par
  défaut, et lève un 413 avant la route. Un texte collé de plus de 500 Ko reçoit donc le
  message du dépassement de taille au lieu de celui de `MAX_TEXT_LENGTH`. Aligner les
  deux plafonds dans `config.py` corrige le message.
- « s'agissant **des** pièces » n'est pas détecté — `des` n'est ni `de` ni `d'`. Le lexique
  traite des locutions figées, pas la morphologie.
- La tokenisation est un `\S+` : la ponctuation reste collée au mot. Suffisant pour
  compter ; la tokenisation fine reste à faire.
- « La porte est ouverte » et « Il est convaincu » peuvent être signalés comme passifs :
  spaCy étiquette le participe `VERB`, et état et passif restent ambigus pour cette
  heuristique.
- La route n'enregistre pas les analyses en base.
- `docx.paragraphs` ignore le texte des tableaux, et l'extracteur `.odt` ne lit que les
  paragraphes et les titres. Le corps du document, pas ses annexes.
- `defusedxml` est bien utilisé, mais par odfpy et non par le code du projet : `odf/opendocument.py` fait `from defusedxml.sax import make_parser`. Le `.odt` est donc lu par un parseur durci, le `.docx` par lxml. La ligne de `requirements.txt` est techniquement redondante, odfpy tirant la dépendance ; elle est **gardée volontairement**, parce qu'elle rend visible dans le fichier des dépendances que le XML des fichiers de bureau est lu par un parseur durci, et qu'elle protège d'un changement de parseur côté odfpy.
- Le champ `Document.spacy_doc` subsiste mais n'est pas utilisé : les règles lisent
  `Sentence.analyse`.
- Le surlignage n'est cliquable qu'à la souris. Le rendre accessible au clavier demande un
  `tabindex` posé dans `rendering.py`.
- Le lexique compte seize entrées : un échantillon représentatif, pas un inventaire.
