"""Root launcher for Boutique Hotel Review AI Analyzer."""

import sys
from pathlib import Path

# Ensure src directory is in Python module search path
SRC_DIR = Path(__file__).parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from analyzer import main

if __name__ == "__main__":
    main()
