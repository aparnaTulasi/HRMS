import uuid
from flask import g, request

def attach_request_id():
    g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

def get_request_id():
    return getattr(g, "request_id", None)