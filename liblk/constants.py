"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from enum import IntEnum, unique
from typing import Final


@unique
class Magic(IntEnum):
    """Magic numbers used in LK image headers."""

    MAGIC = 0x58881688
    EXT_MAGIC = 0x58891689


@unique
class AddressingMode(IntEnum):
    """Addressing modes for memory addressing."""

    NORMAL = -1
    BACKWARD = 0


class Pattern:
    """Constant patterns used in LK image parsing."""

    LOADADDR: Final[bytes] = bytes.fromhex('10FF2FE1')
