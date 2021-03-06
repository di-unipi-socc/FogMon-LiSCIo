from model import mongo, get_leaders, get_lastreports, get_updates, get_spec, get_reports
from bson.son import SON
from bson import json_util
from .spec import associate_spec
import json
import logging

def accuracy(session):
    # get_lastreports(session)
    els = stabilities(session)
    accuracies = []
    for ((begin,end,reports_change,changes), spec) in els:
        # TODO: send also the last report accuracy
        logging.info(((begin,end,changes)))
        logging.info(begin)
        logging.info(end)
        # mean for every leader of intra and inter measurements error
        spec = associate_spec(reports_change, spec, session)
        accuracy = {"B": {"intra": {"mean": 0, "num": 0}, "inter": {"mean": 0, "num": 0}}, "L": {"intra": {"mean": 0, "num": 0}, "inter": {"mean": 0, "num": 0}}}
        acc2 = compute_accuracy2([report for k,report in reports_change.items()],spec)
        logging.info(acc2)
        notExisting = []
        for k,report in reports_change.items():
            baseErrors(report,spec)
            acc = compute_accuracy(report,spec)
            if acc is None:
                notExisting.append(report["sender"]["id"])
                continue
            logging.info(acc)
            for k,v in accuracy.items():
                for k1,v1 in v.items():
                    v1["mean"] += acc[k][k1]["mean"]*acc[k][k1]["num"]
                    v1["num"] += acc[k][k1]["num"]
        for k,v in accuracy.items():
            for k1,v1 in v.items():
                v1["mean"] /= v1["num"]
        stable = min([v for k,v in changes.items() if k not in notExisting])
        
        if end is None:
            accuracy["time"] = 0
            accuracy["stable"] = f"Empty"
        else:
            accuracy["stable"] = f"{stable>=10} ({stable})"
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
    try:
        snd = spec["ids"][snd_id]
    except:
        return None

    for node in report["report"]["reports"]:
        src_id = node["source"]["id"]
        src = spec["ids"][src_id]
        def test_fun(test, T):
            dst_id = test["target"]["id"]
            dst = spec["ids"][dst_id]
            val = spec["links"][T][src][dst]
            acc = (abs(val-test["mean"]))/val
            if acc < 0:
                acc = 0
            diff = abs(val-test["mean"])
            diff = diff-1
            if diff < 0:
                diff = 0
            if abs((diff/val) - acc) > 0.1: # minimal differences produces great differences
                # logging.info(f"minimal diff {(diff/val)} {acc} {val}-{test['mean']}")
                acc = diff/val
            same_leader = leaders[dst_id] == leaders[src_id]
            if test["mean"] == 0 and val > 2:
                pass
                # logging.info("test: "+T + " " + ("intra" if same_leader else "inter") + " " + ( "same" if snd_id == leaders[src_id] else "diff")+" "+ src+" "+ dst)
                # logging.info(val)
                # logging.info(test["mean"])   
            if same_leader: # same leader
                if T == "L" and acc>0.2:
                    logging.info(f"{acc} {val} {test['mean']} {src} {dst}")
                if acc > 1:
                    acc = 1
                accuracy[T]["intra"]["mean"] += acc
                accuracy[T]["intra"]["num"] += 1 
            else: # different leaders
                if acc > 1:
                    pass
                    #logging.info(f"high error: {src} {dst} {acc} {val} {test['mean']}")
                accuracy[T]["inter"]["mean"] += acc
                accuracy[T]["inter"]["num"] += 1
            
        for test in node["latency"]:
            test_fun(test,"L")
        for test in node["bandwidth"]:
            test_fun(test,"B")
    
    for k,v in accuracy.items():
        for k1,v1 in v.items():
            v1["mean"] /= v1["num"]
    return accuracy

