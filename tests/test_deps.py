"""Tests for external dependency checking."""

from unittest.mock import patch

import pytest

from qmdiff.deps import check_dependencies, MissingDependencyError


class TestCheckDependencies:
    def test_all_present(self):
        with patch("shutil.which", return_value="/usr/bin/fake"):
            check_dependencies()

    def test_quarto_missing(self):
        def mock_which(cmd):
            if cmd == "quarto":
                return None
            return "/usr/bin/fake"

        with patch("shutil.which", side_effect=mock_which):
            with pytest.raises(MissingDependencyError, match="quarto"):
                check_dependencies()

    def test_error_message_includes_install_hint(self):
        with patch("shutil.which", return_value=None):
            with pytest.raises(MissingDependencyError) as exc_info:
                check_dependencies()
            assert "quarto" in str(exc_info.value)
            assert "quarto.org" in str(exc_info.value)
