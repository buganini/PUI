# Web intermediate API proposal

This is a proposed v1 contract between a Python session worker and the JavaScript
client. The experimental Linux runtime is runnable for the basic cookbook subset.
Canvas/resource/imperative capabilities remain proposals until implemented. Architecture, missing work and unresolved
dependency/platform decisions are tracked in [web-progress.md](web-progress.md).
Examples show decoded MessagePack values using JSON notation; JSON is not the
transport. Implemented messages and remaining proposals are distinguished below.

Python owns State, bindings, callbacks, VDOM construction, render diffing and
painter execution. JavaScript validates and applies those patches, retains native
edit buffers, measures browser elements and replays Canvas commands. Full
snapshots establish or recover the client tree. The HTTP gateway routes each
connection to its dedicated worker; it does not interpret application State or
run callbacks.

## 1. Transport and session bootstrap

Proposed endpoints:

| Endpoint | Role |
| --- | --- |
| `GET /` | Serve the client entry page |
| `GET /assets/<build>/<file>` | Serve packaged, versioned JS/CSS/codec assets |
| `GET /pui/ws` with WebSocket upgrade | Open one client session and its worker |

These endpoint paths are relative to the configured public `base_url`, default
`"/"`. Accept a root-relative prefix such as `"/tools/pui/"` or an absolute
HTTP(S) URL such as `"https://example.com/tools/pui/"`; normalize a trailing slash.
Keep the upstream `mount_path` separate: its default is the public path, while
`mount_path="/"` allows a proxy to strip that prefix before forwarding requests.
The entry page, redirects, assets and WebSocket must use the same public base.

| Configuration | Public WebSocket | Upstream WebSocket route |
| --- | --- | --- |
| `base_url="/tools/pui/"` | `/tools/pui/pui/ws` | `/tools/pui/pui/ws` |
| `base_url="/tools/pui/", mount_path="/"` | `/tools/pui/pui/ws` | `/pui/ws` |
| `base_url="https://example.com/tools/pui/", mount_path="/"` | `wss://example.com/tools/pui/pui/ws` | `/pui/ws` |

The dependency-free [WebURLs helper](../PUI/web/urls.py) implements this mapping.
`public(endpoint)`, `route(endpoint)`, `asset(build, filename)` and `websocket()`
retain the prefix and reject ambiguous paths, queries/fragments and credentials.
Root-relative WebSocket paths resolve against the browser page's origin, using
`wss:` for HTTPS and `ws:` for HTTP; never derive a public URL from the worker's
listening address. Explicit absolute URLs use their configured public origin.
Do not trust arbitrary forwarding headers or inject a global HTML `<base>` that
changes application HTML/link semantics. The aiohttp gateway uses this mapping for entry redirects, assets and WebSocket.
Prefix-preserving HTTPS/WSS through a TLS-terminating nginx proxy is tested in
Chrome. An isolated nginx prefix-stripping deployment also passes the Chrome
cookbook suite, including assets, edits, cookie-owned resumption and tab isolation;
Safari/Firefox still need browser validation. When TLS terminates at a proxy, configure an absolute HTTPS
`base_url` for the public Origin, WSS URLs and Secure cookie. Preserving Host alone
does not preserve the public scheme on the HTTP upstream.

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

Use WebSocket subprotocol `pui.v1.msgpack.zstd`. Set browser `binaryType` to
`"arraybuffer"`. Each binary WebSocket message is exactly:

```text
Zstandard frame(MessagePack envelope)
```

This applies in both directions, including `hello` and `ready`. Load and verify
the codec before connecting; unsupported codecs show a client startup error.
The selected WebSocket subprotocol establishes the format before payload
decoding. Disable `permessage-deflate` for this channel. No base64 wrapping,
shared compression history, dictionaries, concatenated/skippable zstd frames,
trailing MessagePack values or alternative JSON mode in v1. Every zstd frame must
include its uncompressed content size, checked together with the window size
before decompression.

