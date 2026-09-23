# Analyseur de langage clair — repères de travail

Application Flask qui analyse un texte administratif en français, signale les
obstacles à la clarté et affiche chaque signalement dans le texte. Référentiel :
les dix principes de rédaction claire des institutions européennes.

**Échéance : lundi 28 septembre 2026. Fonctionnalités gelées le mercredi 23 septembre** (prévu le vendredi 25).

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
flask db upgrade        # après chaque nouvelle migration
flask seed              # listes de mots : data/seeds/lexiques.json -> base
flask run
```

Le venv a été créé sous le profil Windows `louis` : `pyvenv.cfg` pointe vers le
Python de ce profil. Les lanceurs `flask.exe` et `pytest.exe` ont été régénérés
le 21 septembre ; si un lanceur échoue, `.venv\Scripts\python.exe -m flask ...`
le contourne. Ne pas recréer le venv avant la soutenance : `requirements.txt`
n'épingle pas les versions.

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
| spaCy | Seul `services/ingestion/linguistics.py` importe spaCy. Les règles lisent `Sentence.analyse`. |
| Signalement | Toute règle renvoie un `Finding` avec un empan absolu. |
| Persistance | `Finding` est une dataclass de transport ; `FindingRecord` est le modèle SQLAlchemy. |
| Extensibilité | Un registre pour les règles, un pour les extracteurs : même motif, deux axes. Tous deux sont des tables littérales, `REGLES` et `REGISTRE` ; pas d'enregistrement par décorateur. |
| Langues | Seuils et lexiques par langue ; une langue non couverte ne doit jamais lever de `KeyError`. |
| Score | Pas de score global sur 100. |
| Données | Listes linguistiques versionnées dans `data/seeds/lexiques.json`, chargées en base par `flask seed` ; aucune requête réseau à l'exécution. |

## Architecture actuelle

```text
app/
├── __init__.py                 create_app(), extensions et /health
├── config.py                   configuration par environnement
├── cli.py                      commande flask seed
├── models/                     DocumentRecord, Analysis, FindingRecord, WordList, WordEntry
├── repositories.py             tout le SQL : listes de mots, analyses enregistrées
├── routes/analyze.py           GET/POST / ; /analyses/ : lister, enregistrer, relire
├── routes/admin.py             /listes/ : afficher, ajouter, supprimer des entrées
├── templates/                  base.html (menu, messages flash), analyze/, admin/
├── static/                     css/style.css (onze sections, variables de couleur), js/app.js
└── services/
    ├── ingestion/              la chaîne qui fait d'un texte brut un Document
    │   ├── normalization.py    normalisation Unicode et espaces
    │   ├── segmentation.py     paragraphes et phrases avec pysbd
    │   ├── tokenization.py     tokens grossiers avec offsets
    │   ├── linguistics.py      chargement spaCy et TokenLinguistique
    │   └── document.py         dataclasses métier et build_document()
    ├── rendering.py            échappement HTML et surlignage
    ├── extraction/
    │   ├── base.py             type Extracteur et erreurs d'import
    │   ├── registry.py         REGISTRE, extraire(), extensions_supportees()
    │   ├── txt.py              décodage sans encodage déclaré
    │   ├── md.py               décodage txt puis retrait des marques
    │   ├── docx.py             paragraphes via python-docx
    │   └── odt.py              paragraphes et titres via odfpy
    └── rules/
        ├── base.py             Finding et contrat Rule
        ├── runner.py           REGLES, regles() et run()
        ├── seuils.py           seuils numériques par langue
        ├── lexiques.py         lit les listes en base via le repository
        ├── fr.py               règles françaises
        └── en.py               vide ; extension anglaise future
