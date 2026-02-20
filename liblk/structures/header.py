"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from ctypes import Structure, c_char, c_uint, c_uint8, sizeof
from enum import IntEnum, unique
from typing import ClassVar, Union

from liblk.constants import Magic


class ImageType(Structure):
    """
    Represents the type of image in a MediaTek image partition.

    Struct Fields:
        _id: Image ID (protected, use id instead)
        reserved0: Reserved field
        reserved1: Reserved field
        _group: Image group (AP, MD, or CERT) (protected, use group instead)

    Attributes:
        group: Image group (AP, MD, or CERT)
        id: Image ID (AP_BIN, MD_LTE, MD_C2K, CERT1, CERT1_MD, CERT2)
    """

    @unique
    class ImageGroup(IntEnum):
        GROUP_AP = 0x0
        GROUP_MD = 0x1
        GROUP_CERT = 0x2

    @unique
    class ImageAPType(IntEnum):
        AP_BIN = 0x0

    @unique
    class ImageMDType(IntEnum):
        MD_LTE = 0x0
        MD_C2K = 0x1

    @unique
    class ImageCertType(IntEnum):
        CERT1 = 0x0
        CERT1_MD = 0x1
        CERT2 = 0x2

    _fields_ = [
        ('_id', c_uint8),
        ('reserved0', c_uint8),
        ('reserved1', c_uint8),
        ('_group', c_uint8),
    ]

    _group_to_type_map_ = {
        ImageGroup.GROUP_AP: type(ImageAPType),
        ImageGroup.GROUP_MD: type(ImageMDType),
        ImageGroup.GROUP_CERT: type(ImageCertType),
    }

    # HACK: These aren't the true types of the fields, but rather
    # what they are cast to when used.
    _id: ClassVar[int]
    reserved0: ClassVar[int]
    reserved1: ClassVar[int]
    _group: ClassVar[int]

    @property
    def group(self) -> ImageGroup:
        """
        Get the image group.
        """
        return self.ImageGroup(self._group)

    @group.setter
    def group(self, value: ImageGroup) -> None:
        """
        Set the image group.

        Args:
            value: New image group
        """
        self._group = value.value

    @property
    def image_id(self) -> Union[ImageAPType, ImageMDType, ImageCertType]:
        """
        Get the image ID.
        """
        if self.group == self.ImageGroup.GROUP_AP:
            return self.ImageAPType(self._id)
        elif self.group == self.ImageGroup.GROUP_MD:
            return self.ImageMDType(self._id)
        elif self.group == self.ImageGroup.GROUP_CERT:
            return self.ImageCertType(self._id)
        else:
            raise ValueError('Invalid image group value')

    @image_id.setter
    def image_id(
        self, value: Union[ImageAPType, ImageMDType, ImageCertType]
    ) -> None:
        """
        Set the image ID.

        Args:
            value: New image type
        """
        if self._group_to_type_map_.get(self.group) is not type(value):
            raise ValueError(
                f'Invalid image type for group {self.group}: {value}'
            )
        self._id = value.value

    def __repr__(self: ImageType) -> str:
        """
        Generate a string representation of the image type.

        Returns:
            Formatted string with image type details
        """
        return f'ImageType(group={self.group.name}, id={self.image_id.name})'


