"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import ctypes
import struct
from dataclasses import dataclass

from liblk.constants import Pattern


@dataclass
class LkHeader:
    """
    Represents the header of an LK (Little Kernel) image partition.

    Attributes:
        magic: Magic number identifying the header
        data_size: Size of the partition data
        name: Name of the partition
        addressing_mode: Memory addressing mode
        memory_address: Memory address for the partition
    """

    magic: int
    data_size: int
    name: str
    addressing_mode: int
    memory_address: int

    @classmethod
    def from_bytes(cls, contents: bytes, start_offset: int = 0) -> LkHeader:
        """
        Create an LK header from raw bytes.

        Args:
            contents: Raw byte contents containing the header
            start_offset: Starting offset for parsing the header

        Returns:
            Parsed LkHeader instance
        """
        magic = struct.unpack_from('<I', contents, start_offset)[0]
        data_size = struct.unpack_from('<I', contents, start_offset + 4)[0]

        name = (
            contents[start_offset + 8 : start_offset + 40]
            .decode('utf-8')
            .rstrip('\0')
        )

        addressing_mode = ctypes.c_int(
            struct.unpack_from('<I', contents, start_offset + 40)[0]
        ).value
        memory_address = struct.unpack_from('<I', contents, start_offset + 44)[
            0
        ]

        if name == 'lk' and (memory_address & 0xFFFFFFFF) == 0xFFFFFFFF:
            loadaddr_index = contents.find(Pattern.LOADADDR)
            if loadaddr_index != -1:
                memory_address = struct.unpack_from(
                    '<I', contents, loadaddr_index + 8
                )[0]

        return cls(
            magic=magic,
            data_size=data_size,
            name=name,
            addressing_mode=addressing_mode,
            memory_address=memory_address,
        )

    def __str__(self) -> str:
        """
        Generate a string representation of the LK header.

        Returns:
            Formatted string with header details
        """
        return (
            f'Partition Name  : {self.name}\n'
            f'Data Size       : {self.data_size} bytes\n'
            f'Addressing Mode : {self.addressing_mode}\n'
            f'Memory Address  : 0x{self.memory_address:08x}'
        )
