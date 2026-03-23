"""Tests for CriticMarkup to Pandoc span conversion."""

from qmdiff.criticmarkup import collapse_whitespace, convert_criticmarkup


# --- collapse_whitespace ---


class TestCollapseWhitespace:
    def test_no_whitespace(self):
        assert collapse_whitespace("hello world") == "hello world"

    def test_newline_collapsed_to_space(self):
        assert collapse_whitespace("hello\nworld") == "hello world"

    def test_newline_with_leading_spaces(self):
        assert collapse_whitespace("hello\n   world") == "hello world"

    def test_multiple_newlines(self):
        assert collapse_whitespace("a\n  b\n  c") == "a b c"

    def test_strips_leading_trailing(self):
        assert collapse_whitespace("  hello  ") == "hello"

    def test_empty_string(self):
        assert collapse_whitespace("") == ""

    def test_only_whitespace(self):
        assert collapse_whitespace("  \n  \n  ") == ""


# --- convert_criticmarkup: additions ---


class TestAdditions:
    def test_simple_addition(self):
        assert convert_criticmarkup("{++added++}") == "[added]{.cm-added}"

    def test_addition_with_spaces(self):
        assert convert_criticmarkup("{++some text++}") == "[some text]{.cm-added}"

    def test_addition_multiline(self):
        result = convert_criticmarkup("{++line one\n  line two++}")
        assert result == "[line one line two]{.cm-added}"

    def test_addition_in_context(self):
        result = convert_criticmarkup("before {++added++} after")
        assert result == "before [added]{.cm-added} after"

    def test_multiple_additions(self):
        result = convert_criticmarkup("{++a++} and {++b++}")
        assert result == "[a]{.cm-added} and [b]{.cm-added}"

    def test_addition_with_special_chars(self):
        result = convert_criticmarkup("{++text with $math$ and _italic_++}")
        assert result == "[text with $math$ and _italic_]{.cm-added}"


# --- convert_criticmarkup: deletions ---


class TestDeletions:
    def test_simple_deletion(self):
        assert convert_criticmarkup("{--deleted--}") == "[deleted]{.cm-deleted}"

    def test_deletion_with_spaces(self):
        assert convert_criticmarkup("{--some text--}") == "[some text]{.cm-deleted}"

    def test_deletion_multiline(self):
        result = convert_criticmarkup("{--line one\n  line two--}")
        assert result == "[line one line two]{.cm-deleted}"

    def test_deletion_in_context(self):
        result = convert_criticmarkup("before {--removed--} after")
        assert result == "before [removed]{.cm-deleted} after"


# --- convert_criticmarkup: substitutions ---


class TestSubstitutions:
    def test_simple_substitution(self):
        result = convert_criticmarkup("{~~old~>new~~}")
        assert result == "[old]{.cm-deleted}[new]{.cm-added}"

    def test_substitution_with_spaces(self):
        result = convert_criticmarkup("{~~old text~>new text~~}")
        assert result == "[old text]{.cm-deleted}[new text]{.cm-added}"

    def test_substitution_multiline(self):
        result = convert_criticmarkup("{~~old\n  text~>new\n  text~~}")
        assert result == "[old text]{.cm-deleted}[new text]{.cm-added}"

    def test_substitution_in_context(self):
        result = convert_criticmarkup("before {~~old~>new~~} after")
        assert result == "before [old]{.cm-deleted}[new]{.cm-added} after"


# --- convert_criticmarkup: highlights ---


class TestHighlights:
    def test_simple_highlight(self):
        assert (
            convert_criticmarkup("{==highlighted==}") == "[highlighted]{.cm-highlight}"
        )

    def test_highlight_multiline(self):
        result = convert_criticmarkup("{==line one\n  line two==}")
        assert result == "[line one line two]{.cm-highlight}"


# --- convert_criticmarkup: comments ---


class TestComments:
    def test_simple_comment(self):
        assert convert_criticmarkup("{>>note<<}") == "[note]{.cm-comment}"

    def test_comment_multiline(self):
        result = convert_criticmarkup("{>>line one\n  line two<<}")
        assert result == "[line one line two]{.cm-comment}"


# --- convert_criticmarkup: mixed and edge cases ---


class TestMixedAndEdgeCases:
    def test_no_markup_passthrough(self):
        text = "This is plain text with no markup."
        assert convert_criticmarkup(text) == text

    def test_empty_string(self):
        assert convert_criticmarkup("") == ""

    def test_adjacent_patterns(self):
        result = convert_criticmarkup("{++a++}{--b--}")
        assert result == "[a]{.cm-added}[b]{.cm-deleted}"

    def test_all_pattern_types(self):
        text = "{++add++} {--del--} {~~old~>new~~} {==hi==} {>>note<<}"
        result = convert_criticmarkup(text)
        assert "[add]{.cm-added}" in result
        assert "[del]{.cm-deleted}" in result
        assert "[old]{.cm-deleted}[new]{.cm-added}" in result
        assert "[hi]{.cm-highlight}" in result
        assert "[note]{.cm-comment}" in result

    def test_empty_addition(self):
        assert convert_criticmarkup("{++++}") == "[]{.cm-added}"

    def test_empty_deletion(self):
        assert convert_criticmarkup("{----}") == "[]{.cm-deleted}"

    def test_markdown_preserved_around_markup(self):
        text = "**bold** {++added++} *italic*"
        result = convert_criticmarkup(text)
        assert result == "**bold** [added]{.cm-added} *italic*"

    def test_realistic_pandiff_output(self):
        """Test with markup that looks like real pandiff output."""
        text = (
            "The study was conducted in {--two--}{++three++} cities "
            "across {~~the United States~>North America~~}."
        )
        result = convert_criticmarkup(text)
        assert result == (
            "The study was conducted in [two]{.cm-deleted}[three]{.cm-added} cities "
            "across [the United States]{.cm-deleted}[North America]{.cm-added}."
        )