The Python `Codec` in `PUI/web/protocol.py` implements framing, value/envelope
validation and configurable `Limits`. Defaults are 8 MiB compressed, 16 MiB
decoded/window, 100,000 value/key items and nesting depth 64. The decoder checks
frame size before allocation, bounds MessagePack container lengths, then checks
aggregate item count/depth and the decoded envelope. The browser codec performs a bounded frame/content-size preflight and scans
MessagePack for UTF-8, duplicate keys, depth/items and extensions before decoding.
The map key `__proto__` is rejected in both languages. Python and Chrome share
malformed fixtures for nested duplicate keys, invalid UTF-8, extensions/timestamps,
unsafe integers, nonfinite values, depth/items, checksum corruption, dictionary
references, size/window limits and concatenated/truncated frames. Tested Python dependency
versions are pinned in `tests/requirements-web.txt`.

1. The entry page establishes an opaque, server-issued HttpOnly, SameSite cookie
   scoped to the public base path (Secure for HTTPS). This identifies the browser
   owner; a separate opaque per-tab session ID selects its worker. Neither value
   is a State ID. Validate cookie ownership on every WebSocket attachment.
2. Client sends `hello` with sequence 1 and `session: null`, including its optional
   `resume_id`. Reject a second active connection for the same retained session;
   do not let it steal the first connection. New tabs create separate sessions.
3. After admission/capacity checks, the worker responds with `ready`, sequence 1,
   a fresh connection epoch and its `resume_id`. A retained worker keeps its
   Python State but resets connection sequence/revision tracking and publishes
   a complete snapshot. Old connection epochs/actions are never replayed.
4. A disconnected worker is retained for `session_ttl` seconds, **900 by default**.
   Start the monotonic deadline at disconnect, cancel it on successful reattach,
   and clean up at expiry. `session_ttl=0` disables retention. Connected workers
   do not expire through this TTL. Explicit quit/server shutdown/crash ends the
   session immediately. A missing/expired resume ID creates a fresh session with
   `resumed: false`, so the client can visibly report the reset.
5. Pause browser-dependent painting while detached; bound retained resources and
   the total number of active plus retained workers. A full retained capacity
   rejects new sessions rather than silently evicting unexpired workers.

The internal `SessionRegistry(session_ttl=900, max_sessions=64)` implements
ownership, connection epochs, capacity and monotonic disconnect deadlines.
`expire()` returns removed reservations for the gateway to stop/reap; expired
workers count toward capacity until collected. It owns no threads or processes.
The gateway implements cookie verification, reattachment, expiry and worker
teardown. A standard-library forkserver with no preloaded modules provides the
clean Linux supervisor; application import happens inside each forked worker. On reconnect, discard uncertain outgoing actions and local
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
`limits`, `resume_id`, `resumed` (boolean), and `session_ttl` (seconds). The current required capabilities are `render.snapshot`, `render.patch` and
`binding.object_id`. Canvas is not yet advertised; `canvas.geometry` will be
negotiated when its recorder/replayer is implemented.
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
keys, non-finite numeric values and unknown message types/opcodes/fields.

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
| `render` | Worker to client | `mode`, `base_rev`, `rev`, `processed_seq`; snapshot or patch payload defined in section 4 |
| `event` | Client to worker | `node_id`, `event`, `token`, `observed_render_rev`, `data` |
| `binding_write` | Client to worker | Binding edit and origin; see section 5 |
| `result` | Worker to client | `reply_to` (client seq), `status`, `code` (string or null); action outcome |
| `measure` | Client to worker | `node_id`, `measure_rev`, `width`, `height`, `dpr`, `visible`; Canvas geometry |
| `ack` | Client to worker | `render_rev`, `applied_rev`, `status` (`applied` or `discarded`); DOM/draft application, see section 8 |
| `canvas_ack` | Client to worker | `node_id`, `frame_rev`, `measure_rev`, `status`; independent Canvas presentation result, see section 7 |
| `resync` | Client to worker | `last_applied_rev`; request a current full snapshot and its resources |
| `resource` | Worker to client | `id`, `rev`, `mime`, `data` (MessagePack binary); optional resource capability |
| `release` | Worker to client | `resources`: array of `{id, rev}`; release unused assets |
| `error` | Either | `code`, `reply_to` (seq or null), `fatal`, `message`; diagnostic |
| `close` | Either | `reason`; graceful session termination, followed by WebSocket close |

