from flask import Flask
from flask_pymongo import PyMongo

application = Flask(__name__)

mongo = PyMongo(application)
db = mongo.db