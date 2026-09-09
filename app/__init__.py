from flask import Flask
from flask_migrate import Migrate

from app.config import Config
from app.models import db
from app.routes import analyze

migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(analyze.bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
