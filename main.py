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

import sys
from liblk.LkImage import LkImage
from liblk.Exceptions import NeedleNotFoundException

# In this example we will patch the LK image to disable the dm verity state warning.
# The warning is displayed when the bootloader detects that the device is unlocked.
# This warning is displayed on the screen every time the device boots and you have
# to press the power button to continue booting.

# In order to disable this warning, we will patch the function that takes care of
# displaying the warning. We do this by replacing the first 4 bytes of the function
# with a 'return 0' instruction.

def main():
    # First, we need to create the LkImage object. The constructor accepts multiple
    # types of arguments, from a string containing the path to the LK image, to a
    # bytearray containing the LK image contents. In this example, we are going to
    # use the path to the LK image.
    lk_image = LkImage(sys.argv[1])

    # Now, once the LkImage object is created, we can use the apply_patch() method
    # to patch the LK image. The function accepts two arguments, the first one is the
    # bytes sequence that we want to patch, and the second one is the replacement.
    # We can provide either the bytearray or a hex-string. In this example, we are
    # going to use a hex-string:
    # 30b583b002ab:      # 00207047:
    # push {r4, r5, lr}  # mov r0, #0
    # sub sp, #0xc       # bx lr (return 0)
    # add r3, sp, #8
    try:
        lk_image.apply_patch("30b583b002ab", "00207047")
    except NeedleNotFoundException as e:
        # If the needle is not found, the patch() method will raise a NeedleNotFoundException
        # exception. This exception is raised when the needle is not found in the LK image.
        exit(f"Needle {e.needle} not found in the LK image.")

    # Now that we have patched the LK image, we can save the patched image to a file.
    with open("patched_lk.img", "wb") as f:
        f.write(lk_image.lk_contents)

    print("Patched LK image saved to patched_lk.img")

if __name__ == '__main__':
    main()