`event` and `binding_write` each produce one `result`. Status is `processed`,
`stale`, `invalid`, or `error`. `processed` means the registered handler/setter
ran; it does not mean a requested value was accepted or a browser frame was
drawn. The following render carries the authoritative result. Do not send
results for results, render acknowledgements or ordinary measurements.

A setter/callback exception can occur after application side effects. Return an
error outcome without automatic retry or a claim of rollback. If the worker
cannot produce a coherent next render state, end the session explicitly.

The implemented client-message schemas validate hello/viewport, click/input,
TextField writes, ACK, resync and close before dispatch. Invalid actions return
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
Schemas for unadvertised Canvas/resource messages remain deferred with those features.

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

Current node types are Window, VBox, HBox, Label, Button, TextField, Text, Spacer,
Divider and Scroll. Canvas remains proposed.
Their supported properties are allowlisted by type. Start with Window `title`,
Label/Button `text`, Button `enabled`, TextField `text`/`placeholder`, Text `text`, Label `selectable`, and Scroll `vertical`/`horizontal`
(`auto`, `scroll`, `hidden`). Canvas `background` remains proposed. A TextField's `text` is Python's display string; its Slot value
retains the underlying type. Empty property maps are valid for layout nodes.

Layout fields are `width`, `height`, `weight`, `padding` and `margin`; padding
and margin are four-element top/right/bottom/left arrays. Dimensions use logical
CSS pixels. Style fields are `color`, `background`, `font_size_pt`, `font_weight`
and `font_family`. Colors use canonical `#rrggbb`/`#rrggbbaa` strings. Node adapters
normalize existing PUI inputs to these fields. Missing overrides restore
defaults/inheritance; null is accepted only for explicitly nullable fields.

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
dictionary slot removal/recreation revoke affected registrations. A new
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

Preserve TextField's existing distinction between `model` and `edit_model`:

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
| Canvas `mousedown`, `mouseup`, `mousemove`, `mouseenter`, `mouseleave`, `dblclick` | `x`, `y`, `button`, `buttons`, `modifiers`, `pointer_id`, `cancelled` |
| `wheel` | `x`, `y`, raw `delta_x`, `delta_y`, `delta_mode`, `modifiers` |
| `keypress` | Browser `key`, `code`, `modifiers`, `repeat`, `composing`; PUI key mapping needs per-component validation |
| TextField `input` | `value`, `edit_seq`, `composing` |

Pointer coordinates are Canvas-local logical pixels. Button bit values and
modifier bits follow [PUI/common.py](../PUI/common.py); convert DOM button codes
explicitly. `button` is the changed button for press/release, NONE for hover,
and the active single button for a simple drag; `buttons` preserves the complete
pressed mask. Pointer capture keeps drag events flowing outside the element;
cancellation releases the captured interaction with `cancelled: true`.

Transmit wheel units explicitly: `delta_mode` is `pixel`, `line`, or `page`.
Pixel mode maps to PUI `x_delta=-delta_x`, `y_delta=-delta_y` and zero angular
deltas. Line/page conversion remains D5; it is not enabled until agreed.
Browser default scrolling/context-menu behavior needs an explicit component
event policy; it cannot wait for a synchronous Python callback return.

## 7. Canvas display lists and resources

Canvas frames travel in snapshot `canvases` or patch `put_canvas` operations, so
their dependencies and UI state have one render revision. A patch omits unchanged
Canvas records; every changed frame is still a complete display list. Python
can cache unchanged recorded lists. DOM diffing does not imply diffing individual
Painter commands or Canvas pixels.

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

All command fields listed below are required, with null for optional paint or
bound values. Arguments are finite numbers, strings, point arrays, colors or
declared resource references; opcodes select an explicit dispatch table.

