# Plan de travail

**Échéance : lundi 28 septembre 2026.**

*Remplace `programme-3-semaines.md`. Ce document dit **quand** et **dans quel ordre**. Les décisions de conception et leurs raisons sont dans [synthese-projet-langage-clair.md](synthese-projet-langage-clair.md), l'environnement dans [setup-projet-vscode.md](setup-projet-vscode.md), les révisions dans [theorie.md](theorie.md).*

---

## L'objectif, énoncé sans ambiguïté

**Un projet fonctionnel le 28 septembre, pas un projet terminé.**

Ce n'est pas une concession, c'est une méthode. Un projet complet à 70 % et démontrable de bout en bout vaut infiniment mieux qu'un projet complet à 95 % qui plante à l'ouverture. Le jury voit ce que tu montres, pas ce que tu avais prévu de faire.

### Ce que « fonctionnel » veut dire précisément

C'est le contrat minimum. Tout le reste est négociable.

1. On colle un texte institutionnel dans une page web.
2. On clique sur *Analyser*.
3. Les problèmes apparaissent surlignés dans le texte, listés à côté, rattachés à un principe de rédaction claire.
4. Rien ne plante sur un texte vide, un texte très long, ou un texte contenant des caractères spéciaux.
5. Une suite de tests s'exécute devant le jury et passe.

**Si ces cinq points tiennent le 24 septembre, le projet est réussi.** Ce qui s'ajoute ensuite améliore la note ; ce qui manque ne la détruit pas.

---

## Le calendrier réel

| Période | Phase |
|---|---|
| lun 07/09 | **Phase 0** — socle *(fait)* |
| lun 07 → ven 11/09 | **Phase 1** — la chaîne complète, en version minimale |
| lun 14 → ven 18/09 | **Phase 2** — ce qui rend le projet intéressant *(close)* |
| lun 21 → jeu 24/09 | **Phase 3** — rendre présentable *(en cours)* |
| **jeu 24/09 au soir** | **Gel des fonctionnalités** |
| ven 25 → dim 27/09 | Répétition de la soutenance |
| **lun 28/09** | Livraison |

Quinze jours ouvrés. Le plan ne suppose plus six heures productives par jour — il suppose seulement que **chaque phase se termine par quelque chose qui marche**. Si une phase déborde, ce n'est pas la suivante qui recule : c'est du contenu qu'on retire à l'intérieur de la phase (voir *Ce qu'on coupe*).

---

## Les quatre principes d'ordonnancement

Ils comptent davantage que le détail des tâches.

**1. La chaîne complète avant la profondeur.** Coller un texte et voir un surlignage doit fonctionner *avant* qu'il y ait plus de deux règles, avant l'import de fichiers, avant spaCy. Un chemin étroit mais complet se remplit ensuite ; un chemin large mais interrompu ne se démontre pas.

**2. Rien n'entre en phase 1 qui ne serve la démonstration minimale.** L'import de `.docx`, la tokenisation fine, les écrans d'administration : tout cela est réel, utile, et attendra la phase 2.

**3. La dépendance la plus lourde arrive en second.** spaCy n'entre en jeu qu'en phase 2, une fois l'application déjà fonctionnelle. *(Le risque d'installation, lui, est déjà écarté : le modèle `fr_core_news_sm` 3.8.0 est installé et vérifié — voir le setup.)*

**4. Gel des fonctionnalités le 24 septembre.** Passé cette date : correction, documentation, répétition. Aucune fonctionnalité nouvelle, quelle que soit la tentation. C'est la décision qui protège le plus efficacement une soutenance, et celle qu'on regrette toujours de ne pas avoir prise.

---

## Phase 0 — Socle ✅

*Terminée le 07/09.*

Dépôt Git, environnement virtuel, dépendances installées (modèle spaCy français compris), arborescence, fabrique d'application, route `/health`, découverte des tests dans VS Code.

Détail et état exact dans [setup-projet-vscode.md](setup-projet-vscode.md).

---

## Phase 1 — La chaîne complète, en version minimale

