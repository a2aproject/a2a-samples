"""Make the sample's flat modules importable under pytest.

The sample is run as a script from its own directory (``uv run .``), so its modules import
each other as top-level names. pytest, seeing ``__init__.py``, would import this directory as
a package instead; putting it on ``sys.path`` keeps both entry points working.
"""

import sys

from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
