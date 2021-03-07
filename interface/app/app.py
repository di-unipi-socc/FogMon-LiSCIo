import os
from flask import Flask
from flask_pymongo import PyMongo
import logging
from views import blueprints
from model import mongo

logging.basicConfig(level=logging.INFO)

def make_app():
    app = Flask(__name__)

    app.config["MONGO_URI"] = 'mongodb://' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']

    for bp in blueprints:
        app.register_blueprint(bp)
        bp.app = app

    mongo.init_app(app)

    mongo.db.spec.create_index("session")
    mongo.db.footprint.create_index("session")
    mongo.db.reports.create_index("datetime")
    mongo.db.reports.create_index("session")
    mongo.db.update.create_index("datetime")
    mongo.db.reports.create_index("session")

    return app


if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", True)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    app = make_app()
    app.run(host='0.0.0.0', port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)