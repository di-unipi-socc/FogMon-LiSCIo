from flask_pymongo import PyMongo
import logging

mongo = PyMongo()

def deaggregate(cursor):
    vals = list(cursor)
    
    for val in vals:
        for id,v in val["_id"].items():
            val[id] = v
    return vals

def clean_results(results):
    item = {}
    data = []
    
    for result in results:
        item = {}
        for k,v in result.items():
            if k == "_id":
                v = str(v)
            item[k] = v
        data.append(item)
    return data

def get_footprints(session):
    return mongo.db.footprint.find_one({"session":session})

def save_footprint(session, data):
    item = {"session":session, "data":data}
    mongo.db.footprint.replace_one({"session": session}, item, upsert=True)

def get_updates(session, begin=None, end=None):
    # return updates from begin date to end date (if set)
    # in reverse order
    query = {"session": session}
    query_date = {}
    if begin is not None:
        query_date["$gt"] = begin 
    if end is not None:
        query_date["$lt"] = end 
    if begin is not None or end is not None:
        query["datetime"] = query_date

    cursor = mongo.db.update.find(query).sort([("datetime", -1)])
    return clean_results(cursor)

def get_spec(session):
    cursor = mongo.db.spec.find({"session": session})
    return clean_results(cursor)[0]

def get_leaders(session):
    cursor = mongo.db.update.find({"session": session}).sort([("datetime", -1)])
    logging.info(cursor[0])
    ids = [el["id"] for el in cursor[0]["update"]["selected"]]
    return ids

def get_reports(session, ids=None, begin=None, end=None):
    # return reports from begin date to end date (if set)
    # if ids is set then filter the id of the sender, checking if is in ids
    # in reverse order
    query = {"session": session}
    query_date = {}
    if begin is not None:
        query_date["$gt"] = begin 
    if end is not None:
        query_date["$lt"] = end 
    if begin is not None or end is not None:
        query["datetime"] = query_date
    if ids is not None:
        query["sender.id"] = {"$in": ids }

    cursor = mongo.db.reports.find(query).sort([("datetime", -1)])
    return clean_results(cursor)

def get_lastreports(session):
    cursor = mongo.db.update.find({"session": session}).sort([("datetime", 1)])
    updates = list(cursor)
    date = updates[0]["datetime"]
    cursor = mongo.db.reports.find({"session": session,"datetime": {"$lt": date}}).sort([("datetime", 1)])
    els = list(cursor)
    ids2 = [(len(el["report"]["reports"]),el["sender"]["id"],el["datetime"]) for el in els ]
    for el in updates:
        date = el["datetime"]
        logging.info(date)
    logging.info("\n\n\n")
    logging.info(ids2)
    logging.info(date)
    for el in updates[1:]:
        first_date = date
        date = el["datetime"]
        cursor = mongo.db.reports.find({"session": session,"datetime": {"$lt": date, "$gt": first_date}}).sort([("datetime", 1)])
        els = list(cursor)
        ids2 = [(len(el["report"]["reports"]),el["sender"]["id"],el["datetime"]) for el in els ]
        logging.info(ids2)
        logging.info(date)
    cursor = mongo.db.reports.find({"session": session,"datetime": {"$gt": date}}).sort([("datetime", 1)])
    els = list(cursor)
    ids2 = [(len(el["report"]["reports"]),el["sender"]["id"],el["datetime"]) for el in els ]
    logging.info(ids2)

    ids = [el["id"] for el in updates[0]["update"]["selected"]]
    logging.info(ids)
    cursor = mongo.db.reports.find({"session": session, "sender.id": {"$in": ids }, "datetime": {"$gt": date}}).sort([("datetime", -1)])
    els = list(cursor)
    logging.info(len(els))
    ids2 = [el["sender"]["id"] for el in els]
    logging.info(ids2)
    reports = []
    checked = []
    for report in els:
        id = report["sender"]["id"]
        if id in ids and id not in checked:
            reports.append(report)
            checked.append(id)
    reports = clean_results(reports)
    return reports
