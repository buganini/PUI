# Web intermediate API proposal

For application startup, deployment and browser widget behavior, see the
[Web backend reference](web-reference.md). This document describes the wire contract.

This is a proposed v1 contract between a Python session worker and the JavaScript
client. The runtime serves the basic cookbook subset with Linux
forkserver workers or spawned workers on macOS/Windows; native validation outside
Linux remains pending.
Unimplemented imperative capabilities remain proposals. Architecture, missing work and unresolved
dependency/platform decisions are tracked in [web-progress.md](web-progress.md).
Examples show decoded MessagePack values using JSON notation; JSON is not the
transport. Implemented messages and remaining proposals are distinguished below.

Python owns State, bindings, callbacks, VDOM construction, render diffing and
painter execution. JavaScript validates and applies those patches, retains native
edit buffers, measures browser elements and replays Canvas commands. Full
snapshots establish or recover the client tree. The HTTP gateway routes each
connection to its dedicated worker; it does not interpret application State or
run application event callbacks. Optional login authentication runs in the gateway.

## 1. Transport and session bootstrap

`Application(title='')` sets the application/page title. `start()` forwards it
to the gateway and worker constructor pipeline as metadata, leaving factory
calls without arguments. A nonempty title appears in the initial HTML and login
page (`Sign in · <title>`); the login form also shows the application title as
its visible heading, falling back to PUI if empty. Titles are escaped in HTML.
An explicit Window.title
overrides the page title in render records, including an empty string to clear
it. Window defaults to title=None, inheriting Application.title or PUI when the
application title is empty. The generic CLI accepts `--title`.
When only the deferred worker class specifies a title, it appears after its
first render; the gateway/login page uses PUI until configured by the launcher.
The login page keeps using the application title. No new
WebSocket field is needed: the resolved title uses the existing Window property.

The listener is configured with `Application.start(bind="127.0.0.1:8000")` or
CLI `--bind`. A bind is `host:port`, `[IPv6]:port`, or a filesystem Unix socket
path (Linux/macOS); it does not define the public URL. The cookbook and Make
default to `localhost:8866`, overridable with `WEB_BIND`. The former separate
host/port arguments and CLI flags are replaced. Unix listeners use a bound socket
without a TCP listener, reject existing filesystem entries, and clean up only
their own socket inode on exit. `socket_mode=None` leaves permissions unchanged;
an explicit integer such as `0o666` applies that mode after binding, before serving
(range `0` through `0o7777`). TCP ignores the option. Directory permissions remain
deployment configuration; a stale socket after forced termination is not removed on startup.
Windows uses TCP; named pipes and native macOS socket validation remain pending.

Proposed endpoints:

| Endpoint | Role |
| --- | --- |
| `GET /` | Serve the login form when auth is required, otherwise the client entry page |
| `POST /pui/login` | Verify optional auth and issue a signed browser-session cookie |
| `POST /pui/logout` | Revoke the browser owner, stop its workers, clear cookies and return to the entry URL |
| `GET /assets/<build>/<file>` | Serve packaged, versioned JS/CSS/codec assets |
| `GET /pui/images/<resource_id>?mtime=<mtime_ns>` | Serve a registered image file unchanged using normal HTTP caching |
| `GET /pui/ws` with WebSocket upgrade | Open one client session and its worker |

These endpoint paths are relative to the configured public `base_url`, default
`"/"`. Accept a root-relative prefix such as `"/tools/pui/"` or an absolute
HTTP(S) URL such as `"https://example.com/tools/pui/"`; normalize a trailing slash.
Keep the upstream `mount_path` separate: its default is the public path, while
`mount_path="/"` allows a proxy to strip that prefix before forwarding requests.
The entry page, redirects, assets and WebSocket must use the same public base.

`Application.start(auth=None)` leaves access open. With a callable,
`auth(username, password)` must return exactly `True` before issuing `pui_owner`.
Synchronous callbacks run in a gateway thread; async results are awaited. No
callback or credentials cross worker IPC. The cookie is a signed opaque token
(no username/password), HttpOnly, SameSite=Lax and Secure under HTTPS, with the
public base path and no persistent expiry. Its signing key lives in the gateway;
a restart invalidates existing login cookies. Resumption, renewal, new tabs and
worker expiry/crashes keep login authorization. Logout revokes it.

Optional `auth_prompt=''` supplies plain text below the login title, with HTML
escaped and line breaks preserved. `None` or an empty string shows no prompt.
It is rendered in the login HTML, including failed attempts, and has no effect
when `auth=None`; it is not part of the WebSocket protocol. The cookbook sets
`auth_prompt="test/test123"`.

The entry page does not issue an owner cookie before authentication. It issues
`pui_login`, a separately signed form token, and embeds its random token in a
hidden field. Login POST accepts only URL-encoded username/password/csrf fields
without duplicates, with an 8 KiB body limit, requires the matching signed form
cookie and rejects a supplied foreign Origin. Success rotates to a fresh owner
token, clears the form cookie, and redirects to the configured public base URL.
Failure shows a generic message without echoing credentials; callback exceptions
deny access without logging their text. The form works without JavaScript.
Packaged static assets are public; WebSocket and registered image access require
the authenticated owner cookie. With `auth=None`, the original anonymous owner
cookie bootstrap remains in place and the login POST endpoint returns 404.

Application and login HTML responses include
`Content-Security-Policy: frame-ancestors 'none'` and `X-Frame-Options: DENY`,
including anonymous entry and failed sign-in pages. Both same-origin and
cross-origin framing are forbidden; the application runs in a top-level page.

Anonymous owner records without workers use a 1,024-entry LRU, refreshed by
valid cookie lookups. Starting worker reservations, live workers and retained
workers pin their owners outside that idle-owner budget. After the final worker
is reaped, its anonymous owner becomes eligible for eviction again. Eviction
invalidates the old cookie; GET of the entry URL creates a fresh anonymous owner.
Authenticated owners are not evicted. Login form CSRF tokens are signed cookies
and do not allocate owner records.

Renew session submits a native form to `POST /pui/renew`, after discarding its
per-tab resume ID and pending input. Entry HTML supplies the renew URL and an
owner-bound HMAC token with a separate renew purpose. The endpoint accepts only
URL-encoded `csrf` and `resume_id` fields without duplicates, limits the body to
1 KiB and rejects supplied foreign/duplicate Origin headers. GET is unsupported.
A valid owner cookie and matching CSRF token are required; another owner's
session cannot be renewed. The selected session is removed under the registry
lock, then its worker is reaped outside the lock before redirecting to the entry
URL with no-store. This releases capacity even with TTL 0. Concurrent duplicate
requests await the same reaper; expired or already-removed IDs are harmless.
The response preserves cookies and authorization, and other session IDs remain
alive. An attached connection for the selected ID receives close code 4003
(Session renewed), clears its UI/resume ID and offers a Continue link.

Logout submits a native form to `POST /pui/logout`, after discarding its
per-tab resume ID and pending input. Entry HTML supplies the logout URL and an
HMAC token bound to the owner under a separate logout purpose. The endpoint
requires that token in a single `csrf` field, accepts URL-encoded forms up to
1 KiB, and rejects supplied foreign/duplicate Origin headers. GET is unsupported.
Without an owner cookie, POST simply clears cookies and returns to the entry URL.
The gateway tracks valid owner tokens; logout removes the owner before releasing
its worker reservations, preventing cookie replay and late hello admission.
All workers for that owner are reaped, including attached tabs and TTL 0 workers;
other owners remain unaffected. Active sockets receive close code 4001 (Logged
out), clear their UI/resume ID and offer a Continue link. Images and subsequent
WebSockets reject revoked cookies. The logout response deletes `pui_owner` and
`pui_login` at the public base path and redirects to the entry URL with no-store.
With auth, another login is required; anonymous apps obtain a fresh owner cookie
and worker. Logout revocation is independent of disconnected-worker TTL.

| Configuration | Public WebSocket | Upstream WebSocket route |
| --- | --- | --- |
| `base_url="/tools/pui/"` | `/tools/pui/pui/ws` | `/tools/pui/pui/ws` |
| `base_url="/tools/pui/", mount_path="/"` | `/tools/pui/pui/ws` | `/pui/ws` |
| `base_url="https://example.com/tools/pui/", mount_path="/"` | `wss://example.com/tools/pui/pui/ws` | `/pui/ws` |

The dependency-free [WebURLs helper](../PUI/web/urls.py) implements this mapping.
`public(endpoint)`, `route(endpoint)`, `asset(build, filename)` and `websocket()`
retain the prefix and reject ambiguous paths, queries/fragments and credentials.
The image route appends its generated `mtime` query after mapping the
resource path; user-supplied queries remain invalid in `base_url`/`mount_path`.
Root-relative WebSocket paths resolve against the browser page's origin, using
`wss:` for HTTPS and `ws:` for HTTP; never derive a public URL from the worker's
listening address. Explicit absolute URLs use their configured public origin.
Do not trust arbitrary forwarding headers or inject a global HTML `<base>` that
changes application HTML/link semantics. The aiohttp gateway uses this mapping for entry redirects, assets and WebSocket.
Prefix-preserving HTTPS/WSS through a TLS-terminating nginx proxy is tested in
Chrome. An isolated nginx prefix-stripping deployment also passes the Chrome
cookbook suite, including assets, edits, cookie-owned resumption and tab isolation;
Safari/Firefox still need browser validation.

