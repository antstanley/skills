"""Make the checkout root importable so ``import text_toolkit`` resolves.

Present in the run-visible ``base/`` tree so the skeleton's smoke test runs;
the hidden suite (injected at the same root on the scoring side) relies on the
same path entry.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