| Opcode | Fields | Capability |
| --- | --- | --- |
| `line` | `x1,y1,x2,y2,color,width` | `canvas.geometry` |
| `polyline` | `points,color,width` | `canvas.geometry` |
| `cubic` | `start,control1,control2,end,color,width` | `canvas.geometry` |
| `polygon` | `points,fill,stroke,width` | `canvas.geometry` |
| `rect` | `x1,y1,x2,y2,fill,stroke,width` | `canvas.geometry` |
| `ellipse` | `x,y,rx,ry,fill,stroke,width` | `canvas.geometry` |
| `text` | `x,y,text,w,h,size,color,rotate,anchor` | Proposed `canvas.text`, pending D6 |
| `image` | `resource,x,y,width,height,src_x,src_y,src_width,src_height,opacity` | Proposed `canvas.image`, pending D6 |
| `path` | `subpaths,fill_rule,fill,stroke,width` | Proposed `canvas.path`, for server-expanded Shapely geometry |

Points are `[x,y]`. Rectangles retain endpoint semantics; ellipses retain center
and radii. Null stroke/fill means no paint of that kind. Each command isolates
its drawing state. Text `anchor` is an Anchor enum name and `size` is points;
rotation is degrees. Text bounds/anchor parity must be settled before advertising
that capability. Image `resource` is `{id,rev}`. A path subpath is
`{points,closed}`, with `fill_rule` equal to `evenodd` or `nonzero`.

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
`hidden`, `stale_measure`, or `superseded`. Send the DOM ACK before presentation
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

Image/font support remains optional. `resource` transfers bytes before a render
that references them. Decode asynchronously and wait for dependencies before
presenting that Canvas frame; bound pending resource memory/time. Resources are
identified by `{id,rev}`, and older decodes cannot replace newer resources.
Send `release` only after an acknowledged newer render no longer references the
asset and no in-flight render or retained desired state needs it. During partial
failure recovery retain assets potentially used by both old and partially applied
trees until a successful snapshot ACK establishes ownership. Missing/failed
resources produce an explicit error rather than silently presenting an incomplete frame. Image
dimensions, crop/scale and font readiness remain D6 implementation decisions.

## 8. Flow control, recovery and errors

The internal `PUI/web/render.py` implements structural record diffs and
`RenderStream`: immutable outstanding targets, one render credit, latest-state
coalescing, empty patches for processed inputs, duplicate ACK handling and
snapshot recovery. The browser validates widget properties and complete structural changes before
DOM mutation. Canvas commands, independent presentation credits and broader
resource budgets are not implemented. Render ACK timeouts/retries still require
transport integration; normal WebSocket delivery drives the current stream.

### Render baseline and coalescing

Initially allow one unacknowledged render plus the latest desired full state.
Keep the acknowledged full state, the outstanding batch's immutable target/body,
and the latest desired state within explicit memory limits. New state may
supersede the unsent desired state. A transmitted batch cannot be changed or
replaced under the same revision. After an applied ACK, promote its exact target
to the acknowledged baseline, then diff that baseline against the latest desired
state. Never discard a patch's dependency while retaining the patch.

For example, send `R10 -> R11`; while awaiting its ACK, coalesce desired R12 and
R13 into R13. After R11 is acknowledged, send `R11 -> R13`, not `R12 -> R13`.
Keep `processed_seq` tied to the target state actually built, never to newer
actions processed after that state. Assign envelope sequence numbers when
sending. Keep action results, resource lifetime operations and close/error
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
automatically reconnect or replay pending actions.

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
Keep subsequent input ordered in a bounded local queue. No silent motion
coalescing, dropped commits or reordered click/release events. A slow worker
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
| Python Canvas recorder | Current painter methods append validated command records; finish a complete frame |
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
- Agree D5 line/page wheels, motion/default browser actions; D6 text/image and
  later imperative browser capabilities.
- Extend fixtures alongside new Canvas/resource messages and list/dict bindings;
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