def compute_accuracy2(reports, spec):
    accuracy = {"B": {"intra": {"mean": 0, "num": 0}, "inter": {"mean": 0, "num": 0}}, "L": {"intra": {"mean": 0, "num": 0}, "inter": {"mean": 0, "num": 0}}}
    leaders = {}

    for report in reports:
        for node in report["report"]["reports"]:
            src_id = node["source"]["id"]
            ldr_id = node["leader"]
            leaders[src_id] = ldr_id

    links = {}
    for T in ["B","L"]:
        links[T] = {}
        for node in leaders:
            links[T][node] = {}
            for node1 in leaders:
                links[T][node][node1] = {"mean":0,"num":0}

    for report in reports:
        for node in report["report"]["reports"]:
            src_id = node["source"]["id"]
            try:
                src = spec["ids"][src_id]
            except:
                # print(f"{src_id} src",flush=True)
                continue
            def test_fun(test, T):
                dst_id = test["target"]["id"]
                try:
                    dst = spec["ids"][dst_id]
                except:
                    # print(f"{dst_id} {T}",flush=True)
                    return
                # if T == "B" and dst == "node8":
                #     logging.info(f"V: {src} {test}")
                if T != "B" or test["mean"]!=0:
                    links[T][src_id][dst_id]["mean"] += test["mean"]
                    links[T][src_id][dst_id]["num"] += 1
            for test in node["latency"]:
                test_fun(test,"L")
            for test in node["bandwidth"]:
                test_fun(test,"B")

    for T in links:
        for src_id in links[T]:
            try:
                src = spec["ids"][src_id]
            except:
                # print(f"{src_id} src",flush=True)
                continue
            for dst_id,v in links[T][src_id].items():
                if src_id == dst_id:
                    continue
                try:
                    dst = spec["ids"][dst_id]
                except:
                    # print(f"{dst_id} {T}",flush=True)
                    continue
                val = spec["links"][T][src][dst]
                if v["mean"] == 0 and val>2:
                    logging.info(f"zero in {T} {src} {dst} {val}")
                else:
                    if v["num"] > 0:
                        v["mean"] /= v["num"]
                    else:
                        logging.info(f"no data in {T} {src} {dst} {val}")            
                same_leader = leaders[dst_id] == leaders[src_id]
                val = spec["links"][T][src][dst]
                if val==0:
                    acc = 0
                else:
                    acc = (abs(val-v["mean"]))/val
                if same_leader: # same leader
                    accuracy[T]["intra"]["mean"] += acc
                    accuracy[T]["intra"]["num"] += 1 
                else: # different leaders
                    accuracy[T]["inter"]["mean"] += acc
                    accuracy[T]["inter"]["num"] += 1
    for k,v in accuracy.items():
        for k1,v1 in v.items():
            v1["mean"] /= v1["num"]
    return accuracy


def stabilities(session):
    # for every change in spec search the stability
    spec = get_spec(session)
    begin = None
    ret = []

    stabs = []
    logging.info(f'{len(spec["change_dates"])}\n\n\n')
    if len(spec["change_dates"]) != 0:
        for i in range(len(spec["change_dates"])):
            date = spec["change_dates"][i]
            try:
                stab = stability(session, spec["specs"][i], begin=begin, end=date)
            except:
                import traceback
                print("1",traceback.format_exc(), flush=True)
                stab = (begin,date,None,None)
            stabs.append(stab)
            begin = date
    try:
        stab = stability(session, spec["specs"][-1], begin=begin, end=None)
    except:
        import traceback
        print("1",traceback.format_exc(), flush=True)
        stab = (begin,None,None,None)
    stabs.append(stab)

    last = None

    for i in range(len(stabs)):
        stab = stabs[i]
        (begin,end,reports_change,changes) = stab
        if reports_change == None:
            ((_,_,reports_change1,changes1),spec1) = last
            stab = ((begin,end,reports_change1,changes1),spec1)
        else:
            stab = (stab,spec["specs"][i])
        ret.append(stab)
        last = stab

    return ret


