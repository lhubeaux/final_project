# Analyseur de langage clair

Analyse de textes en français selon des règles de langage clair.

## Démarrage

```bash
py -m venv .venv
.venv\Scripts\Activate.ps1        # PowerShell
pip install -r requirements.txt
```

Copier `.env.example` vers `.env` et renseigner `SECRET_KEY` :

```bash
cp .env.example .env
```

Puis :

```bash
flask run
```

L'application répond sur http://127.0.0.1:5000 — la route `/health` renvoie `{"status": "ok"}`.

## Tests

```bash
pytest
```
