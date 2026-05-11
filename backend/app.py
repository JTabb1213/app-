from flask import Flask, jsonify
from flask_cors import CORS
from pathlib import Path
import logging
import os

# Load root .env first, then backend/.env for overrides
def load_env_files():
    """Load .env files in order of priority (highest to lowest)."""
    root_env = Path(__file__).resolve().parents[1] / ".env"
    backend_env = Path(__file__).resolve().parent / ".env"
    
    for env_file in [root_env, backend_env]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value

load_env_files()

# Configure logging once at import time so all modules pick it up
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-20s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from routes.score import score_bp
from routes.tokenomics import tokenomics_bp
from routes.cache import cache_bp
from routes.database import database_bp
from routes.realtime import realtime_bp
from routes.volume import volume_bp
from routes.candles import candles_bp
from routes.holder_diversity import holder_diversity_bp

def create_app():
    app = Flask(__name__)
    
    # Parse comma-separated list of allowed origins
    allowed_origins_str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000"  # dev defaults
    )
    allowed_origins = [o.strip() for o in allowed_origins_str.split(",")]
    
    CORS(app, origins=allowed_origins, supports_credentials=True)

    # Verification endpoint for deployment testing
    @app.route("/api/verify", methods=["GET"])
    def verify():
        print("Backend verification: hello")  # This will show in Cloud Run logs
        return jsonify({"message": "Backend deployed successfully!", "status": "hello"})

    app.register_blueprint(score_bp, url_prefix="/api")
    app.register_blueprint(tokenomics_bp, url_prefix="/api")
    app.register_blueprint(cache_bp, url_prefix="/api")
    app.register_blueprint(database_bp, url_prefix="/api")
    app.register_blueprint(realtime_bp, url_prefix="/api")
    app.register_blueprint(volume_bp, url_prefix="/api")
    app.register_blueprint(candles_bp, url_prefix="/api")
    app.register_blueprint(holder_diversity_bp, url_prefix="/api")

    _startup_checks()

    return app


def _startup_checks():
    """Ping Postgres and Redis at startup so failures are visible immediately."""
    # ── Postgres ────────────────────────────────────────────────────────────
    import psycopg2
    primary = os.getenv("DATABASE_URL")
    fallback = os.getenv("DATABASE_URL_IPV4")
    try:
        conn = psycopg2.connect(primary, connect_timeout=5)
        conn.close()
        logger.info("Startup: Postgres reachable (primary)")
    except Exception as e:
        logger.warning(f"Startup: Postgres primary unreachable ({e})")
        if fallback and fallback != primary:
            try:
                conn = psycopg2.connect(fallback, connect_timeout=5)
                conn.close()
                logger.info("Startup: Postgres reachable (IPv4 fallback)")
            except Exception as e2:
                logger.warning(f"Startup: Postgres IPv4 fallback also unreachable ({e2})")

    # ── Redis ───────────────────────────────────────────────────────────────
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis as redis_lib
            r = redis_lib.from_url(redis_url, socket_connect_timeout=5)
            r.ping()
            logger.info("Startup: Redis reachable")
        except Exception as e:
            logger.warning(f"Startup: Redis unreachable ({e}) — cache will be unavailable")

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    app.run(debug=True, port=port)
