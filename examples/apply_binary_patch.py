#!/usr/bin/env python3
"""
SPDX-FileCopyrightText: 2025-2026 Roger Ortiz <me@r0rt1z2.com>
SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from liblk import LkImage, NeedleNotFoundException
except ImportError:
    print('Error: liblk module not found')
    sys.exit(1)


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for the script."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    return logging.getLogger(__name__)


def validate_patch_input(needle: str, patch: str) -> tuple[bytes, bytes]:
    """
    Validate and convert patch inputs.

    Args:
        needle: Byte sequence to replace (hex string)
        patch: Replacement byte sequence (hex string)

    Returns:
        Tuple of needle and patch as bytes
    """
    try:
        needle_bytes = bytes.fromhex(needle)
        patch_bytes = bytes.fromhex(patch)
    except ValueError as e:
        raise ValueError(f'Invalid hex input: {e}')
    return needle_bytes, patch_bytes


def apply_binary_patch(
    image_path: str,
    needle: str,
    patch: str,
    output_path: Optional[str] = None,
    partition: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Apply a binary patch to an LK image or specific partition.

    Args:
        image_path: Path to the input LK image
        needle: Hex string of bytes to replace
        patch: Hex string of replacement bytes
        output_path: Optional path for patched image
        partition: Optional partition name to target
        logger: Optional logger instance
    """
    log = logger or logging.getLogger(__name__)
    output_path = (
        output_path or os.path.splitext(image_path)[0] + '_patched.img'
    )

    try:
        needle_bytes, patch_bytes = validate_patch_input(needle, patch)
        lk_image = LkImage(image_path)
        log.info(f'Loaded image: {image_path}')

        if partition:
            log.info(f'Targeting partition: {partition}')
            lk_image.apply_patch(needle_bytes, patch_bytes, partition)
        else:
            log.info('Patching entire image')
            lk_image.apply_patch(needle_bytes, patch_bytes)

        log.info(f'Applied patch: {needle} -> {patch}')
        lk_image.save(output_path)
        log.info(f'Patched image saved: {output_path}')

    except KeyError as e:
        log.error(f'Partition not found: {e}')
        sys.exit(1)
    except NeedleNotFoundException as e:
        log.error(f'Patch failed: {e}')
        sys.exit(1)
    except Exception as e:
        log.error(f'Error processing image: {e}')
        sys.exit(1)


def main() -> None:
    """
    Main script entry point.
    Parse arguments and apply binary patch.
    """
    parser = argparse.ArgumentParser(
        description='Apply binary patches to LK bootloader images'
    )
    parser.add_argument('image_path', help='Path to the input LK image')
    parser.add_argument(
        'needle', help="Hex string of bytes to replace (e.g., '30b583b002ab')"
    )
    parser.add_argument(
        'patch', help="Hex string of replacement bytes (e.g., '00207047')"
    )
    parser.add_argument('-o', '--output', help='Path for the patched image')
    parser.add_argument(
        '-p',
        '--partition',
        help='Target specific partition (e.g., bl2_ext, lk)',
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose logging'
    )

    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    apply_binary_patch(
        args.image_path,
        args.needle,
        args.patch,
        args.output,
        args.partition,
        logger,
    )


if __name__ == '__main__':
    main()
