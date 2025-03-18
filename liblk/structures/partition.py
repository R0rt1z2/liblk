"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import struct
from typing import Any, Optional, Union

from liblk.constants import Magic
from liblk.exceptions import InvalidLkPartition
from liblk.structures.ext_header import LkExtHeader
from liblk.structures.header import LkHeader


class LkPartition:
    """
    Represents a partition in an LK (Little Kernel) image.

    Attributes:
        header: Primary partition header
        ext_header: Optional extended header
        data: Raw partition data
        end_offset: End offset of the partition in the image
    """

    def __init__(
        self,
        header: LkHeader,
        data: bytes,
        end_offset: int,
        ext_header: Optional[LkExtHeader] = None,
    ):
        """
        Initialize an LK partition.

        Args:
            header: Primary partition header
            data: Raw partition data
            end_offset: End offset of the partition in the image
            ext_header: Optional extended header
        """
        self.header = header
        self.data = data
        self.end_offset = end_offset
        self.ext_header = ext_header

    @property
    def has_ext(self) -> bool:
        """
        Check if the partition has an extended header.

        Returns:
            True if extended header exists, False otherwise
        """
        return self.ext_header is not None

    @classmethod
    def from_bytes(
        cls, contents: Union[bytes, bytearray], offset: int = 0
    ) -> LkPartition:
        """
        Create an LK partition from raw bytes.

        Args:
            contents: Raw byte contents of the image
            offset: Starting offset for parsing the partition

        Returns:
            Parsed LkPartition instance

        Raises:
            InvalidLkPartition: If the partition is invalid
        """
        start_offset = 0x4040 if contents[:4] == b'BFBF' else 0

        try:
            header = LkHeader.from_bytes(contents, start_offset)

            has_ext = (
                struct.unpack_from('<I', contents, start_offset + 48)[0]
                == Magic.EXT_MAGIC
            )
            ext_header = (
                LkExtHeader.from_bytes(contents[start_offset + 52 :])
                if has_ext
                else None
            )

            data_size = header.data_size | (
                ext_header.data_size if ext_header else 0
            )

            header_size = ext_header.header_size if ext_header else 512
            end_offset = offset + header_size + data_size

            alignment = ext_header.alignment if ext_header else 8
            if alignment and end_offset % alignment:
                end_offset += alignment - (end_offset % alignment)

            partition_data = contents[header_size : header_size + data_size]

            return cls(
                header=header,
                data=partition_data,
                end_offset=end_offset,
                ext_header=ext_header,
            )

        except Exception as e:
            raise InvalidLkPartition(
                f'Failed to parse partition: {str(e)}'
            ) from e

    def save(self, filename: str) -> None:
        """
        Save partition data to a file.

        Args:
            filename: Path to save the partition data
        """
        with open(filename, 'wb') as f:
            f.write(self.data)

    def __str__(self) -> str:
        """
        Generate a string representation of the LK partition.

        Returns:
            Formatted string with partition details
        """
        details = [str(self.header)]
        if self.ext_header:
            details.append(str(self.ext_header))
        return '\n'.join(details)

    def __repr__(self) -> str:
        """
        Provide a detailed string representation of the partition.

        Returns:
            Descriptive string with partition details
        """
        return (
            f'LkPartition(name={self.header.name}, '
            f'data_size={len(self.data)}, '
            f'has_ext_header={bool(self.ext_header)})'
        )

    def __eq__(self, other: Any) -> bool:
        """
        Compare two LkPartition instances for equality.

        Args:
            other: Another object to compare with

        Returns:
            True if partitions are considered equal, False otherwise
        """
        if not isinstance(other, LkPartition):
            return False

        return (
            self.header == other.header
            and self.data == other.data
            and self.ext_header == other.ext_header
        )

    def __len__(self) -> int:
        """
        Get the size of the partition data.

        Returns:
            Size of partition data in bytes
        """
        return len(self.data)
