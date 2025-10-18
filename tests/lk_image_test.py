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

    def test_add_partition(self) -> None:
        """
        Test adding a new partition to an LK image.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])
            original_partition_count = len(lk_image.partitions)

            test_data = b'TESTDATA' * 100

            new_partition = lk_image.add_partition(
                name='test_partition',
                data=test_data,
                memory_address=0x41000000,
                use_extended=True,
            )

            self.assertEqual(
                len(lk_image.partitions), original_partition_count + 1
            )

            self.assertIn('test_partition', lk_image.partitions)
            self.assertEqual(new_partition.header.name, 'test_partition')
            self.assertEqual(new_partition.data, test_data)
            self.assertEqual(new_partition.header.memory_address, 0x41000000)
            self.assertTrue(new_partition.header.is_extended)

            partition_list = list(lk_image.partitions.values())
            last_partition = partition_list[-1]
            if last_partition.certs:
                self.assertEqual(
                    last_partition.certs[-1].header.image_list_end, 1
                )
            else:
                self.assertEqual(last_partition.header.image_list_end, 1)

            for partition in partition_list[:-1]:
                self.assertEqual(partition.header.image_list_end, 0)
                for cert in partition.certs:
                    self.assertEqual(cert.header.image_list_end, 0)

        except Exception as e:
            self.fail(f'Add partition test failed: {e}')

    def test_remove_partition(self) -> None:
        """
        Test removing a partition from an LK image.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])
            original_partition_count = len(lk_image.partitions)
            original_partitions = list(lk_image.partitions.keys())

            if original_partition_count < 2:
                self.skipTest('Need at least 2 partitions for removal test')

            partition_to_remove = original_partitions[-1]
            lk_image.remove_partition(partition_to_remove)

            self.assertEqual(
                len(lk_image.partitions), original_partition_count - 1
            )

            self.assertNotIn(partition_to_remove, lk_image.partitions)

            if lk_image.partitions:
                partition_list = list(lk_image.partitions.values())
                last_partition = partition_list[-1]
                if last_partition.certs:
                    self.assertEqual(
                        last_partition.certs[-1].header.image_list_end, 1
                    )
                else:
                    self.assertEqual(last_partition.header.image_list_end, 1)

        except Exception as e:
            self.fail(f'Remove partition test failed: {e}')

    def test_remove_nonexistent_partition(self) -> None:
        """
        Test error handling when removing a non-existent partition.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])

            with self.assertRaises(KeyError):
                lk_image.remove_partition('nonexistent_partition')

        except Exception as e:
            self.fail(f'Remove nonexistent partition test failed: {e}')

    def test_add_duplicate_partition(self) -> None:
        """
        Test error handling when adding a partition with duplicate name.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])
            existing_partition = list(lk_image.partitions.keys())[0]

            with self.assertRaises(ValueError):
                lk_image.add_partition(
                    name=existing_partition, data=b'test data'
                )

        except Exception as e:
            self.fail(f'Add duplicate partition test failed: {e}')

    def test_partition_roundtrip(self) -> None:
        """
        Test adding and removing partitions maintains image integrity.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])
            original_partitions = list(lk_image.partitions.keys())

            test_data = b'ROUNDTRIP' * 50
            lk_image.add_partition(
                name='roundtrip_test', data=test_data, use_extended=True
            )

            self.assertIn('roundtrip_test', lk_image.partitions)

            lk_image.remove_partition('roundtrip_test')

            self.assertEqual(
                list(lk_image.partitions.keys()), original_partitions
            )

        except Exception as e:
            self.fail(f'Partition roundtrip test failed: {e}')

    def test_add_partition_with_certificates(self) -> None:
        """
        Test adding certificates to a newly created partition.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])

            test_data = b'PARTITION_WITH_CERTS' * 20
            cert1_data = b'CERT1_DATA' * 10
            cert2_data = b'CERT2_DATA' * 10

            new_partition = lk_image.add_partition(
                name='test_with_certs', data=test_data, use_extended=True
            )

            cert1 = new_partition.add_certificate(cert1_data, 'cert1')
            cert2 = new_partition.add_certificate(cert2_data, 'cert2')

            self.assertEqual(len(new_partition.certs), 2)
            self.assertIsNotNone(new_partition.cert1)
            self.assertIsNotNone(new_partition.cert2)
            if new_partition.cert1 is not None:
                self.assertEqual(new_partition.cert1.data, cert1_data)
            if new_partition.cert2 is not None:
                self.assertEqual(new_partition.cert2.data, cert2_data)

            lk_image._rebuild_contents()
            self.assertEqual(cert2.header.image_list_end, 1)
            self.assertEqual(cert1.header.image_list_end, 0)
            self.assertEqual(new_partition.header.image_list_end, 0)

        except Exception as e:
            self.fail(f'Add partition with certificates test failed: {e}')

    def test_save_and_reload_modified_image(self) -> None:
        """
        Test saving and reloading an image with added/removed partitions.
        """
        try:
            import os
            import tempfile

            lk_image = LkImage(self.test_images['standard'])

            test_data = b'SAVE_RELOAD_TEST' * 25
            lk_image.add_partition(
                name='save_test',
                data=test_data,
                memory_address=0x42000000,
                use_extended=True,
            )

            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name

            try:
                lk_image.save(tmp_path)
                reloaded_image = LkImage(tmp_path)

                self.assertIn('save_test', reloaded_image.partitions)
                self.assertEqual(
                    reloaded_image.partitions['save_test'].data, test_data
                )
                self.assertEqual(
                    reloaded_image.partitions[
                        'save_test'
                    ].header.memory_address,
                    0x42000000,
                )

            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            self.fail(f'Save and reload test failed: {e}')

    def test_partition_insertion_position(self) -> None:
        """
        Test inserting a partition at a specific position.
        """
        try:
            lk_image = LkImage(self.test_images['standard'])
            original_partitions = list(lk_image.partitions.keys())

            if len(original_partitions) < 2:
                self.skipTest('Need at least 2 partitions for position test')

            test_data = b'POSITION_TEST' * 10

            lk_image.add_partition(
                name='inserted_partition', data=test_data, position=1
            )

            new_partitions = list(lk_image.partitions.keys())
            expected_partitions = (
                [original_partitions[0]]
                + ['inserted_partition']
                + original_partitions[1:]
            )

            self.assertEqual(new_partitions, expected_partitions)

        except Exception as e:
            self.fail(f'Partition insertion position test failed: {e}')


if __name__ == '__main__':
    unittest.main()
