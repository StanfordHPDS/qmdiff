"""Tests for the tokenizer and word-level differ."""

from qmdiff.differ import tokenize, diff_texts


# --- tokenize: basic words ---


class TestTokenizeWords:
    def test_simple_words(self):
        assert tokenize("hello world") == ["hello", " ", "world"]

    def test_preserves_multiple_spaces(self):
        tokens = tokenize("hello  world")
        assert "hello" in tokens
        assert "world" in tokens

    def test_empty_string(self):
        assert tokenize("") == []

    def test_newlines_preserved(self):
        tokens = tokenize("hello\nworld")
        assert "hello" in tokens
        assert "world" in tokens
        # newline should be in the whitespace tokens
        joined = "".join(tokens)
        assert "\n" in joined


# --- tokenize: inline code ---


class TestTokenizeInlineCode:
    def test_inline_code_is_atomic(self):
        tokens = tokenize("Use `dplyr::filter()` here")
        assert "`dplyr::filter()`" in tokens

    def test_inline_code_with_spaces(self):
        tokens = tokenize("Use `x + y` here")
        assert "`x + y`" in tokens

    def test_multiple_inline_code(self):
        tokens = tokenize("`a` and `b`")
        assert "`a`" in tokens
        assert "`b`" in tokens


# --- tokenize: citations ---


class TestTokenizeCitations:
    def test_single_citation(self):
        tokens = tokenize("See [@ref1] for details")
        assert "[@ref1]" in tokens

    def test_multiple_citations_in_group(self):
        tokens = tokenize("See [@ref1; @ref2; @ref3] for details")
        assert "[@ref1; @ref2; @ref3]" in tokens

    def test_citation_with_semicolons_no_spaces(self):
        tokens = tokenize("[@ref1;@ref2;@ref3]")
        assert "[@ref1;@ref2;@ref3]" in tokens

    def test_citation_with_prefix(self):
        tokens = tokenize("See [e.g., @ref1; @ref2] here")
        assert "[e.g., @ref1; @ref2]" in tokens


# --- tokenize: cross-references ---


class TestTokenizeCrossRefs:
    def test_section_ref(self):
        tokens = tokenize("See @sec-methods for details")
        assert "@sec-methods" in tokens

    def test_figure_ref(self):
        tokens = tokenize("See @fig-plot for details")
        assert "@fig-plot" in tokens

    def test_table_ref(self):
        tokens = tokenize("See @tbl-results for details")
        assert "@tbl-results" in tokens


# --- tokenize: math ---


class TestTokenizeMath:
    def test_inline_math(self):
        tokens = tokenize("The formula $x + y = z$ is simple")
        assert "$x + y = z$" in tokens

    def test_display_math(self):
        tokens = tokenize("Before\n$$\nx + y = z\n$$\nAfter")
        assert "$$\nx + y = z\n$$" in tokens

    def test_inline_math_with_subscripts(self):
        tokens = tokenize("where $x_i$ is the value")
        assert "$x_i$" in tokens


# --- tokenize: fenced code blocks ---


class TestTokenizeCodeBlocks:
    def test_r_code_block(self):
        text = "Prose.\n\n```{r}\nlibrary(dplyr)\nx <- 1\n```\n\nMore prose."
        tokens = tokenize(text)
        code_tokens = [t for t in tokens if t.startswith("```")]
        assert len(code_tokens) == 1
        assert "library(dplyr)" in code_tokens[0]
        assert "x <- 1" in code_tokens[0]

    def test_python_code_block(self):
        text = "Text.\n\n```{python}\nimport pandas\n```\n\nMore."
        tokens = tokenize(text)
        code_tokens = [t for t in tokens if t.startswith("```")]
        assert len(code_tokens) == 1
        assert "import pandas" in code_tokens[0]

    def test_code_block_with_options(self):
        text = "Text.\n\n```{r}\n#| label: fig-plot\n#| fig-cap: A plot\nplot(x)\n```\n\nMore."
        tokens = tokenize(text)
        code_tokens = [t for t in tokens if t.startswith("```")]
        assert len(code_tokens) == 1
        assert "#| label: fig-plot" in code_tokens[0]

    def test_plain_code_block(self):
        text = "Text.\n\n```\nsome code\n```\n\nMore."
        tokens = tokenize(text)
        code_tokens = [t for t in tokens if t.startswith("```")]
        assert len(code_tokens) == 1


