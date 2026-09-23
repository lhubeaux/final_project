# Analyseur de langage clair — décisions de conception

*Mise à jour : 23 septembre 2026.*

*Ce document dit **quoi** et **pourquoi**. Le calendrier est dans [plan-de-travail.md](plan-de-travail.md), l'environnement dans [setup-projet-vscode.md](setup-projet-vscode.md), les révisions de soutenance dans [theorie.md](theorie.md).*

---

## 1. Le projet

Une application web qui analyse un texte selon les principes de rédaction claire des institutions européennes, signale ce qui nuit à la clarté et propose, quand c'est possible, une formulation plus simple.

**Pourquoi celui-ci :** le référentiel est publié et citable (les dix principes du guide *Comment écrire clairement*), ce qui évite d'avoir à justifier des critères inventés ; la démonstration est immédiate ; et le sujet rejoint une expertise professionnelle réelle.

**Contraintes :** environ trois semaines, échéance au 28 septembre 2026. L'évaluation porte sur une démonstration en fonctionnement, quelques fonctionnalités, et l'explication du code. Le recours aux bibliothèques existantes est accepté.

---

## 2. Registre des décisions

Chaque décision porte un identifiant, pour que les autres documents y renvoient sans la reproduire.

| Réf. | Décision | Motif en une ligne |
|---|---|---|
| **D-1** | Un texte à la fois ; français d'abord, anglais ensuite | Le périmètre tient dans le temps disponible |
| **D-2** | `.txt`, `.docx`, `.odt`, `.md` acceptés ; `.pdf` et `.doc` refusés | L'extraction PDF casse la segmentation, donc la mesure centrale — *mis en œuvre le 18/09, avec un message de refus par format* |
| **D-3** | `check()` reçoit un objet `Document` maison | Fige l'interface des règles avant d'en écrire |
| **D-4** | Normaliser une fois à l'entrée ; le texte normalisé fait référence | La normalisation change la longueur de la chaîne |
| **D-5** | Toute règle renvoie un empan de caractères | Une seule forme à traiter côté affichage |
| **D-6** | Deux types distincts : `Finding` et `FindingRecord` | Éviter la confusion transport / persistance |
| **D-7** | spaCy isolé derrière `services/ingestion/linguistics.py` | Un seul fichier à toucher si le modèle change |
| **D-8** | Le motif de registre, appliqué deux fois | Extracteurs et règles s'étendent sans modification |
| **D-9** | Un module tant qu'il n'y a pas trois fichiers de même nature | L'arborescence reflète ce qui grossit vraiment |
| **D-10** | Pas de score global sur 100 | Toute pondération serait arbitraire et indéfendable |
| **D-11** | Seuils définis par langue | Une phrase française fait 15 à 20 % de mots de plus |
| **D-12** | Listes de mots amorcées par script ponctuel, résultat versionné | La démonstration ne dépend d'aucun réseau — *mis en œuvre le 21/09 : `data/seeds/lexiques.json` chargé en base par `flask seed`* |
| **D-13** | Développement en venv local ; conteneurisation en bonus facultatif | Non attendue dans l'évaluation ; l'infrastructure n'est pas le sujet |
| **D-14** | Détection du passif = dépendances syntaxiques **+ heuristiques** | Les dépendances seules obtiennent 2 sur 6 (mesuré) |
| **D-15** | Ponctuation conservée ; forme brute et forme normalisée stockées | Le texte reste reconstructible, la casse bascule sans retraitement |
| **D-16** | Une analyse s'enregistre à la demande, sous un nom : texte normalisé et empans, jamais le HTML | Une seule vérité, relue à l'identique parce que `normalize()` est idempotente — *mis en œuvre le 23/09* |

---

## 3. Périmètre

### Retenu
- Analyse d'un texte à la fois **(D-1)**.
- Français d'abord, anglais ensuite ; ajout d'autres langues facilité par la conception.
- Seuils définis par langue **(D-11)**.
- Listes de mots amorcées depuis des sources publiées, puis complétées par l'utilisateur. *(Fait le 21/09 : amorce `flask seed`, écran `/listes/`.)*