For TLS termination with an HTTP upstream, preserve the public Host (including
any public port) and overwrite `X-Forwarded-Proto` with one `http` or `https`
value. `trusted_proxies=None` trusts immediate socket peers in `127.0.0.0/8`
and `::1/128`, plus connections whose transport socket family is AF_UNIX.
A string or list of IP addresses/CIDRs and the literal `"unix"` replaces those
defaults; `[]` disables all trust. `"unix"` does not trust any TCP peer.
Never derive trust from forwarded client addresses.
For trusted peers, apply the forwarded scheme before cookie creation and Origin
validation; malformed, duplicate or comma-separated values return HTTP 400.
For other peers, ignore the header. Do not interpret `X-Forwarded-Host`,
`X-Forwarded-For`, `X-Real-IP` or the standard `Forwarded` header.
Use repeatable CLI `--trusted-proxy` or Make's space-separated
`WEB_TRUSTED_PROXIES`; `--no-trusted-proxy` or an empty Make value disables trust.
A path-only `base_url` therefore works over direct HTTP and trusted HTTPS proxy
connections. HTTPS sets Secure cookies; the browser selects WSS for relative
endpoints. An explicit absolute `base_url` still determines the public Origin
and endpoint scheme; an HTTPS base also sets Secure cookies independently of
forwarded headers.

`allow_hosts` is a separate HTTP Host policy. Its default `None` is equivalent to
`["*"]`, accepting any valid Host. An explicit list matches exact host names,
case-insensitively and without request ports; IPv6 uses brackets. Entries have no
scheme/path/port, partial wildcards are unsupported, and an empty list denies all
hosts. Validate this policy before every route, including assets and WebSocket
upgrades; do not use untrusted forwarding headers to bypass it. Use repeatable
CLI `--allow-host` or Make's space-separated `WEB_ALLOW_HOSTS`.
Independently require the WebSocket Origin to equal the configured public origin
(or the request scheme/Host with a path-only base). `allow_hosts=["*"]` does not
disable that comparison.

Use WebSocket subprotocol `pui.v1.msgpack.zstd-stream`. The envelope schema
remains v1; the distinct subprotocol prevents old clients interpreting the new
framing. Set browser `binaryType` to `"arraybuffer"`. Disable
`permessage-deflate` for this channel. Load codecs before connecting; no CDN,
base64 wrapping or alternative JSON transport is used.

Server-to-browser messages share one open Zstandard frame per connection:

```text
zstd stream(MessagePack ready | MessagePack render | MessagePack result | ...)
                              ^ flush after each complete envelope
```

Python `StreamCodec` uses level 3, a 4 MiB history window (`window_log=22`) and
`COMPRESSOBJ_FLUSH_BLOCK`. The decoder's maximum accepted window remains 16 MiB.
Each binary WebSocket message carries the bytes produced for exactly one complete
envelope, ending on a zstd block boundary. A render envelope includes its entire DOM patch
or snapshot and all included Canvas display lists. Do not flush per operation,
widget or drawing command. Other server messages flush at their own envelope
boundary so acknowledgements and errors cannot wait for a future render.
Flush makes that batch immediately decodable without ending the zstd frame;
subsequent messages can refer to compression history. The first packet includes
the frame header; subsequent packets contain only complete non-final blocks.
The stream header has a bounded window and no dictionary, content size or
checksum. It is never finalized/reused across connections. Packet completeness
comes from WebSocket boundaries, block preflight and one exact MessagePack
value; there is no per-message zstd checksum on this direction.

The browser's bundled `compress-utils` 0.10.1 WASM decoder retains history per connection,
collects a bounded complete envelope and only then dispatches it. It validates
the header/window and block boundaries before decoding, rejects ended/restarted
frames and checks accumulated output before retaining it. Partial blocks,
trailing MessagePack values or a decode failure terminate that connection;
a failed decoder is closed and cannot be reused. On detach/reconnect, discard
both compression contexts even when the application worker resumes. Retries
must re-encode the retained render body with a new message sequence through the
current compressor; never replay previously compressed packets or drop one
packet and continue decoding later packets. DOM and Canvas ACK policies remain
independent and unchanged.

Browser-to-server messages, including `hello`, retain the existing independent
framing through `compress-utils` level 1 (native Zstandard level 2) and Python `Codec`:

```text
Zstandard frame(MessagePack envelope)
```

Each upstream frame declares its content size. Reject dictionaries,
concatenated/skippable frames and trailing data. Private gateway control packets
also use this independent format; the gateway does not decompress downstream
render traffic. Compression history is never shared across clients.

The Python codecs implement framing, value/envelope validation and configurable
`Limits`. Defaults are 8 MiB compressed and 32 MiB decoded per complete message,
a 16 MiB maximum window, 5,000,000 value/key items and nesting depth 64. Totals do
not accumulate across the lifetime of the connection. Item counts include
containers, map keys and values; retained render states use the same budget.
Count/depth errors identify the specific limit and first excess value. Stream
blocks are bounded to 128 KiB (or the window if smaller); decoded output is
checked incrementally. Both browser decoding paths scan MessagePack for UTF-8,
duplicate keys, depth/items and extensions before decoding. Number-range checks
remain strict for upstream packets and non-render downstream messages; render
numbers reach the native drawing/property handlers.
Python also bounds container lengths and validates the decoded envelope. When
encoding its own render output, it checks the envelope and serialized/compressed
byte lengths only; MessagePack itself rejects unserializable Python values.
There is no recursive pre-pack type/range or item/depth scan for render output.
The receiving decoder and reconstructed browser state enforce those budgets.
The map key `__proto__` is rejected in both languages. Shared fixtures cover
malformed independent frames and streamed batches, missing history, ended or
truncated streams, window/output limits and the five-million-item boundary. Tested
Python dependency versions are pinned in `tests/requirements-web.txt`.

1. The entry page (or successful login when auth is configured) establishes an opaque, server-issued HttpOnly, SameSite cookie
   scoped to the public base path (Secure for HTTPS). This identifies the browser
   owner; a separate opaque per-tab session ID selects its worker. Neither value
   is a State ID. Validate cookie ownership on every WebSocket attachment.
2. Client sends `hello` with sequence 1 and `session: null`, including its optional
   `resume_id`. Reject a second active connection for the same retained session;
   do not let it steal the first connection. New tabs create separate sessions.
   Before opening the socket, a browser with a saved per-tab ID asks the user to
   Resume session (send that ID) or Renew session (reset that worker via HTTP).
   Authenticated apps also offer Logout (revoke the owner via HTTP). This
   applies on reload and recoverable connection loss; first visits connect directly.
   The old UI stays inert until a snapshot applies. Failed attempts retry the
   chosen option; a later established-connection loss asks again. An active-ID
   conflict allows retrying resume or explicitly renewing the selected session,
   ending its previous connection and worker instead of taking over that connection.
3. After admission/capacity checks, the worker responds with `ready`, sequence 1,
   a fresh connection epoch and its `resume_id`. A retained worker keeps its
   Python State but resets connection sequence/revision tracking and publishes
   a complete snapshot. Old connection epochs/actions are never replayed.
   With the `state.refs` capability, the next client message must be `options`,
   within 10 seconds. The worker fills `PUI.Options` before application import,
   construction and first sync; resume updates Options without rebuilding the app
   or applying inputs to existing State. Clients without this capability start
   with empty Options and do not receive State ref batches. A private worker IPC
   `S\0` packet signals completed initialization; the gateway's startup watchdog
   remains active across `ready` and Options until that signal arrives, including
   when application initialization blocks the worker event loop.
4. A disconnected worker is retained for `session_ttl` seconds, **900 by default**.
   Start the monotonic deadline at disconnect, cancel it on successful reattach,
   and clean up at expiry. `session_ttl=0` retains disconnected workers indefinitely
   (no deadline or periodic expiry task); it replaces the former immediate-expiry
   meaning of zero. Such workers still count toward `max_sessions`. Connected workers
   do not expire through this TTL. Explicit quit/server shutdown/crash ends the
   session immediately. A missing/expired resume ID creates a fresh session with
   `resumed: false`, so the client can visibly report the reset.
   Renew session destroys the selected worker regardless of TTL, keeps the owner
   cookie/login and starts without the old resume ID. Logout destroys every worker
   for the browser owner and requires another login. The choice banner explains
   renewal, logout when available, expiry fallback and discarded unsent edits/pending
   actions. Neither action adds WebSocket message fields.
5. Pause browser-dependent painting while detached; bound retained resources and
   the total number of active plus retained workers. A full retained capacity
   rejects new sessions rather than silently evicting unexpired workers.

