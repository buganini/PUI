"""Web handshake plus shared browser application message schemas."""
from .._browser.messages import _fields, _require, _text, _number
from .._browser.messages import validate_client_body as validate_application_body


def validate_client_body(kind, body):
    if kind == 'options':
        _fields(body, 'values')
        _require(type(body['values']) is list and all(
            type(pair) is list and len(pair) == 2 and _text(pair[0]) and type(pair[1]) is str
            for pair in body['values']))
    elif kind == 'hello':
        _fields(body, 'client_build capabilities viewport resume_id')
        _require(_text(body['client_build']) and
                 (body['resume_id'] is None or _text(body['resume_id'])))
        caps = body['capabilities']
        _require(type(caps) is list and all(_text(item) for item in caps))
        _require(len(caps) == len(set(caps)))
        viewport = body['viewport']
        _fields(viewport, 'width height dpr')
        _require(_number(viewport['width']) and _number(viewport['height']) and
                 _number(viewport['dpr']) and viewport['dpr'] > 0)
    else:
        validate_application_body(kind, body)
