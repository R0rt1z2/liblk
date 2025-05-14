#!/usr/bin/env python3
"""
SPDX-FileCopyrightText: 2025 Roger Ortiz <me@r0rt1z2.com>
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
    from liblk import InvalidLkPartition, LkImage
    from liblk.structures.partition import LkPartition
except ImportError:
    print('Error: liblk module not found')
    sys.exit(1)


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure logging for the script.

    Args:
        verbose: Enable detailed logging

    Returns:
        Configured logger instance
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    return logging.getLogger(__name__)


def validate_image_path(path: str) -> str:
    """
    Validate the input image path.

    Args:
        path: Path to the LK image file

    Returns:
        Validated absolute path

    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If file is not readable
    """
    abs_path = os.path.abspath(path)

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f'Image file not found: {abs_path}')

    if not os.access(abs_path, os.R_OK):
        raise PermissionError(f'Cannot read image file: {abs_path}')

    return abs_path


def dump_partitions(
    image_path: str,
    output_dir: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Extract and save partitions from an LK image.

    Args:
        image_path: Path to the LK image file
        output_dir: Optional directory to save partitions
        logger: Optional logger instance
    """
    log = logger or logging.getLogger(__name__)

    output_dir = output_dir or os.path.join(
        os.path.dirname(image_path),
        f'{os.path.basename(image_path)}_partitions',
    )

    os.makedirs(output_dir, exist_ok=True)

    try:
        lk_image = LkImage(image_path)
        log.info(f'Loaded image with {len(lk_image)} partitions')

        for name, partition in lk_image.partitions.items():
            if not isinstance(partition, LkPartition):
                log.warning(f'Skipping non-LkPartition item: {name}')
                continue

            safe_name = ''.join(
                c if c.isalnum() or c in ('-', '_') else '_' for c in name
            )
            output_path = os.path.join(output_dir, f'{safe_name}.bin')

            partition.save(output_path)
            log.info(f'Extracted: {name} -> {output_path}')

            if log.getEffectiveLevel() == logging.DEBUG:
                log.debug(str(partition))
                log.debug('-' * 40)

    except InvalidLkPartition as e:
        log.error(f'Partition parsing error: {e}')
        sys.exit(1)
    except Exception as e:
        log.error(f'Unexpected error processing image: {e}')
        sys.exit(1)


def main() -> None:
    """
    Main script entry point.
    Parse arguments and invoke partition dumping.
    """
    parser = argparse.ArgumentParser(
        description='Extract partitions from LK bootloader images'
    )
    parser.add_argument('image_path', help='Path to the LK image file')
    parser.add_argument(
        '-o', '--output', help='Output directory for extracted partitions'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose logging'
    )

    args = parser.parse_args()

    logger = setup_logging(args.verbose)

    try:
        validated_path = validate_image_path(args.image_path)
        dump_partitions(validated_path, args.output, logger)
        logger.info('Partition extraction completed successfully')

    except Exception as e:
        logger.error(f'Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
