"""Pytest bootstrap: ensure the repo root is importable so `api.api` resolves."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