### Écarté

| Écarté | Pourquoi |
|---|---|
| Métriques de lisibilité (Flesch et équivalents) | Formules opaques, mal adaptées au français, et redondantes avec les règles |
| Filtrage par métadonnées de document | Hors sujet |
| Réécriture automatique par un modèle de langue | Déplacerait tout le travail intéressant hors du code présenté |
| Score global sur 100 **(D-10)** | Appellerait une question à laquelle il n'existe pas de bonne réponse |
| Empaquetage en exécutable de bureau | Embarquer Python, Flask, spaCy et un modèle produit un artefact fragile de plusieurs centaines de Mo |

---

## 4. Entrée du texte

| Élément | Décision |
|---|---|
| Saisie directe | Zone de texte avec longueur maximale, contrôlée côté client **et** serveur |
| Formats acceptés | `.txt`, `.docx`, `.odt`, plus `.md` si c'est trivial |
| Formats refusés | `.doc`, `.pdf` |
| OCR | Non |

**Sur le refus du `.pdf` (D-2).** L'extraction ne restitue pas les paragraphes et introduit des retours à la ligne parasites. La segmentation en phrases serait corrompue, donc la mesure de longueur de phrase — le cœur de l'outil — serait fausse. Refus assumé et argumenté, pas un renoncement technique.

**Sur le refus du `.doc`.** Format binaire OLE, sans bibliothèque Python fiable. Le supporter imposerait d'appeler LibreOffice en sous-processus, soit 500 Mo de dépendance. Message d'erreur explicite invitant à enregistrer en `.docx`.

### Chaîne de traitement

```
obtenir le texte  →  normaliser  →  segmenter  →  tokeniser  →  analyser
```

La normalisation s'applique **aux deux chemins d'entrée**. Un copier-coller depuis un traitement de texte apporte apostrophes courbes, espaces insécables et traits d'union conditionnels au même titre qu'un fichier importé.

### D-4 — La décision la plus coûteuse si elle est prise trop tard

La normalisation **change la longueur de la chaîne**. Mesuré sur ce projet :

| Opération | Longueur avant → après |
|---|---|
| NFC sur `e` + accent combinant | 6 → 5 |
| Suppression du trait d'union conditionnel (U+00AD) | 8 → 7 |
| Apostrophe courbe U+2019 → U+0027 | 7 → 7 |

Or les `Finding` portent des empans de caractères **(D-5)**.

**Donc : normaliser une seule fois à l'entrée, stocker le texte normalisé comme texte de référence, calculer tous les empans dessus, et afficher ce même texte.** Conserver l'original pour l'affichage tout en calculant les positions sur le texte normalisé décale les surlignages d'un caractère par accent décomposé — et la cause se cherche pendant des heures.

### Autres points de vigilance à l'import
- Détection d'encodage (`charset-normalizer`), suppression du BOM.
- Conservation des sauts de paragraphe : la segmentation ne doit pas franchir une frontière de paragraphe.
- Vérification des octets d'en-tête plutôt que de l'extension.
- `defusedxml` pour parser `.docx` et `.odt`, qui sont des archives ZIP contenant du XML non fiable.

**Mise en œuvre, 18 septembre.** Les deux premiers points sont tenus : `txt.py` essaie l'UTF-8 d'abord puis restreint `charset-normalizer` à sept encodages européens, et refuse plutôt que de rendre du mojibake ; `.docx` et `.odt` joignent leurs blocs par une ligne vide, que `segment()` lit comme une frontière de paragraphe.

