<div align="center">

# Sweep

**Find and clean dev artifacts across all your projects.**

[![PyPI](https://img.shields.io/pypi/v/sweep-cli?style=flat-square&color=blue)](https://pypi.org/project/sweep-cli/)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-orange?style=flat-square)

</div>

---

Your `~/projects` folder is hoarding gigabytes of `node_modules`, `.venv`, `target/`, `build/`, and other artifacts you don't need. Sweep finds them all and lets you clean them interactively.

```
  SWEEP — 11 projects | 19.0 GB reclaimable

  PROJECT                      TYPE          SIZE       MODIFIED   STATUS
  ──────────────────────────────────────────────────────────────────────────
  artist_desk_website           Next.js    12.8 GB        today    dirty
  artistdesk-mobile             Flutter     3.0 GB      27d ago    clean
  artist-desk-admin             Node.js     1.6 GB        today    clean
  tldr-web                      Next.js   556.8 MB        today    clean
  puppeteer-scraping            Node.js   310.2 MB      3mo ago    clean
  ──────────────────────────────────────────────────────────────────────────
  Total: 19.0 GB across 11 projects

  [Space] select  [a] all  [Enter] delete  [q] quit
```

## Install

```bash
pip install sweep-cli
```

## Usage

```bash
# Scan current directory
sweep

# Scan a specific path
sweep ~/projects

# Dry run — just show what's there, no TUI
sweep ~/projects --dry-run

# JSON output for scripting
sweep ~/projects --json

# Only show projects with 100MB+ of artifacts
sweep --min-size 100MB

# Only show projects untouched for 6+ months
sweep --older-than 6m

# Control scan depth
sweep --depth 3
```

## Interactive TUI

Sweep launches an interactive terminal UI where you can:

| Key | Action |
|-----|--------|
| `↑` `↓` / `j` `k` | Navigate |
| `Space` | Select/deselect project |
| `a` | Select all / deselect all |
| `s` | Sort by size |
| `d` | Sort by date (oldest first) |
| `n` | Sort by name |
| `Enter` | Delete selected artifacts |
| `q` / `Esc` | Quit |

Color-coded safety:
- **Green** — selected for deletion
- **Yellow** — recently modified
- **Red** — has uncommitted git changes (dirty)

## Supported Ecosystems

| Ecosystem | Detected By | Cleans |
|-----------|-------------|--------|
| Node.js | `package.json` | `node_modules/` |
| Next.js | `next.config.*` | `.next/`, `node_modules/` |
| Python | `pyproject.toml`, `setup.py`, `requirements.txt` | `.venv/`, `venv/`, `__pycache__/`, `.tox/`, `.mypy_cache/` |
| Rust | `Cargo.toml` | `target/` |
| Go | `go.mod` | `vendor/` |
| Java (Maven) | `pom.xml` | `target/` |
| Java (Gradle) | `build.gradle` | `build/`, `.gradle/` |
| .NET | `*.csproj`, `*.sln` | `bin/`, `obj/` |
| Flutter | `pubspec.yaml` | `build/`, `.dart_tool/` |
| Ruby | `Gemfile` | `vendor/bundle/` |

## Git-Aware Safety

Sweep checks each project's git status before deletion:
- **clean** — no uncommitted changes, safe to delete
- **dirty** — has uncommitted changes, highlighted in red as a warning
- Projects without git are shown without status

## How It Works

- Walks your directory tree looking for project marker files
- Detects the ecosystem and finds corresponding artifact directories
- Calculates sizes using fast `os.scandir()` recursion
- Checks git status for safety
- Presents everything in a sortable, interactive TUI
- **Zero dependencies** — pure Python stdlib (`curses`, `os`, `shutil`, `argparse`)

## Support

If Sweep saves you disk space, consider buying me a coffee.

<a href="https://buymeacoffee.com/trinity_21" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>

## License

MIT
