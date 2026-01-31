from flask import jsonify

def ok(message="OK", data=None, code=200, **extra):
    payload = {"success": True, "message": message, "data": data}
    payload.update(extra)
    return jsonify(payload), code

def fail(message="Bad Request", code=400, errors=None, **extra):
    payload = {"success": False, "message": message}
    if errors is not None:
        payload["errors"] = errors
    payload.update(extra)
    return jsonify(payload), code