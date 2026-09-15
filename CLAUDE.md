# Analyseur de langage clair — repères de travail

Application Flask qui analyse un texte administratif en français, signale les
obstacles à la clarté et affiche chaque signalement dans le texte. Référentiel :
les dix principes de rédaction claire des institutions européennes.

**Échéance : lundi 28 septembre 2026. Gel des fonctionnalités : jeudi 24 septembre.**

## Collaboration

- Répondre en français et rester court, sauf demande de détail.
- **Ne modifier aucun fichier sans demande explicite.** Donner le code exact à
  écrire pour que l'utilisateur l'applique et puisse l'expliquer.
- Toujours montrer un appel complet :
  `build_document(texte_brut, langue="fr")`, pas seulement son nom.
- Discuter avant toute nouvelle dépendance ou modification de `requirements.txt`.
- Signaler un bug silencieux en une phrase.

## Environnement et commandes

Windows 11, Python 3.14, développement natif sur `C:`, venv local `.venv`.
Ne pas déplacer le dépôt vers WSL.

```powershell
.venv\Scripts\Activate.ps1
.venv\Scripts\python.exe -m pytest -p no:cacheprovider
flask run
```

L'application répond sur `http://127.0.0.1:5000`. Les variables sont dans `.env`
et l'exemple est `.env.example`.

`fr_core_news_sm` 3.8.0 est le modèle de référence, épinglé dans
`requirements.txt`. `fr_core_news_md` est installé localement pour comparaison,
mais n'a montré aucun gain sur le jeu d'essai : ne pas l'ajouter aux dépendances.

## Pipeline et invariant central

```text
texte brut
  -> normalize()
  -> segment()
  -> tokenize()
  -> analyser_phrases()
  -> build_document()
  -> run(document)
  -> surligner()
  -> template
```

`build_document(texte_brut, langue="fr")` est le seul point d'entrée du moteur.
Il normalise une fois, puis le texte normalisé devient l'unique référence.

**Invariant :** pour chaque fragment, token ou signalement :

```python
document.texte[start:end] == fragment.texte
```

Ne jamais retrouver un empan avec `texte.find(...)` et ne jamais cumuler des
longueurs de paragraphes : les textes répétés et les lignes vides décalent les
positions.

Le HTML est échappé segment par segment avant l'insertion de `<mark>`. Ne jamais
échapper un texte déjà balisé ni découper un texte déjà échappé.

## Décisions non négociables

| Sujet | Décision |
|---|---|
| Entrée | Un texte à la fois ; français d'abord. |
| Formats | Prévoir `.txt`, `.md`, `.docx`, `.odt` ; refuser `.pdf` et `.doc`. |
| Objet des règles | `check(document)` reçoit le `Document` métier, jamais Flask ou spaCy. |
| spaCy | Seul `services/linguistics.py` importe spaCy. Les règles lisent `Sentence.analyse`. |
| Signalement | Toute règle renvoie un `Finding` avec un empan absolu. |
| Persistance | `Finding` est une dataclass de transport ; `FindingRecord` est le modèle SQLAlchemy. |
| Extensibilité | Registre pour les règles, et plus tard pour les extracteurs. |
| Langues | Seuils et lexiques par langue ; une langue non couverte ne doit jamais lever de `KeyError`. |
| Score | Pas de score global sur 100. |
| Données | Listes linguistiques versionnées dans le projet, aucune requête réseau à l'exécution. |

## Architecture actuelle

```text
app/
├── __init__.py                 create_app(), extensions et /health
├── config.py                   configuration par environnement
├── models/                     modèles SQLAlchemy : DocumentRecord, Analysis, FindingRecord
├── repositories.py             vide ; future persistance, sans linguistique
├── routes/analyze.py           GET/POST /, orchestration de l'analyse
├── routes/admin.py             vide ; future administration
└── services/
    ├── normalization.py        normalisation Unicode et espaces
    ├── segmentation.py         paragraphes et phrases avec pysbd
    ├── tokenization.py         tokens grossiers avec offsets
    ├── linguistics.py          chargement spaCy et TokenLinguistique
    ├── document.py             dataclasses métier et build_document()
    ├── rendering.py            échappement HTML et surlignage
    ├── extraction/             structure vide pour les imports futurs
    └── rules/
        ├── base.py             Finding et contrat Rule
        ├── runner.py           registre, regles() et run()
        ├── seuils.py           seuils numériques par langue
        ├── lexiques.py         connecteurs et verbes avec être
        ├── fr.py               règles françaises
        └── en.py               vide ; extension anglaise future
```

La documentation détaillée de chaque module est dans
`docs/guide-des-modules-python.md`.

## État au 15 septembre

### Fait

- Chaîne complète : normalisation, segmentation, tokenisation, `Document`,
  moteur de règles, surlignage et interface liée aux fiches.
- Règles : `longueur_phrase`, `connecteurs_lourds`, `passif`.
- Intégration spaCy : chaque phrase est analysée séparément puis projetée dans
  `Sentence.analyse`.
- Règle du passif : `aux:pass` et repli `cop`, participe obligatoirement `VERB`
  (écarte « est susceptible », « est nécessaire »), exclusion des verbes
  conjugués avec *être*, agent `obl:agent`, sévérité plus haute sans agent.
  Score sur les six phrases de référence : 4 sur 6 (2 sur 6 avec les
  dépendances seules).
- Interface : le texte surligné reste visible pendant le défilement des fiches
  sur ordinateur ; une colonne sur mobile.
- Tests : 19 passent ; « La porte est ouverte » est un `xfail` assumé.
  L'invariant des positions est aussi vérifié sur `Sentence.analyse`.

### Limites connues

- « La porte est ouverte » et « Il est convaincu » peuvent être signalés comme
  passifs : spaCy étiquette le participe `VERB`, état et passif restent
  ambigus pour cette heuristique.
- Tokenisation `\S+` : la ponctuation reste collée au mot.
- La route n'enregistre pas encore les analyses en base.
- Les extracteurs de fichiers, l'administration, les repositories et la CLI ne
  sont pas encore implémentés.

## Prochaine priorité

1. Implémenter l'import de fichiers : registre d'extracteurs, `.txt`, `.md`,
   `.docx`, puis `.odt`.
2. Ajouter validation serveur : texte vide, longueur maximale, format refusé,
   taille de fichier et fichier corrompu.
3. Ajouter `tests/test_normalization.py` pour les six transformations.
4. Ensuite seulement : tokenisation fine, règles supplémentaires, configuration,
   historique et export.

Ordre de sacrifice : conteneurisation, export/historique, anglais,
administration, `.odt`/`.docx`, règles supplémentaires, tokenisation fine.
Ne jamais sacrifier la chaîne, les quatre règles visées, le surlignage, le
passif, le durcissement et la répétition de soutenance.
