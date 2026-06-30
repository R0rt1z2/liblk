"""
SPDX-FileCopyrightText: 2025-2026 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

from typing import Union

from pyasn1.codec.der import decoder as der_decoder
from pyasn1.codec.der import encoder as der_encoder
from pyasn1.error import PyAsn1Error
from pyasn1.type.univ import BitString

from liblk.exceptions import InvalidCertificate

IMAGE_HASH_ALIGNMENT = 16
IMAGE_HASH_INDEX = 10
HEADER_HASH_INDEX = 14

IMAGE_HASH_OID_INDEX = IMAGE_HASH_INDEX - 1
HEADER_HASH_OID_INDEX = HEADER_HASH_INDEX - 1


def _encode_der_length(length: int) -> bytes:
    """
    Encode a length using DER's definite-length rules.

    Args:
        length: Length value to encode

    Returns:
        The short- or long-form DER length octets
    """
    if length < 0x80:
        return bytes([length])
    body = length.to_bytes((length.bit_length() + 7) // 8, 'big')
    return bytes([0x80 | len(body)]) + body


class Certificate:
    """
    Parser for the MediaTek ``cert2`` certificate attached to a partition.

    ``cert2`` is a custom ASN.1 (DER) structure whose first inner sequence
    embeds the SHA-256 digests of the partition's header and data. The
    Preloader compares these digests against the loaded image before booting
    it.

    Attributes:
        raw: Raw DER bytes of the certificate
        header_hash: Embedded SHA-256 digest of the partition header
        image_hash: Embedded SHA-256 digest of the partition data
    """

    def __init__(
        self, raw: bytes, header_hash: bytes, image_hash: bytes
    ) -> None:
        """
        Initialize a certificate.

        Args:
            raw: Raw DER bytes of the certificate
            header_hash: Embedded SHA-256 digest of the partition header
            image_hash: Embedded SHA-256 digest of the partition data
        """
        self.raw = raw
        self.header_hash = header_hash
        self.image_hash = image_hash

    @classmethod
    def from_bytes(cls, raw: Union[bytes, bytearray]) -> 'Certificate':
        """
        Parse a ``cert2`` certificate from raw DER bytes.

        Args:
            raw: Raw certificate bytes

        Returns:
            Parsed :class:`Certificate` instance

        Raises:
            InvalidCertificate: If the data is not a well-formed cert
        """
        raw = bytes(raw)

        try:
            decoded, remainder = der_decoder.decode(raw)
        except PyAsn1Error as e:
            raise InvalidCertificate(f'failed to decode DER: {e}') from e

        if remainder:
            raise InvalidCertificate(
                'unexpected trailing data after certificate '
                '(not a standard cert2?)'
            )

        try:
            image_hash = bytes(decoded[0][IMAGE_HASH_INDEX].asOctets())
            header_hash = bytes(decoded[0][HEADER_HASH_INDEX].asOctets())
        except (PyAsn1Error, IndexError, AttributeError) as e:
            raise InvalidCertificate(
                f'not in the expected MediaTek cert2 format: {e}'
            ) from e

        return cls(raw, header_hash, image_hash)

    def encode_with_hashes(
        self, header_hash: bytes, image_hash: bytes
    ) -> bytes:
        """
        Re-encode the certificate with new partition hashes.

        Produces a standard DER ``cert2`` identical to the original except for
        the embedded header and image digests. The signature is **not**
        recomputed and will no longer be valid on its own.

        Args:
            header_hash: New SHA-256 digest of the partition header
            image_hash: New SHA-256 digest of the partition data

        Returns:
            Re-encoded certificate bytes
        """
        decoded, _ = der_decoder.decode(self.raw)
        decoded[0][IMAGE_HASH_INDEX] = BitString(
            hexValue=bytes(image_hash).hex()
        )
        decoded[0][HEADER_HASH_INDEX] = BitString(
            hexValue=bytes(header_hash).hex()
        )
        return der_encoder.encode(decoded)

    def build_hash_override_block(
        self, header_hash: bytes, image_hash: bytes
    ) -> bytes:
        """
        Build a context-specific ``[0]`` block carrying overriding hashes.

        Args:
            header_hash: SHA-256 digest to advertise for the partition header
            image_hash: SHA-256 digest to advertise for the partition data

        Returns:
            DER bytes of the ``[0]`` hash-override block
        """
        decoded, _ = der_decoder.decode(self.raw)
        header_oid = decoded[0][HEADER_HASH_OID_INDEX]
        image_oid = decoded[0][IMAGE_HASH_OID_INDEX]

        content = (
            der_encoder.encode(header_oid)
            + der_encoder.encode(BitString(hexValue=bytes(header_hash).hex()))
            + der_encoder.encode(image_oid)
            + der_encoder.encode(BitString(hexValue=bytes(image_hash).hex()))
        )

        return b'\xa0' + _encode_der_length(len(content)) + content

    def matches(self, header_hash: bytes, image_hash: bytes) -> bool:
        """
        Check whether the embedded digests match the given hashes.

        Args:
            header_hash: SHA-256 digest of the partition header to compare
            image_hash: SHA-256 digest of the partition data to compare

        Returns:
            True if both embedded digests match
        """
        return self.header_hash == bytes(
            header_hash
        ) and self.image_hash == bytes(image_hash)

    def __repr__(self) -> str:
        """
        Provide a string representation of the certificate.

        Returns:
            Descriptive string with the embedded digests
        """
        return (
            f'Certificate(header_hash={self.header_hash.hex()}, '
            f'image_hash={self.image_hash.hex()})'
        )
