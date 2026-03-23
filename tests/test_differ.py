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

    def test_sections_not_cross_matched(self):
        """Diffs should not match words across different sections."""
        old = (
            "## Methods\n\n"
            "We conducted a survey of 500 adults.\n\n"
            "## Results\n\n"
            "Of the 500 participants, 487 provided data.\n\n"
            "## Discussion\n\n"
            "Our findings suggest positive outcomes."
        )
        new = (
            "## Methods\n\n"
            "We conducted a survey of 1,200 adults in three cities.\n\n"
            "## Results\n\n"
            "Of the 1,200 participants, 1,147 provided complete data.\n\n"
            "## Discussion\n\n"
            "Our findings suggest positive outcomes across multiple cities."
        )
        result = diff_texts(old, new)

        # Each section header should appear exactly once (not duplicated)
        assert result.count("## Methods") == 1
        assert result.count("## Results") == 1
        assert result.count("## Discussion") == 1

        # The Methods section changes should be near "## Methods"
        methods_pos = result.index("## Methods")
        results_pos = result.index("## Results")
        # "500" deletion should be between Methods and Results
        deleted_500 = result.index("{--500--}")
        assert methods_pos < deleted_500 < results_pos

        # "1,200" addition should also be between Methods and Results
        # (first occurrence — there are two)
        added_1200 = result.index("{++1,200++}")
        assert methods_pos < added_1200 < results_pos

    def test_rewritten_section_stays_together(self):
        """A rewritten section should show as delete-old then insert-new,
        not interleaved with other sections."""
        old = (
            "## Introduction\n\n"
            "This is the old introduction with some text.\n\n"
            "## Methods\n\n"
            "We used a simple method."
        )
        new = (
            "## Introduction\n\n"
            "This is a completely rewritten introduction paragraph.\n\n"
            "## Methods\n\n"
            "We used a simple method."
        )
        result = diff_texts(old, new)

        # Methods section should be unchanged
        assert "## Methods" in result
        assert "{--## Methods--}" not in result
        assert "{++## Methods++}" not in result

        # "We used a simple method." should appear without diff markers
        assert "We used a simple method." in result
        # Make sure it's not marked as added or deleted
        assert "{++We++}" not in result
        assert "{--We--}" not in result

    def test_expanded_manuscript_no_cross_section_matching(self):
        """Real-world test: v2 significantly expands v1 sections.
        Deletions from v1 should not interleave with additions from v2
        in unrelated sections."""
        old = (
            "## Introduction\n\n"
            "Mental health disorders represent a growing public health concern in urban\n"
            "environments worldwide. As urbanization continues to accelerate, understanding\n"
            "the environmental determinants of mental health becomes increasingly important.\n\n"
            "Previous research has suggested that exposure to natural environments may\n"
            "have beneficial effects on psychological well-being. However, the majority\n"
            "of studies have relied on cross-sectional designs, limiting causal inference.\n\n"
            "In this study, we aimed to examine the association between residential\n"
            "proximity to urban green spaces and mental health outcomes in a diverse\n"
            "sample of urban residents.\n\n"
            "## Methods\n\n"
            "### Study Design and Participants\n\n"
            "We conducted a cross-sectional survey of 500 adults residing in a\n"
            "mid-sized European city between January and June 2024. Participants\n"
            "were recruited through random sampling of residential addresses.\n"
            "Inclusion criteria were: age 18 years or older, residence in the\n"
            "study area for at least 12 months, and ability to complete the\n"
            "survey in English.\n\n"
            "### Measures\n\n"
            "Mental health was assessed using the General Health Questionnaire\n"
            "(GHQ-12), a widely used screening instrument for psychological\n"
            "distress. Green space proximity was measured as the Euclidean\n"
            "distance from each participant's residence to the nearest public\n"
            "green space of at least 1 hectare.\n\n"
            "## Results\n\n"
            "Of the 500 participants, 487 provided complete data and were\n"
            "included in the analysis. The mean age was 42.3 years (SD = 14.1),\n"
            "and 52% were female.\n\n"
            "In the adjusted model, each 100-meter decrease in distance to\n"
            "green space was associated with a 0.8-point improvement in GHQ-12\n"
            "scores.\n\n"
            "## Discussion\n\n"
            "Our findings suggest that proximity to urban green spaces is\n"
            "associated with better mental health outcomes. These results are\n"
            "consistent with previous research highlighting the psychological\n"
            "benefits of nature exposure.\n\n"
            "Several limitations should be noted. First, the cross-sectional\n"
            "design precludes causal inference. Second, we relied on\n"
            "self-reported mental health measures.\n\n"
            "## Conclusion\n\n"
            "This study provides evidence supporting the mental health benefits\n"
            "of urban green spaces. Urban planners should consider these findings\n"
            "when designing cities that promote well-being."
        )
        new = (
            "## Introduction\n\n"
            "Mental health disorders represent a growing public health concern in urban\n"
            "environments worldwide. As urbanization continues to accelerate, understanding\n"
            "the environmental determinants of mental health becomes increasingly important.\n"
            "The World Health Organization estimates that over 55% of the global population\n"
            "now lives in urban areas, a figure projected to reach 68% by 2050.\n\n"
            "Previous research has suggested that exposure to natural environments may\n"
            "have beneficial effects on psychological well-being. However, the majority\n"
            "of studies have relied on cross-sectional designs with limited sample sizes,\n"
            "restricting both causal inference and generalizability. A recent meta-analysis\n"
            "by Chen et al. (2024) identified significant heterogeneity in effect sizes\n"
            "across studies, underscoring the need for larger, multi-site investigations.\n\n"
            "In this study, we aimed to examine the association between residential\n"
            "proximity to urban green spaces and mental health outcomes in a diverse,\n"
            "multi-city sample of urban residents, while also exploring potential\n"
            "effect modification by sociodemographic factors.\n\n"
            "## Methods\n\n"
            "### Study Design and Participants\n\n"
            "We conducted a cross-sectional survey of 1,200 adults residing in three\n"
            "mid-sized European cities (Birmingham, Lyon, and Rotterdam) between\n"
            "January and June 2024. Participants were recruited through stratified\n"
            "random sampling of residential addresses, ensuring representation\n"
            "across income quartiles. Inclusion criteria were: age 18 years or older,\n"
            "residence in the study area for at least 12 months, and ability to\n"
            "complete the survey in the local language or English.\n\n"
            "### Measures\n\n"
            "Mental health was assessed using the General Health Questionnaire\n"
            "(GHQ-12), a widely used screening instrument for psychological\n"
            "distress. We additionally administered the WHO-5 Well-Being Index\n"
            "as a secondary outcome measure. Green space proximity was measured\n"
            "as the Euclidean distance from each participant's residence to the\n"
            "nearest public green space of at least 1 hectare, using municipal\n"
            "GIS databases.\n\n"
            "## Results\n\n"
            "Of the 1,200 participants, 1,147 provided complete data and were\n"
            "included in the analysis. The mean age was 44.1 years (SD = 15.3),\n"
            "and 53% were female. The median distance to the nearest green space\n"
            "was 340 meters (IQR: 180--620).\n\n"
            "In the adjusted model, each 100-meter decrease in distance to\n"
            "green space was associated with a 0.6-point improvement in GHQ-12\n"
            "scores. Results were consistent when using the WHO-5 as the outcome measure.\n\n"
            "The association was stronger among participants aged 60 and older\n"
            "compared to younger age groups. We also observed a significant\n"
            "interaction with income, with stronger effects among participants\n"
            "in the lowest income quartile.\n\n"
            "## Discussion\n\n"
            "Our findings suggest that proximity to urban green spaces is\n"
            "associated with better mental health outcomes across multiple\n"
            "European cities. These results are consistent with previous research\n"
            "highlighting the psychological benefits of nature exposure, and\n"
            "extend the evidence base by demonstrating effect modification by\n"
            "socioeconomic status.\n\n"
            "The stronger association observed among lower-income participants\n"
            "is particularly noteworthy, as these populations often have reduced\n"
            "access to green spaces.\n\n"
            "Several limitations should be noted. First, the cross-sectional\n"
            "design precludes causal inference. Second, we relied on\n"
            "self-reported mental health measures, though we mitigated this\n"
            "concern by using two validated instruments. Third, we did not\n"
            "account for the quality or type of green spaces.\n\n"
            "## Conclusion\n\n"
            "This multi-city study provides robust evidence supporting the\n"
            "mental health benefits of urban green spaces, with effects that\n"
            "are particularly pronounced among older adults and lower-income\n"
            "residents. Urban planners and public health practitioners should\n"
            "consider these findings when designing equitable cities that\n"
            "promote population well-being."
        )
        result = diff_texts(old, new)

        # Each section header should appear exactly once
        for header in [
            "## Introduction",
            "## Methods",
            "## Results",
            "## Discussion",
            "## Conclusion",
        ]:
            assert result.count(header) == 1, (
                f"'{header}' appears {result.count(header)} times"
            )

        # Section ordering must be preserved
        intro_pos = result.index("## Introduction")
        methods_pos = result.index("## Methods")
        results_pos = result.index("## Results")
        discussion_pos = result.index("## Discussion")
        conclusion_pos = result.index("## Conclusion")
        assert intro_pos < methods_pos < results_pos < discussion_pos < conclusion_pos

        # Deletions from v1's Discussion should NOT appear after v2's Conclusion
        # (this was the cross-section matching bug)
        conclusion_text_after = result[conclusion_pos:]
        # After Conclusion header, there should be no deleted section headers
        assert "{--##" not in conclusion_text_after
