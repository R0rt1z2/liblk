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
from liblk.structures.header import ImageHeader, ImageType
from liblk.structures.partition import LkPartition


class LkImage:
    """
    Represents an LK (Little Kernel) image for parsing and manipulation.

    Attributes:
        path: Optional path to the original image file
        contents: Raw image contents
        partitions: List of parsed partitions
        version: LK image version (1 or 2)
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
        self.version: int = 1
        self._parse_partitions()
        self._detect_version()

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

                if self.partitions:
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

            if (
                partition.header.is_extended
                and partition.header.image_list_end == 1
            ):
                break

            offset = partition.end_offset

            if (
                not partition.header.is_extended
                or not self._is_valid_image_list_end(
                    partition.header.image_list_end
                )
            ):
                if self._is_end_of_partitions(offset):
                    break

    def _detect_version(self) -> None:
        """
        Detect LK image version based on partition presence.
        Version 2 contains 'aee' or 'bl2_ext' partitions, version 1 does not.
        """
        v2_partitions = {'aee', 'bl2_ext'}
        if any(partition in self.partitions for partition in v2_partitions):
            self.version = 2
        else:
            self.version = 1

    def _is_valid_image_list_end(self, value: int) -> bool:
        """
        Check if image_list_end contains a valid boolean value.

        Args:
            value: The image_list_end value from header

        Returns:
            True if value is a valid boolean flag (0 or 1)
        """
        return value in (0, 1)

    def _is_end_of_partitions(self, offset: int) -> bool:
        """
        Check if we've reached the end of valid partitions.

        Args:
            offset: Current offset to check

        Returns:
            True if no more valid partitions are expected
        """
        if offset >= len(self.contents):
            return True

        remaining = len(self.contents) - offset
        if remaining < 512:
            return True

        try:
            next_magic = int.from_bytes(
                self.contents[offset : offset + 4], 'little'
            )
            if next_magic != Magic.MAGIC:
                return True
        except (IndexError, ValueError):
            return True

        return False

    def _create_header(
        self,
        name: str,
        data_size: int,
        memory_address: int = 0,
        mode: int = 0,
        image_type: Optional[ImageType] = None,
        use_extended: Optional[bool] = None,
        alignment: int = 8,
    ) -> ImageHeader:
        """
        Create a new partition header.

        Args:
            name: Partition name
            data_size: Size of partition data
            memory_address: Load address in memory
            mode: Addressing mode
            image_type: Image type specification
            use_extended: Force extended header format. If None, auto-detect based on data size
            alignment: Data alignment requirement

        Returns:
            Configured ImageHeader instance
        """
        if len(name) > 32:
            raise ValueError(f'Partition name too long: {name}')

        if use_extended is None:
            use_extended = data_size > 0xFFFFFFFF or memory_address > 0xFFFFFFFF

        header = ImageHeader()
        header.magic = Magic.MAGIC
        header.name = name
        header.data_size = data_size
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

        return header

    def add_partition(
        self,
        name: str,
        data: Union[bytes, bytearray],
        memory_address: int = 0,
        mode: int = 0,
        image_type: Optional[ImageType] = None,
        use_extended: Optional[bool] = None,
        alignment: int = 8,
        position: Optional[int] = None,
    ) -> LkPartition:
        """
        Add a new partition to the LK image.

        Args:
            name: Partition name
            data: Partition data
            memory_address: Load address in memory
            mode: Addressing mode
            image_type: Image type specification
            use_extended: Force extended header format. If None, auto-detect
            alignment: Data alignment requirement
            position: Insert position. If None, append to end

        Returns:
            Created LkPartition instance

        Raises:
            ValueError: If partition name already exists or is invalid
        """
        if name in self.partitions:
            raise ValueError(f"Partition '{name}' already exists")

        data_bytes = bytes(data)
        header = self._create_header(
            name=name,
            data_size=len(data_bytes),
            memory_address=memory_address,
            mode=mode,
            image_type=image_type,
            use_extended=use_extended,
            alignment=alignment,
        )

        partition = LkPartition(
            header=header,
            data=data_bytes,
            end_offset=0,  # will be recalculated during rebuild
        )

        if position is None:
            self.partitions[name] = partition
        else:
            items = list(self.partitions.items())
            items.insert(position, (name, partition))
            self.partitions = OrderedDict(items)

        self._rebuild_contents()
        return partition

    def remove_partition(self, name: str) -> None:
        """
        Remove a partition from the LK image.

        Args:
            name: Name of partition to remove

        Raises:
            KeyError: If partition doesn't exist
        """
        if name not in self.partitions:
            raise KeyError(f"Partition '{name}' not found")

        del self.partitions[name]
        self._rebuild_contents()

    def _rebuild_contents(self) -> None:
        """
        Rebuild the image contents from partitions.
        Ensures image_list_end flag is properly set on the last partition.
        """
        if not self.partitions:
            self.contents = bytearray()
            return

        new_contents = bytearray()
        partition_list = list(self.partitions.items())

        for name, partition in partition_list:
            partition.header.image_list_end = 0
            for cert in partition.certs:
                cert.header.image_list_end = 0

        if partition_list:
            last_partition = partition_list[-1][1]
            if last_partition.certs:
                last_partition.certs[-1].header.image_list_end = 1
            else:
                last_partition.header.image_list_end = 1

        for i, (name, partition) in enumerate(partition_list):
            partition_bytes = bytes(partition)
            partition.end_offset = len(new_contents) + len(partition_bytes)
            new_contents.extend(partition_bytes)

        self.contents = new_contents

    def apply_patch(
        self,
        needle: Union[str, bytes, bytearray],
        patch: Union[str, bytes, bytearray],
        partition: Optional[str] = None,
    ) -> None:
        """
        Apply a binary patch to the image or specific partition.

        Args:
            needle: Byte sequence to replace
            patch: Replacement byte sequence
            partition: Optional partition name to patch. If None, patches entire image.

        Raises:
            KeyError: If partition is specified but not found
            NeedleNotFoundException: If needle is not found
        """
        if partition is not None:
            if partition not in self.partitions:
                raise KeyError(f"Partition '{partition}' not found")
            self.partitions[partition].apply_patch(needle, patch)
            self._rebuild_contents()
        else:
            needle_bytes = (
                bytes.fromhex(needle)
                if isinstance(needle, str)
                else bytes(needle)
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
        return bytes(self.contents)

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
            f'version={self.version}, '
            f'partitions={len(self.partitions)}, '
            f'size={len(self.contents)} bytes)'
        )
