import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///analyseur.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", 20000))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_BYTES", 2097152))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"      # base en mémoire, détruite à la fin
