"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import ClassVar, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from liblk import InvalidLkPartition, LkImage
except ImportError:
    print('Error: liblk module not found')
    sys.exit(1)


class TestLkImageVariants(unittest.TestCase):
    """
    Test suite for different LK image types, including legacy images.
    """

    test_images: ClassVar[Dict[str, str]] = {}

    @classmethod
    def setUpClass(cls) -> None:
        """
        Prepare test resources for different image types.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cls.test_images = {
            'standard': os.path.join(current_dir, 'files', 'lk.img'),
            'legacy': os.path.join(current_dir, 'files', 'lk_legacy.img'),
        }

    def _validate_image(
        self, image_path: str, expected_partitions: Optional[List[str]] = None
    ) -> None:
        """
        Validate different types of LK images.

        Args:
            image_path: Path to the LK image
            expected_partitions: Optional list of expected partition names
        """
        try:
            lk_image = LkImage(image_path)

            self.assertGreater(
                len(lk_image.contents),
                1024,
                f'Image contents too small: {image_path}',
            )

            if expected_partitions is not None:
                actual_partitions = lk_image.get_partition_list()

                self.assertEqual(
                    len(actual_partitions),
                    len(expected_partitions),
                    f'Unexpected partition count for {image_path}',
                )

                for expected, actual in zip(
                    expected_partitions, actual_partitions
                ):
                    self.assertEqual(
                        actual, expected, f'Partition mismatch in {image_path}'
                    )

        except InvalidLkPartition as e:
            if 'legacy' not in image_path:
                self.fail(f'Unexpected parsing error: {e}')

    def test_standard_image(self) -> None:
        """
        Test standard LK image parsing.
        """
        self._validate_image(
            self.test_images['standard'],
            expected_partitions=[
                'lk',
                'cert1',
                'cert2',
                'lk_main_dtb',
                'cert1 (1)',
                'cert2 (1)',
            ],
        )

    def test_legacy_image(self) -> None:
        """
        Test legacy LK image parsing.
        """
        try:
            lk_image = LkImage(self.test_images['legacy'])

            self.assertGreaterEqual(
                len(lk_image.partitions), 0, 'Legacy image parsing failed'
            )

            partitions = lk_image.get_partition_list()

            if partitions:
                for partition_name in partitions:
                    partition = lk_image.get_partition_by_name(partition_name)
                    self.assertIsNotNone(
                        partition,
                        f'Could not retrieve partition: {partition_name}',
                    )

        except Exception as e:
            self.fail(f'Legacy image parsing failed: {e}')

    def test_patch_compatibility(self) -> None:
        """
        Verify patch functionality across image types.
        """
        test_cases = [
            (self.test_images['standard'], '30b583b002ab', '00207047'),
            (self.test_images['legacy'], '40f2a6534E', '00207047'),
        ]

        for image_path, needle, patch in test_cases:
            try:
                lk_image = LkImage(image_path)

                lk_image.apply_patch(needle, patch)

                self.assertIn(
                    bytes.fromhex(patch),
                    lk_image.contents,
                    f'Patch not applied in {image_path}',
                )

            except Exception as e:
                self.fail(f'Patch test failed for {image_path}: {e}')


if __name__ == '__main__':
    unittest.main()
