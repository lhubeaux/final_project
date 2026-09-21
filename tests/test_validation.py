"""Le parcours d'erreur : ce qu'un utilisateur voit quand il se trompe.

Ces tests passent par la route, donc par `client` : ils vérifient le message
affiché, pas la fonction qui le produit. C'est le seul endroit du projet où
l'on teste Flask plutôt que le moteur.
"""

import io


def poster_fichier(client, nom, contenu: bytes):
    """Dépose un fichier dans le formulaire, comme le ferait un navigateur."""
    return client.post(
        "/",
        data={"fichier": (io.BytesIO(contenu), nom)},
        content_type="multipart/form-data",
    )


# --- taille ------------------------------------------------------------------

def test_fichier_trop_volumineux(client):
    """Flask refuse la requête avant la route : c'est `app_errorhandler` qui répond."""
    reponse = poster_fichier(client, "gros.txt", b"a" * 3_000_000)

    assert reponse.status_code == 413
    assert "2 Mo maximum" in reponse.get_data(as_text=True)


def test_texte_trop_long(client):
    """`maxlength` n'existe que dans le navigateur ; un envoi direct le contourne."""
    reponse = client.post("/", data={"texte": "mot " * 8_000})     # 32 000 caractères

    assert reponse.status_code == 200
    assert "Texte trop long" in reponse.get_data(as_text=True)


def test_texte_vide(client):
    reponse = client.post("/", data={"texte": "   \n\n  "})

    assert reponse.status_code == 200
    assert "Aucun texte à analyser." in reponse.get_data(as_text=True)


# --- formats -----------------------------------------------------------------

def test_pdf_refuse_avec_sa_raison(client):
    """Un refus documenté (D-2), pas un « format inconnu ».

    L'assertion évite l'apostrophe : Jinja échappe le message, et « n'est »
    arrive dans la page sous la forme « n&#39;est ».
    """
    corps = poster_fichier(client, "decret.pdf", b"%PDF-1.4").get_data(as_text=True)

    assert "le texte y est disposé, pas structuré" in corps


def test_doc_refuse_et_oriente_vers_docx(client):
    corps = poster_fichier(client, "note.doc", b"\xd0\xcf\x11\xe0").get_data(as_text=True)

    assert "Enregistrez le fichier en .docx" in corps


def test_extension_inconnue_liste_les_formats(client):
    corps = poster_fichier(client, "notes.rtf", b"{\rtf1}").get_data(as_text=True)

    assert "non pris en charge" in corps
    assert ".docx, .md, .odt, .txt" in corps


def test_docx_corrompu(client):
    corps = poster_fichier(client, "casse.docx", b"ceci n'est pas un zip").get_data(as_text=True)

    assert "illisible ou corrompu" in corps


# --- décodage ----------------------------------------------------------------

def test_txt_non_utf8_est_decode(client):
    """Un .txt Windows : l'encodage n'est écrit nulle part, il faut le deviner."""
    corps = poster_fichier(
        client, "note.txt", "La décision a été prise par le conseil.".encode("cp1252")
    ).get_data(as_text=True)

    assert "décision" in corps
    assert "Ã©" not in corps      # le mojibake ne passe pas silencieusement


def test_fichier_l_emporte_sur_la_zone_de_texte(client):
    """Déposer un fichier est le geste le plus explicite."""
    reponse = client.post(
        "/",
        data={
            "texte": "Le texte de la zone de saisie.",
            "fichier": (io.BytesIO("Le texte du fichier.".encode()), "note.txt"),
        },
        content_type="multipart/form-data",
    )
    corps = reponse.get_data(as_text=True)

    assert "Le texte du fichier." in corps
    assert "Le texte de la zone de saisie." not in corps
