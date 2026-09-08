from flask import Flask
from app.routes import analyze

from app.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    app.register_blueprint(analyze.bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}


    return app