Les deux derniers ne le sont pas, et c'est un écart assumé à énoncer. Le choix de l'extracteur se fait sur l'**extension**, pas sur les octets d'en-tête : un fichier mal nommé est refusé par la bibliothèque, avec un message d'erreur exact mais pour la mauvaise raison. Quant à `defusedxml`, il travaille — mais pas depuis le code du projet : c'est odfpy qui l'appelle, `odf/opendocument.py` faisant `from defusedxml.sax import make_parser`. Le `.odt` est donc bien lu par un parseur durci ; le `.docx` passe par lxml. **Tranché le 21 septembre : la ligne de `requirements.txt` est gardée**, bien qu'odfpy tire déjà la dépendance. Une dépendance redondante mais explicite coûte une ligne ; la retirer rendrait invisible le fait que le XML est lu par un parseur durci, et ferait disparaître la protection sans bruit le jour où odfpy changerait de parseur.

---

## 5. Architecture

> **Schéma visuel :** les sept tables, l'objet `Finding` face à `FindingRecord`, et le rôle de chaque couche sont représentés dans un diagramme interactif — [Sept tables, quatre couches](https://claude.ai/code/artifact/08207f6e-0b09-471f-baea-8ea024e7483d). Il signale aussi trois points que ce document laisse ouverts (collision de noms sur `Document`, place des tokens, chemin d'une règle vers sa liste).

### D-8 — Le registre, appliqué deux fois

Une interface commune, plusieurs implémentations, un dictionnaire qui associe une clé à l'implémentation. Ajouter un cas se réduit à une classe et une ligne.

- **Extracteurs** (`services/extraction/`) : recevoir un fichier, renvoyer du texte avec ses paragraphes.
- **Règles** (`services/rules/`) : chaque règle expose `check(document) -> list[Finding]`, avec un identifiant, un principe de rattachement, une sévérité et un message.

Savoir dire en soutenance que c'est **la même idée employée à deux endroits** vaut mieux que de décrire les deux séparément.

**Mise en œuvre, 18 septembre : les deux registres existent, et la différence entre eux se défend.** Une règle est une classe — elle porte quatre attributs d'identité et une méthode. Un extracteur est une simple fonction `Callable[[BinaryIO], str]`, parce qu'il n'a rien à porter : pas d'identifiant, pas de sévérité, pas de principe. Le registre des règles est une liste parcourue en entier à chaque analyse ; celui des extracteurs est un dictionnaire indexé par extension, puisqu'on en cherche exactement un. Même idée, deux formes que le besoin dicte.

**Révisé le 22 septembre.** Les deux registres étaient d'abord remplis par un décorateur `@enregistrer` posé sur chaque classe ou fonction. Ils sont devenus des tables littérales, `REGLES` dans `rules/runner.py` et `REGISTRE` dans `extraction/registry.py` : le jeu de règles et de formats est petit et arrêté, la table se lit d'un coup d'œil, et l'import à effet de bord que le décorateur imposait a disparu. Ajouter un cas reste une classe (ou une fonction) et une ligne.

### D-3 — Ce que reçoit `check()`

**Un objet `Document` maison**, portant le texte normalisé, ses paragraphes, ses phrases et ses tokens.

Ce point était laissé ouvert et devait être tranché au moment d'intégrer spaCy. Il est tranché maintenant, avant l'écriture de la première règle, pour une raison simple : dans l'autre ordre, les règles déjà écrites auraient dû être reprises.

Le plan initial prévoyait d'ajouter à ce même objet un attribut `.spacy_doc` optionnel. **Mise en œuvre, 15 septembre :** chaque `Sentence` porte plutôt un champ `analyse`, une liste de `TokenLinguistique` (dataclass maison projetée par `linguistics.py`). Les règles existantes n'ont pas changé, et aucune règle ne manipule d'objet spaCy : c'est ce qui rend l'isolement décrit en **D-7** effectif. Le champ `spacy_doc` subsiste mais reste inutilisé.

### D-5 et D-6 — L'objet `Finding`

```python
@dataclass(frozen=True)
class Finding:
    rule_id: str          # "longueur_phrase"
    hint: str             # principe concerné
    severity: str         # info / avertissement
    char_start: int
    char_end: int
    message: str
    suggestion: str | None
```

**Toutes les règles renvoient un empan de caractères**, quelle que soit leur granularité. La couche d'affichage n'a donc qu'une seule forme à traiter et ne change plus quand on ajoute une règle.

