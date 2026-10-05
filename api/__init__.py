from flask import Flask
from flask_login import LoginManager

from config.settings import settings
from config.logging import setup_logging
from data.database import init_db, SessionLocal
from data.models import User
from api.routes import bp as api_bp
from dashboard.routes import bp as dashboard_bp

login_manager = LoginManager()
login_manager.login_view = 'dashboard.login'
login_manager.login_message = 'Please sign in with clinician credentials to access the dashboard.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id: str):
    session = SessionLocal()
    try:
        return session.get(User, int(user_id))
    except Exception:
        return None
    finally:
        session.close()


def create_app() -> Flask:
    """
    Application factory for the Vaidya clinical multi-agent Flask app.
    """
    setup_logging()

    # Resilient DB connection check and table initialization
    init_db()

    app = Flask(settings.APP_NAME)
    app.config["SECRET_KEY"] = settings.SECRET_KEY

    # Initialize Flask-Login
    login_manager.init_app(app)

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)

    return app
