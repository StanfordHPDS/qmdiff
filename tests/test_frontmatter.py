"""Tests for YAML frontmatter extraction and filter injection."""

from qmdiff.frontmatter import (
    extract_frontmatter,
    has_format,
    inject_filter,
    assemble_qmd,
)


# --- extract_frontmatter ---


class TestExtractFrontmatter:
    def test_simple_frontmatter(self):
        text = "---\ntitle: Test\nauthor: Me\n---\nBody text"
        yaml, body = extract_frontmatter(text)
        assert yaml == "---\ntitle: Test\nauthor: Me\n---"
        assert body == "Body text"

    def test_no_frontmatter(self):
        text = "Just body text, no YAML."
        yaml, body = extract_frontmatter(text)
        assert yaml == "---\ntitle: Diff\n---"
        assert body == "Just body text, no YAML."

    def test_empty_frontmatter(self):
        text = "---\n---\nBody"
        yaml, body = extract_frontmatter(text)
        assert yaml == "---\n---"
        assert body == "Body"

    def test_frontmatter_with_nested_values(self):
        text = "---\ntitle: Test\nauthor:\n  - name: Alice\n  - name: Bob\n---\nBody"
        yaml, body = extract_frontmatter(text)
        assert "Alice" in yaml
        assert "Bob" in yaml
        assert body == "Body"

    def test_frontmatter_with_blank_line_before_body(self):
        text = "---\ntitle: Test\n---\n\nBody with gap"
        yaml, body = extract_frontmatter(text)
        assert yaml == "---\ntitle: Test\n---"
        assert body == "\nBody with gap"

    def test_dashes_in_body_not_confused(self):
        """A --- in the body should not be treated as frontmatter end."""
        text = "---\ntitle: Test\n---\nBody with --- dashes"
        yaml, body = extract_frontmatter(text)
        assert yaml == "---\ntitle: Test\n---"
        assert "---" in body


# --- inject_filter ---


class TestInjectFilter:
    def test_injects_filter_before_closing(self):
        yaml = "---\ntitle: Test\n---"
        result = inject_filter(yaml, "/path/to/filter.lua")
        assert "filters:" in result
        assert "  - /path/to/filter.lua" in result
        assert result.endswith("---")

    def test_preserves_existing_yaml(self):
        yaml = "---\ntitle: My Paper\nauthor: Me\n---"
        result = inject_filter(yaml, "/path/to/filter.lua")
        assert "title: My Paper" in result
        assert "author: Me" in result

    def test_filter_before_closing_dashes(self):
        yaml = "---\ntitle: Test\n---"
        result = inject_filter(yaml, "/filter.lua")
        lines = result.strip().split("\n")
        assert lines[-1] == "---"
        assert lines[-2] == "  - /filter.lua"
        assert lines[-3] == "filters:"

    def test_merges_with_existing_filters(self):
        yaml = "---\ntitle: Test\nfilters:\n  - existing.lua\n---"
        result = inject_filter(yaml, "/new-filter.lua")
        assert "  - existing.lua" in result
        assert "  - /new-filter.lua" in result
        # Should only have one filters: key
        assert result.count("filters:") == 1

    def test_merges_with_multiple_existing_filters(self):
        yaml = "---\ntitle: Test\nfilters:\n  - a.lua\n  - b.lua\n---"
        result = inject_filter(yaml, "/c.lua")
        assert "  - a.lua" in result
        assert "  - b.lua" in result
        assert "  - /c.lua" in result
        assert result.count("filters:") == 1


# --- has_format ---


class TestHasFormat:
    def test_no_format(self):
        assert has_format("---\ntitle: Test\n---") is False

    def test_simple_format(self):
        assert has_format("---\ntitle: Test\nformat: pdf\n---") is True

    def test_nested_format(self):
        yaml = "---\ntitle: Test\nformat:\n  jasa-pdf:\n    keep-tex: true\n---"
        assert has_format(yaml) is True

    def test_default_yaml(self):
        assert has_format("---\ntitle: Diff\n---") is False


# --- assemble_qmd ---


class TestAssembleQmd:
    def test_combines_yaml_and_body(self):
        yaml = "---\ntitle: Test\n---"
        body = "Some body text"
        result = assemble_qmd(yaml, body, "/filter.lua")
        assert result.startswith("---")
        assert "filters:" in result
        assert "Some body text" in result

    def test_yaml_then_blank_line_then_body(self):
        yaml = "---\ntitle: Test\n---"
        body = "Body"
        result = assemble_qmd(yaml, body, "/filter.lua")
        # Should have a blank line separating YAML from body
        assert "\n\n" in result

    def test_roundtrip_preserves_content(self):
        original = "---\ntitle: Paper\nauthor: Alice\n---\n\nHello world"
        yaml, body = extract_frontmatter(original)
        result = assemble_qmd(yaml, body, "/filter.lua")
        assert "title: Paper" in result
        assert "Hello world" in result
        assert "filters:" in result