*Cas des règles proportionnelles :* la densité de nominalisations produit **un signalement par token concerné** (pour le surlignage), le pourcentage étant reporté séparément dans le bandeau de synthèse. Sans cela, un signalement se retrouverait sans empan et l'uniformité serait rompue.

**D-6 — deux types, deux noms.** `Finding` est la dataclass de transport entre les couches. `FindingRecord` est l'entité persistée en base. Leur donner le même nom garantit une confusion en soutenance, et une hésitation qui se voit.

### D-7 — Séparation des couches

- `repositories.py` — accès aux données, aucune linguistique.
- `services/` — normalisation, segmentation, tokenisation, règles ; fonctions pures, testables sans base.
- `services/ingestion/linguistics.py` — **unique point de contact avec spaCy.** Aucune règle ne l'importe directement.
- `routes/` — minces.

Argument de soutenance : le moteur de règles ne connaît pas la base de données, donc sa suite de tests s'exécute en isolation — et peut tourner en direct devant le jury.

**Révisé le 21 septembre.** Les listes de mots sont passées en base, et `lexiques.py` les lit directement via le repository : c'était le choix le plus court, fait en connaissance de cause. Le moteur dépend donc de la base, et l'argument ci-dessus ne tient plus tel quel. Ce qui reste vrai : aucune règle n'écrit de SQL ni n'importe `models`, les deux fonctions de `lexiques.py` ont gardé leur signature, et les tests du moteur tournent toujours en direct devant le jury — dans une application de test dont la base, en mémoire, est amorcée par la même fonction que `flask seed`. La frontière a bougé : elle passe entre les règles et le SQL, plus entre le moteur et la base.

### D-9 — Modules ou dossiers

Un dossier se justifie quand il contiendra **au moins trois fichiers de même nature**. En dessous, un module suffit.

D'où `repositories.py` en module unique, et `rules/fr.py` contenant les huit ou dix règles françaises plutôt que dix fichiers de quarante lignes. `extraction/` est un dossier parce que c'est là que le motif de registre se lit le mieux : un fichier par format. `models/` est devenu un dossier en application de la même règle : trois entités, trois fichiers — puis un quatrième, `lexique.py`, qui réunit `WordList` et `WordEntry` parce qu'elles ne vont pas l'une sans l'autre.

L'arborescence exacte est dans [setup-projet-vscode.md](setup-projet-vscode.md).

---

## 6. Tokenisation

Tokenisation **à l'import**, avec position enregistrée. Champs par token : forme de surface, forme normalisée, indicateur de ponctuation, empans de caractères.

**D-15 — deux décisions à savoir défendre :**

1. *La ponctuation est conservée*, marquée par un indicateur plutôt que supprimée. Le texte reste reconstructible, et les décomptes filtrent quand ils en ont besoin. Supprimer serait une perte irréversible.
2. *Forme brute et forme normalisée stockées toutes les deux*, ce qui permet une bascule sensible / insensible à la casse sans repasser sur le texte.

**Cas français à traiter explicitement :**
- Élisions (`l'`, `d'`, `qu'`, `n'`, `jusqu'`) : à séparer, sinon chaque déterminant fusionne avec son nom.
- Traits d'union : à séparer pour les clitiques (`est-ce`, `dit-il`, `celui-ci`), à conserver pour les composés (`week-end`, `arc-en-ciel`). **Il n'existe pas de règle formelle** — une liste d'exceptions est inévitable. Bon exemple à présenter : une tâche qui semble mécanique et ne l'est pas.
- Abréviations et nombres (`M.`, `etc.`, `3,14`, `1er`).

Prévoir un **numéro de version du tokeniseur** par document et une commande de retokenisation : le tokeniseur *sera* modifié en cours de route.

*État au 21 septembre :* seule la tokenisation grossière existe (`\S+`, ponctuation collée au mot). D-15 et les cas ci-dessus relèvent de la tokenisation fine, pas encore commencée. La colonne `version_tokeniseur` existe déjà dans `DocumentRecord`.