def stability(session, spec, begin=None, end=None):
    # no change in follower for 3 report (for every leader)
    # maybe no change in 20% measurements?
    updates = get_updates(session, begin=begin, end=end)
    # search last significant report: change!=0
    try:
        update = updates[0]
        for up in updates:
            if up["update"]["changes"] != 0:
                update = up
                break
        begin2 = update["datetime"]
    except:
        updates = get_updates(session, begin=None, end=begin)
        update = updates[0]
        begin2 = begin


    logging.info("stability:")
    logging.info(begin2)
    ids = [el["id"] for el in update["update"]["selected"]]
    reports = get_reports(session, ids=ids, begin=begin2, end=end)
    reports_ids = {}
    for id in ids:
        reports_ids[id] = []
    for report in reports:
        id = report["sender"]["id"]
        reports_ids[id].append(report)

    # rem_ids = []

    # last = begin2

    # for id in ids:
    #     from datetime import datetime
    #     if (reports_ids[id][0]["datetime"]

    # for id in ids:
    #     from datetime import datetime
    #     if (reports_ids[id][0]["datetime"]-) > 200:
    #         rem_ids.append(id)
    # for id in rem_ids:
    #     ids.remove(id)
    #     del reports_ids[id]

    # now search from the last, a no change
    changes = {}
    for id in ids:
        changes[id] = len(reports_ids[id])-1
    for id in ids:
        reportB = None
        spec_ = associate_spec(reports_ids[id], spec, session)
        for i in range(len(reports_ids[id])):
            reportA = reports_ids[id][i]
            try:
                if change1(spec_, reportA, reportB):
                    changes[id] = i-1
                    logging.info(f"break {i-1}")
                    break
            except:
                changes[id] = i-1
                logging.info(f"except {i-1}")
                break
            reportB = reportA

    for id in ids:
        reportA = None
        spec_ = associate_spec(reports_ids[id], spec, session)
        i = 0
        for i in reversed(range(changes[id])):
            logging.info(f"try1 {i}")
            reportB = reports_ids[id][i]
            try:
                if change2(spec_, reportB, reportA):
                    changes[id] = i
                    logging.info(f"break1 {i}")
                    break
            except:
                logging.info(f"except1 {i}")
                break
            reportA = reportB
        changes[id] = i

    logging.info("changes: "+str(changes))

    changes = {k:(0 if v<0 else v) for k,v in changes.items()}
    reports_change = {k:reports_ids[k][0] for k,v in changes.items()}
    begin = begin if begin is not None else updates[-1]["datetime"]
    end = max([reports_ids[k][v]["datetime"] for k,v in changes.items()])
    return (begin,end,reports_change,changes)

def change1(spec, reportA, reportB=None):
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

    for node in leaders:
        if leaders[node] != leaders2[node]:
            logging.info("Change1 "+str(src_id))
            return True

