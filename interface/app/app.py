import os
from flask import Flask, request, jsonify, render_template
from flask_pymongo import PyMongo

from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

application = Flask(__name__)

application.config["MONGO_URI"] = 'mongodb://' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']

mongo = PyMongo(application)
db = mongo.db

from utils.session import unify_reports, get_sessions, get_session, save_update, save_report

@application.route('/')
def index():
    return render_template('index.html')

@application.route('/testbeds.html')
def testbeds():
    data = get_testbeds().json["data"]
    logging.info(data)
    return render_template('testbeds.html', r = data)



@application.route('/testbed')
def get_testbeds():
    data = get_sessions()
    return jsonify(
        status=True,
        data=data,
    )

@application.route('/testbed/<int:session>')
def get_testbed(session):
    print("session",session, flush=True)
    data = get_session(session)

    return jsonify(
        status=True,
        data=data,
    )

@application.route('/data', methods=['POST'])
def post_data():
    data = request.get_json(force=True)
    
    try:
        if data["type"] == 0:
            save_report(data)
        elif data["type"] == 1:
            save_update(data)
    except:
        pass

    return jsonify(
        status=True,
        message='Saved successfully!'
    ), 201

if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", True)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    application.run(host='0.0.0.0', port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG)