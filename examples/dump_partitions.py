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

# In this example, we are going to let the user parse an LK image, and we will print
# and dump the contents of each partition that is found in the LK image.

def main():
    # First, we need to create the LkImage object. The constructor accepts multiple
    # types of arguments, from a string containing the path to the LK image, to a
    # bytearray containing the LK image contents. In this example, we are going to
    # use the path to the LK image.
    lk_image = LkImage(sys.argv[1])

    # Now, once the LkImage object is created, we can use the list_partitions() method
    # to retrieve a list of the partitions that are found in the LK image.
    partitions = lk_image.get_partition_list()

    # Now that we have a list of the partitions that are found in the LK image, we can
    # iterate over the list and extract the contents of each partition.
    for partition in partitions:
        # Use the get_partition_info() method from the LkImage class to retrieve the
        # partition object. Then we can extract the contents of the partition by using
        # the data attribute of the LkPartition class.
        partition_info = lk_image.get_partition_by_name(partition)

        # While we are at it, we can also print the information of each partition. The
        # LkPartition class has a __str__() method that returns a string containing the
        # information of the partition.
        print("=====================================")
        print(str(partition_info))
        print("=====================================")

        # Now open a file stream and write the contents of the partition to the file.
        # Note that this dumps the contents of the partition, excluding its header(s).
        with open(f"{partition}.bin", "wb") as f:
            f.write(partition_info.data)

if __name__ == '__main__':
    main()