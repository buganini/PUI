"""Schemas for client messages supported by the current Web capabilities."""
import math
import re

from .protocol import ProtocolError, SAFE_INTEGER


def _require(condition):
    if not condition:
        raise ProtocolError('INVALID_VALUE', 'Invalid client message body')


def _fields(value, names):
    _require(type(value) is dict and set(value) == set(names.split()))


def _text(value):
    return type(value) is str and bool(value)


def _integer(value, minimum=0):
    return type(value) is int and minimum <= value <= SAFE_INTEGER


def _number(value, minimum=0):
    return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= SAFE_INTEGER


def _pointer(data):
    _fields(data, 'x y button buttons modifiers pointer_id cancelled')
    _require(_number(data['x'], -SAFE_INTEGER) and _number(data['y'], -SAFE_INTEGER) and
             type(data['button']) is int and data['button'] in (0, 1, 2, 4, 8, 16) and
             _integer(data['buttons']) and data['buttons'] <= 31 and
             _integer(data['modifiers']) and data['modifiers'] <= 15 and
             _integer(data['pointer_id']) and type(data['cancelled']) is bool)


def validate_client_body(kind, body):
    """Validate before registration lookup, callback dispatch or render credit."""
    if kind == 'hello':
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
    elif kind == 'event':
        _fields(body, 'node_id event token observed_render_rev data')
        _require(_text(body['node_id']) and _text(body['token']) and
                 _integer(body['observed_render_rev']) and type(body['event']) is str)
        if body['event'] == 'click':
            if body['data']:
                _pointer(body['data'])
            else:
                _fields(body['data'], '')
        elif body['event'] in ('dblclick', 'mousedown', 'mouseup', 'mousemove', 'mouseenter', 'mouseleave'):
            _pointer(body['data'])
        elif body['event'] == 'wheel':
            data = body['data']
            _fields(data, 'x y delta_x delta_y delta_mode modifiers')
            _require(all(_number(data[k], -SAFE_INTEGER) for k in ('x', 'y', 'delta_x', 'delta_y')) and
                     data['delta_mode'] in ('pixel', 'line', 'page') and
                     _integer(data['modifiers']) and data['modifiers'] <= 15)
        elif body['event'] in ('input', 'edit'):
            data = body['data']
            _fields(data, 'value edit_seq composing')
            _require(type(data['value']) is str and _integer(data['edit_seq'], 1) and
                     type(data['composing']) is bool)
        elif body['event'] == 'select':
            _fields(body['data'], 'page_id')
            _require(_text(body['data']['page_id']))
        elif body['event'] == 'toggle':
            _fields(body['data'], 'checked')
            _require(type(body['data']['checked']) is bool)
        elif body['event'] == 'activate':
            _fields(body['data'], '')
        elif body['event'] == 'choose':
            _fields(body['data'], 'item_id')
            _require(_text(body['data']['item_id']))
        else:
            _require(False)
    elif kind == 'binding_write':
        _fields(body, 'node_id role ref slot_token attachment_token observed_render_rev '
                      'observed_value_rev edit_seq phase value')
        _require(all(_text(body[name]) for name in ('node_id', 'role', 'slot_token',
                                                   'attachment_token', 'phase')))
        _require((body['role'], body['phase']) in (('model', 'commit'), ('edit_model', 'input')))
        _require(_integer(body['observed_render_rev']) and
                 _integer(body['observed_value_rev'], 1) and _integer(body['edit_seq'], 1) and
                 type(body['value']) is str)
        ref = body['ref']
        _fields(ref, 'object_id kind key')
        _require(type(ref['object_id']) is str and re.fullmatch(r'[1-9][0-9]*', ref['object_id']))
        _require((ref['kind'] == 'attr' and type(ref['key']) is str) or
                 (ref['kind'] == 'list' and _integer(ref['key'], -SAFE_INTEGER)) or
                 (ref['kind'] == 'dict' and (type(ref['key']) is str or _integer(ref['key'], -SAFE_INTEGER))) or
                 (ref['kind'] == 'value' and ref['key'] is None))
    elif kind == 'measure':
        _fields(body, 'node_id measure_rev width height dpr visible')
        _require(_text(body['node_id']) and _integer(body['measure_rev'], 1) and
                 type(body['visible']) is bool and _number(body['width']) and _number(body['height']) and
                 body['width'] <= 16384 and body['height'] <= 16384 and
                 _number(body['dpr']) and 0 < body['dpr'] <= 8)
        _require(math.ceil(body['width'] * body['dpr']) * math.ceil(body['height'] * body['dpr']) <= 16777216)
    elif kind == 'canvas_ack':
        _fields(body, 'node_id frame_rev measure_rev status')
        _require(_text(body['node_id']) and _integer(body['frame_rev'], 1) and
                 _integer(body['measure_rev'], 1) and
                 body['status'] in ('drawn', 'unchanged', 'hidden', 'stale_measure', 'superseded'))
    elif kind == 'ack':
        _fields(body, 'render_rev applied_rev status')
        _require(_integer(body['render_rev'], 1) and _integer(body['applied_rev']) and
                 body['status'] in ('applied', 'discarded'))
        _require(body['status'] != 'applied' or body['render_rev'] == body['applied_rev'])
    elif kind == 'resync':
        _fields(body, 'last_applied_rev')
        _require(_integer(body['last_applied_rev']))
    elif kind == 'close':
        _fields(body, 'reason')
        _require(type(body['reason']) is str)
    else:
        raise ProtocolError('BAD_FRAME', 'Unsupported client message')
