# Analyseur de langage clair — consignes de travail

Projet de fin de formation. Application Flask qui analyse un texte administratif selon
les dix principes de rédaction claire des institutions européennes.

**Échéance : lundi 28 septembre 2026. Gel des fonctionnalités : jeudi 24 septembre.**

---

## Comment travailler avec moi

- **Ne modifie aucun fichier sans demande explicite.** Donne le code exact à écrire, je
  l'applique moi-même. C'est délibéré : je dois pouvoir expliquer chaque ligne en soutenance.
- **Réponds en français**, et **court par défaut**. Une question ponctuelle appelle une réponse
  de deux ou trois lignes, pas une section structurée. Développe seulement si je le demande.
- **Montre toujours la syntaxe d'appel complète** d'une fonction, pas seulement son nom :
  `render_template("analyze/index.html", texte=valeur)`, pas « utilise render_template ».
- Pas de dépendance nouvelle sans en discuter d'abord.
- Signale un bug silencieux si tu en vois un, mais en une phrase.

---

## Environnement

Windows 11, Python 3.14, venv local. Le dépôt reste sur `C:` — développement natif Windows,
pas de WSL, ne pas déplacer.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1          # PowerShell
# source .venv/Scripts/activate     # Git Bash — Scripts/, pas bin/
pip install -r requirements.txt
Copy-Item .env.example .env         # puis renseigner SECRET_KEY
flask run                           # http://127.0.0.1:5000
pytest
```

`SECRET_KEY` : `python -c "import secrets; print(secrets.token_hex(32))"`

Le modèle spaCy `fr_core_news_sm` 3.8.0 est épinglé par URL dans `requirements.txt` :
`pip install -r` suffit, aucun téléchargement séparé.

---

## Ce qui n'est pas dans le dépôt

`docs/`, `todo.md`, `.env`, `instance/`, `.venv/` sont dans `.gitignore`. Sur une autre machine,
les quatre documents de conception (`plan-de-travail.md`, `synthese-projet-langage-clair.md`,
`theorie.md`, `setup-projet-vscode.md`) **ne seront pas là**. Ce fichier porte donc l'essentiel
de ce qu'ils contiennent.

---

## Décisions de conception à respecter

| Réf. | Décision |
|---|---|
| D-1 | Un texte à la fois ; français d'abord, anglais ensuite |
| D-2 | `.txt` `.docx` `.odt` `.md` acceptés ; `.pdf` et `.doc` refusés |
| D-3 | `check()` reçoit un objet `Document` maison (paragraphes, phrases, tokens) |
| D-4 | Normaliser **une seule fois** à l'entrée ; le texte normalisé est LE texte de référence |
| D-5 | Toute règle renvoie un `Finding` portant un empan de caractères |
| D-6 | `Finding` (transport, dataclass) ≠ `FindingRecord` (persistance) |
| D-7 | spaCy isolé derrière `services/linguistics.py` — aucune règle ne l'importe |
| D-8 | Motif de registre, appliqué deux fois : extracteurs et règles |
| D-9 | Un module tant qu'il n'y a pas trois fichiers de même nature |
| D-10 | Pas de score global sur 100 |
| D-11 | Seuils définis par langue |
| D-12 | Listes de mots amorcées par script ponctuel, résultat versionné |
| D-13 | Conteneurisation = bonus, non attendue dans l'évaluation, à faire en dernier |
| D-14 | Détection du passif = dépendances syntaxiques **+ heuristiques** (2/6 mesuré avec `sm` seul) |
| D-15 | Ponctuation conservée ; forme brute et forme normalisée stockées |

---

## L'invariant des positions

La chaîne est `normaliser → segmenter → tokeniser → analyser`. Chaque couche découpe une
chaîne et **transporte** sa position par addition, elle ne la recalcule jamais :

```
bloc.start()      position du paragraphe dans le texte
+ span.start      position de la phrase dans le paragraphe
= phrase["start"] position de la phrase dans le texte   ─┐ passé en offset
+ match.start()   position du token dans la phrase      ─┘
= token["start"]  position du token dans le texte
```

L'invariant qui garde tout ça en vie, testé dans `tests/test_positions.py` :

```python
texte[fragment["start"]:fragment["end"]] == fragment["texte"]
```

Deux pièges déjà rencontrés, à ne pas réintroduire :

- `texte.find(phrase)` pour retrouver une position — échoue dès qu'une phrase se répète.
- Cumuler les longueurs — dérive de 2 caractères par ligne vide entre paragraphes.

Corollaire XSS : échapper le HTML **avant** d'insérer les balises de surlignage, segment par
segment entre les frontières de signalements. L'échappement change la longueur (`<` → `&lt;`).

---

## Architecture

```
app/
├── __init__.py            fabrique create_app()
├── config.py              configuration par variables d'environnement
├── models.py              Document, Analysis, FindingRecord
├── repositories.py        accès aux données — aucune linguistique
├── cli.py                 commandes : seed, retokenize
├── routes/                analyze (utilisateur) · admin (configuration)
└── services/
    ├── extraction/        registre + un module par format
    ├── normalization.py   BOM, CRLF, NFC, soft hyphen, apostrophes, insécables
    ├── segmentation.py    pysbd, char_span=True — sans franchir les paragraphes
    ├── tokenization.py    \S+ avec offset
    ├── linguistics.py     unique point de contact avec spaCy
    └── rules/             base · runner · fr · en
```

---

## État d'avancement

**Phase 0 — socle** ✅ dépôt, venv, dépendances, `create_app()`, route `/health`.

**Phase 1 — la chaîne complète en version minimale** (→ ven 11/09), en cours :
- ✅ `normalization.py`, `segmentation.py`, `tokenization.py` avec positions absolues
- ✅ route `POST /analyze`, template de diagnostic affichant `texte[start:end]`
- ⬜ `models.py` : `Document`, `Analysis`, `FindingRecord` — trois entités, pas sept
- ⬜ objet `Document` maison (D-3), puis `rules/base.py` et `rules/runner.py`
- ⬜ deux règles : longueur de phrase (seuil), connecteurs lourds (liste + remplacement)
- ⬜ écran de résultats avec surlignage
- ⬜ tests unitaires des règles et de la normalisation, sans base de données

**Phase 2** (→ ven 18/09) : spaCy et détection du passif *(priorité absolue)*, import de
fichiers, tokenisation fine, deux règles de plus.

**Phase 3** (→ jeu 24/09) : durcissement d'abord, documentation, écrans de configuration,
puis historique / export / anglais / conteneurisation.

---

## Ordre de sacrifice si le retard s'installe

Conteneurisation → export et historique → jeu de règles anglais → écrans de configuration →
import `.odt` puis `.docx` → règles au-delà des quatre premières → tokenisation fine.

**Jamais sacrifié :** normalisation, segmentation, moteur de règles, quatre règles,
surlignage, détection du passif, durcissement, journée de répétition.

---

## Habitudes

- Une branche par fonctionnalité, un commit par jour minimum, messages en français.
- Ne jamais terminer la journée sur un dépôt qui ne démarre pas.
- Le moteur de règles ne connaît pas la base : ses tests tournent en isolation, devant le jury.
