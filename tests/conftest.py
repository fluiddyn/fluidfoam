"""Shared fixtures for the fluidfoam test suite."""

import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True, scope="session")
def _run_from_repo_root():
    """The sample cases are referenced with paths relative to the
    repository root; run the tests from there whatever the launch dir."""
    original = os.getcwd()
    os.chdir(REPO_ROOT)
    yield
    os.chdir(original)