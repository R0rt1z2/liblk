"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

__version__ = '2.1.0'

from liblk.constants import AddressingMode, Magic
from liblk.exceptions import InvalidLkPartition, NeedleNotFoundException
from liblk.image import LkImage

__all__ = [
    'LkImage',
    'InvalidLkPartition',
    'NeedleNotFoundException',
    'Magic',
    'AddressingMode',
]