class ImageHeader(Structure):
    """
    Represents the header of a MediaTek image partition.
    This same format is used in numerous other images, such as LK and DTBO.

    Struct Fields:
        magic: Magic number identifying the header (always = MAGIC)
        dsize: Size of the partition data (protected, use data_size instead)
        cname: Name of the partition (protected, use name instead)
        maddr: Memory address for the partition (protected, use memory_address instead)
        mode: Memory addressing mode
        ext_magic: Extended magic number (always = EXT_MAGIC when using new structure)
        hdr_size: Size of the header
        hdr_version: Version of the header
        image_type: Type of image
        image_list_end: Whether this is the last partition in the image
        alignment: Alignment size
        dsize_extend: High word of image size for 64 bit address support (protected, use data_size instead)
        maddr_extend: High word of image load address in RAM for 64 bit address support (protected, use memory_address instead)
        _padding: Padding to align the structure to 512 bytes (do not use)

    Attributes:
        name: Name of the partition (decoded from bytes)
    """

    _fields_ = [
        ('magic', c_uint),
        ('_dsize', c_uint),
        ('_cname', c_char * 32),
        ('_maddr', c_uint),
        ('mode', c_uint),
        ('ext_magic', c_uint),
        ('hdr_size', c_uint),
        ('hdr_version', c_uint),
        ('image_type', ImageType),
        ('image_list_end', c_uint),
        ('alignment', c_uint),
        ('_dsize_extend', c_uint),
        ('_maddr_extend', c_uint),
        ('_padding', c_char * 432),
    ]

    # HACK: These aren't the true types of the fields, but rather
    # what they are cast to when used.
    magic: ClassVar[int]
    _dsize: ClassVar[int]
    _cname: ClassVar[bytes]
    _maddr: ClassVar[int]
    mode: ClassVar[int]
    ext_magic: ClassVar[int]
    hdr_size: ClassVar[int]
    hdr_version: ClassVar[int]
    image_type: ClassVar[ImageType]
    image_list_end: ClassVar[int]
    alignment: ClassVar[int]
    _dsize_extend: ClassVar[int]
    _maddr_extend: ClassVar[int]
    _padding: ClassVar[bytes]

    def __str__(self: ImageHeader) -> str:
        """
        Generate a string representation of the LK header.

        Returns:
            Formatted string with header details
        """
        return (
            f'Partition Name  : {self.name}\n'
            f'Data Size       : {self.data_size} bytes\n'
            f'Addressing Mode : 0x{self.mode:08x}\n'
            f'Memory Address  : 0x{self.memory_address:08x}'
        )

    def end_offset(self: ImageHeader, offset: int) -> int:
        """
        Calculate the end offset of the partition, including header and data size.

        Args:
            offset: Starting offset of the partition header

        Returns:
            The end offset of the partition
        """
        return offset + self.size + self.data_size

    @property
    def is_header(self) -> bool:
        """
        Whether the header have a valid magic number.
        """
        return self.magic == Magic.MAGIC

    @property
    def is_extended(self) -> bool:
        """
        Whether the header is using the extended format.
        """
        return self.ext_magic == Magic.EXT_MAGIC

    @property
    def name(self) -> str:
        """
        Name of the partition.
        """
        return self._cname.decode('ascii')

    @name.setter
    def name(self, value: str) -> None:
        """
        Set the name of the partition.

        Args:
            value: New name of the partition
        """
        if len(value) > 32:
            raise ValueError('Name too long')
        self._cname = value.encode('ascii')

    @property
    def data_size(self) -> int:
        """
        Data size of the partition.
        """
        return (
            (self._dsize_extend << 32) | self._dsize
            if self.is_extended
            else self._dsize
        )

    @data_size.setter
    def data_size(self, value: int) -> None:
        """
        Set the data size of the partition.

        Args:
            value: New data size of the partition
        """
        if self.is_extended:
            self._dsize = value & 0xFFFFFFFF
            self._dsize_extend = (value >> 32) & 0xFFFFFFFF
        else:
            self._dsize = value & 0xFFFFFFFF

    @property
    def size(self) -> int:
        """
        Size of the header.
        """
        return self.hdr_size if self.is_extended else sizeof(ImageHeader)

    @size.setter
    def size(self, value: int) -> None:
        """
        Set the size of the header.

        Args:
            value: New size of the header
        """
        if self.is_extended:
            self.hdr_size = value
        else:
            raise AttributeError(
                'size property is read-only for legacy headers'
            )

    @property
    def memory_address(self) -> int:
        """
        Mmemory (load) address of the partition.
        """
        return (
            (self._maddr_extend << 32) | self._maddr
            if self.is_extended
            else self._maddr
        )

    @memory_address.setter
    def memory_address(self, value: int) -> None:
        """
        Set the memory address of the partition.

        Args:
            value: New memory address of the partition
        """
        if self.is_extended:
            self._maddr = value & 0xFFFFFFFF
            self._maddr_extend = (value >> 32) & 0xFFFFFFFF
        else:
            self._maddr = value & 0xFFFFFFFF
