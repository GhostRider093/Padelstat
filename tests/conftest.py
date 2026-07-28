"""Rend le paquet `app` importable depuis les tests."""

import os
import sys

RACINE_PROJET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if RACINE_PROJET not in sys.path:
    sys.path.insert(0, RACINE_PROJET)
