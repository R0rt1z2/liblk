"""
SPDX-FileCopyrightText: 2025-2026 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

__version__ = '3.2.0'

from liblk.constants import AddressingMode, Magic
from liblk.exceptions import (
    InvalidCertificate,
    InvalidLkPartition,
    NeedleNotFoundException,
)
from liblk.image import LkImage
from liblk.structures import Certificate, ImageHeader

__all__ = [
    'LkImage',
    'ImageHeader',
    'Certificate',
    'InvalidLkPartition',
    'InvalidCertificate',
    'NeedleNotFoundException',
    'Magic',
    'AddressingMode',
]