> **Ordonnancement :** une tokenisation grossière suffit en phase 1 ; la version fine arrive en phase 2. Voir [plan-de-travail.md](plan-de-travail.md).

---

## 7. Les règles

*État au 21 septembre : trois règles livrées — `longueur_phrase`, `connecteurs_lourds` et `passif`. Le jargon et les nominalisations restent à écrire.*

### Les quatre premières — quatre principes différents

| Règle | Principe | Méthode |
|---|---|---|
| Longueur de phrase | P4 — faire court et simple | seuil |
| Connecteurs lourds (« dans le cadre de », « au niveau de ») | P5 — donner du sens | liste + remplacement |
| Jargon institutionnel | P9 — jargon et abréviations | liste + remplacement |
| Densité de nominalisations | P6 — alléger les noms | suffixes |

Trois sont de simples consultations de liste ; la quatrième suffit à éprouver le moteur. Sur un texte institutionnel réel, elles produisent immédiatement des signalements — une démonstration où l'analyseur ne trouve rien serait un échec.

**Piège connu :** le suffixe `-ment` est nominalisant dans *fonctionnement* et adverbial dans *rapidement*. Un simple filtre par suffixe génère un bruit considérable. Bon exemple à présenter.

### D-14 — La règle signature : détection du passif

Détection de `être` + participe passé, puis **passif sans agent exprimé**, signalé plus sévèrement puisque le lecteur ne peut alors pas identifier qui agit.

En français, l'ambiguïté est réelle : *elle est allée* n'est pas un passif, *la porte est ouverte* peut décrire un état. La résolution passe par l'analyse en dépendances de spaCy (`aux:pass`, `nsubj:pass`), **complétée par des heuristiques**.

> **Mesure effectuée le 7 septembre**, avec `fr_core_news_sm` 3.8.0, critère `aux:pass`/`nsubj:pass` seul, sur les six phrases de référence : **2 sur 6**.
>
> Trois enseignements. Le modèle s'appuie fortement sur le complément d'agent — retirer « par le conseil » fait passer `été` de `aux:pass` à `cop` et le passif disparaît. *Elle est allée* est un faux positif corrigeable proprement, le lemme valant `aller` : une liste des verbes intransitifs conjugués avec *être* élimine toute la famille. *La porte est ouverte* reste honnêtement ambigu — c'est une limite à énoncer, pas un bug à corriger.

**Mise en œuvre, 15 septembre :** la règle accepte aussi l'étiquette `cop` pour couvrir le passif sans agent ; elle écarte les attributs dont le gouverneur n'est pas un `VERB` (« est susceptible ») et les lemmes de la liste `verbes_conjugues_avec_etre(langue)`. Résultat : 4 sur 6 sur les phrases de référence. La comparaison de `fr_core_news_sm` et `fr_core_news_md` sur sept phrases n'a montré aucun gain du modèle moyen : `sm` reste le modèle du projet.
>
> **Conséquence : les heuristiques portent la moitié du résultat.** Elles ne sont pas un ajustement final. Le détail des six cas est dans [theorie.md](theorie.md) §6.

Montrer trois phrases où une expression régulière échoue et où l'analyse grammaticale réussit reste le meilleur moment possible de la soutenance — mais il faut désormais l'annoncer avec un taux d'erreur mesuré plutôt qu'avec une confiance non vérifiée. **Un chiffre donné franchement inspire plus confiance qu'une réussite affirmée.**

S'ajoutent, par ordre de valeur : constructions à verbe support (*procéder à l'examen de* → *examiner*), tournures impersonnelles (*il convient de*), sigles employés sans avoir été développés.

*La règle des sigles suit un état à travers le document, contrairement à toutes les autres. Bon contraste à exposer.*

### D-11 et D-12 — Extensibilité et listes de mots

*Données quand c'est possible, code quand c'est nécessaire.*

Les règles fondées sur des listes se portent vers une nouvelle langue par ajout d'un fichier de données, sans toucher au code. Les règles nécessitant une analyse grammaticale déclarent les langues qu'elles savent traiter et ne s'exécutent pas ailleurs.

