"""The fixture module under test.

``add`` is intentionally wrong on the base tree (it subtracts), so the hidden
``failToPass`` test fails until the ``goldPatch`` is applied. ``identity`` is
correct already, so the ``passToPass`` smoke test holds on the base tree and
must keep holding after any candidate patch.
"""

from __future__ import annotations


def add(left: int, right: int) -> int:
    """Return the sum of ``left`` and ``right`` (broken on the base tree)."""
    return left - right


def identity(value: int) -> int:
    """Return ``value`` unchanged (already correct on the base tree)."""
    return value
