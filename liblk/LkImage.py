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

from pathlib import Path

from liblk.Exceptions import InvalidLkPartition, NeedleNotFoundException
from liblk.Constants import Magic
from liblk.structure.LkPartition import LkPartition


class LkImage:
    def __init__(self, lk: str | bytes | bytearray | Path, rename_duplicates=True) -> None:
        '''Initialize the LK image.'''
        if isinstance(lk, str) or isinstance(lk, Path):
            self.lk_contents: bytearray = self.load_image(lk)
        elif isinstance(lk, bytes):
            self.lk_contents: bytearray = bytearray(lk)
        elif isinstance(lk, bytearray):
            self.lk_contents: bytearray = lk

        self.partitions: list = []  # Initialize the partitions list.

        # Parse the partitions.
        self.parse_partitions(rename_duplicates)

    def load_image(self, lk: str) -> bytearray:
        '''Load the LK image.'''
        with open(lk, "rb") as lk_file:
            return bytearray(lk_file.read())

    def parse_partitions(self, rename_duplicates=False) -> None:
        '''Parse the LK image partitions.'''
        offset = 0
        name_counts = {}

        # Loop over the partition contents until we reach the end of the image, or we find a
        # partition with a positive list_end value.
        while offset < len(self.lk_contents):
            partition = LkPartition.from_bytes(self.lk_contents[offset:], offset)

            # Always make sure the partition header magic is valid, this is the only way to tell
            # whether the partition is valid or not.
            if not partition.header.magic == Magic.MAGIC:
                raise InvalidLkPartition(f"Invalid magic 0x{partition.header.magic:x} at offset 0x{offset:x}")

            # There are certain cases where one partition is repeated more than once. In order
            # to avoid name collisions, append a number to the name (e.g. "cert1" -> "cert1 (1)").
            name = partition.header.name
            if rename_duplicates:
                if name in name_counts:
                    name_counts[name] += 1
                    name = f"{name} ({name_counts[name]})"
                else:
                    name_counts[name] = 0

            # Once we're sure the partition is valid and the name is unique, add it to the list.
            self.partitions.append({"name": name, "partition": partition})

            if partition.has_ext:
                # The external header has a property which can be used to determine whether the
                # current partition is the last one or not. If it is, we can stop parsing.
                if partition.ext_header.image_list_end:
                    break

            offset = partition.end_offset

    def apply_patch(self, needle: str | bytes | bytearray, patch: str | bytes | bytearray) -> None:
        '''Apply a binary patch to the LK image.'''
        if isinstance(needle, str):
            needle = bytes.fromhex(needle)
        if isinstance(patch, str):
            patch = bytes.fromhex(patch)

        # First of all make sure the needle is actually present in the LK image. If it's not,
        # there's no point in applying the patch.
        offset = self.lk_contents.find(needle)
        if offset != -1:
            # Replace the needle with the patch. We don't need to worry about the length of the
            # patch, since maybe the user wants to replace a 4-byte needle with a 1-byte patch.
            self.lk_contents[offset:offset + len(needle)] = patch
        else:
            raise NeedleNotFoundException(needle)

    def get_partition_list(self) -> list:
        '''List all partition names.'''
        return [entry["name"] for entry in self.partitions]

    def get_partition_by_name(self, name: str) -> LkPartition:
        '''Retrieve a specific partition by name.'''
        return next((entry["partition"] for entry in self.partitions if entry["name"] == name), None)
