# Deployment rules

Adds to `dev_rules.md` for services deployed to a Linux server behind nginx.

## Layout

- Keep every server file in the repository under `deploy/`: the nginx site, the systemd units and timers, and the production settings file `deploy/config.json`. Never edit them on the server; deploy them.
- Production secrets live only on the server, in `/etc/<app>/env` (`root:<app>`, mode 640), loaded by `EnvironmentFile=`. Never in the repository or the deploy copy.

## Releases

- CI builds the release on a pushed `v*` tag, in the same workflow, and attaches it to a GitHub release: the binary, the bundled static files, and `deploy/`.
- `scripts/deploy.sh <tag>` fetches that release with `gh release download` and copies it over SSH with `rsync -e ssh` to `/opt/<app>/releases/<tag>/`. It then:
  1. switches the `/opt/<app>/current` symlink;
  2. installs the units and nginx site and reloads them;
  3. restarts the service;
  4. checks `GET /healthz`;
  5. switches the symlink back and restarts if the check fails.
- Deploy over SSH with keys only, as a `deploy` user whose `sudo` rights cover only the install and `systemctl` commands the script runs. Never FTP, root logins or password logins.
- Deploy only the release's explicit file list; never sync by extension from a mixed directory.
- Never run as root a file that a less-privileged account can write. Release files are `root`-owned and read-only to the service user.

## Services

- One systemd unit per service, with:
  - its own system user (`User=`), and `EnvironmentFile=/etc/<app>/env`;
  - the start command `ExecStart=/opt/<app>/current/<app> --config /opt/<app>/current/deploy/config.json`;
  - `Restart=on-failure`, `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`;
  - `StateDirectory=` for any writable path.
- Never start services with `nohup`, `killall` or start-up scripts.
- Services log to stdout; journald keeps the logs. No log files and no hand rotation.

## nginx

- nginx terminates TLS and proxies to the app on `127.0.0.1`. Set:
  - `ssl_protocols TLSv1.2 TLSv1.3`;
  - an HTTP server that only redirects to HTTPS;
  - a default server that answers unknown `Host` headers with `444`.
- Rate-limit per client IP with `limit_req_zone`, and give login, signup and password-reset routes their own stricter zone. Rates are in the site file under `deploy/`.
- Set no security headers in nginx (`dev_rules_web.md`); the app sets them all.

## Backups

- A systemd timer runs `pg_dump -Fc` nightly for each database, as a login role granted only `pg_read_all_data`, never a superuser.
- The script encrypts each dump with `age` to a public key from settings and copies it off the host. It keeps `backup_retention_days` of dumps (a setting).
- A backup counts only after a restore test has passed. The same timer restores the newest dump into a scratch database with `pg_restore`, checks each table's row count against the count recorded at dump time, and fails the unit on a mismatch.
- Never write dumps to a web, upload or home directory, and never commit them.
- Move to pgBackRest when losing up to a day of data is no longer acceptable.

## Pitfalls

- nginx `add_header` in a `location` drops every `add_header` inherited from the `server` block.
- Two copies of the proxy config that drift apart; there is one, in `deploy/`.
- A debug flag, auto-confirm or test token left enabled in production settings.
