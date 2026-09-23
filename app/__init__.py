from flask import Flask
from flask_migrate import Migrate

from app.cli import seed
from app.config import Config
from app.models import db
from app.routes import admin, analyze


migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(analyze.bp)
    app.register_blueprint(admin.bp)

    app.cli.add_command(seed)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
