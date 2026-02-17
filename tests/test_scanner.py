"""Tests for sweep scanner."""

import os
import tempfile
import pytest
from sweep.scanner import (
    Project,
    ArtifactDir,
    detect_ecosystem,
    find_artifacts,
    format_size,
    get_dir_size,
    scan,
)


# --- format_size ---

def test_format_bytes():
    assert format_size(500) == "500 B"


def test_format_kb():
    assert format_size(2048) == "2.0 KB"


def test_format_mb():
    assert format_size(5 * 1024 * 1024) == "5.0 MB"


def test_format_gb():
    assert format_size(2 * 1024 * 1024 * 1024) == "2.0 GB"


# --- get_dir_size ---

def test_dir_size_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        assert get_dir_size(tmpdir) == 0


def test_dir_size_with_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a 1KB file
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("x" * 1000)
        size = get_dir_size(tmpdir)
        assert size >= 1000


def test_dir_size_nested():
    with tempfile.TemporaryDirectory() as tmpdir:
        sub = os.path.join(tmpdir, "sub")
        os.makedirs(sub)
        with open(os.path.join(sub, "file.txt"), "w") as f:
            f.write("x" * 500)
        size = get_dir_size(tmpdir)
        assert size >= 500


# --- detect_ecosystem ---

def test_detect_node():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "package.json"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Node.js"


def test_detect_nextjs():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "package.json"), "w").close()
        open(os.path.join(tmpdir, "next.config.js"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Next.js"


def test_detect_python():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "pyproject.toml"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Python"


def test_detect_python_requirements():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "requirements.txt"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Python"


def test_detect_rust():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "Cargo.toml"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Rust"


def test_detect_go():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "go.mod"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Go"


def test_detect_java_maven():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "pom.xml"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Java/Maven"


def test_detect_java_gradle():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "build.gradle"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Java/Gradle"


def test_detect_flutter():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "pubspec.yaml"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Flutter"


def test_detect_ruby():
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "Gemfile"), "w").close()
        result = detect_ecosystem(tmpdir)
        assert result is not None
        assert result[0] == "Ruby"


def test_detect_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = detect_ecosystem(tmpdir)
        assert result is None


# --- find_artifacts ---

def test_find_node_modules():
    with tempfile.TemporaryDirectory() as tmpdir:
        nm = os.path.join(tmpdir, "node_modules")
        os.makedirs(nm)
        with open(os.path.join(nm, "pkg.js"), "w") as f:
            f.write("x" * 100)
        artifacts = find_artifacts(tmpdir, ["node_modules"])
        assert len(artifacts) == 1
        assert artifacts[0].size >= 100


def test_find_no_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts = find_artifacts(tmpdir, ["node_modules"])
        assert len(artifacts) == 0


# --- scan ---

def test_scan_finds_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake Node project with node_modules
        proj = os.path.join(tmpdir, "my-app")
        os.makedirs(os.path.join(proj, "node_modules"))
        open(os.path.join(proj, "package.json"), "w").close()
        with open(os.path.join(proj, "node_modules", "dep.js"), "w") as f:
            f.write("x" * 500)

        projects = scan(proj)
        assert len(projects) == 1
        assert projects[0].name == "my-app"
        assert projects[0].ecosystem == "Node.js"
        assert projects[0].size >= 500


def test_scan_skips_empty_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = os.path.join(tmpdir, "empty-proj")
        os.makedirs(proj)
        open(os.path.join(proj, "package.json"), "w").close()
        # node_modules exists but is empty
        os.makedirs(os.path.join(proj, "node_modules"))

        projects = scan(proj)
        assert len(projects) == 0


def test_scan_multiple_projects():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Node project
        node_proj = os.path.join(tmpdir, "web-app")
        os.makedirs(os.path.join(node_proj, "node_modules"))
        open(os.path.join(node_proj, "package.json"), "w").close()
        with open(os.path.join(node_proj, "node_modules", "dep.js"), "w") as f:
            f.write("x" * 1000)

        # Python project
        py_proj = os.path.join(tmpdir, "api")
        os.makedirs(os.path.join(py_proj, ".venv"))
        open(os.path.join(py_proj, "pyproject.toml"), "w").close()
        with open(os.path.join(py_proj, ".venv", "bin"), "w") as f:
            f.write("x" * 500)

        projects = scan(tmpdir)
        assert len(projects) == 2
        ecosystems = {p.ecosystem for p in projects}
        assert "Node.js" in ecosystems
        assert "Python" in ecosystems


def test_scan_min_size_filter():
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = os.path.join(tmpdir, "tiny")
        os.makedirs(os.path.join(proj, "node_modules"))
        open(os.path.join(proj, "package.json"), "w").close()
        with open(os.path.join(proj, "node_modules", "small.js"), "w") as f:
            f.write("x" * 10)

        # min_size = 1MB should filter this out
        projects = scan(tmpdir, min_size=1024 * 1024)
        assert len(projects) == 0


# --- Project properties ---

def test_project_size_human():
    p = Project(
        path="/tmp/test",
        name="test",
        ecosystem="Node.js",
        artifacts=[ArtifactDir(path="/tmp/test/node_modules", size=5 * 1024 * 1024)],
    )
    assert p.size_human == "5.0 MB"


def test_project_size_total():
    p = Project(
        path="/tmp/test",
        name="test",
        ecosystem="Python",
        artifacts=[
            ArtifactDir(path="/tmp/test/.venv", size=100),
            ArtifactDir(path="/tmp/test/__pycache__", size=50),
        ],
    )
    assert p.size == 150
