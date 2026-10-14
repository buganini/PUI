# Web intermediate API proposal

This is a proposed v1 contract between a Python session worker and the JavaScript
client. It is **not implemented**. Architecture, missing work and unresolved
dependency/platform decisions are tracked in [web-progress.md](web-progress.md).
Examples show decoded MessagePack values using JSON notation; JSON is not the
transport. Names and schemas below are proposals for review before coding.

Python owns State, bindings, callbacks, VDOM construction and painter execution.
JavaScript owns DOM reconciliation, native edit buffers, browser measurements
and Canvas replay. The HTTP gateway routes each connection to its dedicated
worker; it does not interpret application State or run callbacks.

## 1. Transport and session bootstrap

Proposed endpoints:

| Endpoint | Role |
| --- | --- |
| `GET /` | Serve the client entry page |
| `GET /assets/<build>/<file>` | Serve packaged, versioned JS/CSS/codec assets |
| `GET /pui/ws` with WebSocket upgrade | Open one client session and its worker |

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
trailing MessagePack values or alternative JSON mode in v1.

1. Client sends `hello` with sequence 1 and `session: null`.
2. After admission/capacity checks, the worker receives that hello and responds
   with `ready`, sequence 1, and a fresh opaque session epoch.
3. The worker publishes the first `render`; subsequent messages carry that epoch.
4. Connection close ends the session under the proposed initial disconnect
   policy. Reconnection starts a new epoch/worker; old actions are not replayed.

Only the worker produces the ordered server message stream after handoff.
The gateway forwards bytes unchanged; a worker crash closes its WebSocket.
Bootstrap rejection before handoff uses HTTP/WebSocket failure, not a competing
producer of server sequence numbers. A session epoch routes messages; it is not
an authentication credential or a UUID stored on State.

`hello.body` contains `client_build`, `capabilities` (string array), and
`viewport: {width, height, dpr}`. `ready.body` contains `server_build`, the
accepted `capabilities`, and concrete `limits`. The initial required capabilities
are `render.snapshot`, `binding.object_id`, and `canvas.geometry`.
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
| `processed_seq` | Highest client sequence fully processed by the worker when a snapshot was built |
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

`seq` orders messages; render `rev` orders snapshots; `processed_seq` tells the
client which inputs are reflected in a snapshot. These are distinct counters.
Render revisions can skip when unsent snapshots are superseded.

## 3. Messages

All fields listed under body are required unless explicitly marked optional.

| Type | Direction | Body and purpose |
| --- | --- | --- |
| `hello` | Client to worker | Client build, capabilities, viewport; see bootstrap |
| `ready` | Worker to client | Server build, accepted capabilities, limits |
| `render` | Worker to client | `rev`, `processed_seq`, `roots`, `bindings`, `canvases`; full snapshot |
| `event` | Client to worker | `node_id`, `event`, `token`, `observed_render_rev`, `data` |
| `binding_write` | Client to worker | Binding edit and origin; see section 5 |
| `result` | Worker to client | `reply_to` (client seq), `status`, `code` (string or null); action outcome |
| `measure` | Client to worker | `node_id`, `measure_rev`, `width`, `height`, `dpr`, `visible`; Canvas geometry |
| `ack` | Client to worker | `render_rev`, `status` (`applied` or `discarded`), `canvases` (presentation results) |
| `resync` | Client to worker | `last_applied_rev`; request a current full snapshot and its resources |
| `resource` | Worker to client | `id`, `rev`, `mime`, `data` (MessagePack binary); optional resource capability |
| `release` | Worker to client | `resources`: array of `{id, rev}`; release unused assets |
| `error` | Either | `code`, `reply_to` (seq or null), `fatal`, `message`; diagnostic |
| `close` | Either | `reason`; graceful session termination, followed by WebSocket close |

`event` and `binding_write` each produce one `result`. Status is `processed`,
`stale`, `invalid`, or `error`. `processed` means the registered handler/setter
ran; it does not mean a requested value was accepted or a browser frame was
drawn. The following snapshot contains the authoritative result. Do not send
results for results, render acknowledgements or ordinary measurements.

A setter/callback exception can occur after application side effects. Return an
error outcome without automatic retry or a claim of rollback. If the worker
cannot produce a coherent next snapshot, end the session explicitly.

## 4. Render tree and identity

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

`render.body.roots` initially contains exactly one Window/page tree.
`bindings` contains one Slot per exposed source/registration, deduplicated across
controls. `canvases` contains the current full display list for every measured,
ready Canvas, including unchanged frame revisions. An unmeasured Canvas has a
node but no frame yet. A new snapshot completely describes these three lists.

Initial node types are Window, VBox, HBox, Label, Button, TextField and Canvas.
Their supported properties are allowlisted by type. Start with Window `title`,
Label/Button `text`, Button `enabled`, TextField `text`/`placeholder`, and Canvas
`background`. A TextField's `text` is Python's display string; its Slot value
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

JS validates the tree, references and supported types before modifying DOM.
It reuses/moves nodes by ID, patches properties and removes obsolete listeners,
styles and nodes. It must not replace the whole DOM for each full snapshot.
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
normalization, and schedule a snapshot even for a no-op/rejected edit so the
client receives its final value and input watermark.

