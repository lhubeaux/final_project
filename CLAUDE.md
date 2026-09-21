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
saisie ou fichier
  -> extraire(nom_fichier, flux)        # chemin fichier seulement
  -> texte brut
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

Un extracteur rend du texte **brut** et ne normalise jamais : sinon les deux
chemins d'entrée produiraient deux textes de référence différents.

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
| Formats | `.txt`, `.md`, `.docx`, `.odt` acceptés ; `.pdf` et `.doc` refusés avec un message dédié. |
| Objet des règles | `check(document)` reçoit le `Document` métier, jamais Flask ou spaCy. |
| spaCy | Seul `services/linguistics.py` importe spaCy. Les règles lisent `Sentence.analyse`. |
| Signalement | Toute règle renvoie un `Finding` avec un empan absolu. |
| Persistance | `Finding` est une dataclass de transport ; `FindingRecord` est le modèle SQLAlchemy. |
| Extensibilité | Un registre pour les règles, un pour les extracteurs : même motif, deux axes. |
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
    ├── extraction/
    │   ├── registry.py         registre, extraire() et erreurs d'import
    │   ├── txt.py              décodage sans encodage déclaré
    │   ├── md.py               décodage txt puis retrait des marques
    │   ├── docx.py             paragraphes via python-docx
    │   └── odt.py              paragraphes et titres via odfpy
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

## État au 21 septembre

Phase 2 close le 18 septembre, import de fichiers compris. Phase 3 en cours,
gel des fonctionnalités dans trois jours.

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
- Tests : 28 passent, plus un `xfail` assumé (« La porte est ouverte »), en
  moins de 3 secondes. L'invariant des positions est aussi vérifié sur
  `Sentence.analyse`.
- Import de fichiers : registre d'extracteurs, `.txt`, `.md`, `.docx`, `.odt`,
  refus explicite de `.pdf` et `.doc`. Le fichier l'emporte sur la zone de
  texte. Erreurs d'import affichées telles quelles dans le formulaire.
- Parcours d'erreur : `page()` est le rendu unique de l'écran, partagé par la
  route et par `app_errorhandler(413)` ; `MAX_TEXT_LENGTH` est vérifié côté
  serveur ; `tests/test_validation.py` couvre les neuf cas.
- Quatre textes de démonstration dans `exemples/`, dont un `.txt` en cp1252
  qui exerce la détection d'encodage.
- Documentation versionnée dans `docs/`, diaporama de soutenance
  (`docs/soutenance.pptx`).

### Limites connues

- « La porte est ouverte » et « Il est convaincu » peuvent être signalés comme
  passifs : spaCy étiquette le participe `VERB`, état et passif restent
  ambigus pour cette heuristique.
- Tokenisation `\S+` : la ponctuation reste collée au mot.
- La route n'enregistre pas encore les analyses en base.
- L'administration, les repositories et la CLI ne sont pas encore implémentés.
- `docx.paragraphs` ignore le texte des tableaux.
- `MAX_FORM_MEMORY_SIZE` n'est pas encore fixé : un texte collé de plus de
  500 Ko reçoit le message du 413 au lieu de celui de `MAX_TEXT_LENGTH`.

## Prochaine priorité

L'import de fichiers étant livré, la phase 3 n'a plus qu'un objet : le
durcissement. Trois jours avant le gel.

1. Fixer `MAX_FORM_MEMORY_SIZE` sur `MAX_CONTENT_LENGTH` dans `config.py`,
   pour qu'un texte trop long reçoive son message et non celui du 413.
2. Ajouter `tests/test_normalization.py` pour les six transformations.
3. Vérifier l'échappement sur un texte contenant `<`, `>` et `&`.
4. Ensuite seulement : tokenisation fine, règles supplémentaires, configuration,
   historique et export.

Ordre de sacrifice : conteneurisation, export/historique, anglais,
administration, règles supplémentaires, tokenisation fine.
Ne jamais sacrifier la chaîne, les quatre règles visées, le surlignage, le
passif, le durcissement et la répétition de soutenance.
