# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [11.1.0] - 2026-05-07

### Fixed
- Default log level no longer slips to `debug`; defaults to `info` for both terminal and file sinks.

## [11.0.0] - 2026-05-06

### Added
- `--interval` CLI flag and `Interval=` ini key to configure the update interval.
- `-c` flag to specify a config file path; also search `~/.faddnsc.conf` before the system config.

### Changed
- Set a 60s global timeout on HTTP requests.
- More robust hostname detection.
- Fast-retry when no addresses are found or on HTTP error.
- Filter out unsuitable IPv6 addresses.
- Swap `local-ip-address` for `netdev`; restore `ether=` reporting.
- Bump Rust toolchain to 1.93.
- Update dependencies.

### Removed
- Drop production-server fallback; the server URL is now required.

## [10.1.0] - 2025-03-03

### Changed
- Don't exit on DNS update failure.
- More work on Debian packaging.

## [10.0.0] - 2025-01-02

First Rust release. Earlier Python-based versions (up to 3.2) are not included.

### Added
- Initial Rust rewrite.

### Changed
- Default log level set to `info`.
- Fixes for Linux systems.
- systemd service file fix.

---

**Note:** This changelog starts with the 10.x series (first Rust releases). Earlier Python-based versions (up to 3.2) are not included.
