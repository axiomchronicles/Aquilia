"""
Test Template Manager (compilation and linting).
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import pickle

from aquilia.templates import (
    TemplateEngine,
    TemplateLoader,
    TemplateManager,
    InMemoryBytecodeCache,
    SandboxPolicy
)


@pytest.fixture
def temp_templates_dir():
    """Create temporary templates directory."""
    temp_dir = tempfile.mkdtemp()
    templates_path = Path(temp_dir) / "templates"
    templates_path.mkdir()
    
    # Valid template
    (templates_path / "valid.html").write_text(
        "<h1>{{ title }}</h1><p>{{ content }}</p>"
    )
    
    # Template with syntax error
    (templates_path / "syntax_error.html").write_text(
        "{{ unclosed "
    )
    
    # Template with undefined variable
    (templates_path / "undefined.html").write_text(
        "<p>{{ defined_var }}</p><p>{{ undefined_var }}</p>"
    )
    
    yield str(templates_path), temp_dir
    
    shutil.rmtree(temp_dir)


@pytest.fixture
def manager(temp_templates_dir):
    """Create template manager."""
    templates_path, _ = temp_templates_dir
    
    loader = TemplateLoader(search_paths=[templates_path])
    cache = InMemoryBytecodeCache()
    engine = TemplateEngine(
        loader=loader,
        bytecode_cache=cache,
        sandbox=True,
        sandbox_policy=SandboxPolicy.strict()
    )
    
    return TemplateManager(engine, loader)


@pytest.mark.asyncio
async def test_compile_all(manager, temp_templates_dir):
    """Test compiling all templates."""
    _, temp_dir = temp_templates_dir
    output_path = Path(temp_dir) / "templates.crous"
    
    result = await manager.compile_all(output_path=str(output_path))
    
    assert result["count"] >= 1  # At least valid.html
    assert "fingerprint" in result
    assert result["fingerprint"].startswith("sha256:")
    assert output_path.exists()
    
    # Verify artifact structure
    with open(output_path, "rb") as f:
        artifact = pickle.load(f)
    
    assert artifact["__format__"] == "crous"
    assert artifact["artifact_type"] == "templates"
    assert "payload" in artifact
    assert "templates" in artifact["payload"]


@pytest.mark.asyncio
async def test_lint_all(manager):
    """Test linting all templates."""
    issues = await manager.lint_all(strict_undefined=True)
    
    # Should find issues
    assert len(issues) > 0
    
    # Should find syntax error
    syntax_errors = [i for i in issues if i.code == "syntax-error"]
    assert len(syntax_errors) >= 1
    
    # Check issue structure
    issue = issues[0]
    assert issue.template_name
    assert issue.severity in ["error", "warning", "info"]
    assert issue.message
    assert issue.code


@pytest.mark.asyncio
async def test_lint_undefined_variables(manager):
    """Test linting detects undefined variables."""
    issues = await manager.lint_all(strict_undefined=True)
    
    undefined_issues = [i for i in issues if i.code == "undefined-variable"]
    
    # Should find undefined_var in undefined.html
    assert len(undefined_issues) >= 1


@pytest.mark.asyncio
async def test_inspect_template(manager):
    """Test inspecting template metadata."""
    info = await manager.inspect("valid.html")
    
    assert info["name"] == "valid.html"
    assert "path" in info
    assert "hash" in info
    assert info["hash"].startswith("sha256:")
    assert info["size"] > 0
    assert "compiled" in info


@pytest.mark.asyncio
async def test_inspect_missing_template(manager):
    """Test inspecting non-existent template."""
    info = await manager.inspect("missing.html")
    
    assert "error" in info
    assert "not found" in info["error"].lower()


def test_compute_hash(manager):
    """Test hash computation."""
    hash1 = manager._compute_hash("content")
    hash2 = manager._compute_hash("content")
    hash3 = manager._compute_hash("different")
    
    assert hash1 == hash2
    assert hash1 != hash3
    assert hash1.startswith("sha256:")


def test_compute_fingerprint(manager):
    """Test fingerprint computation."""
    from aquilia.templates.manager import TemplateMetadata
    
    templates = {
        "t1.html": TemplateMetadata(
            name="t1.html",
            path="/path/t1.html",
            module="users",
            hash="sha256:abc123",
            size=100,
            mtime=123.456
        ),
        "t2.html": TemplateMetadata(
            name="t2.html",
            path="/path/t2.html",
            module="auth",
            hash="sha256:def456",
            size=200,
            mtime=234.567
        )
    }
    
    fp1 = manager._compute_fingerprint(templates)
    fp2 = manager._compute_fingerprint(templates)
    
    assert fp1 == fp2
    assert fp1.startswith("sha256:")
    
    # Change template hash
    templates["t1.html"].hash = "sha256:changed"
    fp3 = manager._compute_fingerprint(templates)
    
    assert fp1 != fp3


def test_lint_issue_to_dict():
    """Test lint issue serialization."""
    from aquilia.templates.manager import TemplateLintIssue
    
    issue = TemplateLintIssue(
        template_name="test.html",
        line=10,
        column=5,
        severity="error",
        message="Test error",
        code="test-error"
    )
    
    data = issue.to_dict()
    
    assert data["template_name"] == "test.html"
    assert data["line"] == 10
    assert data["column"] == 5
    assert data["severity"] == "error"
    assert data["message"] == "Test error"
    assert data["code"] == "test-error"


def test_lint_issue_str():
    """Test lint issue string representation."""
    from aquilia.templates.manager import TemplateLintIssue
    
    issue = TemplateLintIssue(
        template_name="test.html",
        line=10,
        column=5,
        severity="error",
        message="Test error",
        code="test-error"
    )
    
    string = str(issue)
    
    assert "test.html" in string
    assert "10" in string
    assert "5" in string
    assert "error" in string
    assert "Test error" in string
    assert "test-error" in string


@pytest.mark.asyncio
async def test_compile_updates_metadata(manager, temp_templates_dir):
    """Test compilation updates template metadata."""
    _, temp_dir = temp_templates_dir
    output_path = Path(temp_dir) / "templates.crous"
    
    result = await manager.compile_all(output_path=str(output_path))
    
    # Check metadata is present
    assert "templates" in result
    assert len(result["templates"]) > 0
    
    # Load artifact and verify
    with open(output_path, "rb") as f:
        artifact = pickle.load(f)
    
    payload = artifact["payload"]
    templates_meta = payload["templates"]
    
    # Check valid.html metadata
    if "valid.html" in templates_meta:
        meta = templates_meta["valid.html"]
        assert meta["name"] == "valid.html"
        assert "hash" in meta
        assert "compiled_at" in meta
