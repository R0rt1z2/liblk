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
    from liblk import InvalidLkPartition, LkImage, NeedleNotFoundException
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
        self,
        image_path: str,
        expected_partitions: Optional[List[str]] = None,
        expected_load_addr: Optional[int] = None,
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
                actual_partitions = lk_image.partitions.keys()
                self.assertEqual(
                    list(actual_partitions),
                    expected_partitions,
                    f'Listed partitions do not match expected: {image_path}',
                )

            if expected_load_addr is not None:
                lk_partition = lk_image.partitions['lk']
                self.assertEqual(
                    lk_partition.lk_address,
                    expected_load_addr,
                    f'Load address mismatch in {image_path}',
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
            expected_partitions=['lk', 'lk_main_dtb'],
            expected_load_addr=0x4C400000,
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

            partitions = lk_image.partitions.keys()

            if partitions:
                for partition_name in partitions:
                    partition = lk_image.partitions[partition_name]
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

    def test_partition_specific_patching(self) -> None:
        """
        Test partition-specific patching functionality.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])

            if 'lk' not in lk_image.partitions:
                self.skipTest('LK partition not found in test image')

            original_partition_data = lk_image.partitions['lk'].data
            test_needle = '30b583b002ab'
            test_patch = '00207047'

            lk_image.apply_patch(test_needle, test_patch, 'lk')

            modified_partition_data = lk_image.partitions['lk'].data
            self.assertNotEqual(
                original_partition_data,
                modified_partition_data,
                'Partition data should be modified after patch',
            )

            self.assertIn(
                bytes.fromhex(test_patch),
                modified_partition_data,
                'Patch should be present in partition data',
            )

        except Exception as e:
            self.fail(f'Partition-specific patch test failed: {e}')

    def test_partition_patch_isolation(self) -> None:
        """
        Test that partition-specific patches don't affect other partitions.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])

            if len(lk_image.partitions) < 2:
                self.skipTest('Need at least 2 partitions for isolation test')

            partition_names = list(lk_image.partitions.keys())
            target_partition = partition_names[0]
            other_partition = partition_names[1]

            original_other_data = lk_image.partitions[other_partition].data

            lk_image.apply_patch('30b583b002ab', '00207047', target_partition)

            modified_other_data = lk_image.partitions[other_partition].data
            self.assertEqual(
                original_other_data,
                modified_other_data,
                'Other partitions should not be affected by targeted patch',
            )

        except Exception as e:
            self.fail(f'Partition isolation test failed: {e}')

    def test_invalid_partition_patch(self) -> None:
        """
        Test error handling for non-existent partition names.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])

            with self.assertRaises(KeyError):
                lk_image.apply_patch('30b583b002ab', '00207047', 'nonexistent')

        except Exception as e:
            self.fail(f'Invalid partition test failed: {e}')

    def test_partition_patch_needle_not_found(self) -> None:
        """
        Test error handling when needle is not found in specific partition.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])

            if 'lk' not in lk_image.partitions:
                self.skipTest('LK partition not found in test image')

            with self.assertRaises(NeedleNotFoundException):
                lk_image.apply_patch('DEADBEEFCAFEBABE', '00207047', 'lk')

        except Exception as e:
            self.fail(f'Needle not found test failed: {e}')

    def test_image_rebuild(self) -> None:
        """
        Test rebuilding the LK image.
        """
        try:
            with open(self.test_images['standard'], 'rb') as f:
                original_contents = f.read()
            lk_image = LkImage(original_contents)

            self.assertEqual(
                original_contents,
                bytes(lk_image),
                'Rebuilt image does not match original',
            )

        except Exception as e:
            self.fail(f'Image rebuild test failed: {e}')


if __name__ == '__main__':
    unittest.main()
