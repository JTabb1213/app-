from flask import Flask
from flask_cors import CORS

from routes.score import score_bp
from routes.tokenomics import tokenomics_bp
from routes.cache import cache_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(score_bp, url_prefix="/api")
    app.register_blueprint(tokenomics_bp, url_prefix="/api")
    app.register_blueprint(cache_bp, url_prefix="/api")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=8000)
