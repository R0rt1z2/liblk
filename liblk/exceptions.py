"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from typing import Union


class LkImageError(Exception):
    """Base exception for LK image-related errors."""

    def __init__(self, message: str):
        """
        Initialize the LK image error.

        Args:
            message: Descriptive error message
        """
        super().__init__(message)
        self.message = message


class InvalidLkPartition(LkImageError):
    """
    Raised when an invalid LK partition is encountered.

    Attributes:
        reason: Specific reason for partition invalidity
    """

    def __init__(self, reason: str):
        """
        Initialize the invalid partition error.

        Args:
            reason: Reason for partition invalidity
        """
        super().__init__(f'Invalid LK partition: {reason}')
        self.reason = reason


class NeedleNotFoundException(LkImageError):
    """
    Raised when a specific byte sequence is not found in the LK image.

    Attributes:
        needle: The byte sequence that was not found
    """

    def __init__(self, needle: Union[str, bytes]):
        """
        Initialize the needle not found error.

        Args:
            needle: Byte sequence or hex string that was not found
        """
        needle_repr = needle.hex() if isinstance(needle, bytes) else str(needle)
        super().__init__(f'Needle not found: {needle_repr}')
        self.needle = needle
