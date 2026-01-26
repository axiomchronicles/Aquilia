"""
Test Template Loader functionality.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from aquilia.templates import TemplateLoader
from jinja2 import TemplateNotFound


@pytest.fixture
def temp_templates_dir():
    """Create temporary templates directory."""
    temp_dir = tempfile.mkdtemp()
    templates_path = Path(temp_dir) / "templates"
    templates_path.mkdir()
    
    # Create test templates
    (templates_path / "base.html").write_text("<html>{{ content }}</html>")
    (templates_path / "page.html").write_text("Page content")
    
    # Module templates
    for module in ["users", "auth"]:
        module_path = templates_path / module
        module_path.mkdir()
        (module_path / "index.html").write_text(f"<h1>{module}</h1>")
    
    yield str(templates_path)
    
    shutil.rmtree(temp_dir)


def test_loader_creation(temp_templates_dir):
    """Test loader creation."""
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    
    assert len(loader.search_paths) == 1


def test_load_simple_template(temp_templates_dir):
    """Test loading simple template."""
    from jinja2 import Environment
    
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    env = Environment(loader=loader)
    
    source, filename, uptodate = loader.get_source(env, "base.html")
    
    assert "<html>" in source
    assert filename is not None
    assert callable(uptodate)


def test_load_module_template(temp_templates_dir):
    """Test loading module-namespaced template."""
    from jinja2 import Environment
    
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    env = Environment(loader=loader)
    
    source, filename, uptodate = loader.get_source(env, "users/index.html")
    
    assert "<h1>users</h1>" in source


def test_load_missing_template(temp_templates_dir):
    """Test loading non-existent template."""
    from jinja2 import Environment
    
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    env = Environment(loader=loader)
    
    with pytest.raises(TemplateNotFound):
        loader.get_source(env, "missing.html")


def test_list_templates(temp_templates_dir):
    """Test listing all templates."""
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    
    templates = loader.list_templates()
    
    assert "base.html" in templates
    assert "page.html" in templates
    assert "users/index.html" in templates
    assert "auth/index.html" in templates


def test_parse_template_name_simple():
    """Test parsing simple template name."""
    loader = TemplateLoader()
    
    module, path = loader._parse_template_name("simple.html")
    
    assert module is None
    assert path == "simple.html"


def test_parse_template_name_module():
    """Test parsing module-namespaced template name."""
    loader = TemplateLoader()
    
    module, path = loader._parse_template_name("users/profile.html")
    
    assert module == "users"
    assert path == "profile.html"


def test_parse_template_name_qualified():
    """Test parsing fully-qualified template name."""
    loader = TemplateLoader()
    
    module, path = loader._parse_template_name("users:profile.html")
    
    assert module == "users"
    assert path == "profile.html"


def test_parse_template_name_cross_module():
    """Test parsing cross-module template name."""
    loader = TemplateLoader()
    
    module, path = loader._parse_template_name("@auth/login.html")
    
    assert module == "auth"
    assert path == "login.html"


def test_multiple_search_paths():
    """Test loader with multiple search paths."""
    temp_dir1 = tempfile.mkdtemp()
    temp_dir2 = tempfile.mkdtemp()
    
    try:
        # Create templates in different directories
        (Path(temp_dir1) / "template1.html").write_text("Template 1")
        (Path(temp_dir2) / "template2.html").write_text("Template 2")
        
        loader = TemplateLoader(search_paths=[temp_dir1, temp_dir2])
        
        templates = loader.list_templates()
        
        assert "template1.html" in templates
        assert "template2.html" in templates
    
    finally:
        shutil.rmtree(temp_dir1)
        shutil.rmtree(temp_dir2)


def test_template_file_extensions():
    """Test template file extension detection."""
    loader = TemplateLoader()
    
    assert loader._is_template_file("page.html")
    assert loader._is_template_file("page.htm")
    assert loader._is_template_file("doc.xml")
    assert loader._is_template_file("email.txt")
    assert loader._is_template_file("template.jinja")
    assert loader._is_template_file("template.jinja2")
    assert loader._is_template_file("template.j2")
    
    assert not loader._is_template_file("script.py")
    assert not loader._is_template_file("style.css")
    assert not loader._is_template_file("data.json")
