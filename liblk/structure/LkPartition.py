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

from liblk.Constants import Magic
from liblk.structure.LkExtHeader import LkExtHeader
from liblk.structure.LkHeader import LkHeader

class LkPartition:
    '''LK partition structure.'''
    def __init__(self, header: LkHeader, has_ext: bool, data: bytearray, end_offset: int, ext_header: LkExtHeader = None) -> None:
        '''Initialize the LK partition structure.'''
        self.header: LkHeader = header
        self.has_ext: bool = has_ext
        self.data: bytearray = data
        self.end_offset: int = end_offset
        self.ext_header: LkExtHeader = ext_header

    @classmethod
    def from_bytes(cls, contents: bytes, offset: int = 0) -> "LkPartition":
        '''Create a LK partition structure from bytes.'''
        start_offset = 0x4040 if contents[:4] == b'BFBF' else 0
        header = LkHeader.from_bytes(contents, start_offset)
        has_ext = struct.unpack_from('<I', contents, start_offset + 48)[0] == Magic.EXT_MAGIC
        ext_header = LkExtHeader.from_bytes(contents[start_offset + 52:]) if has_ext else None

        data_size = header.data_size | (ext_header.data_size << 32) if has_ext else header.data_size
        header_size = ext_header.header_size if has_ext else 512
        end_offset = offset + header_size + data_size
        alignment = ext_header.alignment if has_ext else 8
        if alignment and end_offset % alignment:
            end_offset += alignment - end_offset % alignment

        # Ideally, if we wanted to keep the header as well (inside the data) we would simply do
        # contents[:header_size + data_size] but since we are not keeping the header, we skip the
        # header size and only keep the data.
        return cls(header, has_ext, contents[header_size:header_size + data_size], end_offset, ext_header)

    def __str__(self):
        return f"{self.header}" + (f"{self.ext_header}" if self.ext_header else "")