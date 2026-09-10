from app.services.document import build_document


def test_positions_absolues():
    document = build_document(
        "Titre du décret\r\n\r\nL\u2019examen a été effectué par la commission."
    )
    texte = document.texte

    for paragraphe in document.paragraphes:
        assert texte[paragraphe.start:paragraphe.end] == paragraphe.texte

        for phrase in paragraphe.phrases:
            assert texte[phrase.start:phrase.end] == phrase.texte

            for token in phrase.tokens:
                assert texte[token.start:token.end] == token.texte


def test_document_vide():
    document = build_document("   \n\n  ")
    assert document.paragraphes == []
    assert document.tokens == []
