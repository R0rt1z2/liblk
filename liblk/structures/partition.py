"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import struct
from typing import Any, List, Optional, Union

from liblk.constants import Pattern
from liblk.exceptions import InvalidLkPartition, NeedleNotFoundException
from liblk.structures.header import ImageHeader, ImageType


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

    def add_certificate(
        self,
        cert_data: Union[bytes, bytearray],
        cert_type: str = 'cert1',
        image_type: Optional[ImageType] = None,
    ) -> 'LkPartition':
        """
        Add a certificate to this partition.

        Args:
            cert_data: Certificate data
            cert_type: Certificate type ('cert1' or 'cert2')
            image_type: Image type for certificate

        Returns:
            Created certificate partition

        Raises:
            ValueError: If cert_type is invalid
        """
        if cert_type not in ('cert1', 'cert2'):
            raise ValueError(f'Invalid certificate type: {cert_type}')

        base_name = self.header.name
        cert_name = (
            f'{cert_type}_{base_name}' if base_name != 'lk' else cert_type
        )

        cert_header = ImageHeader()
        cert_header.magic = self.header.magic
        cert_header.name = cert_name
        cert_header.data_size = len(cert_data)
        cert_header.memory_address = 0
        cert_header.mode = 0
        cert_header.image_list_end = 0

        if self.header.is_extended:
            cert_header.ext_magic = self.header.ext_magic
            cert_header.hdr_size = 512
            cert_header.hdr_version = 1
            cert_header.alignment = self.header.alignment
        else:
            cert_header.ext_magic = 0
            cert_header.hdr_size = 0
            cert_header.hdr_version = 0
            cert_header.alignment = 0

        if image_type:
            cert_header.image_type = image_type
        else:
            img_type = ImageType()
            img_type._group = ImageType.ImageGroup.GROUP_CERT.value
            if cert_type == 'cert1':
                img_type._id = ImageType.ImageCertType.CERT1.value
            else:
                img_type._id = ImageType.ImageCertType.CERT2.value
            cert_header.image_type = img_type

        cert_partition = LkPartition(
            header=cert_header,
            data=bytes(cert_data),
            end_offset=0,
        )

        self.certs.append(cert_partition)
        return cert_partition

    def remove_certificate(self, cert_type: str) -> bool:
        """
        Remove a certificate from this partition.

        Args:
            cert_type: Certificate type to remove ('cert1' or 'cert2')

        Returns:
            True if certificate was removed, False if not found
        """
        for i, cert in enumerate(self.certs):
            if cert.header.name.startswith(cert_type):
                del self.certs[i]
                return True
        return False

    def apply_patch(
        self,
        needle: Union[str, bytes, bytearray],
        patch: Union[str, bytes, bytearray],
    ) -> None:
        """
        Apply a binary patch to the partition data.

        Args:
            needle: Byte sequence to replace
            patch: Replacement byte sequence

        Raises:
            NeedleNotFoundException: If needle is not found
        """
        needle_bytes = (
            bytes.fromhex(needle) if isinstance(needle, str) else bytes(needle)
        )
        patch_bytes = (
            bytes.fromhex(patch) if isinstance(patch, str) else bytes(patch)
        )

        data_bytearray = bytearray(self._data)
        offset = data_bytearray.find(needle_bytes)
        if offset != -1:
            data_bytearray[offset : offset + len(patch_bytes)] = patch_bytes
            self._data = bytes(data_bytearray)
            self.header.data_size = len(self._data)
        else:
            raise NeedleNotFoundException(needle_bytes)

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

            if header.name.lower() == 'lk':
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

    @classmethod
    def create(
        cls,
        name: str,
        data: Union[bytes, bytearray],
        memory_address: int = 0xffffffff,
        mode: int = 0xffffffff,
        image_type: Optional[ImageType] = None,
        use_extended: bool = False,
        alignment: int = 8,
    ) -> 'LkPartition':
        """
        Create a new LK partition.

        Args:
            name: Partition name
            data: Partition data
            memory_address: Load address in memory
            mode: Addressing mode
            image_type: Image type specification
            use_extended: Use extended header format
            alignment: Data alignment requirement

        Returns:
            New LkPartition instance

        Raises:
            ValueError: If name is too long
        """
        if len(name) > 32:
            raise ValueError(f'Partition name too long: {name}')

        from liblk.constants import Magic

        header = ImageHeader()
        header.magic = Magic.MAGIC
        header.name = name
        header.data_size = len(data)
        header.memory_address = memory_address
        header.mode = mode
        header.image_list_end = 0

        if use_extended:
            header.ext_magic = Magic.EXT_MAGIC
            header.hdr_size = 512
            header.hdr_version = 1
            header.alignment = alignment
        else:
            header.ext_magic = 0
            header.hdr_size = 0
            header.hdr_version = 0
            header.alignment = 0

        if image_type:
            header.image_type = image_type
        else:
            img_type = ImageType()
            img_type._group = ImageType.ImageGroup.GROUP_AP.value
            img_type._id = ImageType.ImageAPType.AP_BIN.value
            header.image_type = img_type

        return cls(
            header=header,
            data=bytes(data),
            end_offset=0,
        )

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
        result = (
            f'Partition Name  : {self.header.name}\n'
            f'Data Size       : {self.header.data_size} bytes\n'
            f'Addressing Mode : 0x{self.header.mode:08x}'
        )

        if self.lk_address is not None:
            result += f'\nMemory Address  : 0x{self.lk_address:08x}'

        return result

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
