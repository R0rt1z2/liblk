"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import struct
from typing import Any, List, Optional, Union

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
        certs: List of certificate partitions associated with this partition
    """

    def __init__(
        self,
        header: LkHeader,
        data: bytes,
        end_offset: int,
        ext_header: Optional[LkExtHeader] = None,
        certs: Optional[List['LkPartition']] = None,
    ):
        """
        Initialize an LK partition.

        Args:
            header: Primary partition header
            data: Raw partition data
            end_offset: End offset of the partition in the image
            ext_header: Optional extended header
            certs: List of certificate partitions associated with this partition
        """
        self.header = header
        self.data = data
        self.end_offset = end_offset
        self.ext_header = ext_header
        self.certs = certs or []

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

    def get_full_bytes(self) -> bytes:
        """
        Get bytes representation of partition with all its certificates.

        Returns:
            Byte representation of this partition followed by all its certificates
        """
        result = bytes(self)

        for cert in self.certs:
            result += bytes(cert)

        return result

    def rebuild(self, new_data: Optional[bytes] = None) -> 'LkPartition':
        """
        Create a new partition with updated data.

        Args:
            new_data: New data to use (if None, uses current data)

        Returns:
            New LkPartition instance with the same headers but updated data
        """
        data_to_use = new_data if new_data is not None else self.data

        return LkPartition(
            header=self.header,
            data=data_to_use,
            end_offset=self.end_offset,
            ext_header=self.ext_header,
            certs=self.certs,
        )

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
            f'has_ext_header={bool(self.ext_header)}, '
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
            and self.ext_header == other.ext_header
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
            Complete binary representation of the partition including header and data
        """
        result = bytearray()
        header_size = self.ext_header.header_size if self.ext_header else 512
        header_bytes = bytearray(512)

        struct.pack_into('<I', header_bytes, 0, self.header.magic)
        struct.pack_into('<I', header_bytes, 4, self.header.data_size)

        name_bytes = self.header.name.encode('utf-8')
        header_bytes[8 : 8 + len(name_bytes)] = name_bytes

        struct.pack_into('<I', header_bytes, 40, self.header.addressing_mode)
        struct.pack_into('<I', header_bytes, 44, self.header.memory_address)

        if self.ext_header:
            struct.pack_into('<I', header_bytes, 48, Magic.EXT_MAGIC)
            struct.pack_into(
                '<I', header_bytes, 52, self.ext_header.header_size
            )
            struct.pack_into(
                '<I', header_bytes, 56, self.ext_header.header_version
            )
            struct.pack_into('<I', header_bytes, 60, self.ext_header.image_type)
            struct.pack_into(
                '<I', header_bytes, 64, self.ext_header.image_list_end
            )
            struct.pack_into('<I', header_bytes, 68, self.ext_header.alignment)
            struct.pack_into(
                '<I', header_bytes, 72, self.ext_header.data_size >> 32
            )
            struct.pack_into(
                '<I', header_bytes, 76, self.ext_header.memory_address >> 32
            )

        result.extend(header_bytes[:header_size])
        result.extend(self.data)

        alignment = self.ext_header.alignment if self.ext_header else 8
        if alignment and len(result) % alignment:
            padding_size = alignment - (len(result) % alignment)
            result.extend(b'\x00' * padding_size)

        return bytes(result)
