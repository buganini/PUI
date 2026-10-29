"""Web handshake plus shared browser application message schemas."""
from .._browser.messages import _fields, _require, _text, _number
from .._browser.messages import validate_client_body as validate_application_body


def validate_client_body(kind, body):
    if kind == 'dialog_result':
        _fields(body, 'request_id value')
        _require(_text(body['request_id']) and
                 (body['value'] is None or type(body['value']) in (str, bool) or
                  type(body['value']) is dict))
        if type(body['value']) is dict:
            _fields(body['value'], 'action value name' if 'name' in body['value'] else 'action value')
            if 'name' in body['value']:
                _require(body['value']['action'] in ('browse', 'page') and
                         type(body['value']['name']) is str and len(body['value']['name']) <= 32768)
            _require(body['value']['action'] in ('download', 'save', 'browse', 'page', 'confirm') and
                     type(body['value']['value']) is str and len(body['value']['value']) <= 32768)
    elif kind == 'options':
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