Les listes sont récupérées par un **script ponctuel produisant un fichier d'amorce versionné**, jamais par une requête à l'exécution : la démonstration ne doit pas dépendre de la disponibilité d'un site. Les ajouts de l'utilisateur se superposent à cette amorce.

---

## 8. Interface

Cinq écrans, dont les deux premiers seuls sont indispensables :

1. **Analyser** — zone de texte avec compteur, bouton d'import, choix de la langue et du jeu de règles.
2. **Résultats** — texte surligné à gauche, liste des signalements à droite, bandeau de synthèse en haut.
3. **Règles** — activation et seuils par langue. C'est le CRUD du projet, et il sert la démonstration : désactiver une règle, relancer, voir les signalements disparaître.
4. **Listes de mots** — terme à éviter, formulation simple, catégorie.
5. **Historique** — analyses précédentes, pour comparer une version révisée à la précédente.

*État au 23 septembre, jour du gel :* les écrans 1, 2 et 4 existent, sans choix de langue ni de jeu de règles sur le premier. L'écran 5 existe en partie — *Analyses enregistrées* : on nomme une analyse, on la retrouve et on la relit à l'identique (D-16), sans comparaison entre versions. L'écran 3 n'est pas fait ; `run()` accepte déjà un ensemble de règles désactivées pour s'y brancher.

### Choix d'affichage

- **Liaison entre les deux panneaux** : cliquer un surlignage sélectionne le signalement correspondant, et réciproquement. Une trentaine de lignes de JavaScript, pour un effet considérable sur la perception de finition.
- **Distinction par forme** : bande de fond pour les signalements de phrase, souligné pour ceux de token. Les deux se superposent sans conflit.
- **Pas de score global (D-10).**

### Points techniques

- Échapper le HTML **avant** d'insérer les balises de surlignage, jamais l'inverse — sinon faille XSS et page cassée.
- L'échappement change la longueur du texte (`<` devient `&lt;`) : construire la sortie **par segments successifs entre les frontières de signalements**, en échappant chaque segment.
- Les suggestions se limitent à un bouton de copie. Appliquer une correction invaliderait tous les empans affichés et supposerait de relancer l'analyse.

---

## 9. Diffusion

**Le livrable réel est le dépôt Git** — code, `requirements.txt`, README, données d'amorce. La démonstration se fait en local, sans dépendance réseau.

**D-13 — développement en environnement virtuel local, conteneurisation en bonus facultatif.** Le formateur l'a confirmé : elle n'est pas attendue dans l'évaluation, elle ne peut que s'ajouter au dossier. L'application ne change pas d'un environnement à l'autre : une application Flask qui lit sa configuration dans des variables d'environnement s'exécute à l'identique dans un venv ou dans un conteneur. Conteneuriser en fin de parcours ne demande alors qu'un `Dockerfile` et une vérification.

Une mise en ligne reste un bonus. Attention alors à la mémoire (le chargement du modèle spaCy occupe quelques centaines de Mo, à faire une seule fois au démarrage) et au disque éphémère, qui efface un fichier SQLite à chaque redémarrage.

---

## 10. Points encore ouverts

| Point | Statut |
|---|---|
| Ce que reçoit `check()` | **Tranché** — objet `Document` maison **(D-3)** |
| Développer dans Docker ou en venv | **Tranché** — venv, conteneurisation en bonus de phase 3 **(D-13)** |
| Le texte reste-t-il modifiable sur l'écran de résultats ? | **Tranché — non.** Lecture seule. La version modifiable complique nettement le surlignage pour un gain de démonstration marginal. |
| La conteneurisation est-elle attendue dans l'évaluation ? | **Tranché — non.** Elle compte comme bonus ; le plan est inchangé. |
| Licence du dépôt | **Tranché — MIT.** Fichier `LICENSE` écrit, README à jour. |
| Mention de l'origine des listes de mots | **Ouvert** — à rédiger avec le script d'amorce |
