import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///analyseur.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", 20000))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_BYTES", 2097152))
    # Flask 3.1 plafonne les champs non-fichier séparément (500 000 octets par
    # défaut) et lève un 413 avant la route. On aligne sur la taille totale :
    # un texte trop long doit recevoir le message de MAX_TEXT_LENGTH, pas une
    # page d'erreur brute.
    MAX_FORM_MEMORY_SIZE = MAX_CONTENT_LENGTH


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"      # base en mémoire, détruite à la fin