The internal `SessionRegistry(session_ttl=900, max_sessions=64)` implements
ownership, connection epochs, capacity and monotonic disconnect deadlines.
`expire()` returns removed reservations for the gateway to stop/reap; expired
workers count toward capacity until collected. It owns no threads or processes.
The gateway implements cookie verification, reattachment, expiry and worker
teardown. A standard-library forkserver with no preloaded modules provides the
clean Linux supervisor. macOS and Windows use a standard-library spawn context
instead, starting a fresh interpreter for each worker. Both paths use socket-pair
IPC and preserve per-session process isolation without changing the global
multiprocessing start method. Application modules must be safe to import again,
with server launch calls inside an `if __name__ == "__main__":` guard.
On reconnect, discard uncertain outgoing actions and local
input queues; do not replay clicks, commits or other callbacks automatically.

The first worker response has a 30-second startup deadline. Constructor failure,
startup cancellation, crash or timeout releases the session and reaps its process.
IPC drain waits are bounded at 30 seconds and occur outside the shared admission
lock. A blocked session therefore does not hold up admission or actions for other
clients. Overloaded IPC closes that session explicitly.
Shutdown bounds pending IPC flushes, then gives the process a short graceful exit,
escalating to terminate/kill and joining it before releasing process descriptors.
Reaping is shared by concurrent cleanup paths and continues if a caller is
cancelled. Workers being reaped still count toward admission capacity.

Only the worker produces the ordered server message stream after handoff.
The gateway forwards bytes unchanged; a worker crash closes its WebSocket.
Bootstrap rejection before handoff uses HTTP/WebSocket failure, not a competing
producer of server sequence numbers. A session epoch routes messages; it is not
an authentication credential or a UUID stored on State.

`hello.body` contains `client_build`, `capabilities` (string array),
`viewport: {width, height, dpr}`, and `resume_id` (string or null).
`ready.body` contains `server_build`, the accepted `capabilities`, concrete
`limits`, `resume_id`, `resumed` (boolean), and `session_ttl` (seconds; zero means
no disconnect expiry). The current required capabilities are `render.snapshot`, `render.patch` and
`binding.object_id`. Canvas additionally advertises `canvas.geometry`,
`canvas.text`, `canvas.path` and `canvas.input`.
Missing required capabilities or incompatible versions fail startup. Additional
components/opcodes are usable only when advertised by both sides.

## 2. Envelope, types and ordering

Every message has the same required envelope:

```json
{
  "v": 1,
  "type": "event",
  "session": "session-example",
  "seq": 9,
  "body": {
    "node_id": "n4",
    "event": "click",
    "token": "t9",
    "observed_render_rev": 3,
    "data": {}
  }
}
```

| Field/type | Rule |
| --- | --- |
| `v` | Protocol major version; initially integer 1 |
| `type` | One of the message names below |
| `session` | Current epoch string; null only in client hello |
| `seq` | Positive safe integer, increasing by one separately in each direction; assign only when a message is sent |
| `body` | Message-specific map with string field names |
| `rev` / `value_rev` / `frame_rev` | Monotonic safe integers scoped to the render stream, binding registration, or Canvas respectively |
| `base_rev` | Required client render revision for a patch; null for a full snapshot |
| `processed_seq` | Highest client sequence fully processed by the worker when the target render state was built |
| Object ID | Decimal string containing the server's `id(obj)` exactly |
| Node/resource/token ID | Opaque session-local strings; separate namespaces from object IDs |
| Data value | Null, boolean, UTF-8 string, finite number, binary, array, or string-keyed map of data values |

Use exact integers only within `-(2^53-1)` through `2^53-1`. Object IDs use
strings regardless of their current size. Larger application integers and other
Python types require explicit future representations; do not silently round or
stringify them. v1 rejects MessagePack extensions, invalid UTF-8, duplicate map
keys and unknown protocol message types/fields. Upstream and non-render messages
also reject non-finite numbers and unsafe integers. Downstream render payloads
allow serializable numeric arguments through to Canvas 2D (large integers may lose
JavaScript precision); sequence/revision and widget-specific schemas still apply.
Unknown Canvas opcodes are drawing errors: log and skip them without executing code.

Decode and dispatch sequentially even if decompression is asynchronous. Check
session/version/sequence before side effects. Duplicate or out-of-order sequence
numbers are protocol errors and must never execute callbacks twice. Reliable
WebSocket ordering does not imply durable execution after a connection fails;
there is no cross-session action replay or exactly-once persistence guarantee.

`seq` orders transmissions; render `rev` identifies a target render state;
`processed_seq` tells the client which inputs that state reflects. These are
distinct counters. Render revisions can skip when unsent states are superseded.
A render retry uses a new envelope `seq` but the same immutable body and
`(session, rev)`. Do not reuse an envelope sequence to retransmit a render or
relabel an old action with a new sequence to retry its callback. Render
deduplication does not provide idempotency for application side effects.

## 3. Messages

All fields listed under body are required unless explicitly marked optional.

| Type | Direction | Body and purpose |
| --- | --- | --- |
| `hello` | Client to worker | Client build, capabilities, viewport; see bootstrap |
| `ready` | Worker to client | Server build, accepted capabilities, limits |
| `options` | Client to worker | `values`: ordered `[name, text]` pairs of URL-decoded strings; once after `ready` when `state.refs` is advertised |
| `state_ref` | Worker to client | `values`: current named State subscriptions as `[name, JSON_text]` pairs; after sync when changed, and on every connection |
| `render` | Worker to client | `mode`, `base_rev`, `rev`, `processed_seq`; snapshot or patch payload defined in section 4 |
| `event` | Client to worker | `node_id`, `event`, `token`, `observed_render_rev`, `data` |
| `binding_write` | Client to worker | Binding edit and origin; see section 5 |
| `result` | Worker to client | `reply_to` (client seq), `status`, `code` (string or null); action outcome |
| `measure` | Client to worker | `node_id`, `measure_rev`, `width`, `height`, `dpr`, `visible`; Canvas geometry |
| `ack` | Client to worker | `render_rev`, `applied_rev`, `status` (`applied` or `discarded`); DOM/draft application, see section 8 |
| `canvas_ack` | Client to worker | `node_id`, `frame_rev`, `measure_rev`, `status`; independent Canvas presentation result, see section 7 |
| `resync` | Client to worker | `last_applied_rev`; request a current full snapshot including image URL references |
| `error` | Either | `code`, `reply_to` (seq or null), `fatal`, `message`; diagnostic |
| `close` | Either | `reason`; graceful session termination, followed by WebSocket close |