**→ vendredi 11 septembre**

**Fin de phase :** je colle un texte, je clique, je vois des phrases trop longues surlignées et listées à côté.

### Contenu

**Modèle de données — trois entités seulement.** ✅ `DocumentRecord`, `Analysis`, `FindingRecord`, et leur migration (`app/models/`). Les quatre autres (`RuleSet`, `RuleConfig`, `WordList`, `WordEntry`) attendent la phase 2 : tant qu'il n'y a pas d'écran de configuration, elles ne servent à rien. Les listes de mots se lisent directement depuis les fichiers JSON de `data/seeds/`.

**Normalisation.** ✅ Un seul service : NFC, apostrophes, espaces insécables, conservation des sauts de paragraphe. (`app/services/normalization.py`)

**Segmentation.** ✅ Découpage en phrases avec `pysbd`, sans franchir les frontières de paragraphe. (`app/services/segmentation.py`)

**Tokenisation grossière.** ✅ Découpage sur les espaces (`\S+` via `re.finditer`), avec positions char_start/char_end. (`app/services/tokenization.py`)

**Route d'analyse.** ✅ `POST /` appelle `build_document(texte_brut, langue="fr")`, exécute les règles et transmet le texte surligné au template. (`app/routes/analyze.py`)

**Le moteur de règles.** ✅ Classe de base `Rule`, `Finding` en dataclass, registre, exécutant filtrant par langue. (`app/services/rules/`)

> **Tranché : ce que reçoit `check()`.** Un objet `Document` maison portant paragraphes, phrases et tokens. En phase 2, spaCy s'y est ajouté sous la forme de `Sentence.analyse` (et non d'un `.spacy_doc` brut) — les règles déjà écrites n'ont pas changé. *(Décision D-3 dans la synthèse.)*

**Deux règles**, pas quatre : ✅ longueur de phrase (seuil) et connecteurs lourds (liste + remplacement). Elles suffisent à éprouver le moteur et produisent immédiatement des signalements sur un texte institutionnel réel.

**Une tokenisation grossière** — ✅ voir ci-dessus.

**L'écran de résultats.** ✅ Texte surligné à gauche, liste des signalements à droite, lien dans les deux sens. Échappement HTML **d'abord**, construction par segments entre frontières de signalements.

**Tests unitaires** sur les deux règles ✅ et sur la normalisation ⬜, sans base de données.

*Jalon du 11/09 atteint.*

### Ce qui n'est PAS en phase 1

L'import de fichiers. Une zone de texte suffit à boucler la chaîne, et l'extraction `.docx`/`.odt` représente une journée entière qui ne rend rien de plus démontrable. C'est le changement le plus important par rapport au plan initial.

---

## Phase 2 — Ce qui rend le projet intéressant

**→ vendredi 18 septembre**

**Fin de phase :** l'application distingue un vrai passif d'un passé composé avec *être*, et accepte des fichiers.

### Contenu, par ordre de valeur décroissante

**1. spaCy et la détection du passif.** C'est la pièce maîtresse de la soutenance, et elle passe avant tout le reste de la phase.

*Bilan de phase, 18/09 : points 1 et 2 réalisés et mesurés. `linguistics.py` analyse chaque phrase isolée, la règle `passif` est couverte par des tests, la comparaison `fr_core_news_sm` / `md` sur sept phrases n'a montré aucun gain pour `md`. Jeu d'essai élargi (passif au futur, attributs adjectivaux) ; score de 4 sur 6 sur les phrases de référence.*

*Point 3 réalisé le 18/09 : registre d'extracteurs, `.txt`, `.md`, `.docx`, `.odt`, refus explicites de `.pdf` et `.doc`, quatre textes de démonstration dans `exemples/`. Un écart au cahier des charges du point : le choix de l'extracteur se fait sur l'extension et non sur les octets d'en-tête. `defusedxml`, lui, est bien à l'œuvre sur le `.odt`, mais appelé par odfpy et non par le code du projet.*

