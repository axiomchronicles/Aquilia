"""
Root conftest.py — sets up sys.path for the authentication app.
"""
import sys
import os

# Add repo root and authentication app to sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_APP = os.path.join(REPO_ROOT, "authentication")

for p in [REPO_ROOT, AUTH_APP]:
    if p not in sys.path:
        sys.path.insert(0, p)