`options` values are plain strings: neither browser nor worker parses them as
JSON or converts their types. Applications choose how to parse and validate them.
`state_ref` values are JSON text on the wire; the browser writes string values
without JSON quotes and other values as JSON text in the URL. Names are nonempty
strings; duplicate names use the last value. Existing message limits apply,
and non-string option values fail schema validation.
Other messages before the required `options`, or repeated
`options` after initialization, fail the connection. Options does not dispatch
binding writes. State refs only publish values declared in `content()` and are
stored independently of node refs. These messages use ordinary epoch/sequence
checks but have no render revision or ACK; a new connection resends current
subscriptions. The browser compares URL-decoded text before merging changed entries
and calls `replaceState` once per changed batch; absent names leave the URL alone.
See [URL Options and State refs](web-reference.md#url-options-and-state-refs).

`event` and `binding_write` each produce one `result`. Status is `processed`,
`stale`, `invalid`, or `error`. `processed` means the registered handler/setter
ran; it does not mean a requested value was accepted or a browser frame was
drawn. The following render carries the authoritative result. Do not send
results for results, render acknowledgements or ordinary measurements.

A setter/callback exception can occur after application side effects. Return an
error outcome without automatic retry or a claim of rollback. If the worker
cannot produce a coherent next render state, end the session explicitly.

The implemented client-message schemas validate hello/viewport, click/input,
native control events, TextField writes, ACK, resync and close before dispatch. Invalid actions return
`invalid` plus an authoritative render without calling setters/callbacks; malformed
bootstrap/control messages close the connection. Future observed revisions are
rejected, while older value revisions remain valid for a live attachment.
Input callbacks deduplicate `edit_seq` per active event registration; writes
deduplicate per attachment/phase. Both counters are scoped to the connection
epoch: reconnect clears them because browser drafts restart their edit sequences,
even when worker State, nodes and binding attachments survive. Repeated edits
within the new epoch are still rejected. Browser ready/result/error/close and render
metadata are validated before changing session, action credit or DOM state.
Unsolicited results and confirmations of unsent client sequences are rejected.
Canvas measure and canvas_ack bodies are validated before changing drawing credit;
image URL/transform schemas are validated before drawing. Image bytes use HTTP, with no
separate WebSocket resource-transfer or cache-release messages.

## 4. Render states, patches and identity

The following definitions describe data shapes, not exported TypeScript APIs:

```typescript
type BindingRef = {
  object_id: string;
  kind: "attr" | "list" | "dict" | "value";
  key: string | number | null;
};
type Slot = {
  ref: BindingRef;
  token: string;
  value_rev: number;
  value: DataValue;
};
type Attachment = {
  ref: BindingRef;
  slot_token: string;
  token: string;
  writable: boolean;
};
type Node = {
  id: string;
  type: string;
  props: Record<string, DataValue>;
  layout: Record<string, DataValue>;
  style: Record<string, DataValue>;
  bindings: Record<string, Attachment>;
  events: Record<string, string>;
  children: Node[];
};
```

`DataValue` is the recursive data-value subset defined in section 2. An `attr`
key is a string, a `list` key an integer, a `dict` key a string or safe integer,
and a `value` key null. Key types are preserved; dictionary key `1` differs from
`"1"`. Other key types are explicitly unsupported until a representation is agreed.

A full render state consists of `roots`, `bindings` and `canvases`. `roots`
initially contains exactly one Window/page tree. `bindings` contains one Slot
per exposed source/registration, deduplicated across controls. `canvases`
contains the current full display list for every measured, ready Canvas. An
unmeasured Canvas has a node but no frame yet. Python retains the acknowledged
state as the base for calculating the next patch.

The `render.body` variants are:

| Mode | Required fields besides `mode`, `rev`, `processed_seq` | Use |
| --- | --- | --- |
| `snapshot` | `base_rev: null`, `roots`, `bindings`, `canvases` | Initial load or explicit recovery; fully describes the target state |
| `patch` | `base_rev`, `ops` | Normal update from that exact acknowledged revision; omitted records remain unchanged |

A snapshot has no `ops`; a patch has no top-level `roots`, `bindings` or
`canvases`. Both variants include a new revision and `processed_seq`, even when
the render data is unchanged. In particular, an empty `ops` list can confirm an
edit whose setter rejected or normalized the value back to the previous value.
The client must retain canonical records and reconcile pending drafts when the
watermark advances, even without a TextField property or Slot update.

Patch operations use stable IDs and absolute values. Individual operations need
not be idempotent; section 8 deduplicates the entire batch before any effects.

| Opcode | Required fields besides `op` | Effect |
| --- | --- | --- |
| `create_node` | `node` | Create a fresh detached node record; its `children` must be empty |
| `patch_node` | `node_id`, `field`, `set`, `unset` | Set named entries and remove named overrides from one map field |
| `place_node` | `node_id`, `parent_id`, `before_id` | Insert or move the existing node immediately before a sibling, or append when `before_id` is null |
| `remove_node` | `node_id` | Remove this node and its current descendants, listeners, Attachments and Canvas records |
| `put_binding` | `slot` | Insert or replace a complete Slot, keyed by its registration `token` |
| `remove_binding` | `slot_token` | Remove an unreferenced Slot registration |
| `put_canvas` | `frame` | Insert or replace one complete Canvas display list, keyed by `node_id` |
| `patch_canvas` | `base_frame_rev`, `start`, `delete_count`, `frame` | Replace one command interval of the retained Canvas frame; `frame.commands` contains only inserted commands, while its other fields describe the resulting frame |
| `remove_canvas` | `node_id` | Clear the retained frame and displayed bitmap of a surviving Canvas |

`patch_node.field` is one of `props`, `layout`, `style`, `bindings` or `events`.
`set` is a map of entries with the corresponding field's types; `unset` is an
array of distinct entry names, disjoint from `set`. Removing an override restores
its default/inherited behavior. Neither node ID/type nor children can be patched
this way. `place_node.parent_id: null` addresses the root list; otherwise it must
name a container. A non-null `before_id` must name another child of that parent.
Validate existence, placement order, no cycles and final single-root ownership.
Move retained descendants out before removing an obsolete ancestor. New nodes
must end up attached; removed IDs cannot be created again in the session.

Validate the full patch against canonical records before touching DOM: structural
operations execute in list order, while the final state must have valid Slot,
Attachment and Canvas references and no orphaned registrations. Slot changes
cannot silently change a registration's source identity. Build operations from
the acknowledged state to the latest desired state, not from the preceding
unacknowledged or discarded intermediate state.

Example patch body, assuming revision 3 contains the TextField shown below and
Slot `t5` with `value: "Alice"` and `value_rev: 2`:

```json
{
  "mode": "patch",
  "base_rev": 3,
  "rev": 4,
  "processed_seq": 9,
  "ops": [
    {"op": "patch_node", "node_id": "n3", "field": "props", "set": {"text": "Bob"}, "unset": []},
    {"op": "put_binding", "slot": {"ref": {"object_id": "140000000000000", "kind": "attr", "key": "name"}, "token": "t5", "value_rev": 3, "value": "Bob"}}
  ]
}
```

Current node types are Window, VBox, HBox, Stack, Grid, Label, Button, TextField, MaskedField, Text,
ProgressBar, Spacer, Divider, Scroll, Views, Tabs, Tab, Checkbox, RadioButton,
ComboBox, ComboBoxItem, Table, Image and Canvas. Canvas geometry/text/input/images are implemented.
Their supported properties are allowlisted by type. Start with Window `title`,
Label/Button `text`, Button `disabled`, TextField/MaskedField `text`/`placeholder`, Text `text`, Label `selectable`, and Scroll `vertical`/`horizontal`
(`auto`, `scroll`, `hidden`). Canvas background is recorded in its frame. A TextField's `text` is Python's display string; its Slot value
retains the underlying type. Empty property maps are valid for layout nodes.
HBox vertically centers compact or explicitly sized children; VBox horizontally
centers them. Children that expand on the cross axis still fill it when no
explicit cross-axis size is set. Main-axis expansion priorities are unchanged.
Stack places children in one CSS Grid cell; later declarations paint on top.
TimelineView is a server-side virtual node and does not add a wire/DOM node.
Scroll additionally carries nullable `scroll_x`/`scroll_y` requests as
`["start" | "end", nonnegative_offset, request_revision]`. Request revisions
advance for changed declarations and every imperative call. The client preserves
manual offsets for unchanged requests and restores them after layout/resize;
end-relative offsets follow content growth. Positions stay local to the browser.
Scrolling near an edge (10 logical pixels) selects that edge as the retained
anchor when the range exceeds 20 pixels. Removed scrollers disconnect observers.
Views/Tabs carry `selected`, a direct child wire ID or null. Tabs additionally
carry `position` (`n`, `s`, `e`, `w`); each Tab carries a string `label`. Hidden
pages remain mounted. Tabs publish a model Attachment and a `select` token tied
to that model registration. `event: select` has `{page_id}` data; the server
checks the live page/model before applying the shared ID/label selection policy.
The browser never supplies an arbitrary model value for tab selection. Model
rebinding changes the selection token, and removal invalidates the page ID.
ProgressBar has finite nonnegative `progress` and `maximum`; progress is clamped
to the maximum. A zero maximum selects native indeterminate progress.

Layout fields are `width`, `height`, `weight`, `padding` and `margin`; padding
and margin are four-element top/right/bottom/left arrays. Dimensions use logical
CSS pixels. Style fields are `color`, `background`, `font_size_pt`, `font_weight`
and `font_family`. Colors use canonical `#rrggbb`/`#rrggbbaa` strings. Node adapters
normalize existing PUI inputs to these fields. Missing overrides restore
defaults/inheritance; null is accepted only for explicitly nullable fields.
Grid children additionally have zero-based integer `row`/`column`, with optional
positive `rowspan`/`columnspan` defaulting to 1. Positions/spans are bounded to
10000. Grid placement outside a Grid is rejected.

Example node from a snapshot (its matching Slot appears in `body.bindings`):

```json
{
  "id": "n3",
  "type": "TextField",
  "props": {"text": "Alice", "placeholder": "Name"},
  "layout": {"weight": 1},
  "style": {},
  "bindings": {
    "model": {
      "ref": {"object_id": "140000000000000", "kind": "attr", "key": "name"},
      "slot_token": "t5",
      "token": "t7",
      "writable": true
    }
  },
  "events": {},
  "children": []
}
```

Server reconciliation retains a node ID for the same matched PUI node, including
keyed moves and independent subview updates. Duplicate PUI keys still receive
distinct IDs. IDs are not reused during the session; replacing a node's type
creates a new ID. Virtual nodes stay in Python's lifecycle tree and do not
introduce browser layout wrappers.

JS applies the supplied operations without calculating ordinary render diffs.
It keeps canonical server records separate from live browser state such as text
drafts and focus; a `base_rev` check describes those records, not the user's live
DOM property values. Property updates use the editor reconciliation rules in
section 5. During snapshot installation/recovery, validate the complete tree and
reuse matching nodes by ID where safe, removing obsolete nodes/listeners/styles.
A healthy tree must not be rebuilt wholesale on each render. Partial-failure
recovery is an explicit exception described in section 8.
Node `events` maps event names to registration tokens, not Python callable IDs.
Keep a token across redraws while the same registration remains active, and
dispatch to the current Python callback. Removing/re-adding the registration
gets a fresh token; recreating a callback wrapper alone does not invalidate it.

## 5. Binding writes and local drafts

Built-in bindings refer to `str(id(binding.state))` plus kind/key. A retained
internal/custom value binding uses `str(id(binding))` and `kind="value"`.
Do not add UUIDs to shared State or identify a slot by the ID of its current value.

Slot tokens protect source/slot lifetime. Attachment tokens protect the current
node/role-to-slot association. Share a Slot across controls, but revoke only the
removed control's Attachment. Release the Slot/strong owner references after
its last consumer disappears. Rebinding, structural list index shifts and
dictionary slot removal/recreation revoke affected registrations. The implemented
policy revokes every index binding after any list structural operation, including
append/extend, insert/pop/remove, clear/reverse/sort. Ordinary index assignment
retains its registration. Dictionaries track each live key's generation: removal
revokes that key, recreation gets a fresh lifetime, and other keys remain valid.
Generation checks run before writes/input callbacks as well as during snapshots,
including batched State mutations. Input callback tokens change when their editor
binding changes. Container mutations must go through State methods; direct
mutation of the original Python list/dictionary bypasses tracking. A new
registration always has a fresh token even if Python reuses an object ID.

`binding_write.body` example:

```json
{
  "node_id": "n3",
  "role": "model",
  "ref": {"object_id": "140000000000000", "kind": "attr", "key": "name"},
  "slot_token": "t5",
  "attachment_token": "t7",
  "observed_render_rev": 3,
  "observed_value_rev": 2,
  "edit_seq": 4,
  "phase": "commit",
  "value": "Bob"
}
```

The worker verifies session, node, source/role association, both tokens,
editability, phase and payload type. It resolves the actual registered binding;
no arbitrary attribute access or pointer dereference is exposed by an object ID.
For a current live source, apply valid edits in received order. Observed
revisions are not blanket compare-and-swap checks: a client's queued second edit
may legitimately refer to a value revision from before its first edit. Structural
replacement is handled by registration invalidation, not silent retargeting.

MaskedField uses its own wire node type with TextField's properties and binding
roles. The browser creates a native password input; values remain original text
in State, bindings and events. Sizing, drafts and composition handling match TextField.

Preserve TextField/MaskedField's distinction between `model` and `edit_model`:

| User action | Message and worker behavior |
| --- | --- |
| Input with an edit_model | `binding_write`, role `edit_model`, phase `input`: update that binding and invoke the current `.input()` callback once |
| Input without an edit_model | `event: input` when `.input()` is registered; send value/edit_seq/composition status, without writing model |
| Enter/blur commit | `binding_write`, role `model`, phase `commit`: write model, update the current edit_model if present, read back model and invoke `.change()` once |
| Button activation after editing | Enqueue any pending commit before `event: click`; the click callback sees committed server State |

Do not send a second input/change event for an action already represented by a
binding write. Emit `.input()` after committed IME text changes; retain composing
text locally and do not prematurely commit it. Deduplicate native Enter/blur
notifications for the same edit. Input and commit may share an `edit_seq` for
the same draft; deduplicate per phase, not by rejecting its first commit because
that draft already produced an input message. Additional controls need their
own declared role/phase policy; a checkbox action must not blindly overwrite a
list model with a boolean.

Setters and callbacks run serially with PUI's existing conversion/notification
behavior. Always read back after processing, including rejected conversion and
normalization, and schedule a render even for a no-op/rejected edit so the
client receives its final value and input watermark. An empty patch still
advances that watermark and triggers reconciliation against retained values.

The client keeps local `edit_seq`, the pending commit's message/edit sequences,
and editing/composition state per editor. A result for an input event or
edit_model write releases action credit but does not mark the model draft as
committed. While editing, preserve that draft even when a render's canonical
records still contain the old model text. Normalize/end the draft only when
`processed_seq` covers its commit, no newer local draft exists and composition
has ended. Outside editing,
apply authoritative text normally. Replacing its Attachment/Slot cancels the old
draft explicitly. Other controls sharing the Slot update unless they have their
own pending drafts. Programmatic DOM writes never emit input/change events.

Example sequence after render revision 3 is already displayed:

| Direction / seq | Message | Meaning |
| --- | --- | --- |
| Client 8 | `binding_write`, phase `commit` | Commit the TextField draft |
| Server 5 | `result`, reply_to 8 | Setter/change callback processed |
| Client 9 | `event`, click | Invoke the Button callback after the commit |
| Server 6 | `result`, reply_to 9 | Button callback processed |
| Server 7 | `render`, mode patch, base_rev 3, rev 4, processed_seq 9 | Coalesced authoritative UI/binding/Canvas changes |
| Client 10 | `ack`, render_rev 4, applied_rev 4, status applied | Patch applied; return render credit |

Client 9 can already be in transit before Server 5 arrives. Worker ordering,
not a blocking browser round trip between the two actions, enforces commit first.

## 6. Event payloads

The `event` envelope example in section 2 shows a Button click. Events carry only
data; callback arguments/keyword arguments remain registered in Python.

| Event | Data |
| --- | --- |
| Button `click` | Empty map initially; native keyboard activation follows the same path |
| Tabs `select` | `page_id`, a live direct child wire ID |
| Checkbox `toggle` | `checked`, a boolean; Python applies scalar/list/dictionary semantics before `.click()` |
| RadioButton `activate` | Empty map; Python assigns the registered item value before `.click()` |
| Read-only ComboBox `choose` | `item_id`, a live ComboBoxItem wire ID |
| Editable ComboBox `edit` | `value` string, `edit_seq`, `composing`; Enter/blur submission |
| Canvas `click`, `mousedown`, `mouseup`, `mousemove`, `mouseenter`, `mouseleave`, `dblclick` | `x`, `y`, `button`, `buttons`, `modifiers`, `pointer_id`, `cancelled` |
| `wheel` | `x`, `y`, raw `delta_x`, `delta_y`, `delta_mode`, `modifiers` |
| `keypress` | Browser `key`, `code`, `modifiers`, `repeat`, `composing`; PUI key mapping needs per-component validation |
| TextField `input` | `value`, `edit_seq`, `composing` |

Checkbox/RadioButton props are `text`, `checked` and `disabled`, with a `model`
attachment. `disabled=true` disables native user interaction and rejects incoming
actions; model updates still synchronize the checked state.
ComboBox props are `editable`, `disabled`, `selected` (child wire ID or null) and
display `text`; optional attachments are `index_model` and `text_model`. Its only
children are ComboBoxItems with `text` labels. Native select option values use
wire IDs, preserving duplicate labels; registered Python item values are assigned
through existing Binding conversion rather than round-tripping display strings.
Exposed model and option values must still satisfy the protocol data-value domain.

Editable ComboBox uses native input/datalist. Exact text matches select the first
matching label; other text sets index `-1` and writes the free string. `.change()`
receives the index for a selected option or the free string. Typing stays local;
Enter/blur submits once per edit sequence, with composition/draft readback rules
matching TextField. Choice order/value/label changes or model rebinding rotate
the native event token, rejecting old input. Scalar model value updates retain it.
Checkbox/RadioButton tokens also cover their registered candidate values.
Radio groups are scoped to model Slot and DOM parent. Pending control selections
survive older render watermarks; a matching confirmation or changed registration
releases them. Disabling ComboBox prevents interaction and server dispatch.

Pointer coordinates are Canvas-local logical pixels. Button bit values and
modifier bits follow [PUI/common.py](../PUI/common.py); convert DOM button codes
explicitly. `button` is the changed button for press/release, NONE for hover,
and the active single button for a simple drag; `buttons` preserves the complete
pressed mask. Pointer capture keeps drag events flowing outside the element;
cancellation releases the captured interaction with `cancelled: true`.

Transmit wheel units explicitly: `delta_mode` is `pixel`, `line`, or `page`.
Pixel mode maps to PUI `x_delta=-delta_x`, `y_delta=-delta_y` and zero angular
deltas. Line/page deltas remain raw in `delta_x`/`delta_y` with `delta_mode`; PUI pixel and angular fields are zero for these modes. Registered wheel handlers prevent page scrolling. Press/release/move handlers set touch-action:none; removal restores defaults. Context menus stay native. Native Pointer Events define button-chord behavior. Capture cancellation/loss sends cancelled mouseup. Press/click flushes a focused editor before its event.

Canvas moves use the bounded action queue with one unconfirmed `mousemove` per
connection. Only its matching `result` releases the move credit; a render or
Canvas ACK does not. While it is pending, replace consecutive compatible moves
at the queue tail with their newest sample, including native coalesced samples.
Compatibility requires the same node ID, handler token, pointer ID, button/buttons,
modifiers and cancellation state. Keep the newest complete event body, including
its observed render revision. Other actions and incompatible moves separate runs;
never search backward past them, reorder actions or allow a later action to pass
a waiting move. Intermediate positions in a merged run are intentionally omitted.
Replacement does not consume a new queue slot, including at the queue limit.
Non-move actions do not coalesce. Disconnect/fatal shutdown clears the queued
moves and in-flight credit; reconnect starts fresh without replaying them.

### Table events and inline editing

Table is one retained Web node with data-only TableNode children. Read-only
adapter cells use data() without calling editData()/setData(); editable() decides
whether the editing interface is needed. Its props are
`rows` (stable row IDs and nullable cell records), `columns` (labels),
`column_header`, nullable `row_headers`, and `autofit`. Each cell contains
`token`, `text`, `editor` (null/text/bool/choice), `value`, choice labels and
an `error` string. Raw choice values stay in Python. The table limit is 10,000 cells.
Native `table` events contain `cell` (token), `action` (click/dblclick/commit),
`value` (text, boolean, choice index or null) and a positive `edit_seq`. Python
validates the current source, collection generation, raw value and choices before
dispatch. Commits deduplicate by cell token/sequence; redraws publish authoritative
display values or validation errors. Browser editors disable during submission.
Data/source changes revoke tokens, adapter reconciliation cancels old targets, and
reconnect resets cell registrations. Table data uses ordinary render patches and
action credit; it has no separate transport.

## 7. Canvas display lists and resources

Geometry/text frames have limits of 300,000 commands, 20,000 points per command,
65,536 Unicode characters per text command, 16,384 logical pixels per dimension,
DPR at most 8, 16,777,216 backing pixels per Canvas and 33,554,432 per session.
General decoded-byte/item limits also apply. Measurement bodies contain
`node_id`, increasing `measure_rev`, `width`, `height`, `dpr` and `visible`.
Connection epochs reset measurement registrations, and partial DOM recreation
continues the same node's measurement revision. One Python frame awaits
presentation per Canvas; newer declarations coalesce into its next painter call.
A newer measurement can replace that frame without granting old ACKs credit.
Browser replay runs through requestAnimationFrame, after sending the DOM ACK.
The recorder accepts existing painter signatures and Python-side arguments;
Canvas input and HTTP images are also advertised.

Canvas frames travel in snapshot `canvases`, patch `put_canvas`, or
`patch_canvas` operations, so their dependencies and UI state have one render
revision. A patch omits unchanged Canvas records. Python still records a complete
display list for each paint; it compares that list against the last acknowledged
render's frame. Matching command prefixes and suffixes are retained and only the
middle replacement interval is transmitted. The current heuristic requires at
least eight reused commands; smaller lists or widespread changes use a complete
`put_canvas`, without encoding both candidates to choose between them. This is
one interval, not a multi-region edit script or a pixel diff.

```json
{
  "node_id": "n6",
  "frame_rev": 12,
  "measure_rev": 2,
  "width": 640,
  "height": 480,
  "dpr": 2,
  "background": "#ffffff",
  "continue": false,
  "commands": [
    {"op": "line", "x1": 0, "y1": 0, "x2": 100, "y2": 50, "color": "#ff0000", "width": 1},
    {"op": "ellipse", "x": 200, "y": 100, "rx": 20, "ry": 10, "fill": "#00ff00", "stroke": null, "width": 1}
  ]
}
```

`patch_canvas.frame` has the same fields as the full frame above, but `commands`
is the insertion list. The client requires an existing frame with exactly
`base_frame_rev`; the new `frame_rev` must increase, and `node_id`, `measure_rev`,
width, height and DPR must match the base. `start` and `delete_count` are
non-negative safe integers within the old list. Reconstruct as
`old[:start] + frame.commands + old[start + delete_count:]`. Empty insertion
supports deletion or metadata-only updates; insertion at the old length appends.
Background and continuation flags come from the new frame.

Prepare and validate the reconstructed state before changing DOM or canonical
records. It must remain within the 300,000-command/frame, five-million-item, 64-depth
and 32 MiB serialized-state budgets; small deltas cannot bypass those limits.
The browser owns incoming command records, shares unchanged immutable records,
and caches subtree sizes without retaining discarded objects. It never splices
the old list in place or re-serializes the full state to measure its budget.
The resulting complete frame goes through the normal clear-and-replay painter,
image retention and independent presentation ACK path.

Initial load, reconnect, recovery, a missing baseline or changed measurement
uses a complete frame. A wrong Canvas base causes the existing render discard
and snapshot recovery flow. Retries resend the same operation against the same
base; the enclosing render revision is deduplicated before applying any splice.
Only acknowledged renders become bases, independently of Canvas presentation
credit. Matching client/server builds are required; `canvas.patch` advertises
the new operation. The painter API and complete-batch zstd flush remain unchanged.

All command fields listed below are required, with null for optional paint or
bound values. The recorder emits numeric coordinates, strings, point arrays,
colors and declared resource references without validating command argument types
or ranges. The browser tries each opcode through explicit Canvas 2D calls;
unknown opcodes and drawing exceptions are logged with node/index information,
then skipped after restoring the context. Native silent ignores remain silent.
Bad commands do not invalidate the render or stop later commands. Frame/patch
metadata, command counts, reconstructed-state budgets and resource ownership
remain checked. Python painter/conversion errors and unserializable values still
fail before transport.

| Opcode | Fields | Capability |
| --- | --- | --- |
| `line` | `x1,y1,x2,y2,color,width` | `canvas.geometry` |
| `polyline` | `points,color,width` | `canvas.geometry` |
| `cubic` | `start,control1,control2,end,color,width` | `canvas.geometry` |
| `polygon` | `points,fill,stroke,width` | `canvas.geometry` |
| `rect` | `x1,y1,x2,y2,fill,stroke,width` | `canvas.geometry` |
| `ellipse` | `x,y,rx,ry,fill,stroke,width` | `canvas.geometry` |
| `text` | `x,y,text,w,h,size,color,rotate,anchor` | `canvas.text` |
| `image` | `resource,transforms,x,y,width,height,src_x,src_y,src_width,src_height,opacity` | `canvas.image` |
| `path` | `subpaths,fill_rule,fill,stroke,width` | `canvas.path`, for server-expanded Shapely geometry |

Points are `[x,y]`. Rectangles retain endpoint semantics; ellipses retain center
and radii. Null stroke/fill means no paint of that kind. Each command isolates
its drawing state. Text `anchor` is an Anchor enum name and `size` is points;
rotation is degrees around (x,y). Text uses native measureText and CSS font-family/weight. Nine anchors align the measured multiline block; explicit w/h clip from its top-left. Newlines are preserved without automatic wrapping, and point sizes convert at 96/72 CSS pixels per point. Browser metrics need not match Qt pixels. Image `resource` is a registered same-origin HTTP URL with an `mtime` query. A path subpath is
`{points,closed}`, with `fill_rule` equal to `evenodd` or `nonzero`. A path shares
the 20,000-point command limit across all subpaths. Python expands Shapely
collections recursively, preserves polygon holes with even-odd fill, and skips
empty geometries without requiring a Shapely import in the backend.

`measure_rev` increments when Canvas dimensions, DPR or visibility change.
No Python paint occurs before positive finite dimensions arrive. JS sizes the
backing bitmap for DPR and replays in logical coordinates. Reset drawing state,
transform, clipping and current path, clear the old bitmap, then apply background
and commands. Replaying a complete frame must not accumulate alpha or transform
changes from a previous replay. A frame for a removed node or outdated
measurement is skipped, not stretched over a new-sized canvas as current output.

Replay through `requestAnimationFrame`. Skip an already presented frame only if
the same `frame_rev`/`measure_rev` is still drawn on the same intact bitmap; resize,
context loss or recovery recreation requires a fresh replay. Frame contents are
immutable within their revision. Each independent `canvas_ack` body is
`{node_id, frame_rev, measure_rev, status}`, where status is `drawn`, `unchanged`,
`hidden`, `stale_measure`, `superseded`, or `failed`. Send the DOM ACK before presentation
results for its frames. DOM progress never waits for drawing or image decoding.
Keep at most one executing and one latest pending frame per Canvas. Replacing a
pending frame reports `superseded`; only a drawn/current frame earns paint credit.
Track these bounded presentation slots separately from the DOM render credit. `continue: true` records a truthy Python painter
return. Report outcomes for all frames supplied by the render; an omitted,
unchanged frame needs no new result. For a continuing frame, the first accepted
`drawn` or `unchanged` outcome for `(node_id, frame_rev)` grants one credit for
another continuous paint. `unchanged` confirms the same intact bitmap is already
presented; this allows recovery after drawing succeeded but its enclosing batch
failed. Duplicate ACKs or recovery replay never grant another credit for an
already credited frame. A retired node or superseded measurement cannot drive
another paint; use current measurements instead. Hidden frames
do not block DOM acknowledgement; a later visible measurement restarts painting.
Stale measurements request painting against the latest dimensions. Never build
an unbounded queue of animation frames or send JS source as a drawing command.

### HTTP image resources

Serve original image files over HTTP without server-side conversion or a Pillow
dependency. Python registers a file under an opaque resource ID; the gateway
serves only registered files belonging to the requesting cookie owner/session.
The resource URL respects `base_url`/`mount_path`, for example
`/pui/pui/images/<resource_id>?mtime=1792000000123456789`. Use the file's
`st_mtime_ns` as a decimal string so JavaScript does not round its value.
Keep the resource ID stable while registered; when reconciliation observes a
changed mtime, publish a new URL. This does not introduce a filesystem watcher.

Use normal browser HTTP caching with `Cache-Control`, `ETag`, `Last-Modified`
and conditional GET/304 responses; see [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html).
Session-owned images use `Cache-Control: private, no-cache` with conditional GET/304. The query separates modified versions
in the cache; cache freshness and revalidation still follow the HTTP headers.
An mtime URL is not a content hash or an immutable archived file: do not promise
immutable caching while serving a mutable source path. The gateway uses aiohttp FileResponse for HTTP validators. An obsolete mtime URL
returns HTTP 409 with no-store; missing/unregistered/foreign resources return 404.

`Image` uses an ordinary `img` element; Canvas loads the same URL and waits for
browser decoding before drawing its dependent frame. Crop/scale operations are
recorded as browser operations without creating converted files on the server.
`transforms` contains ordered `["crop",x,y,width,height]` or
`["scale",width,height,keep_aspect,smooth]` arrays. Dimensions are positive integers
up to 16,384; crop x/y are integers within +/-16,384. Each operation uses the
preceding bitmap. Crop leaves out-of-bounds pixels transparent; scale fits the
requested rectangle when keep_aspect is true, rounding resulting dimensions to
integer pixels. quality=0 maps to smooth=false; other qualities use browser high
quality smoothing. The source resource remains unchanged. Browser-supported formats determine decode support.
Bound active loads and decoded Canvas resources; an older load must not replace
a newer URL/frame. DOM ACKs remain independent of image decoding.

Retain file registrations while referenced by current, in-flight or desired
renders and retained sessions. Release unused registrations and decoded drawing
objects after their consumers retire; the browser manages its HTTP cache normally.
During recovery keep registrations needed by either tree until a successful
snapshot establishes ownership. Test load errors, changed/removed files and stale
URLs explicitly; never acknowledge an incomplete Canvas frame as drawn.
Image registration is private bounded MessagePack metadata over worker/gateway IPC;
paths never enter browser records. Registrations precede referencing renders and
cover acknowledged, outstanding and desired states; session teardown drops them.
Limits: 128 registered files/session, 64 MiB/file and 32 transforms/resource.
The Canvas cache permits 8 active loads, 15 seconds/load, 128 decoded entries,
16,777,216 pixels/image and 33,554,432 decoded cached pixels/session (checked
after native decoding).
Failed Canvas image commands log a warning and are skipped while other commands
draw. The frame sends failed, receives no continuous paint credit and does not
block DOM progress. Native img failures retain their alt text and log a warning.
Text uses the browser's current native font; no asynchronous font resource API
is provided.

## 8. Flow control, recovery and errors

The internal `PUI/web/render.py` implements structural record diffs and
`RenderStream`: immutable outstanding targets, one render credit, latest-state
coalescing, empty patches for processed inputs, duplicate ACK handling and
snapshot recovery. The browser validates widget properties and complete structural changes before
DOM mutation. Canvas geometry/text commands and independent presentation credits are implemented; image resource budgets are enforced separately from message limits. The worker retries an unacknowledged
render after 30 seconds, at most twice, using its immutable body and a fresh
envelope sequence. A further timeout requests a gateway disconnect with code
1013; the worker remains resumable under the normal disconnect TTL. A matching
ACK cancels the deadline and releases one credit. Duplicate ACKs release no
additional credit. Detach/reconnect clears the old stream/deadline; the new epoch
starts with a full snapshot and never replays callbacks.

Gateway WebSocket writes have a 30-second deadline. A stalled write logs the
overload and aborts that transport: a partially sent binary frame cannot be
repaired by sending a second frame or close message. Normal disconnect TTL and
same-worker snapshot recovery still apply. Gateway-to-worker IPC drains are
bounded at 30 seconds; worker-to-gateway drains at 60 seconds, so the gateway can
discard the failed browser connection and resume consuming output first. An
internal IPC timeout terminates the worker without trying another error write
through that stalled channel. Each IPC write queues at most one bounded packet
before awaiting drain. WebSocket close attempts are bounded at one second, then
abort their captured transport without touching a newer connection epoch.
Tests use a real small-window TCP reader paused during a multi-megabyte frame,
then resume the retained worker, plus an unread socketpair for the IPC deadline.

### Render baseline and coalescing

Initially allow one unacknowledged render plus the latest desired full state.
Keep the acknowledged full state, the outstanding batch's immutable target/body,
and the latest desired state within explicit memory limits. New state may
supersede the unsent desired state. A transmitted batch cannot be changed or
replaced under the same revision. After an applied ACK, promote its exact target
to the acknowledged baseline, then diff that baseline against the latest desired
state. Never discard a patch's dependency while retaining the patch.

Inside the serial worker, `Runtime.snapshot(copy=False)` publishes records and
`RenderStream.offer(..., copy=False)` retains them directly. Completed Canvas
frames and binding records remain read-only; new paints build new command lists,
and binding changes replace records and attachment maps instead of mutating
published versions, including rebinding and list/dict structural changes. Backend
`properties()` hooks must return values that remain unchanged after publication,
building new containers for updates rather than exposing mutable application
data. Model values and native choice contexts are still copied at their mutable
application boundary.

Patch operations share the target's values. The outstanding body/target and
acknowledged baseline reuse those records; `next_render(copy=False)` and
`retry(copy=False)` lend bodies to the read-only encoder. Resource retention
also only reads them. The helper defaults still return isolated copies, and
standalone `diff()` returns detached operations. These are internal ownership
rules; retained records must not be mutated by later paints or updates.

Runtime calls `offer(trusted=True)` to index each new state without a recursive
value scan; the recorder also publishes completed Canvas frames without a second
walk. Identity/reference/ownership checks remain in the structural index. The
helper default and standalone `diff()` retain strict input validation. The node,
parent, sibling, binding and Canvas indexes refer to that state's published
records and are
retained with the state, within the same baseline/outstanding/latest-desired
lifetimes. Diffing reuses both retained indexes; ACK promotion, retry and recovery
do not revalidate or rebuild them. When `copy=True`, the state and index are
copied together so index entries refer to owned records. Superseded versions
release their indexes with their states; there is no global identity cache.
Standalone `diff()` still validates both inputs on every call. Transport encoding
checks each assembled envelope and caps encoded/compressed bytes. Render bodies
go directly to MessagePack; item/depth limits are enforced by the receiving
decoder and the browser's reconstructed-state budget, including accumulated splices.
Other messages and incoming client values keep their strict recursive checks.
The no-op check compares full states only when their processed input sequences
match; an advanced sequence already requires a render confirmation. Background
changes at an unchanged input sequence still produce a patch.

For example, send `R10 -> R11`; while awaiting its ACK, coalesce desired R12 and
R13 into R13. After R11 is acknowledged, send `R11 -> R13`, not `R12 -> R13`.
Keep `processed_seq` tied to the target state actually built, never to newer
actions processed after that state. Assign envelope sequence numbers when
sending. Keep action results and close/error
messages out of the render coalescing slot.

One outstanding batch is a bounded initial correctness policy, not a throughput
claim. Its delivery rate is limited by ACK round-trip time plus client processing
(Canvas presentation is tracked independently): at 100 ms RTT the theoretical ceiling is about 10 batches/s
before other work. Measure compressed bytes, diff CPU, memory/client, interaction
latency and Canvas throughput. A future bounded multi-batch window would need
an ordered dependency chain, retained targets and cumulative-ACK/recovery rules;
do not enable it implicitly. Large replacements may not benefit from patches;
any size-based snapshot optimization needs measurement and an explicit policy.

### Deduplication and acknowledgements

Client `applied_rev` starts at 0 (no tree). Every render revision is positive;
a patch requires `0 < base_rev < rev`. Validate the session and envelope before
checking render identity. In a healthy client:

| Received render | Action |
| --- | --- |
| `rev == applied_rev` | Repeat the cached applied ACK, without rerunning DOM, binding reconciliation, Canvas, callbacks or measurements |
| `rev < applied_rev` | Ignore it and send a discarded ACK carrying the current `applied_rev` |
| New patch with `base_rev == applied_rev` | Validate the whole patch, then apply it; commit canonical records/revision only after success |
| New patch with another base | Leave the tree untouched, discard the batch and request a snapshot |
| New snapshot while awaiting bootstrap/recovery | Validate and install the complete state without depending on a previous base |

An unsolicited newer snapshot outside bootstrap/recovery is a protocol error.
Full snapshots are also subject to duplicate/old-revision checks. After success,
cache `ack {render_rev, applied_rev: render_rev, status: "applied"}`.
An applied ACK means DOM updates and draft reconciliation finished, and Canvas
frames were queued in the bounded presentation slots. It does not wait for those
frames to draw. Serialize DOM application through this ACK; process Canvas
presentation independently. A render retry repeats the cached DOM ACK without
queuing its frames again. Duplicate Canvas outcomes cannot earn duplicate credit.

The server validates DOM ACKs against its outstanding batch and Canvas ACKs
against the separately retained presentation records.
The first valid applied ACK advances the baseline and returns one render credit.
Duplicate/older terminal ACKs are ignored, without freeing newer credit,
releasing resources again or scheduling another continuous paint. An unknown
future revision is an error. A discarded ACK retires only its matching batch,
returns that credit once and never promotes the target to the baseline; the
reported `applied_rev` is diagnostic, not authority to adopt an unknown state.
For a discarded outstanding batch, pause ordinary publication until resync;
do not immediately send another patch against the old baseline. Discarded ACKs
use the last successful `applied_rev` (0 before bootstrap); they never grant
Canvas credits. Queue Canvas presentation only after successful DOM application. Retain resources still used by the
last applied or partially applied tree.

Retries, if needed, are bounded by count/time and resend the identical render
body under a new envelope sequence. A lost ACK therefore causes re-acknowledgement,
not duplicate work. In normal operation WebSocket preserves delivery order;
this mechanism is not a reason to retry every batch or replay user actions.

### Failure and snapshot recovery

Prevalidation catches invalid references/types before DOM mutation, but browser
operations are not transactional. If application fails midway, keep the last
successful `applied_rev`, mark the client desynchronized and send a discarded
ACK plus `resync {last_applied_rev}`. Do not retry against the partially changed
DOM or falsely ACK an older duplicate as proof that the DOM is healthy.
While desynchronized, discard incoming patches/old renders, pause new UI actions
and accept only a newer recovery snapshot; ordinary results still drain pending
actions. Preserve local drafts for surviving attachments where safe. Explicitly
cancel drafts whose nodes/registrations cannot be recovered.

The browser promotes canonical records and the applied revision only after DOM
mutation, editor readback and focus restoration all succeed. Real Chrome DOM
tests cover keyed focus/selection, newer drafts surviving old commit replies,
normalization, composition-end after blur, partial-mutation snapshot repair and
draft cancellation on rebinding. Chrome WebSocket tests inject a partial DOM
failure and verify discarded ACK/resync ordering, action suppression while dirty,
same-epoch snapshot recovery, retained draft/focus/selection and subsequent edits.
Additional Chrome tests replay old snapshots and failed patches while withholding
the recovery snapshot. These obsolete renders receive discarded ACKs without
restoring a dirty DOM or consuming recovery attempts. Persistent DOM failures
stop after three recovery snapshots fail, leaving the error visible. Composition
events in these tests are synthetic; native desktop/mobile IMEs and other browser
engines still need checks.

The browser uses application close code 4002 for fatal protocol errors and 4008
for a full input queue. JavaScript may initiate code 1000 or application codes
3000–4999, so it must not attempt to send protocol-reserved 1002/1008 itself.
These fatal paths keep the error visible and require a reload; they do not
automatically reconnect or replay pending actions. Once stopped, queued server
messages cannot revive the connection or drain application actions. The current
client allows at most 64 outstanding actions (or the smaller advertised limit)
and 256 queued actions; each matching result grants exactly one action credit.
Canvas mousemove also has a single result-gated credit as described in section 6.
Chrome pressure tests cover the limit, single-credit draining and overflow;
Canvas input tests cover adjacent move replacement and event boundaries.

Order the discarded ACK before `resync`. A base mismatch uses the same recovery
path. Once the outstanding batch is retired, the worker sends the latest full
state/resources as a snapshot with a fresh revision greater than all previously
issued revisions. If a resync arrives while a batch is still outstanding, wait
for its terminal ACK or the bounded timeout; never create a second render credit.
Coalesce repeated resync requests. Old renders already in transit are discarded
while waiting for that snapshot. A successful snapshot ACK establishes the new
baseline and resumes patches/actions.

Recovery repairs/reuses surviving DOM identities where safe. If a partially
applied tree cannot be reconciled reliably, rebuild the affected subtree and
report a recovery reset; focus/scroll/other browser-only state may be lost in
that exceptional case. Snapshots cannot repeat application callbacks or other
imperative side effects. Recovery keeps the same worker/State and connection
epoch. Reattachment after disconnect instead uses the cookie/TTL policy in
section 1 and a new connection epoch. Bound recovery attempts, resources
and time, and terminate visibly on persistent failure rather than growing queues.

### Action and resource limits

Use a bounded client action window counted until corresponding `result`s arrive.
Keep subsequent input ordered in a bounded local queue. Coalesce only consecutive
compatible Canvas mousemove actions under the rule above; retain commits and
click/release ordering. A slow worker
must not block other clients; a slow browser must not exhaust worker/gateway
memory. Announce concrete limits for compressed bytes, decoded bytes, zstd
window memory, nesting, nodes, commands, resources and pending actions in `ready`.
Bootstrap has fixed smaller decoder limits. Exact values require codec/browser
measurements before implementation; both ends enforce limits during decoding,
not only after allocating the complete result.

Suggested stable error codes: `VERSION_MISMATCH`, `BAD_FRAME`, `LIMIT_EXCEEDED`,
`BAD_SEQUENCE`, `BAD_SESSION`, `STALE_TARGET`, `INVALID_VALUE`,
`UNSUPPORTED_CAPABILITY`, `RESOURCE_FAILED`, `OVERLOADED`, `APP_ERROR`,
`REVISION_MISMATCH`, `RENDER_FAILED`.
Stale/invalid edits return a result and authoritative render where possible;
malformed framing, session violations or unrecoverable state end the connection.
Client-facing messages omit server traceback details; server logs can correlate
session and sequence. Application state is never reconstructed from arbitrary
client object IDs, attribute paths or serialized callables.

Imperative browser commands such as fullscreen/dialog requests need their own
capability and result contract later. They must not be hidden inside coalescible
render properties. No generic remote method invocation is part of this API.

## 9. Internal boundaries to implement

These are proposed internal responsibilities, not new public PUI signatures:

| Boundary | Operations |
| --- | --- |
| Python codec | `encode_message(message)`, `decode_message(frame, limits=...)` |
| Python binding registry | Register live source/role, resolve a write, read canonical values, revoke an attachment/source |
| Python session/renderer | Dispatch ordered actions, build/coalesce desired states, diff against the acknowledged baseline, retain immutable outstanding batches, deduplicate ACKs, publish snapshots for bootstrap/recovery, close |
| Python Canvas recorder | Current painter methods record arguments without type/range checks; finish a complete frame |
| JS transport | Decode in order, validate envelope, send events/writes, manage action/render credits |
| JS patch applier | Validate batch revision/operations, apply server patches, retain canonical records, reconcile local drafts even for empty patches, ACK once per application |
| JS snapshot recovery | Install a validated snapshot, reuse recoverable node IDs, repair partial failure, establish the new baseline |
| JS Canvas renderer | `replayCanvas(element, frame, resources)` and report measurement/presentation outcomes |

The wire schema is independent of the selected HTTP, MessagePack and Zstandard
packages. Keep framework-specific sockets/contexts out of binding and render
records. The gateway/worker IPC transports complete bounded binary messages;
its local framing can be selected with the server library without changing this
client contract. Any additional dependencies still require approval.

## 10. Review and validation still required

- Run the framing/body fixtures on Firefox/Safari and measure limits on supported
  browser versions.
- Stress expiry/reattach and shutdown races over longer runs; basic cookie/TTL,
  process isolation, blocked IPC, crash/startup failure and descriptor cleanup
  have real transport/process regressions.
- Validate the selected pointer, text and image behavior on additional engines;
  agree D6 imperative browser capabilities before implementation.
- Extend fixtures alongside Canvas image references, HTTP image caching and list/dict bindings;
  inject malformed nested render records/operations into recovery scenarios.
- Verify model versus edit_model, IME, normalization/rejection, rapid consecutive
  edits, input-only renders retaining uncommitted text, empty patches confirming
  rejected/no-op commits, shared bindings, attachment replacement and ID/slot reuse.
- Verify that applying each server patch produces its target canonical state;
  cover creation, map removal, keyed moves, subtree removal and registration changes.
- Verify coalescing from the acknowledged baseline, empty patches, immutable
  retries with new envelope sequences, lost/duplicate ACKs, old revisions,
  wrong bases, partial DOM failure and snapshot recovery. Duplicate renders/ACKs
  must not repeat events, draft normalization, resource release or animation credit.
- Verify independently redrawn subviews, token retention on rebuilt callbacks,
  late input, resync during an outstanding batch, two-worker isolation and shutdown.
- Exercise real browser DOM identity/focus/scroll, Canvas resize/DPR, ordered
  dragging, resource loading, hidden-tab animation and bounded slow-client queues.

Protocol references: [MessagePack](https://github.com/msgpack/msgpack/blob/master/spec.md),
[Zstandard framing](https://www.rfc-editor.org/rfc/rfc8878.html),
[WebSocket binary data](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/binaryType),
[IME composition](https://developer.mozilla.org/en-US/docs/Web/API/Element/compositionend_event).

## Drop transport

`ready.upload_limits` contains positive integer `max_files`, `max_file_bytes` and `max_session_bytes`. DOM drop targets expose `drop_extensions` and ordinary `drop` / optional `dragEnter` event tokens.

HTTP POST `pui/upload` receives multipart `files`, authenticated with the owner cookie, Origin and `X-PUI-Upload` token. `X-PUI-Session`, `X-PUI-Epoch`, `X-PUI-Node` and `X-PUI-Target` bind the batch to a live session/target. The response contains a single-use `upload_id`.

A `drop` event carries `{upload_id, text, urls, x, y}`; upload_id is null for text/URL-only drops. Python consumes the batch once and reports `drop_result` with `{accepted, reason}`. Rejections delete owned temporary batches. `dragEnter` carries `{x, y}` and does not transfer files.
