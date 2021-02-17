from flask import Blueprint, request, jsonify
from utils.testbed import get_sessions, get_session, save_update, save_report, add_testbed, change_testbed, remove
from utils.accuracy import accuracy
from utils.footprint import save_footprints, compute_footprint

api = Blueprint('api', __name__)

@api.route('/testbed/<int:session>/remove')
def get_convert(session):
    remove(session)
    return jsonify(
        status=True
    )

@api.route('/testbed')
def get_testbeds():
    data = get_sessions()
    return jsonify(
        status=True,
        data=data,
    )

@api.route('/testbed', methods=['POST'])
def post_testbed():
    data = request.get_json(force=True)
    session = add_testbed(data)

    return jsonify(
        status=True,
        message='Saved successfully!',
        session=session
    ), 201

@api.route('/testbed/<int:session>', methods=['POST'])
def put_testbed(session):
    data = request.get_json(force=True)
    change_testbed(session, data)

    return jsonify(
        status=True,
        message='Saved successfully!',
    ), 201

@api.route('/testbed/<int:session>')
def get_testbed(session):
    try:
        data = get_session(session)
    except:
        data = None

    return jsonify(
        status=True,
        data=data,
    )

@api.route('/testbed/<int:session>/accuracy')
def get_accuracy(session):
    data = accuracy(session)

    return jsonify(
        status=True,
        data=data,
    )

@api.route('/testbed/<int:session>/footprint', methods=['GET'])
def get_footprint(session):
    data = compute_footprint(session)    

    return jsonify(
        status=True,
        message='Saved successfully!',
        data=data
    ), 201

@api.route('/testbed/<int:session>/footprint', methods=['POST'])
def post_footprint(session):
    if request.files is None:
        return jsonify(
            status=False,
            message='No files!'
        ), 400
    
    save_footprints(request.files, session)
    for file in request.files:
        print(file, flush=True)

    return jsonify(
        status=True,
        message='Saved successfully!'
    ), 201
    

@api.route('/data', methods=['POST'])
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