*Points 4 à 6 non réalisés : tokenisation fine, deux règles de plus, script d'amorce. Ils entrent dans l'ordre de sacrifice.*

- Chargement du modèle **une seule fois** au démarrage, derrière `services/linguistics.py`.
- **Le jeu d'essai d'abord, la règle ensuite.** Une vingtaine de phrases : passifs véritables, et faux positifs classiques (*elle est allée*, *la porte est ouverte*, *il est convaincu*).
- Détection par `aux:pass` / `nsubj:pass`, **plus heuristiques**.

> **Résultat mesuré, à connaître avant de s'y engager :** sur les six phrases de référence, le critère `aux:pass`/`nsubj:pass` seul obtient **2 sur 6** avec `fr_core_news_sm`. Les heuristiques ne sont pas un ornement, elles portent la moitié du résultat. Budgète-les. Détail des cas dans [theorie.md](theorie.md) §6.
>
> **Premier réflexe :** tester `fr_core_news_md` sur le même jeu d'essai. Si le score monte nettement, une ligne de `requirements.txt` remplace des heures de travail.

**2. Passif sans agent exprimé**, signalé plus sévèrement — le lecteur ne peut alors pas savoir qui agit, ce qui est exactement le défaut visé.

**3. Import de fichiers.** Registre d'extracteurs, `.txt`, `.md`, `.docx`, puis `.odt`. Vérification des octets d'en-tête, `defusedxml`, plafond de taille. Chaque extracteur renvoie du texte brut qui passe ensuite par `build_document(texte_brut, langue="fr")`.

**4. Tokenisation propre.** Élisions, traits d'union avec liste d'exceptions, abréviations, nombres. Numéro de version du tokeniseur et commande de retokenisation.

**5. Deux règles de plus :** jargon institutionnel, densité de nominalisations (un signalement par token). *Piège connu : le suffixe `-ment` est nominalisant dans « fonctionnement » et adverbial dans « rapidement ».*

**6. Script d'amorce des listes de mots**, produisant un fichier versionné — jamais une requête réseau à l'exécution.

### Si la phase 2 déborde

Coupe dans l'ordre inverse : d'abord le script d'amorce (les listes se saisissent à la main), puis les deux règles supplémentaires, puis la tokenisation fine, puis `.odt`. **Ne coupe jamais le point 1.**

---

## Phase 3 — Rendre présentable

**→ jeudi 24 septembre — en cours depuis le lundi 21.**

**Fin de phase :** un jury peut manipuler l'application sans la casser, et le dépôt se lit tout seul.

> **État au 21/09, à l'ouverture de la phase.** Chaîne complète, surlignage, trois règles sur les quatre visées, import des quatre formats, 28 tests plus un `xfail`, documentation et diaporama faits.
>
> **L'import étant livré avec la phase 2, la phase 3 n'a plus qu'un objet : le durcissement.** Fait le 21/09 : l'erreur 413 rend désormais la page du formulaire avec son bandeau, `MAX_TEXT_LENGTH` est vérifié côté serveur, et `tests/test_validation.py` couvre le parcours d'erreur. Restent `MAX_FORM_MEMORY_SIZE` dans la configuration et `tests/test_normalization.py`.
>
> **Une décision reste à prendre**, et elle n'est pas technique : « quatre règles fonctionnelles » figure ci-dessous parmi ce qui n'est jamais sacrifié, et il n'y en a que trois. Soit la quatrième s'écrit — le jargon est une entrée de lexique de plus, une demi-journée — soit la liste descend à trois et c'est assumé à l'oral. Ne pas laisser la question ouverte jusqu'au 24.

### Contenu

**1. Durcissement — c'est la priorité de la phase, avant toute fonctionnalité.**

- Parcours d'erreur : fichier trop volumineux, format refusé, texte vide, texte à la longueur maximale, fichier corrompu.
- Vérifier l'échappement HTML sur un texte contenant `<`, `>` et `&`.
- Compléter la suite de tests là où elle est mince.
- Relire les messages d'erreur destinés à l'utilisateur.

**2. Documentation.** README à jour et honnête, licence choisie, origine des listes de mots mentionnée.

