"""PUI private WebSocket close codes; standard codes use aiohttp.WSCloseCode.

Keep these wire values in sync with browser-client/web/close-codes.js.
"""
from enum import IntEnum


class AppCloseCode(IntEnum):
    LOGGED_OUT = 4001
    CLIENT_ERROR = 4002
    SESSION_RENEWED = 4003
    AUTH_EXPIRED = 4004
    SESSION_TAKEN_OVER = 4005
    INPUT_QUEUE_FULL = 4008
