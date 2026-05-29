"""Hidden failToPass suite: ``add`` must return a true sum.

Scoring-side ONLY. This file lives under the fixture's ``hidden/`` tree and is
injected by the local ScoringBackend at scoring time; it is never part of the
run-visible ``base/`` tree.
"""

from __future__ import annotations

from calculator import add


def test_add_sums() -> None:
    assert add(2, 3) == 5


def test_add_zero() -> None:
    assert add(0, 0) == 0
