#
# This file is part of liblk (https://github.com/R0rt1z2/liblk).
# Copyright (c) 2023 Roger Ortiz.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import struct

class LkExtHeader:
    def __init__(self, header_size: int, header_version: int, image_type: int, image_list_end: int, alignment: int,
                 data_size: int, memory_address: int) -> None:
        '''Initialize the LK extension header.'''
        self.header_size: int = header_size
        self.header_version: int = header_version
        self.image_type: int = image_type
        self.image_list_end: int = image_list_end
        self.alignment: int = alignment
        self.data_size: int = data_size
        self.memory_address: int = memory_address

    @classmethod
    def from_bytes(cls, contents: bytes):
        '''Initialize the LK extension header from bytes.'''
        header_size = struct.unpack_from('<I', contents)[0]
        header_version = struct.unpack_from('<I', contents, 4)[0]
        image_type = struct.unpack_from('<I', contents, 8)[0]
        image_list_end = struct.unpack_from('<I', contents, 12)[0]
        alignment = struct.unpack_from('<I', contents, 16)[0]
        data_size = struct.unpack_from('<I', contents, 20)[0] << 32
        memory_address = struct.unpack_from('<I', contents, 24)[0] << 32
        return cls(header_size, header_version, image_type, image_list_end, alignment, data_size, memory_address)

    def __str__(self) -> str:
        return (
            f"| {'Header Size':<15}: {self.header_size}\n"
            f"| {'Header Version':<15}: {self.header_version}\n"
            f"| {'Image Type':<15}: {self.image_type:#x}\n"
            f"| {'Image List End':<15}: {self.image_list_end}\n"
            f"| {'Alignment':<15}: {self.alignment}\n"
            f"| {'Data Size':<15}: {self.data_size}\n"
            f"| {'Memory Address':<15}: {self.memory_address:#x}"
        )