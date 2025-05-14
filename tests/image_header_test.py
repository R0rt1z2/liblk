"""
SPDX-FileCopyrightText: 2025 Ben Grisdale <bengris32@protonmail.ch>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
import sys
import unittest
from ctypes import sizeof
from typing import ClassVar, Dict

from liblk.structures.header import ImageType

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from liblk import ImageHeader, Magic
except ImportError:
    print('Error: liblk module not found')
    sys.exit(1)


class TestImageHeaderClass(unittest.TestCase):
    """
    Test suite for the ImageHeader class.
    """

    test_files: ClassVar[Dict[str, str]] = {}

    @classmethod
    def setUpClass(cls) -> None:
        """
        Prepare test resources for different tests.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cls.test_files = {
            'image_header': os.path.join(
                current_dir, 'files', 'image_header.bin'
            ),
        }

    def _load_header(self) -> bytes:
        """
        Load the ImageHeader's bytes from a file.
        """
        with open(self.test_files['image_header'], 'rb') as f:
            image_file = f.read()

        header_bytes = image_file[: sizeof(ImageHeader)]
        return header_bytes

    def test_image_header_size(self) -> None:
        """
        Tests the sizeof the ImageHeader structure.
        This should always be 512 bytes.
        """
        header_sz = sizeof(ImageHeader)
        self.assertEqual(
            header_sz,
            512,
            f'Expected ImageHeader size of 512 bytes, got {header_sz}',
        )

    def test_image_header(self) -> None:
        """
        Tests parsing of the ImageHeader structure.
        """
        with open(self.test_files['image_header'], 'rb') as f:
            image_file = f.read()

        header = ImageHeader.from_buffer_copy(image_file)
        self.assertEqual(
            header.magic,
            Magic.MAGIC,
            f'Expected magic {Magic.MAGIC:08x}, got {header.magic:08x}',
        )
        self.assertEqual(
            header.ext_magic,
            Magic.EXT_MAGIC,
            f'Expected extended magic {Magic.EXT_MAGIC:08x}, got {header.ext_magic:08x}',
        )
        self.assertEqual(
            header.mode,
            474,
            f'Expected mode 474, got {header.mode}',
        )
        self.assertEqual(
            header._maddr,
            0xDEADBEEF,
            f'Expected memory address 0xDEADBEEF, got 0x{header._maddr:08x}',
        )
        self.assertEqual(
            header._maddr_extend,
            0xBEEFDEED,
            f'Expected extended memory address 0xBEEFDEED, got 0x{header._maddr_extend:08x}',
        )
        self.assertEqual(
            header.memory_address,
            0xBEEFDEEDDEADBEEF,
            f'Expected full memory address 0xBEEFDEEDDEADBEEF, got 0x{header.memory_address:08x}',
        )
        self.assertEqual(
            header.data_size,
            8,
            f'Expected data size 8, got 0x{header.data_size}',
        )
        self.assertEqual(
            header.name,
            'test',
            f'Expected name "test", got {header.name}',
        )
        self.assertEqual(
            header.image_type.id,
            ImageType.ImageCertType.CERT2,
            f'Expected image type CERT2, got {header.image_type}',
        )
        content = image_file[
            sizeof(ImageHeader) : sizeof(ImageHeader) + header.data_size
        ]
        self.assertEqual(
            content,
            b'    BOOT',
            f"Expected content b'    BOOT', got {content!r}",
        )

    def test_image_header_bytes(self) -> None:
        """
        Tests the byte representation of the ImageHeader structure.
        """
        header_bytes = self._load_header()
        header = ImageHeader.from_buffer_copy(header_bytes)
        self.assertEqual(
            bytes(header),
            header_bytes,
            'Expected byte representation of ImageHeader to match original file',
        )

    def test_image_header_mutability(self) -> None:
        header_bytes = self._load_header()
        header = ImageHeader.from_buffer_copy(header_bytes)

        header.name = 'aaaaaaaa'
        new_header = ImageHeader.from_buffer_copy(bytes(header))
        self.assertEqual(
            new_header.name,
            'aaaaaaaa',
            f"Expected name b'aaaaaaaa', got {new_header.name!r} after modification",
        )


if __name__ == '__main__':
    unittest.main()
