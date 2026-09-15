# Analyseur de langage clair

Application web qui analyse un texte administratif ou institutionnel, signale ce qui nuit à sa clarté, et propose quand c'est possible une formulation plus simple.

L'outil s'appuie sur les dix principes de rédaction claire des institutions européennes — un référentiel publié et citable, plutôt que des critères inventés pour l'occasion.

> **État : en développement.** Projet de fin de formation, réalisé sur trois semaines. Voir [Avancement](#avancement) pour ce qui fonctionne aujourd'hui.

---

## Le problème

Un texte administratif peut être parfaitement correct et rester illisible. Les causes sont connues et récurrentes : des phrases de soixante mots, des tournures passives qui masquent qui décide, des noms formés sur des verbes (*procéder à l'examen de* au lieu de *examiner*), un jargon institutionnel opaque, des sigles jamais développés.

Ces défauts sont repérables automatiquement. C'est ce que fait cette application.

## Ce qu'elle fait

- **Analyse d'un texte** collé dans le navigateur ou importé depuis un fichier `.txt`, `.docx`, `.odt` ou `.md`
- **Signalements localisés** dans le texte, surlignés et liés à une liste détaillée
- **Rattachement à un principe** — chaque signalement indique quel principe de rédaction claire il met en cause
- **Suggestions de reformulation** lorsque la règle en propose une
- **Configuration des règles** — activation, seuils par langue, jeux de règles multiples
- **Listes de mots modifiables** — amorcées depuis des sources publiées, complétées par l'utilisateur
- **Historique** des analyses, pour comparer une version révisée à la précédente

### Ce qu'elle ne fait pas, délibérément

| Écarté | Pourquoi |
|---|---|
| Import de PDF | L'extraction ne restitue pas les paragraphes et introduit des retours à la ligne parasites. La segmentation en phrases serait corrompue — donc la mesure de longueur de phrase, qui est le cœur de l'outil, serait fausse. |
| Import de `.doc` | Format binaire OLE, sans bibliothèque Python fiable. Le supporter imposerait d'appeler LibreOffice en sous-processus, soit 500 Mo de dépendance pour un format obsolète. |
| Score global sur 100 | Toute formule de pondération serait arbitraire. Des décomptes par principe se défendent ; un « 73/100 » ne se défend pas. |
| Réécriture par un modèle de langue | Cela déplacerait tout le travail intéressant hors du code, vers un appel d'API. |

---

## Architecture

Deux idées structurent le code, et la seconde est la première appliquée une deuxième fois.

**Un registre d'extracteurs.** Une interface commune — recevoir un fichier, renvoyer du texte avec ses paragraphes — et une implémentation par format. Ajouter un format se réduit à une classe et une ligne d'enregistrement.

**Un registre de règles.** Chaque règle est une classe autonome exposant `check(document) -> list[Finding]`. L'exécutant filtre par langue et par configuration. Ajouter une règle ne touche à aucun code existant.

**Toutes les règles renvoient la même forme.** Quelle que soit leur granularité — une phrase entière, un token, un pourcentage — les règles produisent des `Finding` portant un empan de caractères. La couche d'affichage n'a donc qu'une seule forme à traiter, et ne change plus quand le jeu de règles s'étoffe.

```python
@dataclass
class Finding:
    rule_id: str          # "longueur_phrase"
    hint: str             # principe concerné
    severity: str         # info / avertissement
    char_start: int
    char_end: int
    message: str
    suggestion: str | None
```

**spaCy est isolé derrière un seul fichier.** Aucune règle n'importe la bibliothèque directement : tout passe par `services/linguistics.py`. Changer de modèle, ou remplacer spaCy, ne concerne qu'un fichier.

### Chaîne de traitement

```
obtenir le texte  →  normaliser  →  segmenter  →  tokeniser  →  analyser
```

La normalisation s'applique aux **deux** chemins d'entrée. Un copier-coller depuis un traitement de texte apporte apostrophes courbes, espaces insécables et traits d'union conditionnels au même titre qu'un fichier importé.

### Structure du dépôt

```
app/
├── __init__.py            fabrique d'application
├── config.py              configuration par variables d'environnement
├── models.py              entités persistées
├── repositories.py        accès aux données — aucune linguistique
├── cli.py                 commandes : seed, retokenize
├── routes/                analyze (utilisateur) · admin (configuration)
└── services/
    ├── extraction/        registre + un module par format
    ├── normalization.py   encodage, NFC, apostrophes, paragraphes
    ├── segmentation.py
    ├── tokenization.py
    ├── linguistics.py     unique point de contact avec spaCy
    └── rules/             base · runner · fr · en
data/seeds/                listes de mots versionnées
tests/
docs/                      décisions de conception, programme, théorie
```

Le découpage suit les axes qui grossissent réellement — les formats, les règles, les langues — plutôt que des couches architecturales qu'on risquerait de ne jamais remplir. Un dossier se justifie à partir de trois fichiers de même nature ; en dessous, un module suffit.

---

## Installation

Python 3.12 ou supérieur.

```bash
git clone <url-du-depot>
cd analyseur-langage-clair

py -m venv .venv
.venv\Scripts\Activate.ps1        # Windows / PowerShell
# source .venv/bin/activate       # Linux, macOS, WSL

pip install -r requirements.txt
```

L'installation récupère aussi le modèle linguistique français de spaCy (`fr_core_news_sm`), épinglé par URL dans `requirements.txt`. Aucune étape de téléchargement séparée n'est nécessaire.

Puis créer le fichier de configuration :

```bash
cp .env.example .env
```

et y renseigner une `SECRET_KEY`. Une valeur convenable s'obtient par :

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Utilisation

```bash
flask run
```

L'application répond sur http://127.0.0.1:5000.

## Tests

```bash
pytest
```

Le moteur de règles ne connaît pas la base de données : sa suite de tests s'exécute en isolation, sans fixture de persistance.

---

## Choix techniques

| Domaine | Choix | Motif |
|---|---|---|
| Cadre web | Flask | Léger, explicite, adapté à un projet où l'architecture doit rester lisible |
| Persistance | SQLite via SQLAlchemy | Zéro configuration, un fichier, suffisant pour un usage mono-utilisateur |
| Segmentation | `pysbd` | Gère les abréviations et les nombres par langue, là où un découpage sur le point échoue |
| Analyse grammaticale | spaCy | L'analyse en dépendances permet de distinguer un passif véritable d'un passé composé avec *être* |
| Encodage | `charset-normalizer` | Un fichier n'annonce pas son encodage : il faut le deviner |
| Parsage XML | `defusedxml` | `.docx` et `.odt` sont des archives ZIP contenant du XML non fiable |

### La détection du passif

C'est la règle la plus intéressante du projet, et celle qu'une expression régulière ne peut pas traiter. Un motif `être + participe passé` confond quatre constructions différentes :

| Phrase | Nature |
|---|---|
| La décision a été prise | passif véritable |
| Elle est allée à Paris | passé composé avec l'auxiliaire *être* |
| La porte est ouverte | description d'un état |
| Il est convaincu | adjectif |

La détection s'appuie sur les relations de dépendance `aux:pass` et `nsubj:pass` de spaCy, complétées par des heuristiques — notamment une liste des verbes intransitifs conjugués avec *être*, qui élimine toute la famille de *elle est allée*.

Le passif **sans agent exprimé** est signalé plus sévèrement : le lecteur ne peut alors pas identifier qui agit, ce qui est précisément le défaut que vise le référentiel.

### Extensibilité

*Données quand c'est possible, code quand c'est nécessaire.*

Les règles fondées sur des listes se portent vers une nouvelle langue par simple ajout d'un fichier de données. Les règles nécessitant une analyse grammaticale déclarent les langues qu'elles savent traiter et ne s'exécutent pas ailleurs. Les seuils sont définis par langue — une phrase française compte naturellement 15 à 20 % de mots de plus que son équivalent anglais, et un seuil unique produirait un biais systématique.

---

## Avancement

Projet mené en trois phases, chacune close par quelque chose qui fonctionne.

**Phase 0 — Socle**
- [x] Dépôt, environnement, dépendances
- [x] Fabrique d'application et route de santé

**Phase 1 — La chaîne complète, en version minimale**
- [ ] Modèle de données : `Document`, `Analysis`, `Finding`
- [ ] Normalisation et segmentation
- [ ] Moteur de règles et deux premières règles
- [ ] Écran de résultats avec surlignage

**Phase 2 — Analyse grammaticale**
- [x] Intégration de spaCy et détection du passif
- [ ] Import de fichiers
- [ ] Tokenisation fine
- [ ] Deux règles supplémentaires

**Phase 3 — Finition**
- [ ] Durcissement et parcours d'erreur
- [ ] Écrans de configuration
- [ ] Historique, export, jeu de règles anglais
- [ ] Conteneurisation *(bonus — non attendue dans l'évaluation)*

## Limites connues

- Un texte à la fois, sans traitement par lots.
- Les suggestions se copient mais ne s'appliquent pas automatiquement : corriger le texte invaliderait toutes les positions affichées et supposerait de relancer l'analyse.
- *La porte est ouverte* reste un cas ambigu que l'analyse grammaticale ne tranche pas — le français ne distingue pas formellement le passif d'état du passif d'action.
- `fr_core_news_md` a été comparé à `fr_core_news_sm` sur le jeu d'essai du passif : aucun gain constaté. Le projet conserve donc le modèle léger, seul référencé dans `requirements.txt`.
- Le chargement du modèle spaCy occupe quelques centaines de mégaoctets au démarrage.

## Documentation

Le dossier `docs/` — non versionné — rassemble les décisions de conception, le programme de développement et un mémo théorique.

## Licence

[MIT](LICENSE). Les listes de mots et les jeux de règles sont couverts par la même licence ; leur origine est mentionnée avec le script d'amorce.
