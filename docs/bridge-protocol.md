# Bridge protocol (native messaging)

The bridge is the only component allowed to touch a browser. It is deliberately
dumb: it executes named actions and returns page content. It knows nothing
about any website.

## Envelope

One JSON object per line over stdio. Requests carry an id; responses must echo
it. No streaming, no batching.

```json
{"id":"7f3a","action":"goto","params":{"url":"https://kns.cnki.net/"},"deadline_ms":15000}
{"id":"7f3a","ok":true,"data":{"url":"https://kns.cnki.net/"},"meta":{"duration_ms":612}}
```

```json
{"id":"7f3b","ok":false,"error":{"code":"policy.domain","message":"host not allowed"},"meta":{"duration_ms":0}}
```

## Verbs

| Verb | Params | Returns |
|---|---|---|
| `goto` | `url` | `{url, title}` |
| `wait_for` | `selector`, `state?`, `timeout_ms?` | `{matched: bool}` |
| `type` | `selector`, `text`, `clear?` | `{}` |
| `click` | `selector` | `{}` |
| `select` | `selector`, `value` | `{}` |
| `read_html` | — | `{html}` |
| `read_text` | `selector` | `{text}` |
| `scroll` | `to` (`bottom`/`top`) | `{}` |
| `sleep` | `ms` (≤3000) | `{}` |

Unknown verbs are rejected, never ignored.

## Validation layers

1. **Extension** – action name must be in the compiled whitelist; parameters
   are type-checked before touching the page.
2. **Native host** – re-validates action, domain, parameter schema, message
   size, and deadline. A request failing here never reaches the browser.
3. **Kernel** – validates the whole plan before the first action: verb set,
   domain allowlist, action count (≤40), estimated duration (≤120s).
4. **Runtime** – interval floor, daily quota, cooldown state.

## Error codes

| Code | Meaning |
|---|---|
| `policy.verb` | verb not allowed |
| `policy.domain` | host not in the channel allowlist |
| `policy.params` | parameter schema violation |
| `policy.rate` | interval or quota exceeded |
| `risk.captcha` | captcha detected; plan aborted |
| `risk.verify` | redirected to `/verify/home` |
| `risk.http403` | forbidden response |
| `bridge.timeout` | no response within deadline |
| `bridge.closed` | host or browser went away |

`risk.*` errors are terminal for the session: the kernel sets a cooldown and
refuses further plans until `scholar-search reset --confirm`.

## Size and time limits

- message ≤ 2 MiB (HTML pages are truncated with a marker if larger);
- per-action deadline ≤ 15s, whole plan ≤ 120s;
- `read_html` returns a single document, never a tab dump.

## Versioning

The host and extension exchange `protocol_version` at handshake. A mismatch is
a hard failure: refusing to run is safer than guessing.
