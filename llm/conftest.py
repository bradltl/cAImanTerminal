"""Make legacy relative fixture paths deterministic from either working directory."""
from pathlib import Path
import os
import pytest

@pytest.fixture(autouse=True)
def benchmark_working_directory(monkeypatch):
    monkeypatch.chdir(Path(__file__).parent)
