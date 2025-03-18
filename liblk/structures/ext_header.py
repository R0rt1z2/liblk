"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional


@dataclass
class LkExtHeader:
    """
    Represents the extended header for an LK (Little Kernel) image partition.

    Attributes:
        header_size: Size of the extended header
        header_version: Version of the extended header
        image_type: Type of the image
        image_list_end: Flag indicating if this is the last image in the list
        alignment: Memory alignment requirement
        data_size: Size of the partition data (extended)
        memory_address: Extended memory address for the partition
    """

    header_size: int
    header_version: int
    image_type: int
    image_list_end: int
    alignment: int
    data_size: int
    memory_address: int

    @classmethod
    def from_bytes(cls, contents: bytes) -> Optional[LkExtHeader]:
        """
        Create an LK extended header from raw bytes.

        Args:
            contents: Raw byte contents containing the extended header

        Returns:
            Parsed LkExtHeader instance, or None if parsing fails
        """
        try:
            header_size = struct.unpack_from('<I', contents)[0]
            header_version = struct.unpack_from('<I', contents, 4)[0]
            image_type = struct.unpack_from('<I', contents, 8)[0]
            image_list_end = struct.unpack_from('<I', contents, 12)[0]
            alignment = struct.unpack_from('<I', contents, 16)[0]

            data_size = struct.unpack_from('<I', contents, 20)[0] << 32
            memory_address = struct.unpack_from('<I', contents, 24)[0] << 32

            return cls(
                header_size=header_size,
                header_version=header_version,
                image_type=image_type,
                image_list_end=image_list_end,
                alignment=alignment,
                data_size=data_size,
                memory_address=memory_address,
            )
        except (struct.error, IndexError):
            return None

    def __str__(self) -> str:
        """
        Generate a string representation of the LK extended header.

        Returns:
            Formatted string with extended header details
        """
        return (
            f'Header Size     : {self.header_size} bytes\n'
            f'Header Version  : {self.header_version}\n'
            f'Image Type      : 0x{self.image_type:08x}\n'
            f'Image List End  : {bool(self.image_list_end)}\n'
            f'Alignment       : {self.alignment} bytes\n'
            f'Data Size       : {self.data_size} bytes\n'
            f'Memory Address  : 0x{self.memory_address:08x}'
        )
