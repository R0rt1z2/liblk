"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Optional, Union, overload

from liblk.constants import Magic
from liblk.exceptions import InvalidLkPartition, NeedleNotFoundException
from liblk.structures.partition import LkPartition


class LkImage:
    """
    Represents an LK (Little Kernel) image for parsing and manipulation.

    Attributes:
        path: Optional path to the original image file
        contents: Raw image contents
        partitions: List of parsed partitions
    """

    @overload
    def __init__(self, source: Union[str, Path]) -> None: ...

    @overload
    def __init__(self, source: Union[bytes, bytearray]) -> None: ...

    def __init__(
        self,
        source: Union[str, Path, bytes, bytearray],
    ) -> None:
        """
        Initialize LK image from file or byte-like object.

        Args:
            source: Image source (file path or byte-like object)

        Raises:
            FileNotFoundError: If file path is invalid
            InvalidLkPartition: If image parsing fails
        """
        if isinstance(source, (str, Path)):
            self.path: Optional[str] = str(source)
            self.contents = self._load_image(source)
        else:
            self.path = None
            self.contents = bytearray(source)

        self.partitions: OrderedDict[str, LkPartition] = OrderedDict()
        self._parse_partitions()

    def _load_image(self, path: Union[str, Path]) -> bytearray:
        """
        Load image contents from file.

        Args:
            path: Path to the image file

        Returns:
            Raw image contents as bytearray
        """
        with open(path, 'rb') as f:
            return bytearray(f.read())

    def _parse_partitions(self) -> None:
        """
        Parse partitions from image contents and associate certificates.

        Raises:
            InvalidLkPartition: If partition parsing fails
        """
        offset = 0
        last_name = ''

        while offset < len(self.contents):
            try:
                partition = LkPartition.from_bytes(
                    self.contents[offset:], offset
                )
            except InvalidLkPartition:
                if self.partitions and last_name == 'lk':
                    break
                raise

            part_magic = partition.header.magic
            part_name = partition.header.name

            if part_magic != Magic.MAGIC:
                raise InvalidLkPartition(
                    f'Invalid magic 0x{part_magic:x} at offset 0x{offset:x}'
                )

            if part_name.startswith('cert'):
                if last_name not in self.partitions:
                    raise InvalidLkPartition(
                        'Certificate partition placed before actual partition'
                    )
                self.partitions[last_name].certs.append(partition)
            elif part_name not in self.partitions:
                last_name = part_name
                self.partitions[last_name] = partition
            else:
                raise InvalidLkPartition(
                    f'Duplicate partition name: {last_name}'
                )

            if partition.header.is_extended and partition.header.image_list_end:
                break

            offset = partition.end_offset

    def apply_patch(
        self,
        needle: Union[str, bytes, bytearray],
        patch: Union[str, bytes, bytearray],
    ) -> None:
        """
        Apply a binary patch to the image.

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

        offset = self.contents.find(needle_bytes)
        if offset != -1:
            self.contents[offset : offset + len(patch_bytes)] = patch_bytes
        else:
            raise NeedleNotFoundException(needle_bytes)

    def save(self, path: Union[str, Path]) -> None:
        """
        Save modified image contents to a file.

        Args:
            path: Destination file path
        """
        with open(path, 'wb') as f:
            f.write(self.contents)

    def __bytes__(self) -> bytes:
        """
        Bytes representation of the LK image.

        Returns:
            Concatenated bytes of all partitions
            and their certificates.
        """
        return b''.join(
            bytes(partition) for partition in self.partitions.values()
        )

    def __len__(self) -> int:
        """
        Get number of partitions in the image.

        Returns:
            Number of partitions
        """
        return len(self.partitions)

    def __repr__(self) -> str:
        """
        Provide a string representation of the LK image.

        Returns:
            Descriptive string with image details
        """
        return (
            f'LkImage(path={self.path}, '
            f'partitions={len(self.partitions)}, '
            f'size={len(self.contents)} bytes)'
        )
