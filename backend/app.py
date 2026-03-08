from flask import Flask
from flask_cors import CORS
import os

from routes.score import score_bp
from routes.tokenomics import tokenomics_bp
from routes.cache import cache_bp
from routes.database import database_bp
from routes.realtime import realtime_bp

def create_app():
    app = Flask(__name__)
    
    # Parse comma-separated list of allowed origins
    allowed_origins_str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000"  # dev defaults
    )
    allowed_origins = [o.strip() for o in allowed_origins_str.split(",")]
    
    CORS(app, origins=allowed_origins, supports_credentials=True)

    app.register_blueprint(score_bp, url_prefix="/api")
    app.register_blueprint(tokenomics_bp, url_prefix="/api")
    app.register_blueprint(cache_bp, url_prefix="/api")
    app.register_blueprint(database_bp, url_prefix="/api")
    app.register_blueprint(realtime_bp, url_prefix="/api")

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    app.run(debug=True, port=port)
