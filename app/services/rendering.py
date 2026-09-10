from markupsafe import Markup, escape

from app.services.rules.base import Finding


def surligner(texte: str, findings: list[Finding]) -> Markup:
    """Rend le texte avec un <mark> autour de chaque empan signalé.

    Chaque segment est échappé AVANT d'être entouré de balises : dans l'autre
    sens on échapperait ses propres balises, ou on laisserait passer celles de
    l'utilisateur.

    Le découpage se fait aux frontières de TOUS les signalements, si bien que
    deux signalements qui se chevauchent — une phrase trop longue contenant un
    connecteur lourd — produisent un segment commun portant les deux classes,
    et non deux balises imbriquées.
    """
    if not findings:
        return escape(texte)

    frontieres = {0, len(texte)}
    for finding in findings:
        frontieres.add(max(0, min(finding.char_start, len(texte))))
        frontieres.add(max(0, min(finding.char_end, len(texte))))
    bornes = sorted(frontieres)

    morceaux: list[Markup] = []
    for debut, fin in zip(bornes, bornes[1:]):
        segment = escape(texte[debut:fin])

        couvrants = [
            rang for rang, finding in enumerate(findings)
            if finding.char_start <= debut and finding.char_end >= fin
        ]
        if not couvrants:
            morceaux.append(segment)
            continue

        classes = " ".join(
            ["signalement"] + [f"r-{findings[rang].rule_id}" for rang in couvrants]
        )
        renvois = ",".join(str(rang) for rang in couvrants)
        morceaux.append(
            Markup('<mark class="{}" data-findings="{}">{}</mark>').format(
                classes, renvois, segment
            )
        )

    return Markup("").join(morceaux)
