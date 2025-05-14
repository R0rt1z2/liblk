"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import struct
from typing import Any, List, Optional, Union

from liblk.constants import Pattern
from liblk.exceptions import InvalidLkPartition
from liblk.structures.header import ImageHeader


class LkPartition:
    """
    Represents a partition in an LK (Little Kernel) image.

    Attributes:
        header: Primary partition header
        data: Raw partition data
        end_offset: End offset of the partition in the image
        certs: List of certificate partitions associated with this partition
        lk_address: Load address of the LK image. Only set if this is the 'lk' partition, otherwise None.
    """

    def __init__(
        self,
        header: ImageHeader,
        data: bytes,
        end_offset: int,
        certs: Optional[List['LkPartition']] = None,
        lk_address: Optional[int] = None,
    ):
        """
        Initialize an LK partition.

        Args:
            header: Primary partition header
            data: Raw partition data
            end_offset: End offset of the partition in the image
            certs: List of certificate partitions associated with this partition
        """
        self.header = header
        self._data = data
        self.end_offset = end_offset
        self.certs = certs or []
        self.lk_address = lk_address

    @property
    def cert1(self) -> Optional['LkPartition']:
        """Get the first certificate (cert1) if available"""
        return self.certs[0] if len(self.certs) >= 1 else None

    @property
    def cert2(self) -> Optional['LkPartition']:
        """Get the second certificate (cert2) if available"""
        return self.certs[1] if len(self.certs) >= 2 else None

    def has_cert(self, cert_type: str = '') -> bool:
        """
        Check if the partition has certificates of the specified type.

        Args:
            cert_type: Certificate type to check for (e.g., 'cert1', 'cert2').
                       If empty, checks for any certificates.

        Returns:
            True if matching certificates exist
        """
        if not cert_type:
            return len(self.certs) > 0

        for cert in self.certs:
            if cert.header.name.startswith(cert_type):
                return True
        return False

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
            header_contents = contents[start_offset : start_offset + 512]
            header = ImageHeader.from_buffer_copy(header_contents)

            assert header.is_header, (
                f'Invalid magic 0x{header.magic:x} at offset 0x{offset:x}'
            )

            end_offset = header.end_offset(offset)

            alignment = header.alignment if header.is_extended else 8
            if alignment and end_offset % alignment:
                end_offset += alignment - (end_offset % alignment)

            partition_data = contents[
                header.size : header.size + header.data_size
            ]

            if header.name == 'lk':
                lk_address = header.memory_address
                if (lk_address & 0xFFFFFFFF) == 0xFFFFFFFF:
                    loadaddr_index = contents.find(Pattern.LOADADDR)
                    if loadaddr_index != -1:
                        lk_address = struct.unpack_from(
                            '<I', contents, loadaddr_index + 8
                        )[0]
            else:
                lk_address = None

            return cls(
                header=header,
                data=partition_data,
                end_offset=end_offset,
                lk_address=lk_address,
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

    @property
    def data(self) -> bytes:
        """
        Get the raw data of the partition.

        Returns:
            Raw partition data
        """
        return self._data

    @data.setter
    def data(self, value: bytes) -> None:
        """
        Set the raw data of the partition.

        Args:
            value: New raw partition data
        """
        self._data = value
        self.header.data_size = len(value)

    def __str__(self) -> str:
        """
        Generate a string representation of the LK partition.

        Returns:
            Formatted string with partition details
        """
        return (
            f'Partition Name  : {self.header.name}\n'
            f'Data Size       : {self.header.data_size} bytes\n'
            f'Addressing Mode : 0x{self.header.mode:08x}\n'
            f'Memory Address  : 0x{self.lk_address:08x}'
        )

    def __repr__(self) -> str:
        """
        Provide a detailed string representation of the partition.

        Returns:
            Descriptive string with partition details
        """
        return (
            f'LkPartition(name={self.header.name}, '
            f'data_size={len(self.data)}, '
            f'has_ext_header={bool(self.header.is_extended)}, '
            f'certs={len(self.certs)})'
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
            and self.certs == other.certs
        )

    def __len__(self) -> int:
        """
        Get the size of the partition data.

        Returns:
            Size of partition data in bytes
        """
        return len(self.data)

    def __bytes__(self) -> bytes:
        """
        Convert the partition to bytes.

        Returns:
            Complete binary representation of the partition including header, data
            and certificate data.
        """
        if self.header.data_size != len(self.data):
            # If you are hitting this, please change your
            # code to use the `data` property instead of
            # accessing _data and header.data_size directly.
            raise ValueError(
                f'Header data size {self.header.data_size} does not match '
                f'actual data size {len(self.data)}'
            )

        alignment = self.header.alignment if self.header.is_extended else 8
        if alignment and self.header.data_size % alignment:
            padding_size = alignment - (self.header.data_size % alignment)
        else:
            padding_size = 0

        return (
            bytes(self.header)
            + bytes(self.data)
            + b'\x00' * padding_size
            + b''.join(bytes(cert) for cert in self.certs)
        )
