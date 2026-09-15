# Environnement de développement

*Mise à jour : 15 septembre 2026 — phase 2 en cours.*

*Ce document dit **comment le projet tourne**. Les décisions de conception sont dans [synthese-projet-langage-clair.md](synthese-projet-langage-clair.md), le calendrier dans [plan-de-travail.md](plan-de-travail.md).*

---

## 1. Le choix : venv local

**Environnement virtuel local pour développer. Conteneurisation en phase 3, si le temps le permet.** *(Décision D-13.)*

C'est le choix qui coûte le moins de temps. Développer dans un conteneur suppose de régler la question de l'interpréteur côté éditeur, le montage du code, le rechargement automatique et les événements de fichier sous Windows — une demi-journée dans le meilleur des cas, pour une catégorie de problèmes qui n'a rien à voir avec le sujet du projet.

L'application ne change pas d'un environnement à l'autre : une application Flask qui lit sa configuration dans des variables d'environnement s'exécute à l'identique dans un venv ou dans un conteneur.

---

## 2. État vérifié

| Élément | Valeur |
|---|---|
| Python | 3.14.4 |
| Emplacement | `C:\Users\louis\Documents\PythonFS\final_project` |
| Environnement | `.venv` local |
| Dépendances | installées, modèle spaCy français compris |
| Tests | `pytest` découvert par VS Code ; 19 passent, plus un `xfail` assumé |

**Paquets installés et vérifiés :** Flask 3.1.3, Flask-SQLAlchemy 3.1.1, Flask-Migrate 4.1.0, python-dotenv 1.2.3, charset-normalizer 3.5.1, python-docx 1.2.0, odfpy 1.4.1, pysbd 0.3.4, defusedxml 0.7.1, spacy 3.8.16, **fr_core_news_sm 3.8.0**, pytest 9.1.1. `fr_core_news_md` 3.8.0 est aussi présent pour comparaison, mais le projet utilise `sm` et seul ce dernier est épinglé dans `requirements.txt`.

> **Le risque d'installation de spaCy est écarté.** Le modèle français s'importe et s'exécute. C'est un point d'ordonnancement : le plan initial différait spaCy pour limiter ce risque, qui n'existe plus. Voir [plan-de-travail.md](plan-de-travail.md), principe 3.

### Note sur Python 3.14

Version récente, et spaCy publie bien une roue `cp314` — vérifié. Si une dépendance ajoutée plus tard refuse de s'installer faute de roue compilée pour 3.14, la solution est un venv en 3.12 plutôt qu'une compilation locale. Aucun signe de ce problème pour l'instant.

### Note sur Windows

Le dépôt est sur `C:`, ce qui est **correct** ici : le développement est natif Windows, il n'y a pas de frontière WSL à traverser. L'avertissement classique sur `/mnt/c/…` ne vaut que si l'on développe *sous* WSL ou dans un conteneur — ce n'est pas le cas. **Ne pas déplacer le dépôt.**

---

## 3. Repartir de zéro

Sur une autre machine, ou après un `git clone` :

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Puis renseigner `SECRET_KEY` dans `.env` :

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Et lancer :

```powershell
flask run                                                # http://127.0.0.1:5000
.venv\Scripts\python.exe -m pytest -p no:cacheprovider   # tests
```

**Deux pièges rencontrés :**

- Si l'activation est refusée par la politique d'exécution PowerShell : `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`. L'invite affiche `(.venv)` quand c'est actif.
- **Sous Git Bash, c'est `source .venv/Scripts/activate`**, pas `bin/activate`. Le chemin `bin/` n'existe que pour un venv créé sous Linux.

---

## 4. Arborescence

*Le raisonnement derrière ce découpage est dans la synthèse, décisions D-8 et D-9.*

```
final_project/
├── .vscode/
│   └── settings.json          # découverte des tests par pytest
├── app/
│   ├── __init__.py            # fabrique d'application, /health
│   ├── config.py              # configuration par variables d'environnement
│   ├── models/                # DocumentRecord, Analysis, FindingRecord
│   ├── repositories.py        # accès aux données (vide)
│   ├── cli.py                 # commandes : seed, retokenize (vide)
│   ├── routes/
│   │   ├── analyze.py         # saisie, résultats
│   │   └── admin.py           # règles, listes de mots, historique (vide)
│   ├── services/
│   │   ├── extraction/        # fichiers vides, prévus pour l'import
│   │   │   ├── registry.py    # interface commune + enregistrement
│   │   │   ├── txt.py
│   │   │   ├── docx.py
│   │   │   ├── odt.py
│   │   │   └── md.py
│   │   ├── document.py        # dataclasses métier, build_document()
│   │   ├── normalization.py   # BOM, fins de ligne, NFC, apostrophes, insécables
│   │   ├── segmentation.py    # paragraphes et phrases (pysbd)
│   │   ├── tokenization.py    # tokens grossiers avec positions
│   │   ├── linguistics.py     # unique point de contact avec spaCy
│   │   ├── rendering.py       # échappement HTML et surlignage
│   │   └── rules/
│   │       ├── base.py        # classe Rule, dataclass Finding
│   │       ├── runner.py      # registre, exécution, filtrage par langue
│   │       ├── seuils.py      # seuils par langue
│   │       ├── lexiques.py    # listes de mots par langue
│   │       ├── fr.py          # longueur_phrase, connecteurs_lourds, passif
│   │       └── en.py          # (vide)
│   ├── templates/analyze/index.html
│   └── static/                # css/style.css, js/app.js
├── data/seeds/                # listes de mots versionnées (vide)
├── scripts/                   # futur script d'amorce, hors application (vide)
├── tests/                     # positions, règles, passif, smoke
├── migrations/                # Alembic, première migration écrite
├── instance/                  # base SQLite locale — non versionnée
├── docs/                      # documentation du projet, versionnée
├── .env.example
├── .env                       # non versionné
├── .gitattributes
├── .gitignore
├── requirements.txt
├── Dockerfile                 # phase 3, si le temps le permet (absent)
├── LICENSE                    # MIT
└── README.md
```

