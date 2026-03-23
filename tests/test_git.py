"""Tests for git revision extraction."""

from unittest.mock import patch, MagicMock

import pytest

from qmdiff.git import validate_revision, extract_file_at_revision


class TestValidateRevision:
    def test_valid_revision(self):
        result = MagicMock()
        result.returncode = 0
        with patch("subprocess.run", return_value=result):
            validate_revision("v1.0")

    def test_invalid_revision_raises(self):
        result = MagicMock()
        result.returncode = 128
        result.stderr = "fatal: bad revision"
        with patch("subprocess.run", return_value=result):
            with pytest.raises(ValueError, match="v999"):
                validate_revision("v999")


class TestExtractFileAtRevision:
    def test_extracts_content(self, tmp_path):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "---\ntitle: Old\n---\nOld content"

        with patch("subprocess.run", return_value=result):
            path = extract_file_at_revision("manuscript.qmd", "v1.0", tmp_path)
            assert path.exists()
            assert path.read_text() == "---\ntitle: Old\n---\nOld content"

    def test_returns_temp_file_with_qmd_suffix(self, tmp_path):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "content"

        with patch("subprocess.run", return_value=result):
            path = extract_file_at_revision("manuscript.qmd", "HEAD~1", tmp_path)
            assert path.suffix == ".qmd"

    def test_file_not_at_revision_raises(self, tmp_path):
        result = MagicMock()
        result.returncode = 128
        result.stderr = "fatal: path 'missing.qmd' does not exist"

        with patch("subprocess.run", return_value=result):
            with pytest.raises(FileNotFoundError, match="missing.qmd"):
                extract_file_at_revision("missing.qmd", "v1.0", tmp_path)

    def test_resolves_relative_path(self, tmp_path):
        """Ensure relative paths are resolved against the git root."""
        result = MagicMock()
        result.returncode = 0
        result.stdout = "content"

        with patch("subprocess.run", return_value=result) as mock_run:
            extract_file_at_revision("subdir/file.qmd", "HEAD", tmp_path)
            # The git show call should use the path as given
            call_args = mock_run.call_args_list[0]
            assert "HEAD:subdir/file.qmd" in call_args[0][0]
