<div align="center">

# Sweep

**Your projects are 90% junk. Sweep shows you exactly how much — and cleans it.**

[![PyPI](https://img.shields.io/pypi/v/sweep-cli?style=flat-square&color=blue)](https://pypi.org/project/sweep-cli/)
[![Downloads](https://img.shields.io/pypi/dm/sweep-cli?style=flat-square&color=green)](https://pypi.org/project/sweep-cli/)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-orange?style=flat-square)

</div>

---

Your `~/projects` folder is hoarding gigabytes of `node_modules`, `.venv`, `target/`, `build/`, and other build artifacts. Most of that space is **regenerable junk** you don't need.

Sweep scans your projects, shows you exactly how much of each project is junk vs actual code, and lets you reclaim it all with one keypress.

```
  SWEEP — 11 projects | 19.0 GB reclaimable (93% junk)

  PROJECT                        TYPE         FULL SIZE      ARTIFACTS   % JUNK
  ────────────────────────────────────────────────────────────────────────────────
  cloud-dashboard                 Next.js        13.1 GB       12.8 GB    97.7%
  pulse-mobile                    Flutter         3.1 GB        3.0 GB    96.8%
  nexus-admin                     Node.js         1.7 GB        1.6 GB    94.1%
  microkit-api                    Next.js       580.0 MB      556.8 MB    96.0%
  datastream-scraper              Node.js       315.0 MB      310.2 MB    98.5%
  ────────────────────────────────────────────────────────────────────────────────
  TOTAL                                          20.5 GB       19.0 GB    92.7%

  You can reclaim 19.0 GB out of 20.5 GB (93% is junk)

  [Space] select  [a] all  [Enter] delete  [q] quit
```

**That `cloud-dashboard` project? 97.7% of its 13.1 GB is just `node_modules` and `.next` cache.** Your actual code is only ~300 MB.

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

## What It Shows You

For every project, Sweep breaks down:

| Column | What It Means |
|--------|---------------|
| **FULL SIZE** | Total size of the entire project folder |
| **ARTIFACTS** | Size of deletable build artifacts (`node_modules`, `.venv`, `target/`, etc.) |
| **% JUNK** | How much of your project is regenerable junk |

Most projects are **80-98% junk** — artifacts that get regenerated automatically when you run `npm install`, `pip install`, or `cargo build`.

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
- **Red** — has uncommitted git changes (be careful!)

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

Artifacts like `node_modules` and `.venv` are always safe to delete — they regenerate with a single command (`npm install`, `pip install`, etc.).

## How It Works

1. Walks your directory tree looking for project marker files (`package.json`, `Cargo.toml`, etc.)
2. Detects the ecosystem and finds corresponding artifact directories
3. Calculates **full project size** vs **artifact size** to show you the **% junk**
4. Checks git status for safety
5. Presents everything in a sortable, interactive TUI
6. Deletes only the artifacts you select — your source code is never touched

**Zero dependencies** — pure Python stdlib (`curses`, `os`, `shutil`, `argparse`).

## Support

If Sweep saves you disk space, consider buying me a coffee.

<a href="https://buymeacoffee.com/trinity_21" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>

## License

MIT