Les fichiers marqués *(vide)* existent déjà et se remplissent au fil des phases. Les `.gitkeep` de `data/seeds/` et `scripts/` servent à faire suivre ces dossiers vides par git. Ceux de `templates/` et `static/` peuvent être supprimés, puisque ces dossiers ont maintenant du contenu.

---

## 5. Fichiers de configuration

### `requirements.txt`

```
Flask
Flask-SQLAlchemy
Flask-Migrate
python-dotenv
charset-normalizer
python-docx
odfpy
pysbd
defusedxml
spacy
https://github.com/explosion/spacy-models/releases/download/fr_core_news_sm-3.8.0/fr_core_news_sm-3.8.0-py3-none-any.whl
pytest
```

**Le modèle spaCy est épinglé par URL.** Une installation ordinaire le récupère comme n'importe quelle autre dépendance — dans le venv aujourd'hui, dans l'image Docker en phase 3, sur un hébergeur en cas de mise en ligne. Une ligne qui évite une soirée de perplexité.

`fr_core_news_md` a été comparé à `sm` sur sept phrases de référence, sans gain observé. Cette ligne reste donc inchangée.

### `.env.example`

```
FLASK_APP=app
FLASK_DEBUG=1
SECRET_KEY=changez-moi
DATABASE_URL=sqlite:///instance/analyseur.db
MAX_TEXT_LENGTH=20000
MAX_UPLOAD_BYTES=2097152
```

Versionner `.env.example`, jamais `.env`. Celui qui clone copie l'un vers l'autre, et le README le dit.

`MAX_UPLOAD_BYTES` alimente `MAX_CONTENT_LENGTH`, que **Flask applique lui-même** avant que le code ne voie la requête. `MAX_TEXT_LENGTH` est propre au projet et sert à valider le formulaire.

### `.gitignore`

```
__pycache__/
*.py[cod]
.venv/
.env
instance/
*.db
.pytest_cache/
todo.md
```

*`docs/` n'est plus exclu : la documentation est versionnée. Seul `todo.md` reste local.*

### `.gitattributes`

```
* text=auto eol=lf
```

Évite que des fins de ligne CRLF se glissent dans des fichiers destinés à être lus sous Linux. À committer **en premier** dans un dépôt : la règle ne s'applique qu'aux fichiers indexés après elle.

---

## 6. VS Code

L'essentiel tient en trois gestes, tous effectués :

1. Extension **Python** installée (Pylance vient avec).
2. Interpréteur `.venv` sélectionné — palette de commandes, *Python: Select Interpreter*.
3. Découverte des tests activée — *Python: Configure Tests* → pytest → dossier `tests`. Le résultat est dans `.vscode/settings.json`, versionné : celui qui clone hérite de la configuration.

**Faire le geste 2 avant d'écrire du code**, pas après. Sinon Pylance reste sur le Python global : aucune autocomplétion sur `flask`, et un avertissement d'import non résolu sur chaque ligne.

Deux extensions de confort : **Jinja** pour la coloration des gabarits, **SQLite Viewer** pour inspecter la base sans quitter l'éditeur.

Le reste — formatage, linter, configuration de débogage — peut attendre le jour où il manque. Ce n'est pas de la structure, c'est du confort, et le confort s'ajoute en cours de route sans rien casser.

---

## 7. Versionnement de `docs/`

**Tranché : `docs/` est versionné.** La synthèse des décisions montre qu'une réflexion a précédé le code : formats refusés avec leurs raisons, rejet du score sur 100, arbitrage sur les règles proportionnelles. C'est ce qu'un jury ou un recruteur cherche et trouve rarement.

`theorie.md` et `soutenance.md` sont des mémos personnels. Ils peuvent rester dans le dépôt ou être ajoutés à `.gitignore` avant la livraison.
