"""
SPDX-FileCopyrightText: 2025-2026 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import ClassVar

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyasn1.codec.der import decoder
from pyasn1.codec.der.encoder import encode as der_encode
from pyasn1.type.univ import BitString

from liblk import Certificate, InvalidCertificate, LkImage


class TestCertificate(unittest.TestCase):
    """Tests for the generic MediaTek cert2 parsing helpers."""

    image: ClassVar[LkImage]

    @classmethod
    def setUpClass(cls) -> None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cls.image = LkImage(os.path.join(current_dir, 'files', 'lk.img'))

    def test_matches_cert2_on_unmodified_image(self) -> None:
        """An untouched, signed partition matches its certificate."""
        for name, partition in self.image.partitions.items():
            if partition.cert2 is None:
                continue
            self.assertTrue(
                partition.matches_cert2(),
                f"Partition '{name}' should match its cert2",
            )

    def test_compute_hashes_match_embedded(self) -> None:
        """Computed hashes equal the digests embedded in cert2."""
        lk = self.image.partitions['lk']
        cert = Certificate.from_bytes(lk.cert2.data)
        header_hash, data_hash = lk.compute_hashes()
        self.assertEqual(cert.header_hash, header_hash)
        self.assertEqual(cert.image_hash, data_hash)
        self.assertTrue(cert.matches(header_hash, data_hash))

    def test_modifying_data_breaks_match(self) -> None:
        """Mutating partition data makes it stop matching cert2."""
        image = LkImage(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'files', 'lk.img'
            )
        )
        lk = image.partitions['lk']
        data = bytearray(lk.data)
        data[0x100] ^= 0xFF
        lk.data = bytes(data)
        self.assertFalse(lk.matches_cert2())

    def test_partition_without_cert2(self) -> None:
        """Partitions without a cert2 report None."""
        legacy = LkImage(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'files',
                'lk_legacy.img',
            )
        )
        self.assertIsNone(legacy.partitions['lk'].matches_cert2())

    def test_encode_with_hashes_roundtrip(self) -> None:
        """Re-encoding swaps only the embedded hashes."""
        lk = self.image.partitions['lk']
        cert = Certificate.from_bytes(lk.cert2.data)

        new_header = b'\xaa' * 32
        new_image = b'\xbb' * 32
        encoded = cert.encode_with_hashes(new_header, new_image)

        reparsed = Certificate.from_bytes(encoded)
        self.assertEqual(reparsed.header_hash, new_header)
        self.assertEqual(reparsed.image_hash, new_image)

    def test_build_hash_override_block(self) -> None:
        """The ``[0]`` override block carries the supplied hashes verbatim."""
        lk = self.image.partitions['lk']
        cert = Certificate.from_bytes(lk.cert2.data)

        new_header = b'\xaa' * 32
        new_image = b'\xbb' * 32
        block = cert.build_hash_override_block(new_header, new_image)

        self.assertEqual(block[0], 0xA0)
        self.assertIn(new_header, block)
        self.assertIn(new_image, block)
        self.assertNotIn(cert.header_hash, block)
        self.assertNotIn(cert.image_hash, block)
        decoded, _ = decoder.decode(bytes(lk.cert2.data))
        self.assertIn(der_encode(decoded[0][13]), block)
        self.assertIn(der_encode(decoded[0][9]), block)

    def test_invalid_certificate_rejected(self) -> None:
        """Garbage and bypass-shaped data raise InvalidCertificate."""
        with self.assertRaises(InvalidCertificate):
            Certificate.from_bytes(b'not a certificate')

        lk = self.image.partitions['lk']
        bypass_shaped = der_encode(
            BitString(hexValue=bytes(lk.cert2.data).hex())
        ) + bytes(lk.cert2.data)

        first, _ = decoder.decode(bypass_shaped)
        self.assertTrue(isinstance(first, BitString))
        with self.assertRaises(InvalidCertificate):
            Certificate.from_bytes(bypass_shaped)


if __name__ == '__main__':
    unittest.main()
