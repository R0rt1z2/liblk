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

import os
import unittest

from liblk.LkImage import LkImage
from liblk.Exceptions import NeedleNotFoundException

class TestLkImage(unittest.TestCase):
    def setUp(self) -> None:
        # The repository contains a sample LK image for testing purposes.
        # This file is the bootloader image of the Realme 8 (RMX3085 - nashc).
        self.lk_image = LkImage("tests/files/lk.img")

    def test_lk_image_load(self) -> None:
        # Make sure the file was loaded correctly by checking for 'lk_contents'.
        self.assertGreater(len(self.lk_image.lk_contents), 0, "Contents of the LK image are empty.")

        # Make sure the partitions list is not empty and contains at least one
        # valid partition.
        self.assertGreater(len(self.lk_image.partitions), 0, "Partitions list is empty.")

    def test_lk_image_patch(self) -> None:
        # Try to patch the LK image with a valid needle and patch.
        try:
            self.lk_image.apply_patch(bytearray.fromhex("30b583b002ab"),
                                      bytearray.fromhex("00207047"))
        except NeedleNotFoundException:
            self.fail("Needle not found.")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))

        # Check whether the patch was applied correctly.
        self.assertIn(bytearray.fromhex("00207047"), self.lk_image.lk_contents)

if __name__ == '__main__':
    unittest.main()