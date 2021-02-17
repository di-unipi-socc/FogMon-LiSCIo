from model import mongo, get_leaders, get_lastreports, get_updates, get_spec, get_reports
from bson.son import SON
from bson import json_util
from .spec import associate_spec
import json
import logging

def accuracy(session):
    get_lastreports(session)
    els = stabilities(session)
    accuracies = []
    for ((begin,reports_change), spec) in els:
        # TODO: send also the last report accuracy
        end = begin
        for k,v in reports_change.items():
            logging.info(v)
            date = v["datetime"]
            if date > end:
                end = date
        logging.info(end)
        logging.info(begin)
        logging.info((end-begin).total_seconds())
        # mean for every leader of intra and inter measurements error
        spec = associate_spec(reports_change, spec, session)
        accuracy = {"B": {"intra": {"mean": 0, "num": 0}, "inter": {"mean": 0, "num": 0}}, "L": {"intra": {"mean": 0, "num": 0}, "inter": {"mean": 0, "num": 0}}}
        for k,report in reports_change.items():
            acc = compute_accuracy(report,spec)
            for k,v in accuracy.items():
                for k1,v1 in v.items():
                    v1["mean"] += acc[k][k1]["mean"]*acc[k][k1]["num"]
                    v1["num"] += acc[k][k1]["num"]
        for k,v in accuracy.items():
            for k1,v1 in v.items():
                v1["mean"] /= v1["num"]
        
        accuracy["time"] = (end-begin).total_seconds()
        logging.info(accuracy)
        accuracies.append(accuracy)
    return accuracies

def compute_accuracy(report, spec):
    accuracy = {"B": {"intra": {"mean": 0, "num": 0}, "inter": {"mean": 0, "num": 0}}, "L": {"intra": {"mean": 0, "num": 0}, "inter": {"mean": 0, "num": 0}}}
    leaders = {}

    for node in report["report"]["reports"]:
        src_id = node["source"]["id"]
        ldr_id = node["leader"]
        leaders[src_id] = ldr_id

    snd_id = report["sender"]["id"]
    snd = spec["ids"][snd_id]

    for node in report["report"]["reports"]:
        src_id = node["source"]["id"]
        src = spec["ids"][src_id]
        def test_fun(test, T):
            dst_id = test["target"]["id"]
            dst = spec["ids"][dst_id]
            val = spec["links"][T][src][dst]
            acc = 1-(abs(val-test["mean"]))/val   
            same_leader = leaders[dst_id] == leaders[src_id]
            if test["mean"] == 0:
                logging.info("test: "+T + " " + ("intra" if same_leader else "inter") + " " + ( "same" if snd_id == leaders[src_id] else "diff")+" "+ src+" "+ dst)
                logging.info(val)
                logging.info(test["mean"])
                return      
            if same_leader: # same leader
                accuracy[T]["intra"]["mean"] += acc
                accuracy[T]["intra"]["num"] += 1 
            else: # different leaders
                accuracy[T]["inter"]["mean"] += acc
                accuracy[T]["inter"]["num"] += 1
            
        for test in node["latency"]:
            test_fun(test,"L")
        for test in node["bandwidth"]:
            test_fun(test,"B")
    
    for k,v in accuracy.items():
        for k1,v1 in v.items():
            v1["mean"] /= v1["num"]
    logging.info(accuracy)
    return accuracy

def stabilities(session):
    # for every change in spec search the stability
    spec = get_spec(session)
    begin = None
    ret = []
    if len(spec["change_dates"]) != 0:
        for i in range(len(spec["change_dates"])):
            date = spec["change_dates"][i]
            ret.append((stability(session, begin=begin, end=date)), spec["specs"][i])
            begin = date
    ret.append((stability(session, begin=begin, end=None), spec["specs"][-1]))
    return ret


def stability(session, begin=None, end=None):
    # no change in follower for 3 report (for every leader)
    # maybe no change in 20% measurements?

    updates = get_updates(session, begin=begin, end=end)
    # search last significant report: change!=0
    update = updates[0]
    for up in updates:
        if up["update"]["changes"] != 0:
            update = up
            break
    begin2 = update["datetime"]
    ids = [el["id"] for el in update["update"]["selected"]]
    reports = get_reports(session, ids=ids, begin=begin2, end=end)
    reports_ids = {}
    for id in ids:
        reports_ids[id] = []
    for report in reports:
        id = report["sender"]["id"]
        reports_ids[id].append(report)
    
    # now search from the last the last 3 with no change
    changes = {}
    for id in ids:
        changes[id] = len(reports_ids[id])-1
    for id in ids:
        reportB = None
        for i in range(len(reports_ids[id])):
            reportA = reports_ids[id][i]
            try:
                if change(reportA, reportB):
                    changes[id] = i-1
                    break
            except:
                changes[id] = i-1
                break
            reportB = reportA

    logging.info(changes)

    changes = {k:(0 if v<0 else v) for k,v in changes.items()}
    reports_change = {k:reports_ids[k][v] for k,v in changes.items()}
    begin = begin if begin is not None else updates[-1]["datetime"]
    return (begin,reports_change)

def change(reportA, reportB=None):
    if reportB == None:
        return False
    #logging.info("computing change")

    #stri = json.dumps(reportA, default=json_util.default)
    #logging.info(stri[:500])

    leaders = {}

    for node in reportA["report"]["reports"]:
        src_id = node["source"]["id"]
        ldr_id = node["leader"]
        leaders[src_id] = ldr_id

    leaders2 = {}

    for node in reportB["report"]["reports"]:
        src_id = node["source"]["id"]
        ldr_id = node["leader"]
        leaders2[src_id] = ldr_id

    #logging.info(leaders)
    #logging.info(leaders2)

    for node in reportA["report"]["reports"]:
        src_id = node["source"]["id"]
        ldr_id = node["leader"]
        if leaders[src_id] != ldr_id:
            logging.info("Change "+str(src_id))
            return True

    def build_data(data, report):
        for node1,leader1 in leaders.items():
            data[node1] = {}
            for node2,leader2 in leaders.items():
                data[node1][node2] = {}

        # for every link check diff
        for nodeA in report["report"]["reports"]:
            id1 = nodeA["source"]["id"]
            for test in nodeA["latency"]:
                id2 = test["target"]["id"]
                data[id1][id2]["L"] = test["mean"]
            for test in nodeA["bandwidth"]:
                id2 = test["target"]["id"]
                data[id1][id2]["B"] = test["mean"]

    dataA = {}
    dataB = {}
    build_data(dataA, reportA)
    build_data(dataB, reportB)
    try:
        for node1,leader1 in leaders.items():
            for node2,leader2 in leaders.items():
                for k in dataA[node1][node2]:
                    valA = dataA[node1][node2][k]
                    valB = dataB[node1][node2][k]
                    if valB == 0:
                        if valA != 0:
                            diff = 1
                        elif valA == 0:
                            diff = 0
                    else:
                        diff = abs(valA - valB)/valB
                    if diff > 0.2:
                        logging.info("Change diff "+str(diff) +" "+k)
                        return True
    except:
        logging.info(dataA)
        logging.info(dataB)
        raise
    return False