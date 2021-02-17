from model import mongo
from datetime import datetime
from bson.son import SON
import json
from collections import OrderedDict
from model import clean_results, deaggregate
import logging

def get_sessions():
    sessions1 = mongo.db.spec.find({})
    sessions2 = mongo.db.reports.aggregate([
        {"$sort": SON([("datetime", -1)])},
        {"$group": {
            "_id": {"session": "$session"},
            #"sender": "$sender",
            "datetime": {"$first": "$datetime"},
            #"report": {"$first": "$report"}
        }}
    ])
    sessions1 = clean_results(sessions1)
    sessions = deaggregate(sessions2)
    for session in sessions1:
        found = False
        for session2 in sessions:
            if session["session"] == session2["session"]:
                found = True
                session2["specs"] = True
                break
        if not found:
            session["specs"] = True
            sessions.append(session)
    logging.info(str(sessions))
    return sessions

def get_session(id):
    updates = mongo.db.update.find({"session":id}).sort([("datetime", -1)])
    reports = mongo.db.reports.find({"session":id}).sort([("datetime", -1)])
    data = unify_reports(reports,updates)
    return data

def add_testbed(data):
    stri = json.dumps(data, sort_keys=True)
    data = json.loads(stri, object_pairs_hook=OrderedDict)
    data = SON(data)

    with mongo.cx.start_session() as mongo_session:
        with mongo_session.start_transaction():
            els = mongo.db.spec.find({})
            found = False
            for el in els:
                el["_id"] = str(el["_id"])
                stri = json.dumps(el)
                if data == el["specs"][0]:
                    logging.info("Equal: "+stri[:100])
                    found = True
                    break
            if found:
                logging.info("Old session")
                session = el["session"]
            else:
                logging.info("New session")
                sessions = get_sessions()
                session = 0
                while session in [el["session"] for el in sessions]:
                    session+=1
                item = {
                    "session": session,
                    "specs": [data],
                    "change_dates": []
                }
                mongo.db.spec.replace_one({"session": session}, item, upsert=True)
    return session

def change_testbed(session, data):
    stri = json.dumps(data, sort_keys=True)
    data = json.loads(stri, object_pairs_hook=OrderedDict)
    data = SON(data)
    with mongo.cx.start_session() as mongo_session:
        with mongo_session.start_transaction():
            spec = mongo.db.spec.find_one({"session": session})
            spec["change_dates"].append(datetime.utcnow())
            spec["specs"].append(data)
            mongo.db.spec.replace_one({"session": session}, spec, upsert=True)

def remove(session):
    with mongo.cx.start_session() as mongo_session:
        with mongo_session.start_transaction():
            mongo.db.update.remove({"session": session})
            mongo.db.reports.remove({"session": session})




def search_lasts(reports, update):
    selected = update["update"]["selected"]
    lasts = []
    for leader in selected:
        for report in reports:
            if report["sender"]["id"] == leader["id"]:
                lasts.append(report["report"])
                break
    return lasts


def unify_reports(reports,updates):
    reports = clean_results(reports)
    updates = clean_results(updates)

    reports = search_lasts(reports, updates[0])
    return {"Reports":reports,"Leaders":updates[0]}

def save_report(report):
    item = {
        'report': report["data"],
        'session': report["argument"],
        'sender': report["sender"],
        'datetime': datetime.utcnow()
    }
    #logging.info(str(item))
    mongo.db.reports.insert_one(item)


def save_update(update):
    item = {
        'update': update["data"],
        'session': update["argument"],
        'sender': update["sender"],
        'datetime': datetime.utcnow()
    }
    logging.info(str(item))
    mongo.db.update.insert_one(item)