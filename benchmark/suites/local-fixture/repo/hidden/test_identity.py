"""Hidden passToPass smoke suite: ``identity`` must stay an identity.

Scoring-side ONLY. Holds on the base tree and must keep holding after the
candidate patch, so a regression here flips ``regressed`` to true.
"""

from __future__ import annotations

from calculator import identity


def test_identity_round_trips() -> None:
    assert identity(7) == 7