# --- tokenize: shortcodes ---


class TestTokenizeShortcodes:
    def test_include_shortcode(self):
        tokens = tokenize("Text {{< include intro.qmd >}} more")
        assert "{{< include intro.qmd >}}" in tokens

    def test_embed_shortcode(self):
        tokens = tokenize("Text {{< embed notebook.ipynb#fig-1 >}} more")
        assert "{{< embed notebook.ipynb#fig-1 >}}" in tokens


# --- tokenize: roundtrip ---


class TestTokenizeRoundtrip:
    """Joining tokens must reproduce the original text exactly."""

    def test_simple_text(self):
        text = "Hello world, this is a test."
        assert "".join(tokenize(text)) == text

    def test_complex_document(self):
        text = (
            "See [@ref1; @ref2] and $x + y$.\n\n"
            "```{r}\nx <- 1\n```\n\n"
            "Use `filter()` per @sec-methods."
        )
        assert "".join(tokenize(text)) == text

    def test_with_shortcodes(self):
        text = "Before {{< include file.qmd >}} after."
        assert "".join(tokenize(text)) == text


# --- diff_texts: prose changes ---


class TestDiffTextsProseChanges:
    def test_no_changes(self):
        text = "The quick brown fox."
        result = diff_texts(text, text)
        assert result == text

    def test_word_addition(self):
        old = "The brown fox."
        new = "The quick brown fox."
        result = diff_texts(old, new)
        assert "{++quick++}" in result
        assert "brown fox." in result

    def test_word_deletion(self):
        old = "The quick brown fox."
        new = "The brown fox."
        result = diff_texts(old, new)
        assert "{--quick--}" in result

    def test_word_replacement(self):
        old = "The quick brown fox."
        new = "The slow brown fox."
        result = diff_texts(old, new)
        assert "{--quick--}" in result
        assert "{++slow++}" in result

    def test_multiple_changes(self):
        old = "The study had two groups in three cities."
        new = "The experiment had four groups in five cities."
        result = diff_texts(old, new)
        assert "{--study--}" in result
        assert "{++experiment++}" in result
        assert "{--two--}" in result
        assert "{++four++}" in result
        assert "{--three--}" in result
        assert "{++five++}" in result


# --- diff_texts: code blocks preserved ---


class TestDiffTextsCodeBlocks:
    def test_unchanged_code_block(self):
        old = "Prose.\n\n```{r}\nx <- 1\n```\n\nMore."
        new = "Prose.\n\n```{r}\nx <- 1\n```\n\nMore."
        result = diff_texts(old, new)
        assert "```{r}\nx <- 1\n```" in result

    def test_changed_code_uses_new_version(self):
        old = "Prose.\n\n```{r}\nx <- 1\n```\n\nMore."
        new = "Prose.\n\n```{r}\nx <- 1\ny <- 2\n```\n\nMore."
        result = diff_texts(old, new)
        assert "y <- 2" in result
        # No diff markup inside code
        assert "{++" not in result.split("```")[1]
        assert "{--" not in result.split("```")[1]

    def test_prose_around_code_still_diffed(self):
        old = "Old prose.\n\n```{r}\nx <- 1\n```\n\nOld ending."
        new = "New prose.\n\n```{r}\nx <- 1\n```\n\nNew ending."
        result = diff_texts(old, new)
        assert "{--Old--}" in result or "{--Old prose.--}" in result
        assert "{++New++}" in result or "{++New prose.++}" in result


# --- diff_texts: citations preserved ---


class TestDiffTextsCitations:
    def test_citation_unchanged(self):
        old = "See [@ref1; @ref2] for details."
        new = "See [@ref1; @ref2] for details."
        result = diff_texts(old, new)
        assert "[@ref1; @ref2]" in result

    def test_citation_group_changed(self):
        old = "See [@ref1; @ref2] for details."
        new = "See [@ref1; @ref2; @ref3] for details."
        result = diff_texts(old, new)
        # The whole citation group should be replaced atomically
        assert "{--[@ref1; @ref2]--}" in result
        assert "{++[@ref1; @ref2; @ref3]++}" in result

    def test_prose_around_citation_diffed(self):
        old = "Results [@ref1] were clear."
        new = "Results [@ref1] were very clear."
        result = diff_texts(old, new)
        assert "[@ref1]" in result
        assert "{++very++}" in result


