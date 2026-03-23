"""External dependency checking."""

import shutil


class MissingDependencyError(RuntimeError):
    """Raised when a required external tool is not found."""


_REQUIRED = {
    "pandiff": "npm install -g pandiff",
    "quarto": "https://quarto.org/docs/get-started/",
}


def check_dependencies() -> None:
    """Check that all required external tools are available.

    Raises MissingDependencyError with install hints on failure.
    """
    missing = []
    for cmd, hint in _REQUIRED.items():
        if shutil.which(cmd) is None:
            missing.append(f"  {cmd}: {hint}")

    if missing:
        detail = "\n".join(missing)
        raise MissingDependencyError(f"Missing required tools:\n{detail}")
