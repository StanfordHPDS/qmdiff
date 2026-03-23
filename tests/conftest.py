"""Shared test fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def v1_manuscript(fixtures_dir):
    return (fixtures_dir / "manuscript-v1.qmd").read_text()


@pytest.fixture
def v2_manuscript(fixtures_dir):
    return (fixtures_dir / "manuscript-v2.qmd").read_text()