# --- diff_texts: cross-references preserved ---


class TestDiffTextsCrossRefs:
    def test_crossref_unchanged(self):
        old = "See @sec-methods for details."
        new = "See @sec-methods for details."
        result = diff_texts(old, new)
        assert "@sec-methods" in result

    def test_crossref_added(self):
        old = "See @sec-methods for details."
        new = "See @sec-methods and @sec-results for details."
        result = diff_texts(old, new)
        assert "@sec-methods" in result
        assert "@sec-results" in result


# --- diff_texts: math preserved ---


class TestDiffTextsMath:
    def test_inline_math_unchanged(self):
        old = "The formula $x + y = z$ is simple."
        new = "The formula $x + y = z$ is simple."
        result = diff_texts(old, new)
        assert "$x + y = z$" in result

    def test_inline_math_changed(self):
        old = "The formula $x + y = z$ is simple."
        new = "The formula $x + y + w = z$ is simple."
        result = diff_texts(old, new)
        # Math should be replaced atomically
        assert "{--$x + y = z$--}" in result
        assert "{++$x + y + w = z$++}" in result

    def test_math_not_split(self):
        """Diff markers should never appear inside math delimiters."""
        old = "Where $x + y = z$ holds."
        new = "Where $x + y + w = z$ holds."
        result = diff_texts(old, new)
        # No diff markup should be inside a $...$ span
        import re

        math_spans = re.findall(r"\$[^$]+\$", result)
        for span in math_spans:
            assert "{++" not in span
            assert "{--" not in span


# --- diff_texts: inline code preserved ---


class TestDiffTextsInlineCode:
    def test_inline_code_unchanged(self):
        old = "Use `filter()` here."
        new = "Use `filter()` here."
        result = diff_texts(old, new)
        assert "`filter()`" in result

    def test_inline_code_changed(self):
        old = "Use `dplyr::filter()` here."
        new = "Use `dplyr::select()` here."
        result = diff_texts(old, new)
        assert "{--`dplyr::filter()`--}" in result
        assert "{++`dplyr::select()`++}" in result


# --- diff_texts: realistic manuscript ---


class TestDiffTextsRealisticManuscript:
    def test_academic_paragraph(self):
        old = (
            "We applied the method of @smith2020 to analyze "
            "the data [@jones2019; @lee2021]. Results are in @fig-results "
            "and @tbl-summary. The model $y = \\beta_0 + \\beta_1 x$ was fit "
            "using `lm()` in R.\n\n"
            "```{r}\n#| label: fig-results\nplot(x, y)\n```\n\n"
            "The results were significant."
        )
        new = (
            "We applied the approach of @smith2020 to analyze "
            "the data [@jones2019; @lee2021; @chen2023]. Results are in @fig-results "
            "and @tbl-summary. The model $y = \\beta_0 + \\beta_1 x + \\beta_2 z$ was fit "
            "using `glm()` in R.\n\n"
            "```{r}\n#| label: fig-results\nplot(x, y, col='red')\n```\n\n"
            "The results were highly significant."
        )
        result = diff_texts(old, new)

        # Prose diffs
        assert "{--method--}" in result
        assert "{++approach++}" in result

        # Citations atomic
        assert "{--[@jones2019; @lee2021]--}" in result
        assert "{++[@jones2019; @lee2021; @chen2023]++}" in result

        # Cross-refs intact
        assert "@fig-results" in result
        assert "@tbl-summary" in result

        # Math atomic
        assert "{--$y = \\beta_0 + \\beta_1 x$--}" in result
        assert "{++$y = \\beta_0 + \\beta_1 x + \\beta_2 z$++}" in result

        # Inline code atomic
        assert "{--`lm()`--}" in result
        assert "{++`glm()`++}" in result

        # Code block uses new version, no diff markup inside
        assert "plot(x, y, col='red')" in result
        code_section = result.split("```{r}")[1].split("```")[0]
        assert "{++" not in code_section
        assert "{--" not in code_section

        # Unchanged cross-ref not wrapped in diff
        assert "{--@smith2020--}" not in result
