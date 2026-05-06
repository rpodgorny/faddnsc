# Rust rewrite vs. Python: deployment review

Comparison of the Rust faddnsc (this repo) against the Python `faddns` package
shipped to existing hosts. Win7 support is no longer a concern.

## Critical — behavior changes that can break the fleet

### 1. MAC addresses (`ether=…`) no longer sent — RESOLVED
- Replaced `local-ip-address` with `netdev = "0.43.0"` (no default features).
- Iterates `netdev::get_interfaces()`; emits `inet=` per IPv4, `inet6=` per
  IPv6, and `ether=` per non-zero MAC. Loopback ifaces and zero MACs are
  skipped.
- Smoke-tested locally — output matches Python's set of `inet/inet6/ether`
  query params.

### 2. IPv6 temporary (privacy) addresses are no longer filtered — RESOLVED
- `netdev` exposes per-IPv6 flags (`Ipv6AddrFlags`); the vector is
  index-aligned with `iface.ipv6`.
- Filter: skip any IPv6 where `temporary || deprecated || tentative ||
  duplicated`. Stricter than Python's `if 'temporary' in line` because
  none of those states are suitable as a DNS target.
- Link-local (`fe80::…`) is still sent — Python sent it too, server can
  ignore.

### 3. Default URL silently points at production — RESOLVED
- Removed the `https://faddns.podgorny.cz` fallback.
- `Config::from_ini_and_args` now returns `anyhow::Result` and bails with
  `"no url configured"` when neither config nor CLI provides a URL.
  Matches Python's `no url!` behavior.

### 4. Response body `OK` check is gone — ACCEPTED
- Decision: drop it. HTTP 4xx/5xx are still surfaced as errors via ureq's
  default `http_status_as_error=true`. Server-level 200+ERROR responses
  (if any exist) will be silently accepted; that's deemed acceptable.

## High — UX regressions for non-default deployments

### 5. `-c <config>` CLI flag removed — RESOLVED
- Re-added as `-c, --config <CONFIG>` clap arg (`src/cfg.rs`).
- When passed, it overrides the platform default. If the explicit path
  doesn't exist, the binary exits with `config file <path> does not exist`
  — matches Python's behavior. Implicit-default missing file still falls
  back to `IniConfig::default()` as before.

### 6. `--log-level` and `--interval` CLI flags removed — RESOLVED
- `--log-level`: not re-added. `RUST_LOG` env var covers the use case;
  systemd users can drop in `Environment=RUST_LOG=debug`.
- `--interval`: re-added as `-i, --interval <SECS>` clap arg. Default
  600 s preserved.

### 7. Linux config search path narrowed — RESOLVED
- Search order: explicit `-c <path>` (errors if missing) → user-local
  `~/.faddnsc.conf` (silently skipped if absent) → system-wide
  `/etc/faddnsc.conf` (Linux) / `/faddnsc/faddnsc.ini` (Windows).
- The Python-era cwd-relative `./faddnsc.ini` is intentionally not
  restored — too ambiguous, and nothing in the fleet relies on it.
- Home dir resolved via `$HOME` (Linux) or `%USERPROFILE%` (Windows) —
  no extra deps.

### 8. `Interval=` ini key silently ignored — RESOLVED
- `IniConfig` now reads `Interval=` from the `[General]` section as `u64`
  seconds. Precedence: CLI `--interval` > `Interval=` ini key > default
  600 s. Folded into #6.

### 9. Hostname is no longer lowercased — RESOLVED
- Auto-detected fallback now uses `.to_lowercase()`, matching Python's
  `socket.gethostname().lower()`. Ini-provided and CLI-provided values
  pass through verbatim — also matching Python.

### 10. `rust-ini` is case-sensitive on keys — ACCEPTED
- Decision: leave the crate's default (case-sensitive) behavior. Fleet
  configs all use exact `Url=`/`Host=`/`Interval=` so no real-world
  impact; latent footgun for hand edits documented but not patched.

## Medium — packaging and ops

### 11. `Cargo.toml` `revision = "3"` still set — RESOLVED
- TODO honored: dropped `revision = "3"` from `[package.metadata.deb]`.
- Next deb will be named `faddnsc_<ver>-1_<arch>.deb`.

### 12. Arch PKGBUILD still builds the Python package — RESOLVED
- Rewrote `/home/radek/mnt_data_radek/pkgbuilds/faddnsc-git/PKGBUILD` to
  build with `cargo build --frozen --release` and install the binary
  directly. `arch` switched from `any` to `x86_64 aarch64 armv7h`,
  python deps removed, `cargo` makedepend added, pkgrel bumped to 10,
  pkgver baseline refreshed to `r232.8e1ee15`.

### 13. Windows path uses `/faddnsc/...` — ACCEPTED
- Decision: leave `/faddnsc/faddnsc.{ini,log}` as-is. Resolves to
  `<current-drive>:\faddnsc\...`; works on every existing host because
  nssm sets `AppDirectory=c:\faddnsc`.

### 14. Windows atxpkg upgrade leaves Python leftover files — DEFERRED
- Cannot be verified from this environment; needs a real upgrade test.
- **Action item:** before fan-out, upgrade ONE Windows host manually.
  Inspect `c:\faddnsc\` afterwards. If `python33.dll`, `*.pyd`,
  `pywintypes33.dll`, etc. are still present, atxpkg overlays without
  cleanup — write a one-time cleanup script or do a fresh install on
  affected hosts.

## Low — minor / cosmetic

### 16. Log format differs — ACCEPTED
- Decision: keep simplelog's default format (timestamp + level + thread +
  module + message). Logs are read by humans; any external parser is
  expected to adapt.

### 17. Retry interval doesn't accelerate on transient failure — RESOLVED
- After each iteration: sleep 60 s if no addresses were collected OR the
  HTTP request returned an error; otherwise sleep `cfg.interval` (default
  600 s). Goes a step beyond Python (which only fast-retried on
  no-addresses) by also fast-retrying on transport failure.

### 18. `hostname::get().unwrap().to_str().unwrap()` can panic — RESOLVED
- Replaced both unwraps with `?`. The `io::Error` from `hostname::get()`
  bubbles up via anyhow; non-UTF-8 hostnames return
  `anyhow!("hostname is not valid UTF-8")`. Service exits cleanly with a
  message instead of panicking; systemd `Restart=on-failure` will
  respawn (and any persistent breakage stays loud rather than hidden).

### 19. No connect/global timeout on `ureq` — RESOLVED
- Built a single `ureq::Agent` with `timeout_global(60s)` once at
  startup; the loop reuses it for every request. Hung connection now
  aborts after 60 s and is treated as an HTTP error → fast-retry path
  from #17 kicks in.

### 20. `Restart=on-failure` in service file — ACCEPTED
- Decision: leave as-is. Matches the Python service file. Loop never
  exits cleanly today, so the distinction doesn't matter in practice.

## Already handled / not an issue

- HTTP redirects: `ureq` follows up to 10 by default — this is the actual
  fix the user wanted.
- TLS: `ureq` uses rustls — no system OpenSSL surprises.
- systemd unit otherwise identical (correctly dropped `PYTHONUNBUFFERED=1`).
- atxpkg config preservation: `atxpkg_backup` lists `faddnsc/faddnsc.ini`,
  so existing Windows configs won't be clobbered.
- Win7 support concerns (rustc 1.77 image, `.cargo/config.toml` resolver
  fallback, `rust-version = "1.74"` comment): no longer relevant; can be
  cleaned up, but not blocking deployment.
