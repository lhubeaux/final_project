"""Accès aux données : ranger des objets en lignes de table, et les relire.

Aucune linguistique ici. Le repository ne décide rien, il range et relit.
"""

from app.models import WordEntry, WordList, db


def amorcer_liste(nom: str, langue: str, entrees: dict[str, str | None]) -> int:
    """Ajoute à la liste les entrées qui n'y sont pas encore ; renvoie leur nombre.

    N'écrase et ne supprime jamais rien : relancer l'amorce ne doit pas effacer
    ce qu'un utilisateur aurait ajouté ou corrigé depuis.
    """
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


def lire_liste(nom: str, langue: str) -> dict[str, str | None]:
    """Les entrées d'une liste, {expression: remplacement} ; vide si elle n'existe pas.

    Une liste absente n'est pas une erreur : c'est une langue pas encore
    couverte, et la règle concernée ne s'exécutera simplement pas.
    """
    lignes = db.session.execute(
        db.select(WordEntry.expression, WordEntry.remplacement)
        .join(WordList)
        .where(WordList.nom == nom, WordList.langue == langue)
    ).all()
    return dict(lignes)

    

def toutes_les_listes() -> list[WordList]:
    """Toutes les listes de mots, par nom puis par langue."""
    return list(
        db.session.execute(
            db.select(WordList).order_by(WordList.nom, WordList.langue)
        ).scalars()
    )


def trouver_liste(liste_id: int) -> WordList | None:
    return db.session.get(WordList, liste_id)


def ajouter_entree(liste: WordList, expression: str, remplacement: str | None) -> bool:
    """Ajoute une entrée à la liste ; renvoie False si l'expression y est déjà."""
    if any(entree.expression == expression for entree in liste.entrees):
        return False
    liste.entrees.append(WordEntry(expression=expression, remplacement=remplacement))
    db.session.commit()
    return True


def supprimer_entree(entree_id: int) -> tuple[str, int] | None:
    """Supprime une entrée ; renvoie son expression et l'id de sa liste, ou None.

    Les deux valeurs sont lues AVANT la validation : après `commit()`, l'objet
    supprimé ne peut plus être relu.
    """
    entree = db.session.get(WordEntry, entree_id)
    if entree is None:
        return None
    expression, liste_id = entree.expression, entree.word_list_id
    db.session.delete(entree)
    db.session.commit()
    return expression, liste_id
