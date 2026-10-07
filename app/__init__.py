from flask import Flask, render_template, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config.get("BEHIND_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app import models
    from app.utils import to_local, money

    from app.auth import bp as auth_bp
    from app.bookings import bp as bookings_bp
    from app.dashboard import bp as dashboard_bp
    from app.events import bp as events_bp
    from app.main import bp as main_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(bookings_bp, url_prefix="/bookings")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(events_bp, url_prefix="/events")
    app.register_blueprint(main_bp)

    app.jinja_env.filters["event_dt"] = lambda dt: to_local(dt).strftime("%a %d %b, %I:%M %p")
    app.jinja_env.filters["money"] = money

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template("429.html"), 429

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("500.html"), 500

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        flash("Your form expired. Please try again.", "danger")
        return redirect(url_for("main.index"))

    with app.app_context():
        db.create_all()

    return app