def change2(spec, reportB, reportA=None):
    if reportA == None:
        return False

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
    
    # search if has any empty vals
    for nodeA in reportB["report"]["reports"]:
        src_id = nodeA["source"]["id"]
        if src_id not in spec["spec"]["nodes"]:
            continue
        leaderA = leaders2[src_id]
        def check_empty(test):
            dst_id = test["target"]["id"]
            leaderB = leaders2[dst_id]
            if leaderA == leaderB and test["lasttime"] == 0:
                logging.info(f'zero: {nodeA["source"]["ip"]} {test["target"]["ip"]} {leaderA}')
                logging.info(spec["specs"][0]["nodes"])
                return True
            return False
                
        for test in nodeA["latency"]:
            if check_empty(test):
                return False
        for test in nodeA["bandwidth"]:
            if check_empty(test):
                return False
    return True

    valsA = compute_accuracy(reportA, spec)
    valsB = compute_accuracy(reportB, spec)
    for k,v in valsB.items():
        if k != "B":
            continue
        for k2,v in v.items():
            if k2 != "inter":
                continue
            if v["num"] != valsA[k][k2]["num"]:
                logging.info("Change2")
                return True
            diff = (v["mean"]-valsA[k][k2]["mean"])/v["mean"]
            if diff > 0.01: # gain in error
                logging.info("Change3 diff "+str(diff))
                return True

    # def build_data(data, report):
    #     for node1,leader1 in leaders.items():
    #         data[node1] = {}
    #         for node2,leader2 in leaders.items():
    #             data[node1][node2] = {}

    #     # for every link check diff
    #     for nodeA in report["report"]["reports"]:
    #         id1 = nodeA["source"]["id"]
    #         for test in nodeA["latency"]:
    #             id2 = test["target"]["id"]
    #             data[id1][id2]["L"] = test["mean"]
    #         for test in nodeA["bandwidth"]:
    #             id2 = test["target"]["id"]
    #             data[id1][id2]["B"] = test["mean"]

    # dataA = {}
    # dataB = {}
    # build_data(dataA, reportA)
    # build_data(dataB, reportB)
    # try:
    #     for node1,leader1 in leaders.items():
    #         for node2,leader2 in leaders.items():
    #             for k in dataA[node1][node2]:
    #                 valA = dataA[node1][node2][k]
    #                 valB = dataB[node1][node2][k]
    #                 if valB == 0:
    #                     if valA != 0:
    #                         diff = 1
    #                     elif valA == 0:
    #                         diff = 0
    #                 else:
    #                     diff = (valA - valB)/valB
    #                 if leader1 == leader2:
    #                     if diff >= 0.4:
    #                         logging.info("Change4 diff1 "+str(diff) +" "+k)
    #                         return True
    #                 else:
    #                     if diff >= 1:
    #                         logging.info("Change4 diff2 "+str(diff) +" "+k)
    #                         return True
    # except:
    #     logging.info(dataA)
    #     logging.info(dataB)
    #     raise
    return False

def baseErrors(report, spec):
    leaders = {}

    for node in report["report"]["reports"]:
        src_id = node["source"]["id"]
        try:
            src = spec["ids"][src_id]
            leader = spec["ids"][node["leader"]]
            leaders[src] = leader
        except:
            continue
    
    links = {}
    for T in ["B","L"]:
        links[T] = {}
        for nodeA in leaders:
            links[T][nodeA] = {}
            leaderA = leaders[nodeA]
            for nodeB in leaders:
                leaderB = leaders[nodeB]
                same_leader = leaderA == leaderB
                if same_leader:
                    links[T][nodeA][nodeB] = spec["links"][T][nodeA][nodeB]
                else:
                    if nodeA == leaderA and nodeB == leaderB:
                        links[T][nodeA][nodeB] = spec["links"][T][nodeA][nodeB]

    error = {}
    for T in ["B","L","B2","B3"]:
        T2= T
        if T == "B2" or T == "B3":
            T="B"
        error[T2] = {"mean": 0, "num": 0}
        for nodeA in leaders:
            leaderA = leaders[nodeA]
            for nodeB in leaders:
                leaderB = leaders[nodeB]
                same_leader = leaderA == leaderB
                val = spec["links"][T][nodeA][nodeB]
                if not same_leader:
                    if T2 == "B":
                        links[T][nodeA][nodeB] = min(max([v for k,v in links[T][nodeA].items()]),max([v for k,v in links[T][nodeB].items()]))#,links[T][leaderA][leaderB])
                    elif T2 == "B2":
                        links[T][nodeA][nodeB] = min(links[T][leaderA][leaderB],links[T][nodeA][leaderA],links[T][leaderB][nodeB])
                    elif T2 == "B3":
                        links[T][nodeA][nodeB] = min(min(max([v for k,v in links[T][nodeA].items()]),max([v for k,v in links[T][nodeB].items()])),links[T][leaderA][leaderB])
                    else:
                        links[T][nodeA][nodeB] = spec["links"][T][nodeA][leaderA]+spec["links"][T][leaderA][leaderB]+spec["links"][T][leaderB][nodeB]
                    error[T2]["num"] += 1
                    try:
                        error[T2]["mean"] += abs(links[T][nodeA][nodeB]-val)/val
                    except:
                        logging.info(links[T][nodeA][nodeB])
                        logging.info(val)
                        raise
    for T in ["B","L","B2"]:
        error[T]["mean"] /= error[T]["num"]
    logging.info("min error:")
    logging.info(error)
