"""Tests for CLI entry point."""

from contextlib import ExitStack
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from qmdiff.cli import main


class TestCLIHelp:
    def test_help_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "qmdiff" in result.output.lower() or "diff" in result.output.lower()

    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestCLIValidation:
    def test_no_args_shows_help(self):
        runner = CliRunner()
        result = runner.invoke(main, [])
        # Should fail or show usage since no files given
        assert result.exit_code != 0 or "Usage" in result.output

    def test_output_is_required(self):
        runner = CliRunner()
        result = runner.invoke(main, ["old.qmd", "new.qmd"])
        assert result.exit_code != 0
        assert "output" in result.output.lower() or "required" in result.output.lower()

    def test_missing_deps_shows_clean_error(self, tmp_path):
        old = tmp_path / "old.qmd"
        old.write_text("---\ntitle: T\n---\nbody")
        new = tmp_path / "new.qmd"
        new.write_text("---\ntitle: T\n---\nbody")
        runner = CliRunner()
        with patch("shutil.which", return_value=None):
            result = runner.invoke(
                main,
                [str(old), str(new), "--output", str(tmp_path / "diff.pdf")],
            )
        assert result.exit_code == 1
        assert "Missing required tools" in result.output
        assert "pandiff" in result.output

    def test_two_file_mode_requires_two_files(self):
        runner = CliRunner()
        result = runner.invoke(main, ["only-one.qmd", "--output", "out.pdf"])
        assert result.exit_code != 0

    def test_rev_mode_requires_one_file(self):
        runner = CliRunner()
        result = runner.invoke(
            main, ["a.qmd", "b.qmd", "--rev", "v1.0", "--output", "out.pdf"]
        )
        assert result.exit_code != 0

    def test_rev_mode_with_one_file_accepted(self):
        """Validation should pass (will fail at pandiff, but args are valid)."""
        runner = CliRunner()
        # Use mix_stderr=False to capture stderr separately
        result = runner.invoke(
            main,
            ["manuscript.qmd", "--rev", "v1.0", "--output", "out.pdf"],
            catch_exceptions=True,
        )
        # Should get past arg validation — will fail at dep check or file ops
        # but NOT with a usage error about wrong number of files
        if result.exit_code != 0:
            assert "Usage" not in (result.output or "")


class TestYAMLSource:
    """Test that YAML frontmatter is sourced from the correct file."""

    def _mock_deps_and_pipeline(self):
        """Return patches that bypass dep checks and subprocess calls."""
        return [
            patch("qmdiff.cli.check_dependencies"),
            patch(
                "qmdiff.cli.run_pandiff",
                return_value="{++new text++}",
            ),
            patch("qmdiff.cli.render_diff"),
        ]

    def test_two_file_mode_yaml_from_first_file(self, tmp_path):
        """In two-file mode, YAML should come from the first file (OLD)."""
        old = tmp_path / "old.qmd"
        old.write_text("---\ntitle: Old Title\nauthor: Alice\n---\nOld body")
        new = tmp_path / "new.qmd"
        new.write_text("---\ntitle: New Title\nauthor: Bob\n---\nNew body")

        output = tmp_path / "diff.pdf"
        runner = CliRunner()

        with ExitStack() as stack:
            for p in self._mock_deps_and_pipeline():
                stack.enter_context(p)
            result = runner.invoke(
                main,
                [str(old), str(new), "--output", str(output)],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        # Check the intermediate .qmd was written with OLD file's YAML
        diff_qmd = output.with_suffix(".qmd")
        # render_diff deletes it, but we mocked render_diff, so it should exist
        content = diff_qmd.read_text()
        assert "Old Title" in content
        assert "New Title" not in content

    def test_git_mode_yaml_from_current_file(self, tmp_path):
        """In git mode, YAML should come from the current file on disk."""
        current = tmp_path / "manuscript.qmd"
        current.write_text("---\ntitle: Current Title\n---\nCurrent body")

        output = tmp_path / "diff.pdf"
        runner = CliRunner()

        mock_extract = MagicMock(
            return_value=tmp_path / "old.qmd",
        )
        (tmp_path / "old.qmd").write_text("---\ntitle: Old Git Title\n---\nOld")

        with ExitStack() as stack:
            for p in self._mock_deps_and_pipeline():
                stack.enter_context(p)
            stack.enter_context(patch("qmdiff.cli.validate_revision"))
            stack.enter_context(
                patch("qmdiff.cli.extract_file_at_revision", mock_extract)
            )
            result = runner.invoke(
                main,
                [str(current), "--rev", "v1.0", "--output", str(output)],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        content = output.with_suffix(".qmd").read_text()
        assert "Current Title" in content
        assert "Old Git Title" not in content

    def test_yaml_from_overrides_default(self, tmp_path):
        """--yaml-from should override the default YAML source."""
        old = tmp_path / "old.qmd"
        old.write_text("---\ntitle: Old Title\n---\nOld body")
        new = tmp_path / "new.qmd"
        new.write_text("---\ntitle: New Title\n---\nNew body")
        custom = tmp_path / "custom.qmd"
        custom.write_text("---\ntitle: Custom Title\nauthor: Custom\n---\nCustom")

        output = tmp_path / "diff.pdf"
        runner = CliRunner()

        with ExitStack() as stack:
            for p in self._mock_deps_and_pipeline():
                stack.enter_context(p)
            result = runner.invoke(
                main,
                [
                    str(old),
                    str(new),
                    "--output",
                    str(output),
                    "--yaml-from",
                    str(custom),
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        content = output.with_suffix(".qmd").read_text()
        assert "Custom Title" in content
        assert "Old Title" not in content

    def test_yaml_from_nonexistent_file_errors(self, tmp_path):
        old = tmp_path / "old.qmd"
        old.write_text("---\ntitle: T\n---\nbody")
        new = tmp_path / "new.qmd"
        new.write_text("---\ntitle: T\n---\nbody")

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                str(old),
                str(new),
                "--output",
                str(tmp_path / "diff.pdf"),
                "--yaml-from",
                "/nonexistent/file.qmd",
            ],
        )
        assert result.exit_code != 0
