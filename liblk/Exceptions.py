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

# Raised if the LK image is not valid.
class InvalidLkPartition(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def __str__(self) -> str:
        return f"Invalid LK partition: {self.reason}"

# Raised if the given needle is not found in the haystack (LK image).
class NeedleNotFoundException(Exception):
    def __init__(self, needle: str | bytes) -> None:
        self.needle = needle

    def __str__(self) -> str:
        return f"Needle not found: {self.needle}"