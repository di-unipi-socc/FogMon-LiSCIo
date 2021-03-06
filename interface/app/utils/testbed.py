from .spec import get_associations
from model import mongo
from datetime import datetime
from bson.son import SON
import json
from collections import OrderedDict
from model import clean_results, deaggregate
import logging

def get_sessions():
    sessions1 = mongo.db.spec.find({}, projection={'_id': False})
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
    return sessions

def get_session(session):
    logging.info("start")
    updates = mongo.db.update.find({"session":session}, projection={'_id': False}).sort([("datetime", -1)])
    reports = mongo.db.reports.find({"session":session}, projection={'_id': False}).sort([("datetime", -1)]).limit(10)
    logging.info("query")
    data = unify_reports(reports,updates)
    logging.info("unify")
    import networkx as nx
    import json

    G = nx.DiGraph()
    leaders = {}
    nodes = {}
    id = 0
    Nodes,Ids =get_associations(session)
    logging.info("associations")
    ids = {}
    reports = mongo.db.reports.find({"session":session}, projection={'_id': False}).sort([("datetime", -1)]).limit(1)
    reports = list(reports)
    for report in reports[0]["report"]["reports"]:
        nodes[Ids[report["source"]["id"]]] = id
        ids[id] = Ids[report["source"]["id"]]
        leaders[id] = Ids[report["leader"]]
        G.add_node(id)
        id+=1
    logging.info("reports")
    # this d3 example uses the name attribute for the mouse-hover value,
    # so add a name to each node
    for n in G:
        G.nodes[n]["name"] = ids[n]
        G.add_edge(n, nodes[leaders[n]],l=0)
    # write json formatted data
    d = nx.json_graph.node_link_data(G)  # node-link format to serialize
    # write json
    logging.info(d)
    data["d3"] = d

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
                if data == el["specs"][0]:
                    if len(el["specs"]) != 1:
                        if (datetime.now()-el["change_dates"][0]).total_seconds() > 60*60*5:
                            break
                    found = True
                    break
            if found:
                logging.info("Old session")
                session = el["session"]
                el["change_dates"] = []
                el["specs"] = el["specs"][:1]
                mongo.db.spec.replace_one({"session": session}, el, upsert=True)
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
            moment = len(spec["change_dates"])
            mongo.db.spec.replace_one({"session": session}, spec, upsert=True)
    return moment

def remove(session):
    with mongo.cx.start_session() as mongo_session:
        with mongo_session.start_transaction():
            mongo.db.update.remove({"session": session})
            mongo.db.reports.remove({"session": session})
            mongo.db.footprint.remove({"session": session})




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
    updates = clean_results(updates)
    logging.info("clean")
    try:
        reports = search_lasts(reports, updates[0])
        logging.info("search_lasts")
        reports = clean_results(reports)
        logging.info("clean2")
    except:
        return {"Reports":[reports[0]["report"]],"Leaders":None}
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