The client keeps local `edit_seq`, the pending commit's message/edit sequences,
and editing/composition state per editor. A result for an input event or
edit_model write releases action credit but does not mark the model draft as
committed. While editing, preserve that draft even when a snapshot still contains
the old model text. Normalize/end the draft only when `processed_seq` covers its
commit, no newer local draft exists and composition has ended. Outside editing,
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
| Server 7 | `render`, rev 4, processed_seq 9 | Coalesced authoritative UI/binding/Canvas snapshot |
| Client 10 | `ack`, render_rev 4 | Snapshot applied; return render credit |

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

Canvas frames travel inside `render.body.canvases` so their dependencies and UI
state have one render revision. Python can cache the unchanged recorded list;
the client can skip replay for an already presented frame revision.

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
backing bitmap for DPR and replays in logical coordinates, clearing the old
frame and applying background first. A frame for a removed node or outdated
measurement is skipped, not stretched over a new-sized canvas as current output.

Replay through `requestAnimationFrame`. Each Canvas result in a render `ack` is
`{node_id, frame_rev, measure_rev, status}`, where status is `drawn`, `unchanged`,
`hidden`, or `stale_measure`. `continue: true` records a truthy Python painter
return. Only `drawn` grants a credit for another continuous paint. Hidden frames
do not block DOM acknowledgement; a later visible measurement restarts painting.
Stale measurements request painting against the latest dimensions. Never build
an unbounded queue of animation frames or send JS source as a drawing command.

Image/font support remains optional. `resource` transfers bytes before a render
that references them. Decode asynchronously and wait for dependencies before
presenting that Canvas frame; bound pending resource memory/time. Resources are
identified by `{id,rev}`, and older decodes cannot replace newer resources.
Send `release` only after an acknowledged newer render no longer references the
asset and no in-flight frame needs it. Missing/failed resources produce an
explicit error rather than silently presenting an incomplete frame. Image
dimensions, crop/scale and font readiness remain D6 implementation decisions.

## 8. Flow control, recovery and errors

Allow one unacknowledged render plus the latest unsent snapshot. A new snapshot
can supersede the unsent one because it includes the full tree, binding values
and Canvas lists. Assign wire sequence numbers when sending, not when building.
Keep action results, resource lifetime operations and close/error messages out
of that coalescing slot.

Client `ack(status="applied")` means the DOM snapshot is installed and each
Canvas has a presentation outcome. Validate the acknowledged revision against
the actual outstanding render. `discarded` frees the transport credit without
claiming presentation; retain resources still used by the last applied tree.
After discarding an unusable snapshot, the client can request `resync`. Resync
queues the latest full snapshot/resources through the same credit mechanism;
it does not replay actions or create a new State. Bound recovery attempts and
terminate on persistent failure.

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
`UNSUPPORTED_CAPABILITY`, `RESOURCE_FAILED`, `OVERLOADED`, `APP_ERROR`.
Stale/invalid edits return a result and authoritative snapshot where possible;
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
| Python session | Dispatch ordered actions, coalesce redraws, build a consistent snapshot, publish, close |
| Python Canvas recorder | Current painter methods append validated command records; finish a complete frame |
| JS transport | Decode in order, validate envelope, send events/writes, manage action/render credits |
| JS syncer | `syncDom(previous, next)`, reconcile bindings without destroying local drafts, remove retired nodes |
| JS Canvas renderer | `replayCanvas(element, frame, resources)` and report measurement/presentation outcomes |

The wire schema is independent of the selected HTTP, MessagePack and Zstandard
packages. Keep framework-specific sockets/contexts out of binding and render
records. The gateway/worker IPC transports complete bounded binary messages;
its local framing can be selected with the server library without changing this
client contract. Any additional dependencies still require approval.

## 10. Review and validation still required

- Confirm the proposed WebSocket subprotocol/bootstrap and choose packages,
  limits and browser baseline under D1/D3 in the progress document.
- Agree D4 disconnect behavior; D5 line/page wheels, motion/default browser
  actions; D6 text/image and later imperative browser capabilities.
- Build Python/JS fixtures for every required message and opcode, including
  typed keys, object IDs beyond JS numeric precision and invalid frames.
- Verify model versus edit_model, IME, normalization/rejection, rapid consecutive
  edits, input-only snapshots retaining uncommitted text, shared bindings,
  attachment replacement and ID/slot reuse.
- Verify snapshot skipping, independently redrawn subviews, token retention on
  rebuilt callbacks, late input, resync, two-worker isolation and shutdown.
- Exercise real browser DOM identity/focus/scroll, Canvas resize/DPR, ordered
  dragging, resource loading, hidden-tab animation and bounded slow-client queues.

Protocol references: [MessagePack](https://github.com/msgpack/msgpack/blob/master/spec.md),
[Zstandard framing](https://www.rfc-editor.org/rfc/rfc8878.html),
[WebSocket binary data](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/binaryType),
[IME composition](https://developer.mozilla.org/en-US/docs/Web/API/Element/compositionend_event).
