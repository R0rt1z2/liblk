"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union, overload

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
    def __init__(
        self, source: Union[str, Path], rename_duplicates: bool = True
    ) -> None: ...

    @overload
    def __init__(
        self, source: Union[bytes, bytearray], rename_duplicates: bool = True
    ) -> None: ...

    def __init__(
        self,
        source: Union[str, Path, bytes, bytearray],
        rename_duplicates: bool = True,
    ) -> None:
        """
        Initialize LK image from file or byte-like object.

        Args:
            source: Image source (file path or byte-like object)
            rename_duplicates: Automatically rename duplicate partitions

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

        self.partitions: List[Dict[str, Any]] = []
        self._parse_partitions(rename_duplicates)

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

    def _parse_partitions(self, rename_duplicates: bool = False) -> None:
        """
        Parse partitions from image contents.

        Args:
            rename_duplicates: Automatically rename duplicate partitions

        Raises:
            InvalidLkPartition: If partition parsing fails
        """
        offset = 0
        name_counts: Dict[str, int] = {}

        while offset < len(self.contents):
            try:
                partition = LkPartition.from_bytes(
                    self.contents[offset:], offset
                )
            except InvalidLkPartition:
                if self.partitions and self.partitions[-1].get('name') == 'lk':
                    break
                raise

            if partition.header.magic != Magic.MAGIC:
                raise InvalidLkPartition(
                    f'Invalid magic 0x{partition.header.magic:x} at offset 0x{offset:x}'
                )

            name = partition.header.name
            if rename_duplicates:
                if name in name_counts:
                    name_counts[name] += 1
                    name = f'{name} ({name_counts[name]})'
                else:
                    name_counts[name] = 0

            self.partitions.append({'name': name, 'partition': partition})

            if (
                partition.has_ext
                and partition.ext_header
                and partition.ext_header.image_list_end
            ):
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

    def get_partition_list(self) -> List[str]:
        """
        Retrieve names of all partitions.

        Returns:
            List of partition names
        """
        return [str(entry['name']) for entry in self.partitions]

    def get_partition_by_name(self, name: str) -> Optional[LkPartition]:
        """
        Retrieve a specific partition by name.

        Args:
            name: Name of the partition

        Returns:
            Matching partition or None if not found
        """
        for entry in self.partitions:
            if entry['name'] == name:
                return entry['partition']  # type: ignore
        return None

    def save(self, path: Union[str, Path]) -> None:
        """
        Save modified image contents to a file.

        Args:
            path: Destination file path
        """
        with open(path, 'wb') as f:
            f.write(self.contents)

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
