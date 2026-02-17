"""Sweep scanner — detect dev projects and their artifact directories."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Each ecosystem: (marker_files, artifact_dirs, display_name)
ECOSYSTEMS: List[Tuple[List[str], List[str], str]] = [
    # Node.js — check before Next.js so Next.js can override
    (["package.json"], ["node_modules"], "Node.js"),
    # Next.js (also has package.json, detected by next.config.*)
    (["next.config.js", "next.config.mjs", "next.config.ts"], [".next", "node_modules"], "Next.js"),
    # Python
    (["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"], [".venv", "venv", "__pycache__", ".tox", ".mypy_cache", ".pytest_cache"], "Python"),
    # Rust
    (["Cargo.toml"], ["target"], "Rust"),
    # Go
    (["go.mod"], ["vendor"], "Go"),
    # Java / Maven
    (["pom.xml"], ["target"], "Java/Maven"),
    # Java / Gradle
    (["build.gradle", "build.gradle.kts"], ["build", ".gradle"], "Java/Gradle"),
    # .NET
    (["*.csproj", "*.sln"], ["bin", "obj"], ".NET"),
    # Flutter / Dart
    (["pubspec.yaml"], ["build", ".dart_tool"], "Flutter"),
    # Ruby
    (["Gemfile"], ["vendor/bundle"], "Ruby"),
]

# Directories to always skip when scanning
SKIP_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", ".venv", "venv", "target", "build",
    ".Trash", ".cache", "Library", "Applications",
    ".local", ".npm", ".cargo", ".rustup",
    "__pycache__", ".tox", ".mypy_cache",
}


@dataclass
class ArtifactDir:
    """A single deletable artifact directory."""
    path: str
    size: int  # bytes


@dataclass
class Project:
    """A detected dev project with its artifacts."""
    path: str
    name: str
    ecosystem: str
    artifacts: List[ArtifactDir] = field(default_factory=list)
    last_modified: Optional[datetime] = None
    git_dirty: Optional[bool] = None

    @property
    def size(self) -> int:
        """Total artifact size in bytes."""
        return sum(a.size for a in self.artifacts)

    @property
    def size_human(self) -> str:
        """Human-readable size string."""
        return format_size(self.size)

    @property
    def age_str(self) -> str:
        """Human-readable age string."""
        if not self.last_modified:
            return "unknown"
        delta = datetime.now() - self.last_modified
        days = delta.days
        if days < 1:
            return "today"
        if days < 30:
            return f"{days}d ago"
        if days < 365:
            months = days // 30
            return f"{months}mo ago"
        years = days // 365
        return f"{years}y ago"


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def get_dir_size(path: str) -> int:
    """Calculate total size of a directory. Fast, using scandir."""
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += get_dir_size(entry.path)
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    return total


def get_last_modified(project_path: str) -> Optional[datetime]:
    """Get the last modified date of a project via git or fallback to mtime."""
    git_dir = os.path.join(project_path, ".git")
    if os.path.isdir(git_dir):
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct"],
                capture_output=True, text=True, timeout=5,
                cwd=project_path,
            )
            if result.returncode == 0 and result.stdout.strip():
                ts = int(result.stdout.strip())
                return datetime.fromtimestamp(ts)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            pass

    # Fallback: newest file mtime in project root (not recursive)
    newest = 0.0
    try:
        with os.scandir(project_path) as it:
            for entry in it:
                try:
                    mtime = entry.stat(follow_symlinks=False).st_mtime
                    if mtime > newest:
                        newest = mtime
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass

    if newest > 0:
        return datetime.fromtimestamp(newest)
    return None


def check_git_dirty(project_path: str) -> Optional[bool]:
    """Check if project has uncommitted git changes."""
    git_dir = os.path.join(project_path, ".git")
    if not os.path.isdir(git_dir):
        return None
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
            cwd=project_path,
        )
        if result.returncode == 0:
            return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def _has_marker(project_path: str, markers: List[str]) -> bool:
    """Check if any marker file exists in the directory."""
    for marker in markers:
        if "*" in marker:
            # Glob pattern like *.csproj
            ext = marker.replace("*", "")
            try:
                for entry in os.scandir(project_path):
                    if entry.name.endswith(ext) and entry.is_file():
                        return True
            except (PermissionError, OSError):
                pass
        else:
            if os.path.exists(os.path.join(project_path, marker)):
                return True
    return False


def detect_ecosystem(project_path: str) -> Optional[Tuple[str, List[str]]]:
    """Detect the ecosystem of a project directory.

    Returns (ecosystem_name, artifact_dir_names) or None.
    """
    # Check Next.js first (it also has package.json)
    for markers, artifacts, name in ECOSYSTEMS:
        if name == "Next.js" and _has_marker(project_path, markers):
            return name, artifacts

    # Then check the rest
    for markers, artifacts, name in ECOSYSTEMS:
        if name == "Next.js":
            continue
        if _has_marker(project_path, markers):
            return name, artifacts

    return None


def find_artifacts(project_path: str, artifact_names: List[str]) -> List[ArtifactDir]:
    """Find artifact directories that exist and have size > 0."""
    found = []
    for name in artifact_names:
        artifact_path = os.path.join(project_path, name)
        if os.path.isdir(artifact_path):
            size = get_dir_size(artifact_path)
            if size > 0:
                found.append(ArtifactDir(path=artifact_path, size=size))
        elif name == "__pycache__":
            # __pycache__ can be nested, find all of them
            for root, dirs, _files in os.walk(project_path):
                # Don't recurse into artifact dirs themselves
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                if os.path.basename(root) == "__pycache__":
                    size = get_dir_size(root)
                    if size > 0:
                        found.append(ArtifactDir(path=root, size=size))
    return found


def scan(
    root: str,
    min_size: int = 0,
    max_depth: int = 5,
    callback=None,
) -> List[Project]:
    """Scan a directory tree for dev projects with cleanable artifacts.

    Args:
        root: Root directory to scan.
        min_size: Minimum artifact size in bytes to include.
        max_depth: Maximum directory depth to search.
        callback: Optional function called with (current_path,) during scan.

    Returns:
        List of Project objects sorted by size (largest first).
    """
    root = os.path.expanduser(root)
    root = os.path.abspath(root)
    projects: List[Project] = []

    def _walk(path: str, depth: int) -> None:
        if depth > max_depth:
            return

        try:
            entries = list(os.scandir(path))
        except (PermissionError, OSError):
            return

        if callback:
            callback(path)

        # Check if this directory is a project
        result = detect_ecosystem(path)
        if result:
            eco_name, artifact_names = result
            artifacts = find_artifacts(path, artifact_names)
            if artifacts:
                total_size = sum(a.size for a in artifacts)
                if total_size >= min_size:
                    project = Project(
                        path=path,
                        name=os.path.basename(path),
                        ecosystem=eco_name,
                        artifacts=artifacts,
                        last_modified=get_last_modified(path),
                        git_dirty=check_git_dirty(path),
                    )
                    projects.append(project)
            # Don't recurse into project subdirectories
            return

        # Recurse into subdirectories
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            if entry.name.startswith("."):
                continue
            if entry.name in SKIP_DIRS:
                continue
            _walk(entry.path, depth + 1)

    _walk(root, 0)

    # Sort by size descending
    projects.sort(key=lambda p: p.size, reverse=True)
    return projects


def delete_artifacts(project: Project) -> int:
    """Delete all artifact directories for a project. Returns bytes freed."""
    import shutil

    freed = 0
    for artifact in project.artifacts:
        try:
            size = artifact.size
            shutil.rmtree(artifact.path)
            freed += size
        except (PermissionError, OSError):
            pass
    return freed
