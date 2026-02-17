"""Sweep CLI — entry point and argument parsing."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from sweep.scanner import Project, format_size, scan
from sweep.tui import run_tui


def parse_size(value: str) -> int:
    """Parse a human-readable size string into bytes."""
    value = value.strip().upper()
    # Check longest suffixes first to avoid "B" matching before "MB"
    multipliers = [
        ("GB", 1024 * 1024 * 1024),
        ("MB", 1024 * 1024),
        ("KB", 1024),
        ("B", 1),
    ]
    for suffix, mult in multipliers:
        if value.endswith(suffix):
            num = value[: -len(suffix)].strip()
            return int(float(num) * mult)
    return int(float(value))


def parse_age(value: str) -> int:
    """Parse an age string like '6m', '1y', '30d' into days."""
    value = value.strip().lower()
    if value.endswith("d"):
        return int(value[:-1])
    elif value.endswith("m"):
        return int(value[:-1]) * 30
    elif value.endswith("y"):
        return int(value[:-1]) * 365
    return int(value)


def print_dry_run(projects: List[Project]) -> None:
    """Print scan results as a readable table."""
    if not projects:
        print("No projects with cleanable artifacts found.")
        return

    total_size = sum(p.size for p in projects)

    # Header
    print(f"\n  SWEEP — {len(projects)} projects | {format_size(total_size)} reclaimable\n")
    print(f"  {'PROJECT':<35} {'TYPE':<12} {'SIZE':>10} {'MODIFIED':>14} {'STATUS':>8}")
    print(f"  {'─' * 80}")

    for p in projects:
        status = ""
        if p.git_dirty:
            status = "dirty"
        elif p.git_dirty is False:
            status = "clean"

        name = p.name
        if len(name) > 33:
            name = name[:32] + "…"

        print(f"  {name:<35} {p.ecosystem:<12} {p.size_human:>10} {p.age_str:>14} {status:>8}")

    print(f"  {'─' * 80}")
    print(f"  Total: {format_size(total_size)} across {len(projects)} projects\n")


def print_json(projects: List[Project]) -> None:
    """Print scan results as JSON."""
    data = {
        "total_projects": len(projects),
        "total_size": sum(p.size for p in projects),
        "total_size_human": format_size(sum(p.size for p in projects)),
        "projects": [
            {
                "path": p.path,
                "name": p.name,
                "ecosystem": p.ecosystem,
                "size": p.size,
                "size_human": p.size_human,
                "last_modified": p.last_modified.isoformat() if p.last_modified else None,
                "git_dirty": p.git_dirty,
                "artifacts": [
                    {"path": a.path, "size": a.size}
                    for a in p.artifacts
                ],
            }
            for p in projects
        ],
    }
    print(json.dumps(data, indent=2))


def main() -> None:
    """Sweep CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="sweep",
        description="Find and clean dev artifacts across all your projects.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show results without interactive TUI (no deletion)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--min-size",
        type=str,
        default=None,
        help="Minimum artifact size to show (e.g., 100MB, 1GB)",
    )
    parser.add_argument(
        "--older-than",
        type=str,
        default=None,
        help="Only show projects older than (e.g., 30d, 6m, 1y)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Maximum directory depth to scan (default: 5)",
    )

    args = parser.parse_args()

    min_size = 0
    if args.min_size:
        try:
            min_size = parse_size(args.min_size)
        except ValueError:
            print(f"Invalid size: {args.min_size}", file=sys.stderr)
            sys.exit(1)

    max_age_days = None
    if args.older_than:
        try:
            max_age_days = parse_age(args.older_than)
        except ValueError:
            print(f"Invalid age: {args.older_than}", file=sys.stderr)
            sys.exit(1)

    # Scan
    if not args.json_output:
        print(f"  Scanning {args.path}...", end="", flush=True)

    projects = scan(
        root=args.path,
        min_size=min_size,
        max_depth=args.depth,
    )

    # Filter by age
    if max_age_days is not None:
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)
        projects = [
            p for p in projects
            if p.last_modified and p.last_modified < cutoff
        ]

    if not args.json_output:
        print(f" found {len(projects)} projects.\n")

    # Output mode
    if args.json_output:
        print_json(projects)
    elif args.dry_run:
        print_dry_run(projects)
    else:
        run_tui(projects)


if __name__ == "__main__":
    main()
