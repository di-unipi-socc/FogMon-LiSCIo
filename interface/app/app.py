import os
from flask import Flask, request, jsonify
from flask_pymongo import PyMongo

from datetime import datetime

application = Flask(__name__)

application.config["MONGO_URI"] = 'mongodb://' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']

mongo = PyMongo(application)
db = mongo.db

@application.route('/')
def index():
    return jsonify(
        status=True,
        message='Welcome to the Dockerized Flask MongoDB app!'
    )


@application.route('/data')
def get_info():
    updates = db.update.find().sort([("datetime", -1)]).limit(1)
    item = {}
    data = []
    for update in updates:
        item = {
            'id': str(update['_id']),
            'data': update['data'],
            'date': update['datetime']
        }
        data.append(item)

    return jsonify(
        status=True,
        data=data,
        num=len(data)
    )

@application.route('/data', methods=['POST'])
def sendUpdate():
    data = request.get_json(force=True)
    item = {
        'data': data,
        'datetime': datetime.utcnow()
    }
    db.update.insert_one(item)

    return jsonify(
        status=True,
        message='Saved successfully!'
    ), 201

if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", True)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    application.run(host='0.0.0.0', port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)