```

La documentation détaillée de chaque module est dans
`docs/guide-des-modules-python.md`.

## État au 23 septembre

Phase 2 close le 18 septembre, import de fichiers compris. **Fonctionnalités
gelées le mercredi 23 septembre**, deux jours avant la date prévue : il ne reste
que des tests, la documentation et la répétition.

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
- Tests : 48 passent, plus un `xfail` assumé (« La porte est ouverte »), en
  moins de 3 secondes. L'invariant des positions est aussi vérifié sur
  `Sentence.analyse`.
- Import de fichiers : registre d'extracteurs, `.txt`, `.md`, `.docx`, `.odt`,
  refus explicite de `.pdf` et `.doc`. Le fichier l'emporte sur la zone de
  texte. Erreurs d'import affichées telles quelles dans le formulaire.
- Parcours d'erreur : `page()` est le rendu unique de l'écran, partagé par
  toutes les routes et par `app_errorhandler(413)` ; elle calcule elle-même le
  surlignage et le résumé. Le formulaire lit `maxlength` et le plafond en Mo
  dans `config`, plus rien d'écrit en dur ; `MAX_TEXT_LENGTH` est vérifié côté
  serveur ; `MAX_FORM_MEMORY_SIZE` est aligné sur `MAX_CONTENT_LENGTH` pour
  qu'un texte trop long reçoive son propre message ; `tests/test_validation.py`
  couvre les neuf cas.
- Quatre textes de démonstration dans `exemples/`, dont un `.txt` en cp1252
  qui exerce la détection d'encodage.
- Listes de mots en base : tables `word_lists` et `word_entries`, amorcées
  par `flask seed` depuis `data/seeds/lexiques.json` (idempotent : n'ajoute
  que ce qui manque, n'écrase rien). `lexiques.py` garde ses deux fonctions et
  lit la base via `repositories.lire_liste()` ; aucune règle n'a changé.
- Écran des listes de mots (`/listes/`, menu commun dans `base.html`) :
  afficher, ajouter, supprimer. La saisie passe par `normalize()` puis en
  minuscules, pour correspondre au texte analysé ; doublons et remplacement
  manquant refusés ; POST-Redirect-GET. Une modification vaut dès l'analyse
  suivante, sans cache ni redémarrage. `tests/test_admin.py` : onze cas.
- Documentation versionnée dans `docs/`, diaporama de soutenance
  (`docs/soutenance.pptx`).
- Les deux registres sont passés en tables littérales le 22 septembre :
  `REGLES` dans `rules/runner.py`, `REGISTRE` dans `extraction/registry.py`.
  Le décorateur `@enregistrer` a disparu des deux, avec l'import à effet de
  bord qu'il obligeait à garder. Le contrat des extracteurs est sorti dans
  `extraction/base.py`, comme `rules/base.py` : c'est ce qui évite le cycle
  `registry` → `docx` → `registry`. Aucun appelant n'a changé, les 39 tests
  passent à l'identique. `docs/` suit.
- Analyses enregistrées, le 23 septembre : « Analyser » n'enregistre rien.
  Sous le résultat, un formulaire demande un nom ; `POST /analyses/` relance
  l'analyse sur le texte normalisé renvoyé en champ caché (jamais d'empans
  venus du navigateur), l'enregistre via `repositories.enregistrer_analyse()`
  puis redirige vers `/analyses/<id>` (POST-Redirect-GET). La relecture
  reconstruit le `Document` et refait le surlignage depuis les `FindingRecord` :
  le HTML n'est jamais stocké. Cela tient parce que `normalize()` est
  idempotente. `Analysis.nom` et sa migration (`1436e85304b1`,
  `server_default='Sans nom'`). `/analyses/` liste les analyses ; menu à trois
  entrées ; messages flash dans `base.html`. `tests/test_historique.py` :
  neuf cas, dont les CRLF renvoyés par le navigateur.
- Mise en forme revue le 23 septembre : `style.css` en onze sections numérotées,
  variables de couleur dans `:root` (les 153 déclarations sont restées
  identiques), lignes vides et indentation corrigées dans le Python et les
  gabarits.
- Les cinq modules de la chaîne d'ingestion (normalisation, segmentation,
  tokenisation, spaCy, `Document`) regroupés le 23 septembre dans
  `services/ingestion/`, avec `git mv`. Seuls les imports ont changé ;
  48 tests passent à l'identique.

### Limites connues

- « La porte est ouverte » et « Il est convaincu » peuvent être signalés comme
  passifs : spaCy étiquette le participe `VERB`, état et passif restent
  ambigus pour cette heuristique.
- Tokenisation `\S+` : la ponctuation reste collée au mot.
- **Bug silencieux possible** : l'enregistrement relance les règles ; si une
  liste de mots change entre l'affichage et le clic sur « Enregistrer », les
  signalements enregistrés diffèrent de ceux affichés.
- `cree_le` est en UTC : seule la date est affichée, l'heure aurait 2 h de
  retard. Le résumé d'une analyse relue part des règles actives aujourd'hui.
- L'écran des listes n'a ni protection CSRF ni authentification : acceptable pour
  une application locale mono-utilisateur, à dire à l'oral. Flask-WTF réglerait le
  CSRF, mais c'est une nouvelle dépendance.
- Une entrée d'origine supprimée depuis l'écran revient au prochain `flask seed`,
  qui reprend les entrées manquantes. Les ajouts de l'utilisateur ne sont jamais
  touchés.
- Les règles lisent la base : `test_rules.py` et `test_passif.py` tournent dans
  une application de test amorcée (fixture `base_amorcee`), plus sans base.
- **Bug silencieux possible** : sur une base migrée mais non amorcée, rien ne
  plante — `connecteurs_lourds` disparaît des règles actives et `Passif` perd
  son exclusion des verbes avec *être*. Toujours `flask seed` après
  `flask db upgrade`.
- `docx.paragraphs` ignore le texte des tableaux.
- Ajouter l'anglais demandera une ligne dans `REGLES` et l'import de `en.py`
  dans `runner.py` : c'est le seul endroit du moteur où le couple de langues
  livrées devient visible.

## Prochaine priorité

Fonctionnalités gelées le 23 septembre. D'ici la soutenance, seulement des
tests, de la documentation et la répétition.

1. ~~Enregistrer les analyses~~ — fait le 23 septembre, sur demande et sous un nom.
2. ~~Passer en base les connecteurs lourds et les verbes conjugués avec
   *être*~~ — fait le 21 septembre.
3. Ajouter `tests/test_normalization.py` pour les six transformations.
4. Ajouter un test d'échappement sur `<`, `>` et `&` (vérifié à la main le
   23 septembre, sans test).
5. ~~Une quatrième règle~~ — abandonnée avec le gel.

Ordre de sacrifice : conteneurisation, export/historique, anglais,
administration, règles supplémentaires, tokenisation fine.
Ne jamais sacrifier la chaîne, les trois règles livrées, le surlignage, le
passif, le durcissement et la répétition de soutenance. La quatrième règle est
facultative depuis le 21 septembre.