**3. Écrans de configuration** — *si le temps le permet.* Écran *Règles* (activation, seuils) et écran *Listes de mots*. C'est le CRUD du projet, et il sert bien la démonstration : désactiver une règle, relancer, voir les signalements disparaître. Les quatre entités restantes du modèle de données arrivent ici.

**4. Le reste, par ordre de renoncement** : historique des analyses, export du rapport, filtres par principe, jeu de règles anglais, conteneurisation.

> **Sur la conteneurisation.** Question tranchée auprès du formateur : elle **n'est pas attendue dans l'évaluation**, elle compte comme bonus. Elle reste donc en dernier, après tout le reste, et elle est la première chose coupée si le retard s'installe. Un `Dockerfile` en cible unique se rédige en une heure quand le reste est fini — ne pas l'entamer avant.

---

## Gel, répétition, livraison

**Jeudi 24/09 au soir : gel.** Plus aucune fonctionnalité.

**Vendredi 25/09 et le week-end : répétition.** Cette journée n'est pas du confort, c'est la journée la plus rentable des trois semaines.

- Préparer deux ou trois textes de démonstration, dont un déjà chargé au démarrage.
- Répéter **à voix haute, chronomètre en main, au moins deux fois.**
- Trame : le problème et le référentiel → démonstration → parcours du code (le motif de registre, l'objet `Finding`, la détection du passif) → limites assumées → suite envisageable.
- Réviser [theorie.md](theorie.md) §10 — les quinze questions probables.
- Plan B : captures d'écran ou courte vidéo, si la machine refuse de coopérer.

**Lundi 28/09 : livraison.**

---

## Ce qu'on coupe si le retard s'installe

Par ordre de sacrifice, du plus facile au plus douloureux. Coupe **dans cet ordre**, sans négocier avec toi-même.

1. Conteneurisation et mise en ligne
2. Export et historique
3. Jeu de règles anglais — mais savoir expliquer comment il s'ajouterait
4. Écrans de configuration — remplaçables par des données d'amorce en base
5. ~~Import `.odt`, puis `.docx`~~ — *fait le 18/09, sorti de la liste*
6. Les règles au-delà des quatre premières
7. La tokenisation fine — un découpage grossier tient debout

## Ce qui n'est jamais sacrifié

- La normalisation et la segmentation
- Le moteur de règles et son registre
- Quatre règles fonctionnelles
- L'écran de résultats avec surlignage
- La détection du passif
- Le durcissement de la phase 3
- La journée de répétition

Si tu dois choisir entre une fonctionnalité de plus et la journée de répétition, **garde la répétition.** Beaucoup de projets perdent des points pour avoir été construits sans avoir été montrés une seule fois à voix haute.

---

## Habitudes quotidiennes

- Une branche par fonctionnalité, un commit par jour au minimum, messages cohérents dans une seule langue.
- Un ticket par élément de phase, comme pour le projet de groupe : le jury voit une méthode.
- Tenir un journal court des décisions et de leurs raisons — c'est la matière première de la soutenance, et elle s'évapore en trois semaines.
- **Ne jamais terminer la journée sur un dépôt qui ne démarre pas.**

---

## Jalons de contrôle

Trois moments où l'on s'arrête pour constater, honnêtement, où l'on en est.

| Date | Question | Si la réponse est non |
|---|---|---|
| **ven 11/09** | Est-ce que je colle un texte et vois des signalements surlignés ? | Retirer des règles jusqu'à ce que oui, avant de toucher à spaCy. |
| **ven 18/09** | Est-ce que la détection du passif distingue *la décision a été prise* de *elle est allée à Paris* ? | ✅ **Oui.** 4 sur 6 sur les phrases de référence, contre 2 sur 6 avec les dépendances seules ; les deux échecs sont documentés, dont un en `xfail`. |
| **jeu 24/09** | Est-ce qu'un inconnu peut manipuler l'application dix minutes sans la casser ? | Geler quand même et corriger. Le gel n'est pas négociable. |
