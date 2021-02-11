from app import db,application
from sys import stderr
from datetime import datetime
from bson.son import SON

def get_sessions():
    sessions = db.reports.aggregate([
        {"$sort": SON([("datetime", -1)])},
        {"$group": {
            "_id": {"session": "$session"},
            #"sender": "$sender",
            "datetime": {"$first": "$datetime"},
            #"report": {"$first": "$report"}
        }}
    ])
    sessions = [sessions for session in sessions]
    application.logger.info(str(sessions))
    return sessions

def get_session(id):
    updates = db.update.find().sort([("datetime", -1)])
    reports = db.reports.find().sort([("datetime", -1)])
    data = unify_reports(reports,updates)
    return data

def clean_results(results):
    item = {}
    data = []
    
    for result in results:
        print("packet" in result, flush=True)
        item = {
            'id': str(result['_id']),
            'packet': result['packet'],
            'date': result['datetime']
        }
        data.append(item)
    return data

def search_lasts(reports, update):
    selected = update["packet"]["data"]["selected"]
    lasts = []
    for leader in selected:
        for report in reports:
            if report["packet"]["sender"]["id"] == leader["id"]:
                lasts.append(report["packet"])
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
    application.logger.info(str(item))
    db.reports.insert_one(item)


def save_update(update):
    item = {
        'update': update["data"],
        'session': update["argument"],
        'sender': update["sender"],
        'datetime': datetime.utcnow()
    }
    application.logger.info(str(item))
    db.update.insert_one(item)