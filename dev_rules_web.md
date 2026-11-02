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
