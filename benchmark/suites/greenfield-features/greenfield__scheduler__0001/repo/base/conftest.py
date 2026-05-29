"""Make the checkout root importable so ``import task_scheduler`` resolves.

Ships in the run-visible ``base/`` tree; the hidden suite injected at the same
root on the scoring side relies on the same path entry.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
