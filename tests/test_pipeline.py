"""Tests for pipeline orchestrator."""

from unittest.mock import patch, MagicMock

import pytest

from qmdiff.pipeline import get_filter_path, run_pandiff, render_diff, NoDiffError


class TestGetFilterPath:
    def test_returns_lua_file(self):
        path = get_filter_path()
        assert path.suffix == ".lua"
        assert path.name == "diff-highlight.lua"

    def test_file_exists(self):
        assert get_filter_path().exists()


class TestRunPandiff:
    def test_returns_diff_text(self, tmp_path):
        old = tmp_path / "old.qmd"
        new = tmp_path / "new.qmd"
        old.write_text("old content")
        new.write_text("new content")

        result = MagicMock()
        result.returncode = 0
        result.stdout = "{++new content++}"

        with patch("subprocess.run", return_value=result):
            diff = run_pandiff(old, new)
            assert diff == "{++new content++}"

    def test_no_diff_raises(self, tmp_path):
        old = tmp_path / "old.qmd"
        new = tmp_path / "new.qmd"
        old.write_text("same")
        new.write_text("same")

        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        with patch("subprocess.run", return_value=result):
            with pytest.raises(NoDiffError):
                run_pandiff(old, new)

    def test_pandiff_failure_raises(self, tmp_path):
        old = tmp_path / "old.qmd"
        new = tmp_path / "new.qmd"
        old.write_text("old")
        new.write_text("new")

        result = MagicMock()
        result.returncode = 1
        result.stderr = "pandiff error"

        with patch("subprocess.run", return_value=result):
            with pytest.raises(RuntimeError, match="pandiff"):
                run_pandiff(old, new)


class TestRenderDiff:
    def test_calls_quarto_render(self, tmp_path):
        diff_qmd = tmp_path / "test-diff.qmd"
        diff_qmd.write_text("---\ntitle: Test\n---\nBody")
        output = tmp_path / "out.pdf"

        result = MagicMock()
        result.returncode = 0

        with patch("subprocess.run", return_value=result) as mock_run:
            render_diff(diff_qmd, output, "pdf")
            args = mock_run.call_args[0][0]
            assert "quarto" in args
            assert "render" in args
            assert str(diff_qmd) in args

    def test_quarto_failure_raises(self, tmp_path):
        diff_qmd = tmp_path / "test-diff.qmd"
        diff_qmd.write_text("content")
        output = tmp_path / "out.pdf"

        result = MagicMock()
        result.returncode = 1
        result.stderr = "quarto error"

        with patch("subprocess.run", return_value=result):
            with pytest.raises(RuntimeError, match="quarto"):
                render_diff(diff_qmd, output, "pdf")

    def test_cleanup_removes_intermediate(self, tmp_path):
        diff_qmd = tmp_path / "test-diff.qmd"
        diff_qmd.write_text("content")
        output = tmp_path / "out.pdf"

        result = MagicMock()
        result.returncode = 0

        with patch("subprocess.run", return_value=result):
            render_diff(diff_qmd, output, "pdf", keep=False)
            assert not diff_qmd.exists()

    def test_keep_preserves_intermediate(self, tmp_path):
        diff_qmd = tmp_path / "test-diff.qmd"
        diff_qmd.write_text("content")
        output = tmp_path / "out.pdf"

        result = MagicMock()
        result.returncode = 0

        with patch("subprocess.run", return_value=result):
            render_diff(diff_qmd, output, "pdf", keep=True)
            assert diff_qmd.exists()

    def test_no_format_omits_to_flag(self, tmp_path):
        """When fmt is None, --to should not be passed to quarto."""
        diff_qmd = tmp_path / "test-diff.qmd"
        diff_qmd.write_text("content")
        output = tmp_path / "out.pdf"

        result = MagicMock()
        result.returncode = 0

        with patch("subprocess.run", return_value=result) as mock_run:
            render_diff(diff_qmd, output, fmt=None)
            args = mock_run.call_args[0][0]
            assert "--to" not in args

    def test_format_passes_to_flag(self, tmp_path):
        """When fmt is provided, --to should be passed."""
        diff_qmd = tmp_path / "test-diff.qmd"
        diff_qmd.write_text("content")
        output = tmp_path / "out.pdf"

        result = MagicMock()
        result.returncode = 0

        with patch("subprocess.run", return_value=result) as mock_run:
            render_diff(diff_qmd, output, fmt="pdf")
            args = mock_run.call_args[0][0]
            assert "--to" in args
            assert "pdf" in args
