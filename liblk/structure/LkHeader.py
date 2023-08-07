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

import ctypes
import struct

from liblk.Constants import Pattern

class LkHeader:
    '''LK header structure.'''
    def __init__(self, magic: int, data_size: int, name: str, addressing_mode: int, memory_address: int) -> None:
        '''Initialize the LK header structure.'''
        self.magic: int = magic
        self.data_size: int = data_size
        self.name: str = name
        self.addressing_mode: int = addressing_mode
        self.memory_address: int = memory_address

    @classmethod
    def from_bytes(cls, contents: bytes, start_offset: int) -> "LkHeader":
        '''Create a LK header structure from bytes.'''
        magic = struct.unpack_from('<I', contents, start_offset)[0]
        data_size = struct.unpack_from('<I', contents, start_offset + 4)[0]
        name = contents[start_offset + 8:start_offset + 40].decode('utf-8').rstrip('\0')
        addressing_mode = ctypes.c_int(struct.unpack_from('<I', contents, start_offset + 40)[0]).value
        memory_address = struct.unpack_from('<I', contents, start_offset + 44)[0]

        if name == 'lk' and (memory_address & 0xffffffff) == 0xffffffff:
            if contents.find(Pattern.LOADADDR) != -1:
                memory_address = struct.unpack_from('<I', contents, contents.find(Pattern.LOADADDR) + 8)[0]

        return cls(magic, data_size, name, addressing_mode, memory_address)

    def __str__(self) -> str:
        return (
            f"| {'Partition Name':<15}: {self.name}\n"
            f"| {'Data Size':<15}: {self.data_size}\n"
            f"| {'Addressing Mode':<15}: {self.addressing_mode}\n"
            f"| {'Address':<15}: {self.memory_address:#x}\n"
        )