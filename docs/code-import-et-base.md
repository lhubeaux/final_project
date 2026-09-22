# Le code de l'import et du lien à la base

*Rédigé le 21 septembre 2026. Couvre le travail du vendredi 18 (import de fichiers) et du lundi 21 (parcours d'erreur, listes de mots en base, écran des listes).*

Ce document explique le code **ligne par ligne**, dans l'ordre où une requête le traverse. Il complète trois autres documents sans les répéter :

- `guide-des-modules-python.md` dit *ce que fait* chaque module ;
- `documentation.md` dit *pourquoi* le projet est construit ainsi ;
- l'artefact « Import et listes en base » en donne une vue d'ensemble lisible en trente minutes.

Ici, on ouvre les fichiers. Chaque section cite le code tel qu'il est dans le dépôt, puis l'explique : ce qu'il fait, pourquoi il le fait ainsi, et quelle notion de Python, de Flask ou de SQLAlchemy il met en jeu. Ces notions sont récapitulées en fin de document, avec la section où chacune apparaît.

---

## Sommaire

**Partie 1 — L'import de fichiers**
1. [Le contrat : `extraction/base.py`](#1-le-contrat--extractionbasepy)
2. [Le registre : `extraction/registry.py`](#2-le-registre--extractionregistrypy)
3. [Le `.txt` : deviner un encodage](#3-le-txt--deviner-un-encodage)
4. [Le `.md` : six expressions régulières](#4-le-md--six-expressions-régulières)
5. [Le `.docx`](#5-le-docx)
6. [Le `.odt` : un parcours d'arbre](#6-le-odt--un-parcours-darbre)
7. [La route : `routes/analyze.py`](#7-la-route--routesanalyzepy)
8. [La configuration : `config.py`](#8-la-configuration--configpy)
9. [Le formulaire](#9-le-formulaire)
10. [Les tests du parcours d'erreur](#10-les-tests-du-parcours-derreur)

**Partie 2 — Le lien à la base**

11. [Les modèles : `models/lexique.py`](#11-les-modèles--modelslexiquepy)
12. [La migration](#12-la-migration)
13. [L'amorce : `data/seeds/lexiques.json` et `cli.py`](#13-lamorce--dataseedslexiquesjson-et-clipy)
14. [Le repository : `repositories.py`](#14-le-repository--repositoriespy)
15. [La lecture par les règles : `lexiques.py` et `fr.py`](#15-la-lecture-par-les-règles--lexiquespy-et-frpy)
16. [D'où vient le contexte d'application](#16-doù-vient-le-contexte-dapplication)
17. [La fixture de test : `conftest.py`](#17-la-fixture-de-test--conftestpy)
18. [L'écran : `routes/admin.py`](#18-lécran--routesadminpy)
19. [Les gabarits : `base.html` et `admin/listes.html`](#19-les-gabarits--basehtml-et-adminlisteshtml)
20. [Les tests de l'écran](#20-les-tests-de-lécran)

**Partie 3 — Le fichier de test**

21. [`exemples/paragraphes-de-test.txt`](#21-exemplesparagraphes-de-testtxt)

[Récapitulatif des notions](#récapitulatif-des-notions)

---

# Partie 1 — L'import de fichiers

Le principe tient en une phrase : **un extracteur transforme des octets en texte brut, et rien de plus**. La normalisation reste le travail de `build_document(texte_brut, langue="fr")`, qui la fait une seule fois pour les deux chemins d'entrée — la zone de texte et le fichier.

```
zone de texte ──────────────────────────────┐
                                             ├─► texte brut ─► build_document(texte_brut, langue="fr")
fichier ──► extraire(nom, flux) ─► texte brut┘
```

## 1. Le contrat : `extraction/base.py`

Ce module ne contient que ce qu'un extracteur doit connaître : son type, et les erreurs qu'il peut lever. Il n'importe rien du projet, et c'est voulu — voir la fin de la section 2.

### Les exceptions

```python
class ExtractionError(Exception):
    """Erreur d'import dont le message est montrable à l'utilisateur."""


class FormatNonSupporte(ExtractionError):
    """L'extension n'a pas d'extracteur dans le registre."""


class FichierIllisible(ExtractionError):
    """Le fichier a la bonne extension mais ne s'ouvre pas."""
```

Trois classes, une hiérarchie. `ExtractionError` hérite de `Exception`, et les deux autres héritent d'`ExtractionError`.

**Pourquoi une classe mère ?** Pour que la route n'ait qu'un seul type à attraper. `except ExtractionError` attrape aussi ses deux filles : c'est le polymorphisme appliqué aux exceptions. Si demain on ajoute une `FichierTropAncien(ExtractionError)`, la route n'a pas à changer.

**Pourquoi des classes vides ?** Le corps d'une classe peut se réduire à sa docstring. Ces classes n'ajoutent aucun comportement : elles servent à *nommer* une situation, et à la distinguer dans un `except` ou un test.

Le contrat implicite, écrit dans la docstring : le message d'une `ExtractionError` est **destiné à l'utilisateur**. Quiconque lève une de ces erreurs écrit donc un message en français, compréhensible, qui dit quoi faire.

### Le type d'un extracteur

```python
Extracteur = Callable[[BinaryIO], str]
```

Un **alias de type**. `Callable[[BinaryIO], str]` se lit : « une fonction qui prend un flux binaire et renvoie une chaîne ». Python ne vérifie rien à l'exécution ; l'alias sert au lecteur et à l'éditeur (Pylance signale une fonction qui ne respecte pas la forme).

`BinaryIO` désigne tout objet qui se lit comme un fichier ouvert en mode binaire : un vrai fichier, un `io.BytesIO` en test, ou le flux d'un fichier téléversé dans Flask.

Un extracteur est donc une **fonction**, pas une classe. Contrairement à une règle, il n'a ni identifiant, ni sévérité, ni état à porter : il n'y a rien à mettre dans un objet.

## 2. Le registre : `extraction/registry.py`

### La table et les refus

```python
REGISTRE: dict[str, Extracteur] = {
    ".txt": extraire_txt,
    ".md": extraire_md,
    ".docx": extraire_docx,
    ".odt": extraire_odt,
}

_REFUS = {
    ".pdf": "Le PDF n'est pas accepté : le texte y est disposé, pas structuré.",
    ".doc": "Le format .doc n'est pas accepté. Enregistrez le fichier en .docx.",
}
```

`REGISTRE` associe une extension (`".txt"`) à la fonction qui sait la lire. La table est écrite en clair, d'un seul tenant.

**Pourquoi pas un décorateur ?** Une version antérieure enregistrait chaque extracteur avec un `@enregistrer(".txt")` posé sur sa fonction, et le registre commençait vide. Le mécanisme est élégant, et il reste courant dans les bibliothèques, mais il coûte deux choses ici :

- **Il faut importer un module pour qu'il existe.** Un extracteur jamais importé ne s'enregistre pas, sans erreur ni message : la liste des formats rétrécit en silence. Il fallait donc une ligne d'import à effet de bord, que n'importe quel outil de nettoyage aurait supprimée comme inutile.
- **Rien ne se lit d'un seul endroit.** Pour savoir ce que le programme accepte, il fallait ouvrir les quatre modules et y chercher un décorateur.

Le jeu de formats est **arrêté par décision de conception** (D-2) : `.txt`, `.md`, `.docx`, `.odt`, et deux refus explicites. Il n'y a donc pas d'extension à découvrir à l'exécution, et le dictionnaire littéral dit tout ce que le décorateur faisait, en se lisant d'un coup d'œil. Le registre des règles (`REGLES` dans `rules/runner.py`) suit exactement le même raisonnement.

`_REFUS` traite à part les deux formats refusés (D-2). Ils ne sont pas simplement absents du registre : ils ont un message qui donne la raison, ce qui vaut mieux qu'un « format inconnu ». Le **tiret bas initial** est une convention Python : « privé au module ». Rien ne l'interdit techniquement ; c'est un signal au lecteur.

### `extensions_supportees()`

```python
def extensions_supportees() -> tuple[str, ...]:
    return tuple(sorted(REGISTRE))
```

`sorted()` appliqué à un dictionnaire trie ses **clés**. Le résultat est converti en tuple, immuable : un appelant ne peut pas modifier la liste des formats par accident. `tuple[str, ...]` signifie « un tuple de chaînes, de longueur quelconque ». Aujourd'hui : `('.docx', '.md', '.odt', '.txt')`.

Le gabarit s'en sert pour l'attribut `accept` du formulaire et pour la ligne des formats acceptés : ajouter un extracteur met l'interface à jour sans y toucher.

### `extraire()`

```python
def extraire(nom_fichier: str, flux: BinaryIO) -> str:
    extension = Path(nom_fichier).suffix.lower()

    if extension in _REFUS:
        raise FormatNonSupporte(_REFUS[extension])

    extracteur = REGISTRE.get(extension)
    if extracteur is None:
        raise FormatNonSupporte(
            f"Format « {extension or 'sans extension'} » non pris en charge. "
            f"Formats acceptés : {', '.join(extensions_supportees())}."
        )

    return extracteur(flux)
```

Appelée depuis la route sous la forme `extraire(fichier.filename, fichier.stream)`.

- `Path(nom_fichier).suffix` extrait l'extension avec son point : `"note.TXT"` donne `".TXT"`, puis `.lower()` donne `".txt"`. Un nom sans point donne `""`. C'est cette mise en minuscules qui fait que `.TXT` et `.txt` désignent le même format — dans la version à décorateur, le même `.lower()` était appliqué à la clé au moment de l'enregistrement.
- L'ordre des tests compte : les refus documentés passent **avant** la recherche dans le registre, pour que `.pdf` reçoive son message dédié.
- `REGISTRE.get(extension)` renvoie `None` si la clé est absente, là où `REGISTRE[extension]` lèverait une `KeyError`.
- `extension or 'sans extension'` : si l'extension est la chaîne vide (fausse en Python), l'expression vaut `'sans extension'`.
- Les deux f-strings côte à côte sont concaténées par Python avant l'exécution : c'est une seule chaîne écrite sur deux lignes.
- Dernière ligne : `extracteur` est une variable qui contient une fonction ; `extracteur(flux)` l'appelle.

Le nom du fichier vient du navigateur, donc de l'utilisateur. Il sert **uniquement** à choisir l'extracteur ; il n'est jamais utilisé pour écrire sur le disque, ce qui écarte les attaques par nom de fichier (`../../app/config.py`).

### La façade : `extraction/__init__.py`

```python
from app.services.extraction.base import (
    Extracteur,
    ExtractionError,
    FichierIllisible,
    FormatNonSupporte,
)
from app.services.extraction.registry import (
    REGISTRE,
    extensions_supportees,
    extraire,
)

__all__ = [ ... ]
```

Ce fichier ne fait plus qu'une chose : **réexporter l'interface publique**. La route écrit `from app.services.extraction import extraire` au lieu d'aller chercher dans `registry`. Le paquet présente une façade ; son organisation interne peut changer sans toucher aux appelants. `__all__` liste ce qui est public.

Dans la version à décorateur, ce fichier portait en plus la ligne `from app.services.extraction import docx, md, odt, txt`, suivie d'un `# noqa: F401` : un import dont on ne voulait que l'effet de bord. Elle n'a plus de raison d'être.

### Pourquoi `base.py` existe

C'est la seule contrainte technique du montage, et elle mérite d'être comprise.

`registry.py` importe les quatre extracteurs, pour construire sa table. Les extracteurs, eux, ont besoin de `FichierIllisible` pour signaler un fichier corrompu. Si cette exception vivait dans `registry.py`, on aurait :

```text
registry.py ──importe──► docx.py ──importe──► registry.py
```

Un **cycle d'import** : Python commencerait à exécuter `registry.py`, sauterait dans `docx.py`, qui redemanderait `registry.py` alors qu'il n'a pas fini de s'exécuter. Selon l'ordre des lignes, cela marche par accident ou casse avec une `ImportError` difficile à lire.

Sortir le contrat dans un module qui n'importe rien supprime le cycle. Les dépendances vont toutes dans le même sens :

```text
base.py ◄────── docx.py, md.py, odt.py, txt.py ◄────── registry.py
   ▲                                                       │
   └───────────────────────────────────────────────────────┘
```

C'est le même découpage que pour les règles : `rules/base.py` porte le contrat (`Finding`, `Rule`), `rules/runner.py` porte la table et l'exécution.

## 3. Le `.txt` : deviner un encodage

```python
_CANDIDATS = [
    "utf_8",
    "utf_16",
    "cp1252",       # Windows, Europe occidentale
    "iso8859_15",   # latin-9, avec le signe €
    "cp1250",       # Europe centrale
    "cp1251",       # cyrillique
    "cp1253",       # grec
]


def decoder(donnees: bytes) -> str:
    if not donnees:
        return ""

    try:
        return donnees.decode("utf_8_sig")      # retire le BOM s'il y en a un
    except UnicodeDecodeError:
        pass

    meilleure = from_bytes(donnees, cp_isolation=_CANDIDATS).best()
    if meilleure is None:
        raise FichierIllisible("Encodage du fichier non reconnu.")

    return str(meilleure)


def extraire_txt(flux: BinaryIO) -> str:
    return decoder(flux.read())
```

**Le problème.** Un fichier texte est une suite d'octets. Le même octet `0xE9` vaut « é » en cp1252 et n'est pas un caractère valide en UTF-8. Rien, dans un `.txt`, n'indique l'encodage utilisé : il faut le deviner.

**`bytes` et `str`.** `flux.read()` renvoie des `bytes` (des octets) ; les règles travaillent sur des `str` (des caractères Unicode). `decode()` fait la conversion, à condition de connaître l'encodage.

**Étape 1 — un fichier vide** donne une chaîne vide. `not donnees` est vrai pour `b""`.

**Étape 2 — UTF-8 d'abord.** On l'essaie en premier parce qu'il domine, et surtout parce qu'il est **auto-vérifiant** : sa structure est si contrainte que des octets en cp1252 échouent presque toujours au décodage, au lieu de produire un texte faux. Si `decode()` lève `UnicodeDecodeError`, le `except ...: pass` passe simplement à l'étape suivante.

La variante `utf_8_sig` retire le BOM, trois octets (`EF BB BF`) que le Bloc-notes de Windows ajoute parfois en tête. Sans elle, le texte commencerait par un caractère invisible. `normalize()` le retire aussi, mais autant ne pas le transmettre.

**Étape 3 — `charset-normalizer`.** `from_bytes()` essaie les encodages et note la vraisemblance du résultat ; `.best()` renvoie la meilleure proposition, ou `None`. Le paramètre `cp_isolation` restreint les candidats aux encodages de `_CANDIDATS`. Sans cette restriction, sur un texte court, la bibliothèque peut élire un encodage asiatique et rendre des idéogrammes. `str(meilleure)` donne le texte décodé.

**Étape 4 — refuser.** Si aucun candidat ne convient, on lève `FichierIllisible`. Rendre un texte mal décodé serait pire qu'une erreur : la segmentation et l'étiquetage porteraient sur des mots qui n'existent pas, et aucune erreur ne le signalerait.

`decoder()` est une fonction séparée, et non le corps d'`extraire_txt`, parce que `md.py` la réutilise.

Le fichier `exemples/notification.txt` est enregistré en cp1252 : il passe par l'étape 3.

## 4. Le `.md` : six expressions régulières

```python
_TITRE = re.compile(r"^#{1,6}[ \t]+", re.MULTILINE)
_CITATION = re.compile(r"^[ \t]*>[ \t]?", re.MULTILINE)
_PUCE = re.compile(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+", re.MULTILINE)
_LIEN = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPHASE = re.compile(r"(\*{1,3}|_{1,3})(\S.*?\S|\S)\1")
_CODE = re.compile(r"`+")


def extraire_md(flux: BinaryIO) -> str:
    texte = decoder(flux.read())

    texte = _TITRE.sub("", texte)
    texte = _CITATION.sub("", texte)
    texte = _PUCE.sub("", texte)
    texte = _LIEN.sub(r"\1", texte)      # garde le libellé, jette l'URL
    texte = _EMPHASE.sub(r"\2", texte)
    texte = _CODE.sub("", texte)

    return texte
```

Markdown n'est pas un format de fichier : c'est du texte avec des conventions. Le décodage est donc celui du `.txt`. Ensuite, on retire les marques, pour qu'un `##` ou un `**` ne soit pas compté comme un mot par la règle de longueur.

`re.compile()` prépare le motif une fois, au chargement du module, au lieu de le recompiler à chaque fichier. Le préfixe `r"..."` (chaîne brute) évite de doubler les antislashs.

| Motif | Reconnaît | Avant → après |
|---|---|---|
| `_TITRE` | 1 à 6 `#` en début de ligne, suivis d'espaces | `## Objet` → `Objet` |
| `_CITATION` | un `>` en début de ligne | `> Rappel` → `Rappel` |
| `_PUCE` | une puce `-`, `*`, `+` ou `1.` en début de ligne | `- Pièce` → `Pièce` |
| `_LIEN` | `[libellé](url)` | `[le formulaire](https://…)` → `le formulaire` |
| `_EMPHASE` | `*…*`, `**…**`, `_…_` | `**délai**` → `délai` |
| `_CODE` | un ou plusieurs accents graves | `` `R. 441-1` `` → `R. 441-1` |

Quelques éléments de syntaxe :

- **`re.MULTILINE`** change le sens de `^` : sans l'option, `^` ne désigne que le début du texte ; avec elle, le début de **chaque ligne**. Indispensable pour les titres et les puces.
- **`(?:…)`** est un groupe *non capturant* : il regroupe sans créer de groupe numéroté.
- **Les groupes et `\1`.** Dans `_LIEN`, `([^\]]*)` capture le libellé dans le groupe 1 ; le remplacement `r"\1"` remet ce libellé seul. Dans `_EMPHASE`, `\1` *à l'intérieur du motif* exige que la marque fermante soit identique à l'ouvrante : `**gras**` est reconnu, `**gras*` non.
- **`.*?`** est un quantificateur *non gourmand* : il s'arrête au plus tôt. Dans `**a** et **b**`, il reconnaît `**a**` puis `**b**`, et non tout le segment d'un bloc.

Le nettoyage est volontairement minimal, et sans dépendance nouvelle. Une limite à connaître : `_EMPHASE` retirerait les tirets bas d'un identifiant comme `mot_clé_test`. C'est rare dans un texte administratif.

## 5. Le `.docx`

```python
from docx import Document as DocumentDocx


def extraire_docx(flux: BinaryIO) -> str:
    try:
        docx = DocumentDocx(flux)
    except Exception as erreur:      # python-docx lève des types variés
        raise FichierIllisible("Fichier .docx illisible ou corrompu.") from erreur

    paragraphes = [paragraphe.text.strip() for paragraphe in docx.paragraphs]

    return "\n\n".join(paragraphe for paragraphe in paragraphes if paragraphe)
```

- **`import … as DocumentDocx`.** python-docx appelle sa classe `Document`, comme notre dataclass métier. Le renommage à l'import évite toute confusion à la lecture.
- **`DocumentDocx(flux)`** accepte un objet-fichier : pas besoin d'enregistrer le téléversement sur le disque.
- **`except Exception` large, exceptionnellement.** D'ordinaire, on attrape un type précis. Ici, un fichier corrompu peut faire lever à python-docx une erreur de ZIP, de XML ou de clé manquante selon la nature du dégât. Toutes signifient la même chose pour l'utilisateur.
- **`raise … from erreur`** chaîne les exceptions : l'erreur d'origine reste attachée (`__cause__`) et apparaît dans la trace en développement, tandis que l'utilisateur ne voit que le message clair.
- **La compréhension de liste** récupère le texte de chaque paragraphe, nettoyé de ses espaces de bord.
- **Le `join` avec une expression génératrice** ne garde que les paragraphes non vides (`if paragraphe` : une chaîne vide est fausse) et les colle avec `"\n\n"`.

**La ligne vide n'est pas cosmétique.** `segment()` délimite un paragraphe par une ligne vide. Joindre par `"\n"` seul ferait de tout le document un unique paragraphe.

Un `.docx` est une archive ZIP de fichiers XML : l'encodage y est déclaré, aucune devinette n'est nécessaire. Limite : `docx.paragraphs` ne contient que le corps du document ; les tableaux, les en-têtes et les notes sont ignorés.

## 6. Le `.odt` : un parcours d'arbre

```python
_BLOCS = {(TEXTNS, "p"), (TEXTNS, "h")}      # paragraphes et titres


def _parcourir(noeud: Element) -> Iterator[str]:
    for enfant in noeud.childNodes:
        if not isinstance(enfant, Element):
            continue
        if enfant.qname in _BLOCS:
            yield teletype.extractText(enfant)
        else:
            yield from _parcourir(enfant)


def extraire_odt(flux: BinaryIO) -> str:
    try:
        odt = load(flux)
    except Exception as erreur:
        raise FichierIllisible("Fichier .odt illisible ou corrompu.") from erreur

    blocs = [bloc.strip() for bloc in _parcourir(odt.text)]

    return "\n\n".join(bloc for bloc in blocs if bloc)
```

Un `.odt` est lui aussi une archive ZIP contenant du XML. odfpy le charge en **arbre** : chaque balise est un nœud, avec ses enfants.

**Les noms qualifiés.** En XML, une balise appartient à un *espace de noms*. Un paragraphe OpenDocument est la balise `p` de l'espace `TEXTNS`. odfpy représente ce nom qualifié par un tuple `(espace, nom)`, d'où `_BLOCS`, un **ensemble** de deux tuples : paragraphes (`p`) et titres (`h`). Un ensemble rend le test `in` immédiat.

**Le parcours récursif.** `_parcourir` descend l'arbre en profondeur :

- `noeud.childNodes` liste les enfants directs ;
- `isinstance(enfant, Element)` écarte les nœuds de texte brut situés entre les balises ;
- un paragraphe ou un titre : on renvoie son texte avec `yield` ;
- toute autre balise (une section, un cadre, un tableau) : on descend à l'intérieur avec `yield from _parcourir(enfant)`.

**`yield` fait de `_parcourir` un générateur** : elle produit ses valeurs une à une, à la demande, au lieu de construire une liste. `yield from` délègue à un sous-générateur, ici l'appel récursif.

**Pourquoi ne pas utiliser `getElementsByType()` ?** Cette méthode d'odfpy renvoie tous les éléments d'un type. Il faudrait l'appeler deux fois, pour les paragraphes puis pour les titres, et l'ordre de lecture serait perdu : les titres se retrouveraient tous à la fin. Le parcours en profondeur visite les nœuds dans l'ordre du document.

`teletype.extractText()` reconstitue le texte d'un nœud, y compris les espaces qu'OpenDocument encode sous forme de balises (`text:s`). `odt.text` est le corps du document.

Côté sécurité, odfpy lit son XML avec `defusedxml`, qui neutralise les attaques par expansion d'entités (« bombe XML »). C'est pourquoi `defusedxml` figure dans `requirements.txt`, bien qu'aucun fichier du projet ne l'importe.

## 7. La route : `routes/analyze.py`

### `page()`

```python
def page(document=None, findings=None, texte_surligne=None, resume=None, erreur=None):
    return render_template(
        "analyze/index.html",
        document=document,
        findings=findings or [],
        texte_surligne=texte_surligne,
        resume=resume or [],
        erreur=erreur,
        extensions=extensions_supportees(),
    )
```

Le rendu unique de la page d'analyse. Tous les paramètres ont une valeur par défaut : on peut appeler `page(erreur="…")` seul.

`findings or []` : un piège classique de Python l'explique. On n'écrit jamais `def page(findings=[])`, parce que la liste par défaut est créée **une seule fois**, à la définition de la fonction, puis partagée entre tous les appels. On met `None` par défaut, et on fabrique une liste neuve dans le corps.

`extensions=extensions_supportees()` est ajouté ici, et non par chaque appelant : impossible d'oublier la liste des formats.

### Le gestionnaire du 413

```python
@bp.app_errorhandler(413)
def envoi_trop_volumineux(_echec):
    plafond = current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return page(erreur=f"Envoi trop volumineux : {plafond} Mo maximum."), 413
```

Quand le corps d'une requête dépasse `MAX_CONTENT_LENGTH`, Flask lève une erreur **pendant sa lecture**, avant d'appeler la route. `index()` n'est jamais exécutée ; aucun `try` ne peut donc attraper l'erreur. Flask cherche alors un **gestionnaire d'erreur** enregistré pour le code 413.

- **`app_errorhandler` et non `errorhandler`.** Sur un blueprint, `errorhandler` ne vaut que pour les erreurs levées dans ses propres routes. Un 413 survient avant tout routage : il n'appartient à aucun blueprint. `app_errorhandler` enregistre le gestionnaire au niveau de l'application entière.
- **`_echec`** reçoit l'exception, que la fonction n'utilise pas. Le tiret bas initial le signale.
- **`current_app`** désigne l'application qui traite la requête. On lit la configuration à travers lui plutôt qu'en important un objet `app` : avec une fabrique `create_app()`, il n'existe pas d'objet `app` global à importer.
- **`// (1024 * 1024)`** : division entière, des octets vers les mégaoctets. 2 097 152 octets donnent `2`.
- **Le tuple `(page, 413)`.** Une vue Flask peut renvoyer `(corps, code)`. Le code 413 est conservé : rien n'a été analysé, répondre 200 mentirait au navigateur.

### `index()`, pas à pas

```python
    if request.method == "POST":
        fichier = request.files.get("fichier")
```

`request.files` contient les fichiers téléversés, indexés par le `name` du champ HTML. `.get()` renvoie `None` si le champ est absent. `fichier` est un objet `FileStorage` de Werkzeug.

```python
        try:
            if fichier and fichier.filename:
                texte_brut = extraire(fichier.filename, fichier.stream)
            else:
                texte_brut = request.form.get("texte", "")
        except ExtractionError as echec:
            erreur = str(echec)
            texte_brut = ""
```

- **`fichier and fichier.filename`.** Quand l'utilisateur ne choisit aucun fichier, le navigateur envoie quand même le champ, avec un nom vide. `filename` vaut alors `""`, qui est faux. Ce double test couvre les deux cas : champ absent, champ vide.
- **Le fichier l'emporte.** Si les deux sont remplis, le dépôt d'un fichier est le geste le plus explicite.
- **`fichier.stream`** est le flux binaire du fichier, que Flask a déjà reçu : c'est lui que l'extracteur lit.
- **Le `try` n'entoure que l'obtention du texte.** Une erreur de l'analyse elle-même ne doit pas être déguisée en erreur d'import.
- **`str(echec)`** donne le message de l'exception, écrit pour l'utilisateur. La route ne le reformule pas.

```python
        maximum = current_app.config["MAX_TEXT_LENGTH"]
        if len(texte_brut) > maximum:
            erreur = (
                f"Texte trop long : {len(texte_brut)} caractères "
                f"pour {maximum} au maximum."
            )
            texte_brut = ""
```

La vérification de longueur, **au niveau du `try`**, pas à l'intérieur du `except` : elle doit s'exécuter dans tous les cas. L'attribut `maxlength` du formulaire n'existe que dans le navigateur ; un envoi direct le contourne. Vider `texte_brut` fait échouer le test suivant, et le message est déjà prêt.

```python
        if texte_brut.strip():
            document = build_document(texte_brut, langue="fr")
            findings = run(document)
            texte_surligne = surligner(document.texte, findings)
            comptes = Counter(finding.rule_id for finding in findings)
            resume = [(regle.hint, comptes[regle.id]) for regle in regles(document.langue)]
        elif erreur is None:
            erreur = "Aucun texte à analyser."
```

- **`.strip()`** retire les blancs de bord : un texte fait d'espaces et de lignes vides est traité comme vide.
- **`Counter`** compte les signalements par règle. `comptes[regle.id]` renvoie `0` pour une règle absente, au lieu de lever une `KeyError` : c'est ce qui permet d'afficher les règles qui n'ont rien trouvé.
- **`elif erreur is None`** : le message « Aucun texte » ne remplace pas une erreur déjà posée (fichier refusé, texte trop long).

La fin de `index()` appelle `render_template(...)` avec les mêmes arguments que `page()`. Les deux sont équivalents ; écrire `return page(document=document, findings=findings, ...)` retirerait la répétition.

## 8. La configuration : `config.py`

```python
    MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", 20000))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_BYTES", 2097152))
    MAX_FORM_MEMORY_SIZE = MAX_CONTENT_LENGTH
```

- **`os.environ.get(nom, défaut)`** lit une variable d'environnement, remplie depuis `.env` par python-dotenv. Les variables d'environnement sont toujours des chaînes, d'où `int(...)`.
- **`MAX_CONTENT_LENGTH`** est une clé que Flask connaît : il l'applique lui-même au corps de chaque requête.
- **`MAX_FORM_MEMORY_SIZE`** est une autre clé de Flask, apparue en 3.1 : elle plafonne *à part* les champs non-fichier, à 500 000 octets par défaut. Sans l'alignement, un texte collé de 800 Ko recevait un 413 alors qu'il était sous les 2 Mo.
- **`MAX_TEXT_LENGTH`** est propre au projet : Flask l'ignore, la route le lit.

Ces attributs sont évalués **une fois**, quand Python lit la classe. `TestConfig(Config)` en hérite.

## 9. Le formulaire

```html
<form method="post" enctype="multipart/form-data">
  <textarea id="texte" name="texte" rows="8" maxlength="20000">…</textarea>
  <p class="depot">
    <label for="fichier">ou déposer un fichier :</label>
    <input id="fichier" type="file" name="fichier" accept="{{ extensions | join(',') }}">
    <span class="formats">{{ extensions | join(' · ') }} — 2 Mo maximum</span>
  </p>
  …
</form>
{% if erreur %}
  <p class="erreur">{{ erreur }}</p>
{% endif %}
```

- **`enctype="multipart/form-data"` est indispensable.** Sans lui, le navigateur envoie le formulaire en `application/x-www-form-urlencoded` : seul le *nom* du fichier part, pas son contenu, et `request.files` reste vide.
- **`accept`** filtre les fichiers proposés par la fenêtre de sélection. C'est un confort, pas une sécurité : le serveur revérifie.
- **Le filtre Jinja `join`** colle les éléments d'une liste. La même liste sert deux fois, sous deux formes : `.docx,.md,.odt,.txt` pour `accept`, `.docx · .md · .odt · .txt` pour le texte affiché.
- **`name`** est la clé côté serveur (`request.files["fichier"]`), **`id`** la cible du `<label for>`.

## 10. Les tests du parcours d'erreur

```python
def poster_fichier(client, nom, contenu: bytes):
    return client.post(
        "/",
        data={"fichier": (io.BytesIO(contenu), nom)},
        content_type="multipart/form-data",
    )
```

Le client de test de Flask simule un navigateur sans lancer de serveur. Pour téléverser un fichier, on passe un tuple `(flux, nom)` : `io.BytesIO(contenu)` fabrique en mémoire un flux binaire à partir d'octets. Aucun fichier n'est écrit sur le disque.

```python
def test_fichier_trop_volumineux(client):
    reponse = poster_fichier(client, "gros.txt", b"a" * 3_000_000)

    assert reponse.status_code == 413
    assert "2 Mo maximum" in reponse.get_data(as_text=True)
```

`b"a" * 3_000_000` fabrique trois millions d'octets. Les tirets bas dans un nombre sont décoratifs : `3_000_000 == 3000000`. `get_data(as_text=True)` renvoie le corps de la réponse décodé en texte.

```python
def test_txt_non_utf8_est_decode(client):
    corps = poster_fichier(
        client, "note.txt", "La décision a été prise par le conseil.".encode("cp1252")
    ).get_data(as_text=True)

    assert "décision" in corps
    assert "Ã©" not in corps
```

`.encode("cp1252")` produit les octets qu'aurait écrits le Bloc-notes d'un Windows ancien. Le test vérifie le texte décodé, et l'absence du mojibake typique.

Un piège, commenté dans le fichier : Jinja **échappe** les messages. L'apostrophe de « n'est pas accepté » arrive dans la page sous la forme `n&#39;est`. Les assertions visent donc des fragments sans apostrophe.

---

# Partie 2 — Le lien à la base

Les deux listes de mots quittent le code pour la base. Le trajet des données :

```
data/seeds/lexiques.json ──flask seed──► repositories.amorcer_liste() ──► base SQLite
                                                                               │
règles (fr.py) ─► lexiques.py ─► repositories.lire_liste() ◄───────────────────┘
écran /listes/ ─► admin.py ─► repositories.ajouter_entree() / supprimer_entree() ─► base
```

## 11. Les modèles : `models/lexique.py`

```python
class WordList(db.Model):
    __tablename__ = "word_lists"
    __table_args__ = (UniqueConstraint("nom", "langue"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str]
    langue: Mapped[str]

    entrees: Mapped[list["WordEntry"]] = relationship(
        back_populates="liste", cascade="all, delete-orphan"
    )


class WordEntry(db.Model):
    __tablename__ = "word_entries"
    __table_args__ = (UniqueConstraint("word_list_id", "expression"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    word_list_id: Mapped[int] = mapped_column(ForeignKey("word_lists.id"))
    expression: Mapped[str]
    remplacement: Mapped[str | None]

    liste: Mapped["WordList"] = relationship(back_populates="entrees")
```

C'est le style **déclaratif** de SQLAlchemy 2.0 : une classe Python décrit une table, chaque attribut annoté une colonne.

**Les annotations décident de la colonne.**

| Annotation | Colonne obtenue |
|---|---|
| `Mapped[int] = mapped_column(primary_key=True)` | clé primaire entière, attribuée par la base |
| `Mapped[str]` | texte, **obligatoire** (`NOT NULL`) |
| `Mapped[str \| None]` | texte, **facultatif** (`NULL` autorisé) |
| `Mapped[int] = mapped_column(ForeignKey("word_lists.id"))` | clé étrangère vers `word_lists.id` |

SQLAlchemy déduit l'obligation de l'annotation : `str` seul donne une colonne obligatoire, `str | None` une colonne facultative. `remplacement` est facultatif parce que les verbes n'ont pas de reformulation.

**`__table_args__`** reçoit les contraintes de table. C'est un tuple, d'où la **virgule finale** : `(UniqueConstraint(...),)`. Sans elle, les parenthèses ne seraient qu'un regroupement.

**Les contraintes d'unicité** portent sur un *couple* de colonnes. (`nom`, `langue`) : une seule liste `connecteurs_lourds` en français, mais une autre possible en anglais. (`word_list_id`, `expression`) : pas deux fois « afin de » dans la même liste. Ce sont elles qui garantiront, côté base, qu'aucun doublon n'entre, même si le code oubliait de vérifier.

**`relationship` relie les objets Python**, là où la clé étrangère relie les lignes :

- `liste.entrees` donne la liste Python des entrées d'une liste ;
- `entree.liste` donne la liste à laquelle appartient une entrée ;
- `back_populates` déclare que ces deux attributs sont les deux faces d'un même lien : modifier l'un met l'autre à jour.

**`cascade="all, delete-orphan"`** :

- `all` : les opérations sur une liste se propagent à ses entrées. Ajouter une liste à la session y ajoute ses entrées, supprimer une liste supprime ses entrées.
- `delete-orphan` : une entrée retirée de `liste.entrees` est supprimée de la base, puisqu'une entrée sans liste n'a pas de sens.

**`"WordEntry"` entre guillemets** : dans `WordList`, la classe `WordEntry` n'est pas encore définie. La chaîne est une *référence différée*, résolue par SQLAlchemy une fois les deux classes connues.

Les deux classes partagent un fichier parce qu'elles ne vont pas l'une sans l'autre. Les autres modèles du projet suivent la règle « une classe, un fichier ».

`app/models/__init__.py` importe ces deux classes. Ce n'est pas qu'une commodité : c'est parce qu'elles sont importées que `flask db migrate` les a vues. Alembic compare les modèles *chargés en mémoire* à la base ; un modèle jamais importé n'existe pas pour lui.

## 12. La migration

```powershell
flask db migrate -m "listes de mots : word_lists, word_entries"
flask db upgrade
```

**`migrate`** compare les modèles à la base et **génère** un script dans `migrations/versions/`. Il n'applique rien. **`upgrade`** exécute les scripts en attente.

```python
revision = '346c000e5787'
down_revision = '7b70f94273c6'

def upgrade():
    op.create_table('word_lists',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nom', sa.String(), nullable=False),
    sa.Column('langue', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nom', 'langue')
    )
    op.create_table('word_entries', …)

def downgrade():
    op.drop_table('word_entries')
    op.drop_table('word_lists')
```

- **`revision` et `down_revision`** chaînent les migrations. Celle-ci suit `7b70f94273c6`, la migration des trois premières tables. La base retient la dernière appliquée dans la table `alembic_version` ; `flask db current` l'affiche.
- **`upgrade()`** crée `word_lists` *avant* `word_entries`, qui la référence par clé étrangère.
- **`downgrade()`** défait dans l'ordre inverse, pour la même raison. `flask db downgrade` l'exécuterait.
- **`nullable=False` / `nullable=True`** retrouve exactement ce que les annotations `Mapped[str]` et `Mapped[str | None]` exprimaient.

Relire le script généré avant l'`upgrade` est une habitude à garder : l'autogénération ne détecte pas tout (un renommage de colonne, par exemple, apparaît comme une suppression suivie d'un ajout).

## 13. L'amorce : `data/seeds/lexiques.json` et `cli.py`

### Le fichier

```json
{
  "connecteurs_lourds": {
    "fr": { "afin de": "pour", "en vue de": "pour", … }
  },
  "verbes_conjugues_avec_etre": {
    "fr": [ "aller", "arriver", … ]
  }
}
```

La structure est `liste → langue → entrées`. Les connecteurs sont un objet (expression → remplacement), les verbes une simple liste.

**Pourquoi un fichier, si les listes sont en base ?** Git ne suit pas la base (`instance/` et `*.db` sont dans `.gitignore`). Le JSON est la source **versionnée** des listes d'origine (D-12) ; la base en est la copie d'exécution, reconstructible à tout moment.

### Le chemin du fichier

```python
AMORCE = Path(__file__).resolve().parent.parent / "data" / "seeds" / "lexiques.json"
```

À lire de gauche à droite :

- `__file__` : le chemin de `cli.py` lui-même ;
- `.resolve()` : le rend absolu ;
- `.parent` : le dossier `app/` ; `.parent` encore : la racine du projet ;
- `/ "data" / "seeds" / …` : l'opérateur `/` de `pathlib` assemble les morceaux de chemin, avec le bon séparateur sur chaque système.

Ce calcul rend le chemin indépendant du dossier depuis lequel on lance `flask seed`.

### `charger_amorce()`

```python
def charger_amorce(chemin: Path = AMORCE) -> dict[str, dict[str, dict[str, str | None]]]:
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    return {
        nom: {
            langue: entrees if isinstance(entrees, dict) else dict.fromkeys(entrees)
            for langue, entrees in par_langue.items()
        }
        for nom, par_langue in brut.items()
    }
```

- **`read_text(encoding="utf-8")`** : l'encodage est donné explicitement. Sans lui, Windows utiliserait cp1252 par défaut, et « préalablement à » serait mal lu.
- **`json.loads`** transforme le texte JSON en dictionnaires et listes Python.
- **Deux compréhensions de dictionnaire imbriquées.** L'extérieure parcourt les listes, l'intérieure les langues de chaque liste. Le résultat a la même forme que le JSON, à une différence près :
- **`dict.fromkeys(entrees)`** transforme une liste en dictionnaire dont toutes les valeurs valent `None` : `["aller", "venir"]` devient `{"aller": None, "venir": None}`. Toutes les listes prennent ainsi la même forme `{expression: remplacement}`, et le reste du code n'a qu'un seul cas à traiter.

### `amorcer_lexiques()` et la commande

```python
def amorcer_lexiques(chemin: Path = AMORCE) -> list[tuple[str, str, int, int]]:
    bilan = []
    for nom, par_langue in charger_amorce(chemin).items():
        for langue, entrees in par_langue.items():
            ajoutees = amorcer_liste(nom, langue, entrees)
            bilan.append((nom, langue, ajoutees, len(entrees)))
    return bilan


@click.command("seed")
def seed():
    """Charge en base les listes de mots de data/seeds/lexiques.json."""
    for nom, langue, ajoutees, total in amorcer_lexiques():
        click.echo(f"{nom} ({langue}) : {ajoutees} ajoutée(s) sur {total}")
```

- **`amorcer_lexiques()` ne fait rien à l'écran** : elle renvoie un bilan. C'est ce qui lui permet d'être appelée par la commande **et** par la fixture de test (section 17), sans affichage parasite.
- **`@click.command("seed")`** fait de `seed` une commande en ligne. Click est la bibliothèque sur laquelle repose la commande `flask` elle-même.
- **Le déballage `for nom, langue, ajoutees, total in …`** répartit chaque tuple du bilan dans quatre variables.
- **La docstring de `seed`** sert d'aide : `flask seed --help` l'affiche.

La commande est rattachée à l'application dans la fabrique :

```python
# app/__init__.py
from app.cli import seed
...
    app.cli.add_command(seed)
```

`app.cli` est le groupe de commandes de l'application. Une commande qui y est ajoutée s'exécute avec un **contexte d'application** actif (Flask 3.1) : `db.session` est utilisable dans `seed`, sans rien d'autre à écrire.

**Le partage du travail** suit les frontières du projet : `cli.py` lit un fichier, `repositories.py` écrit en base. Un repository ne lit pas de fichiers.

## 14. Le repository : `repositories.py`

Tout le SQL du projet est ici. La route et les règles n'importent jamais `db` directement.

### `amorcer_liste()`

```python
def amorcer_liste(nom: str, langue: str, entrees: dict[str, str | None]) -> int:
    liste = db.session.execute(
        db.select(WordList).filter_by(nom=nom, langue=langue)
    ).scalar_one_or_none()
    if liste is None:
        liste = WordList(nom=nom, langue=langue)
        db.session.add(liste)

    presentes = {entree.expression for entree in liste.entrees}
    ajouts = [
        WordEntry(expression=expression, remplacement=remplacement)
        for expression, remplacement in entrees.items()
        if expression not in presentes
    ]
    liste.entrees.extend(ajouts)
    db.session.commit()
    return len(ajouts)
```

**La lecture, en style SQLAlchemy 2.0**, en trois temps :

1. `db.select(WordList).filter_by(nom=nom, langue=langue)` *construit* la requête, sans l'exécuter. Elle correspond à `SELECT * FROM word_lists WHERE nom = ? AND langue = ?`.
2. `db.session.execute(...)` l'exécute.
3. `.scalar_one_or_none()` renvoie l'objet trouvé, `None` s'il n'y en a pas, et lève une erreur s'il y en a plusieurs — ce que la contrainte d'unicité rend impossible.

**La création si besoin.** `WordList(nom=..., langue=...)` crée un objet Python ; `db.session.add()` l'inscrit dans la session. Rien n'est encore écrit en base.

**Le tri des entrées nouvelles.**

- `presentes` est un **ensemble** construit par compréhension : les expressions déjà en base. Un ensemble rend le test `in` immédiat. Pour une liste neuve, `liste.entrees` est vide, sans requête.
- `ajouts` ne garde que les expressions absentes. C'est ce filtre qui rend l'amorce **idempotente** : la relancer n'ajoute rien, n'écrase aucun remplacement modifié, ne supprime rien.

**L'écriture.** `liste.entrees.extend(ajouts)` rattache les nouvelles entrées à la liste. Grâce à la cascade, elles entrent dans la session avec elle. `db.session.commit()` écrit tout en base, **en une transaction** : soit tout passe, soit rien.

### `lire_liste()`

```python
def lire_liste(nom: str, langue: str) -> dict[str, str | None]:
    lignes = db.session.execute(
        db.select(WordEntry.expression, WordEntry.remplacement)
        .join(WordList)
        .where(WordList.nom == nom, WordList.langue == langue)
    ).all()
    return dict(lignes)
```

- **`db.select(WordEntry.expression, WordEntry.remplacement)`** ne sélectionne que deux colonnes, pas des objets complets.
- **`.join(WordList)`** fait la jointure. SQLAlchemy déduit la condition (`word_entries.word_list_id = word_lists.id`) de la clé étrangère.
- **`.where(WordList.nom == nom, ...)`** : ici, `==` ne compare rien en Python. Appliqué à une colonne, il *fabrique* une condition SQL. Plusieurs conditions séparées par des virgules sont combinées par `AND`.
- **`.all()`** renvoie une liste de lignes, et chaque ligne se comporte comme un tuple `(expression, remplacement)`.
- **`dict(lignes)`** : `dict()` appliqué à une suite de couples fabrique un dictionnaire.

La requête SQL produite :

```sql
SELECT word_entries.expression, word_entries.remplacement
FROM word_entries JOIN word_lists ON word_lists.id = word_entries.word_list_id
WHERE word_lists.nom = ? AND word_lists.langue = ?
```

Une liste absente donne `{}`, pas une erreur. C'est voulu — une langue non couverte ne doit jamais lever de `KeyError` —, mais c'est aussi ce qui rend silencieuse une base qu'on aurait oublié d'amorcer (section 15).

### Les fonctions de l'écran

```python
def toutes_les_listes() -> list[WordList]:
    return list(
        db.session.execute(
            db.select(WordList).order_by(WordList.nom, WordList.langue)
        ).scalars()
    )


def trouver_liste(liste_id: int) -> WordList | None:
    return db.session.get(WordList, liste_id)
```

- **`.scalars()`** extrait le premier élément de chaque ligne, ici l'objet `WordList`. Sans lui, on obtiendrait des lignes d'un seul élément.
- **`db.session.get(Modèle, clé)`** cherche par clé primaire. Il consulte d'abord la session : un objet déjà chargé est renvoyé sans requête.

```python
def ajouter_entree(liste: WordList, expression: str, remplacement: str | None) -> bool:
    if any(entree.expression == expression for entree in liste.entrees):
        return False
    liste.entrees.append(WordEntry(expression=expression, remplacement=remplacement))
    db.session.commit()
    return True
```

`any()` parcourt une expression génératrice et s'arrête au premier élément vrai. La fonction renvoie un booléen plutôt que de lever une exception : un doublon est un cas normal d'utilisation, pas une anomalie.

```python
def supprimer_entree(entree_id: int) -> tuple[str, int] | None:
    entree = db.session.get(WordEntry, entree_id)
    if entree is None:
        return None
    expression, liste_id = entree.expression, entree.word_list_id
    db.session.delete(entree)
    db.session.commit()
    return expression, liste_id
```

**Pourquoi lire l'expression avant `commit()` ?** Après chaque validation, SQLAlchemy *expire* les objets de la session : leurs attributs seront relus en base au prochain accès. Pour un objet supprimé, cette relecture échoue (`ObjectDeletedError`). On garde donc les deux valeurs dans des variables locales, avant la validation.

## 15. La lecture par les règles : `lexiques.py` et `fr.py`

```python
from app.repositories import lire_liste


def connecteurs_lourds(langue: str) -> dict[str, str]:
    return lire_liste("connecteurs_lourds", langue)


def verbes_conjugues_avec_etre(langue: str) -> frozenset[str]:
    return frozenset(lire_liste("verbes_conjugues_avec_etre", langue))
```

Tout le fichier, docstring mise à part. **Les deux signatures n'ont pas changé** : les règles appelaient déjà `connecteurs_lourds(document.langue)` et `verbes_conjugues_avec_etre(document.langue)`, et elles continuent. Seul l'intérieur a été remplacé. C'est l'intérêt d'avoir fait passer les règles par une fonction plutôt que par un dictionnaire importé.

`frozenset(dictionnaire)` fabrique un ensemble immuable des **clés** : les lemmes. Les valeurs (`None`) sont ignorées.

`lexiques.py` passe par le repository plutôt que par les modèles : le SQL reste dans un seul fichier, et aucune règle n'importe `models`.

Dans `Passif.check()`, un ajustement :

```python
        findings = []
        # Une seule lecture par analyse, et non une par auxiliaire rencontré :
        # la liste vient de la base.
        verbes_etre = verbes_conjugues_avec_etre(document.langue)

        for phrase in document.phrases:
            for auxiliaire in phrase.analyse:
                ...
                if participe.lemme in verbes_etre:
                    continue
```

Avant, l'appel était dans la boucle. Il ne coûtait rien tant que la liste était un dictionnaire en mémoire ; il coûterait une requête par auxiliaire maintenant qu'elle vient de la base. Sortir un calcul invariant d'une boucle est un réflexe à garder, et le seul changement apporté aux règles.

**Aucun cache, volontairement.** La base est relue à chaque analyse : deux petites requêtes, sans conséquence sur SQLite. En échange, une modification faite depuis l'écran vaut dès l'analyse suivante.

**Le bug silencieux.** Sur une base migrée mais non amorcée, `lire_liste()` rend `{}`. `ConnecteursLourds.s_applique_a()` renvoie alors `False` — la règle disparaît sans bruit — et `Passif` n'exclut plus aucun verbe : « Elle est allée » redevient un faux positif. D'où l'ordre d'installation : `flask db upgrade`, **puis** `flask seed`.

## 16. D'où vient le contexte d'application

`db.session` a besoin d'un **contexte d'application** : c'est lui qui dit à Flask-SQLAlchemy de quelle application, donc de quelle base, il s'agit. Hors contexte, l'accès lève :

```
RuntimeError: Working outside of application context.
```

Depuis que les règles lisent la base, elles ont besoin de ce contexte. Il vient de trois endroits :

| Situation | Qui ouvre le contexte |
|---|---|
| une requête HTTP (`flask run`) | Flask, automatiquement, pour la durée de chaque requête |
| une commande (`flask seed`) | Flask, pour les commandes ajoutées à `app.cli` |
| un test | la fixture `base_amorcee`, avec `with application.app_context():` |

C'est la raison du piège évité au passage : ne pas remplir un cache des listes dans `create_app()`. `flask db upgrade` appelle lui-même `create_app()` ; interroger `word_entries` avant que la migration l'ait créée ferait échouer la migration elle-même.

## 17. La fixture de test : `conftest.py`

```python
@pytest.fixture
def base_amorcee():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        amorcer_lexiques()
        yield application
        db.drop_all()


@pytest.fixture
def client(base_amorcee):
    return base_amorcee.test_client()
```

Une **fixture** pytest est une fonction qui prépare quelque chose pour un test. pytest la repère au nom du paramètre : un test qui déclare `client` reçoit ce que la fixture `client` renvoie.

**`yield` coupe la fixture en deux.** Tout ce qui précède est la préparation, exécutée avant le test ; `yield application` donne la main au test ; ce qui suit est le nettoyage, exécuté après, même si le test échoue.

Pas à pas :

1. `create_app(TestConfig)` : une application dont la base est `sqlite://`, c'est-à-dire **en mémoire**. Elle n'existe que le temps du test ; la base réelle n'est jamais touchée.
2. `with application.app_context():` ouvre le contexte (section 16) pour toute la durée du test.
3. `db.create_all()` crée les tables d'après les modèles. En test, on n'a pas besoin des migrations : la base part de zéro à chaque fois.
4. `amorcer_lexiques()` : la **même** fonction que `flask seed`. Tests et application s'amorcent par le même chemin.
5. `db.drop_all()` détruit les tables.

**Les fixtures se composent.** `client` déclare `base_amorcee` en paramètre : pytest exécute d'abord `base_amorcee`, puis passe son résultat à `client`. Les tests de la route voient donc les mêmes listes que les tests du moteur.

Les fichiers de tests du moteur, qui n'utilisent pas `client`, déclarent la fixture pour tout le fichier :

```python
pytestmark = pytest.mark.usefixtures("base_amorcee")
```

`pytestmark` est un nom que pytest reconnaît au niveau d'un module : la marque s'applique à chaque test du fichier. `usefixtures` exécute une fixture sans que le test ait à la recevoir en paramètre — ici, on n'a besoin que de son effet : le contexte ouvert et la base amorcée.

## 18. L'écran : `routes/admin.py`

```python
bp = Blueprint("admin", __name__, url_prefix="/listes")

LISTES = {
    "connecteurs_lourds": ("Connecteurs lourds", True),
    "verbes_conjugues_avec_etre": ("Verbes conjugués avec être", False),
}
```

- **`Blueprint("admin", __name__, url_prefix="/listes")`** : un ensemble de routes nommé `admin`, toutes préfixées par `/listes`. Les noms des routes prennent la forme `admin.listes`, `admin.ajouter` — c'est sous ce nom qu'on les désigne dans `url_for`.
- **`LISTES`** associe à chaque liste un tuple : son libellé, et un booléen qui dit si ses entrées portent un remplacement. C'est ce qui décide de la colonne affichée et de ce qui est obligatoire à l'ajout.

### `nettoyer()`

```python
def nettoyer(saisie: str) -> str:
    return " ".join(normalize(saisie).split())
```

Deux opérations enchaînées :

1. **`normalize(saisie)`** : la même normalisation que le texte analysé. Une apostrophe courbe devient droite, une espace insécable devient une espace ordinaire.
2. **`" ".join(....split())`** : `split()` sans argument coupe sur toute suite de blancs et ignore ceux des bords ; `" ".join` recolle avec une seule espace. `"  afin   de "` devient `"afin de"`.

**Pourquoi normaliser la saisie ?** Les règles cherchent les expressions dans `document.texte`, qui est toujours normalisé. Une expression copiée depuis Word, avec une apostrophe courbe, ne correspondrait jamais : on la stockerait, et elle ne serait jamais surlignée. C'est l'invariant du projet appliqué aux données au lieu du document.

### L'affichage

```python
@bp.get("/")
def listes():
    return render_template(
        "admin/listes.html",
        listes=repositories.toutes_les_listes(),
        descriptions=LISTES,
    )
```

`@bp.get("/")` est un raccourci de `@bp.route("/", methods=["GET"])`. Avec le préfixe, l'adresse est `/listes/`. Flask redirige de lui-même `/listes` vers `/listes/`.

### L'ajout

```python
@bp.post("/<int:liste_id>/entrees")
def ajouter(liste_id):
    liste = repositories.trouver_liste(liste_id)
    if liste is None:
        abort(404)
```

- **`<int:liste_id>`** est une variable d'URL avec un *convertisseur* : Flask extrait le nombre de `/listes/1/entrees` et le passe en argument, déjà converti en entier. `/listes/abc/entrees` ne correspond même pas à la route.
- **`abort(404)`** lève une exception HTTP : la fonction s'arrête là, et le client reçoit une page 404. Il n'y a pas besoin de `return`.

```python
    _, avec_remplacement = LISTES.get(liste.nom, (liste.nom, False))
    expression = nettoyer(request.form.get("expression", "")).lower()
    remplacement = nettoyer(request.form.get("remplacement", "")) or None
```

- **`LISTES.get(clé, défaut)`** : une liste inconnue du tableau reçoit un tuple par défaut. **Le déballage** `_, avec_remplacement = …` répartit le tuple ; le tiret bas signale la valeur ignorée.
- **`.lower()`** : la règle ignore la casse, deux casses feraient un doublon apparent.
- **`… or None`** : une chaîne vide devient `None`, ce que la base stocke comme `NULL`.

```python
    if not expression:
        flash("L'expression est vide.", "erreur")
    elif avec_remplacement and remplacement is None:
        flash(f"« {expression} » : cette liste demande un remplacement.", "erreur")
    elif not repositories.ajouter_entree(
        liste, expression, remplacement if avec_remplacement else None
    ):
        flash(f"« {expression} » est déjà dans la liste.", "erreur")
    else:
        flash(f"« {expression} » ajouté.", "succes")

    return redirect(url_for("admin.listes", _anchor=f"liste-{liste.id}"))
```

- **La chaîne `if / elif`** s'arrête au premier cas vrai. L'appel à `ajouter_entree()` est *dans* une condition : il n'est exécuté que si les deux contrôles précédents sont passés, et son résultat décide du message.
- **`remplacement if avec_remplacement else None`** : l'expression conditionnelle de Python. Pour une liste sans remplacement, un remplacement envoyé est ignoré.
- **`flash(message, catégorie)`** met un message de côté pour **la prochaine page affichée**. Il est stocké dans la session de l'utilisateur, un cookie signé avec `SECRET_KEY` — c'est pourquoi `flash` ne fonctionne pas sans clé secrète.
- **`redirect(url_for(...))`** : le motif **POST-Redirect-GET**. Au lieu de renvoyer une page, la route renvoie une redirection (code 302) ; le navigateur recharge alors `/listes/` en `GET`. Rafraîchir cette page rejoue le `GET`, jamais l'ajout.
- **`url_for("admin.listes", _anchor="liste-1")`** fabrique `/listes/#liste-1`. `url_for` construit l'URL à partir du *nom* de la route : si l'adresse change un jour, aucun lien n'est à corriger. `_anchor` ajoute la partie `#…`, qui fait défiler la page jusqu'à la liste modifiée.

La suppression suit le même schéma : `repositories.supprimer_entree()`, `abort(404)` si rien n'a été trouvé, `flash`, redirection.

## 19. Les gabarits : `base.html` et `admin/listes.html`

### L'héritage

```html
<!-- base.html -->
<nav class="menu">
  <a href="{{ url_for('analyze.index') }}"
     class="{{ 'actif' if request.blueprint == 'analyze' }}">Analyse</a>
  <a href="{{ url_for('admin.listes') }}"
     class="{{ 'actif' if request.blueprint == 'admin' }}">Listes de mots</a>
</nav>

{% block contenu %}{% endblock %}

{% block scripts %}{% endblock %}
```

```html
<!-- analyze/index.html -->
{% extends "base.html" %}

{% block contenu %}
<h1>Analyseur de langage clair</h1>
…
{% endblock %}
```

`base.html` est un **gabarit parent** : il contient la structure commune et des *blocs* vides. Une page enfant déclare `{% extends "base.html" %}` et remplit les blocs. Le menu n'existe ainsi qu'à un seul endroit.

- **`request.blueprint`** vaut le nom du blueprint de la route qui répond : `analyze` ou `admin`. Il permet de souligner le lien de la page courante.
- **`'actif' if …`** sans `else` : Jinja produit une chaîne vide quand la condition est fausse.
- **Le bloc `scripts`** n'est rempli que par la page d'analyse, la seule qui utilise `app.js`.

### La page des listes

```html
{% for categorie, message in get_flashed_messages(with_categories=true) %}
  <p class="{{ categorie }}">{{ message }}</p>
{% endfor %}
```

`get_flashed_messages()` récupère les messages mis de côté par `flash()`, **et les efface** : ils ne s'affichent qu'une fois. Avec `with_categories=true`, chaque élément est un couple `(catégorie, message)`. La catégorie devient la classe CSS : `erreur` ou `succes`.

```html
{% for liste in listes %}
  {% set libelle, avec_remplacement = descriptions.get(liste.nom, (liste.nom, false)) %}
  <section class="bloc-liste" id="liste-{{ liste.id }}">
    …
      {% for entree in liste.entrees | sort(attribute="expression") %}
        <tr>
          <td>{{ entree.expression }}</td>
          {% if avec_remplacement %}<td>{{ entree.remplacement }}</td>{% endif %}
          <td class="action">
            <form method="post" action="{{ url_for('admin.supprimer', entree_id=entree.id) }}">
              <button type="submit" class="discret">Supprimer</button>
            </form>
          </td>
        </tr>
      {% endfor %}
```

- **`{% set a, b = … %}`** : Jinja accepte le déballage comme Python. Le même défaut que dans la route.
- **`id="liste-{{ liste.id }}"`** est la cible de l'ancre `#liste-1` de la redirection.
- **`liste.entrees`** : le gabarit parcourt la relation définie dans le modèle. SQLAlchemy charge les entrées au premier accès.
- **Le filtre `sort(attribute="expression")`** trie par ordre alphabétique.
- **Un petit formulaire par ligne**, parce qu'une suppression modifie des données : elle passe par `POST`, jamais par un simple lien (`GET`), qu'un navigateur ou un robot pourrait suivre tout seul.
- **`url_for('admin.supprimer', entree_id=entree.id)`** remplit la variable d'URL de la route.

Tout ce qui est affiché entre `{{ }}` est **échappé** par Jinja : une expression saisie contenant `<script>` s'affiche comme du texte.

## 20. Les tests de l'écran

```python
def id_liste(nom):
    return db.session.execute(
        db.select(WordList.id).filter_by(nom=nom, langue="fr")
    ).scalar_one()


def ajouter(client, nom, **champs):
    return client.post(
        f"/listes/{id_liste(nom)}/entrees", data=champs, follow_redirects=True
    ).get_data(as_text=True)
```

- **`id_liste()`** interroge la base directement, pour ne pas supposer que les connecteurs ont l'identifiant 1. Elle fonctionne parce que le test s'exécute dans le contexte ouvert par `base_amorcee`, sur la même base en mémoire que les requêtes du client.
- **`**champs`** recueille les arguments nommés dans un dictionnaire : `ajouter(client, "connecteurs_lourds", expression="à cet égard", remplacement="sur ce point")` envoie `{"expression": ..., "remplacement": ...}`.
- **`follow_redirects=True`** : le client suit la redirection, comme un navigateur. On récupère la page `/listes/` finale, avec son message.

Le test qui compte pour la démonstration :

```python
def test_un_ajout_s_applique_des_l_analyse_suivante(client):
    texte = "À cet égard, le dossier est complet."
    assert not signale_un_connecteur(client, texte)

    corps = ajouter(client, "connecteurs_lourds", expression="à cet égard",
                    remplacement="sur ce point")

    assert "« à cet égard » ajouté." in corps
    assert signale_un_connecteur(client, texte)
```

Il vérifie le parcours entier : avant l'ajout, rien ; après, le connecteur est signalé, sans redémarrage. Et le test de redirection, sans `follow_redirects`, vérifie le motif POST-Redirect-GET lui-même :

```python
    assert reponse.status_code == 302
    assert reponse.headers["Location"].endswith(f"#liste-{id_liste('connecteurs_lourds')}")
```

---

# Partie 3 — Le fichier de test

## 21. `exemples/paragraphes-de-test.txt`

Huit paragraphes de texte administratif, encodés en UTF-8, à déposer dans l'analyseur. Chacun vise un comportement précis. Le tableau donne le résultat **réellement obtenu** le 21 septembre, avec les listes d'origine : 14 signalements.

| § | Contenu | Signalements obtenus | Ce que ça vérifie |
|---|---|---|---|
| 1 | Titre d'une ligne | aucun | un paragraphe d'une seule ligne |
| 2 | Une phrase de plus de 25 mots, avec « R. 441-1 » | longueur ; « Dans le cadre de » ; « conformément à » ; passif « a été examinée » (sans agent : avertissement) | une abréviation ne coupe pas la phrase ; plusieurs signalements se chevauchent dans la même phrase |
| 3 | « Afin d'assurer… », « S'agissant&nbsp;&nbsp;de » (double espace) | « Afin d' » ; passif « a été prise » (avec agent : info) ; « S'agissant  de » ; passif « sera communiquée » (futur, sans agent) | l'élision, la double espace, les deux sévérités du passif |
| 4 | « est susceptible de », « n'est nécessaire », « est allée » | seulement le connecteur « est susceptible d' » | trois faux positifs du passif, tous écartés |
| 5 | « La porte du guichet est ouverte », « S'agissant des pièces » | passif « est ouverte » ; « il convient de » ; « préalablement à » | deux limites connues : l'état confondu avec le passif, et « des » qui n'est ni « de » ni « d' » |
| 6 | Apostrophes courbes, espaces insécables, un trait d'union conditionnel invisible dans « transmission » | longueur ; « nonobstant » | la normalisation : tout est redressé, et l'invariant tient |
| 7 | Une phrase répétée ; `<`, `>`, `&` et une balise `<script>` | aucun | les positions d'un texte répété ; l'échappement HTML — la balise s'affiche telle quelle |
| 8 | « À cet égard, le dossier… » | aucun | la démonstration de l'écran des listes |

Deux lignes vides séparent les paragraphes 7 et 8, pour vérifier que la segmentation ne crée pas de paragraphe fantôme.

**Une observation instructive au §6.** La phrase compte 29 tokens, dont trois signes de ponctuation isolés : `:`, `«` et `»`. Dans le fichier, ils sont précédés d'espaces insécables, que la normalisation change en espaces ordinaires ; la tokenisation `\S+` les compte alors comme des mots. Même sans eux, il reste 26 mots, au-dessus du seuil de 25 : le signalement est justifié, mais le décompte affiché est gonflé. C'est la limite « tokenisation grossière » rendue visible.

**La démonstration de l'écran, avec le §8 :**

1. Déposer le fichier : le §8 n'a aucun signalement.
2. Menu → *Listes de mots* : ajouter « à cet égard », remplacement « sur ce point ».
3. Revenir sur *Analyse*, redéposer le fichier : « À cet égard » est surligné, avec sa proposition.

Pensez ensuite à supprimer l'entrée ajoutée, pour retrouver les listes d'origine.

---

## Récapitulatif des notions

| Notion | Où |
|---|---|
| Hiérarchie d'exceptions, `raise … from` | §1, §5 |
| Alias de type, `Callable`, `BinaryIO` | §1 |
| Fabrique de décorateurs, fermeture, `*args` | §1 |
| Import pour effet de bord, `__all__`, `# noqa` | §2 |
| `bytes` et `str`, `decode`, BOM | §3 |
| Expressions régulières : `MULTILINE`, groupes, `\1`, non gourmand | §4 |
| Compréhensions de liste, d'ensemble, de dictionnaire ; générateurs | §5, §13, §14 |
| Générateur récursif, `yield from` | §6 |
| Valeur par défaut mutable | §7 |
| `app_errorhandler`, `current_app`, réponse `(corps, code)` | §7 |
| `request.files`, `FileStorage`, `enctype` | §7, §9 |
| Variables d'environnement, configuration Flask | §8 |
| Client de test, `io.BytesIO` | §10 |
| Modèles déclaratifs, `Mapped`, contraintes, `relationship`, cascade | §11 |
| Migrations Alembic, `revision` / `down_revision` | §12 |
| `pathlib`, `__file__` | §13 |
| Commande Click, `app.cli` | §13 |
| `select`, `execute`, `scalar_one_or_none`, `scalars`, jointure, transaction | §14 |
| Expiration des objets après `commit()` | §14 |
| Contexte d'application | §16 |
| Fixtures pytest, `yield`, composition, `pytestmark` | §17 |
| Blueprint, `url_prefix`, convertisseur `<int:…>`, `abort` | §18 |
| `flash`, POST-Redirect-GET, `url_for` et `_anchor` | §18 |
| Héritage de gabarits Jinja, blocs, filtres, échappement | §19 |
