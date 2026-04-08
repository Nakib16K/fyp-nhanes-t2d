# ============================================================
# PYTEST CONFIGURATION — PATH SETUP
# ============================================================
# Inserts the project root into sys.path so that src/ and api/
# are importable as packages during test collection.
# This file must sit at the project root alongside main.py.
# ============================================================

import sys
import os

# Add project root to path — makes 'src' and 'api' importable
sys.path.insert(0, os.path.dirname(__file__))