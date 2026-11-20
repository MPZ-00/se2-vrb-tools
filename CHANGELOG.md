# Changelog
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-20
First release.

### Added
- `vrb.py`: reader and writer for VR3B archives (`.vrb`), with header and per-section xxHash64 verification and recompression of the main chunk.
- `unflag.py`: removes the "altered with Debug Menu" mark from a save, in both `sessioncomponents.vrb` and `.container-info`. Supports `--dry-run`, refuses to write while the game is running, and backs up touched files to `%LocalAppData%\se2-vrb-tools\backups`.
- `inspect_vrb.py`: prints archive header, sections and checksums, lists type and field names (`--names`), and dumps decompressed sections (`--extract`).
- Path arguments expand environment variables such as `%AppData%`, so the README commands work in PowerShell and bash, not just cmd.
- Notes on the `.vrb` format in `docs/vrb-format.md`.

[0.1.0]: https://github.com/MPZ-00/se2-vrb-tools/releases/tag/v0.1.0
