"""Enregistrer une analyse sous un nom, puis la relire à l'identique."""

import re

from app.repositories import toutes_les_analyses
from app.services.ingestion.document import build_document

TEXTE = "Afin d'agir, la décision a été prise.\n\nNonobstant tout, le rapport sera publié."


def texte_surligne(corps):
    return re.search(r'<div class="texte">(.*?)</div>', corps, re.S).group(1)


def enregistrer(client, texte=TEXTE, nom="Note de service", **champs):
    return client.post("/analyses/", data={"texte": texte, "nom": nom, **champs})


def test_analyser_n_enregistre_rien(client):
    client.post("/", data={"texte": TEXTE})

    assert toutes_les_analyses() == []


def test_l_analyse_propose_l_enregistrement(client):
    corps = client.post("/", data={"texte": TEXTE}).get_data(as_text=True)

    assert 'action="/analyses/"' in corps
    assert 'name="nom"' in corps


def test_enregistrer_redirige_vers_l_analyse(client):
    """POST-Redirect-GET : rafraîchir la page ne réenregistre rien."""
    reponse = enregistrer(client)

    assert reponse.status_code == 302
    assert reponse.headers["Location"].endswith("/analyses/1")


def test_une_analyse_relue_est_identique(client):
    affichee = client.post("/", data={"texte": TEXTE}).get_data(as_text=True)
    enregistrer(client)
    relue = client.get("/analyses/1").get_data(as_text=True)

    assert texte_surligne(relue) == texte_surligne(affichee)
    assert "« Note de service »" in relue


def test_les_crlf_du_navigateur_ne_decalent_rien(client):
    """Un navigateur renvoie les retours à la ligne du champ caché en CRLF."""
    affichee = client.post("/", data={"texte": TEXTE}).get_data(as_text=True)
    enregistrer(client, texte=TEXTE.replace("\n", "\r\n"))
    relue = client.get("/analyses/1").get_data(as_text=True)

    assert texte_surligne(relue) == texte_surligne(affichee)


def test_la_liste_montre_le_nom_et_le_fichier(client):
    enregistrer(client, nom="Décret 2026", nom_fichier="decret.docx")
    corps = client.get("/analyses/").get_data(as_text=True)

    assert "Décret 2026" in corps
    assert "decret.docx" in corps


def test_un_nom_vide_est_refuse(client):
    corps = enregistrer(client, nom="   ").get_data(as_text=True)

    assert "Donnez un nom" in corps
    assert toutes_les_analyses() == []


def test_analyse_inconnue_donne_404(client):
    assert client.get("/analyses/999").status_code == 404


def test_normaliser_deux_fois_ne_change_rien():
    """C'est ce qui rend la relecture sûre : les empans enregistrés restent valides."""
    brut = "\ufeffTitre\r\n\r\nL\u2019e\u0301te\u0301\u00a0tran\u00adsmis."
    texte = build_document(brut).texte
    assert build_document(texte).texte == texte
