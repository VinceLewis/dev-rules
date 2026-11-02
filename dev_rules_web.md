# Web rules

Adds to `dev_rules.md` for any HTTP server or browser UI. The stack file names the library for each rule.

## Requests and responses

- Authenticate API calls with `Authorization: Bearer <access token>`. Send no CORS headers until a second origin needs them.
- Verify JWTs locally: pin the algorithm, and require `exp`, `iss` and `aud` to match the settings. No token cache and no call to the auth server per request. Libraries: Go `github.com/golang-jwt/jwt/v5`, .NET `Microsoft.AspNetCore.Authentication.JwtBearer`, Python `PyJWT`, TypeScript `jose`.
- Error responses are RFC 9457 `application/problem+json` with `type`, `title`, `status` and `request_id`, built by one helper. `title` is a fixed message per error kind; never internal error text. Use .NET's built-in `ProblemDetails`.
- Reject a body over the `max_body_bytes` setting with 413, and unknown JSON fields with 400.
- Behind the proxy, bind `127.0.0.1` and trust forwarded headers from it only.

## Security headers

- The application sets every security header on every response, from settings; the proxy sets none. Start with:
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains`;
  - `Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'`, plus `connect-src` for each API origin;
  - `X-Content-Type-Options: nosniff`;
  - `Referrer-Policy: strict-origin-when-cross-origin`.
- Send HSTS whatever the request's own scheme; the proxy terminates TLS.
- One end-to-end test asserts these headers on an HTML page, a static file and an API response.

## Browser code

- Browser code is TypeScript bundled with Vite (`dev_rules_typescript.md`). Install libraries from the lock file; never commit minified vendor copies.
- Put user data into the page with `textContent`, `createElement` and attribute setters; never `innerHTML`, `outerHTML`, `insertAdjacentHTML` or `document.write` with interpolated values.
- No inline scripts, `on*=` attributes or `javascript:` URLs; attach handlers with `addEventListener`. The CSP blocks the rest.
- Accept only `https:` URLs for user-supplied links. Validate them on the server, and render them with `rel="noopener noreferrer"`.
- Keep the access token in memory only. Keep the refresh token in an `HttpOnly; Secure; SameSite=Strict` cookie scoped to the refresh path. The refresh endpoint checks that `Origin` equals the app's origin. Never put a token in `localStorage`, `sessionStorage`, IndexedDB or a URL.
- No `console.*` calls (Biome `noConsole`) and no debug consoles or dev tools in the shipped bundle.
- Report uncaught errors (`error` and `unhandledrejection` events) to `POST /api/client-errors`, rate-limited, with message, source location, page path and request ID only. The server logs each at `error`.

## Interface quality

- Name each screen's job before designing it: operate (tools, admin, dashboards, forms), read (docs, help) or persuade
  (marketing). Operate and read screens use familiar patterns, one font family, restrained colour (an accent only for
  primary actions, selection and state), dense tables where users need them, and motion only to show a state change
  (150–250 ms). No modal unless the task needs interruption.
- Every screen meets this floor, checked on the rendered page:
  - text contrast at least 4.5:1, large text 3:1, and status shown in text, never by colour alone;
  - every control has default, hover, visible focus, active, disabled, loading and error states;
  - the whole screen works by keyboard alone, every input has a label, and data tables have header cells;
  - empty states say what to do next; errors name the problem and the way to recover; controls name their action;
  - lists page on the server; long values wrap or truncate visibly, never overflow.
- No decoration standing in for content: no gradient text, glow or halo shadows, nested cards, labels above headings,
  thick coloured side borders, or emoji in place of icons.
- Review every UI change with the Impeccable plugin before merging, alongside the section 12 review in
  `dev_rules.md`: `/impeccable audit <screen>` on each changed screen, and `/impeccable critique <screen>` on each
  new one. Merge at an audit score of 14/20 or more with no accessibility finding left open; fix each finding or
  record the user's acceptance in the pull request. Use `harden`, `clarify` and `distill` to fix findings; do not run
  `bolder`, `overdrive`, `delight`, `animate`, `colorize`, `live` or `generate` on operate or read screens unless the
  user asks. Without the plugin, check the floor above by hand on every changed screen.
- Commit the plugin's `PRODUCT.md`, `DESIGN.md` and `.impeccable/config.json`; they count towards the docs budget, so
  keep them short. Ignore `.impeccable/config.local.json`. Turn its per-edit hook on (`/impeccable hooks on`) only
  where UI lives in `.html`, `.css`, `.js`, `.ts` or `.tsx` files; for HTML built in server code, audit the running
  pages instead.

## Service workers

- Derive the cache name from the build hash that Vite emits; never bump a version by hand. Delete old caches in `activate`.
- Cache only responses with `ok` true. Never cache API responses that carry user data unless the app has an offline mode that needs them.

## Health

- `GET /healthz` returns 200 when the process can serve requests and reach its database, and 503 otherwise, with no body detail. The deploy script checks it after each restart.
- No metrics or tracing until one request crosses two services you run; then use OpenTelemetry.

## Pitfalls

- An auth allow-list in the app that the proxy routes around. Send each path through exactly one gateway.
- HSTS set only when the app sees TLS directly, which never happens behind a proxy.
- Two CSPs on one response (proxy and app); the browser enforces both.
- A design review run on source files only: contrast, overflow and focus problems show only on the rendered page.
