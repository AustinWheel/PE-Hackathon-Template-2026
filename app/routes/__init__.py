def register_routes(app):
    """Register all route blueprints with the Flask app.

    Add your blueprints here. Example:
        from app.routes.products import products_bp
        app.register_blueprint(products_bp)
    """
    from app.routes.products import products_bp
    app.register_blueprint(products_bp)

    from app.routes.metrics import metrics_bp
    app.register_blueprint(metrics_bp)

    from app.routes.logs import logs_bp
    app.register_blueprint(logs_bp)

    from app.routes.chaos import chaos_bp
    app.register_blueprint(chaos_bp)

    from app.routes.prom_metrics import prom_bp
    app.register_blueprint(prom_bp)

    from app.routes.urls import urls_bp
    app.register_blueprint(urls_bp)

    from app.routes.users import users_bp
    app.register_blueprint(users_bp)

    from app.routes.events import events_bp
    app.register_blueprint(events_bp)

    from app.routes.alerts import alerts_bp
    app.register_blueprint(alerts_bp)
