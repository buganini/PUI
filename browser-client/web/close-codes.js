// Browsers expose connection states, but no WebSocket close-code constants.
// Standard names match aiohttp.WSCloseCode.
export const WSCloseCode=Object.freeze({
  OK:1000,
  GOING_AWAY:1001,
  PROTOCOL_ERROR:1002,
  POLICY_VIOLATION:1008,
  INTERNAL_ERROR:1011,
  TRY_AGAIN_LATER:1013,
});

// Keep private wire values in sync with PUI/web/close_codes.py.
export const AppCloseCode=Object.freeze({
  LOGGED_OUT:4001,
  CLIENT_ERROR:4002,
  SESSION_RENEWED:4003,
  AUTH_EXPIRED:4004,
  SESSION_TAKEN_OVER:4005,
  INPUT_QUEUE_FULL:4008,
});
