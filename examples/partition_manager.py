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
    from liblk import InvalidLkPartition, LkImage
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


def list_partitions(
    image_path: str,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    List all partitions in an LK image.

    Args:
        image_path: Path to the LK image file
        logger: Optional logger instance
    """
    log = logger or logging.getLogger(__name__)

    try:
        lk_image = LkImage(image_path)
        log.info(f'Loaded image with {len(lk_image)} partitions')

        print('\nPartitions in LK image:')
        print('-' * 50)
        for i, (name, partition) in enumerate(lk_image.partitions.items(), 1):
            certs_info = (
                f' ({len(partition.certs)} certs)' if partition.certs else ''
            )
            print(
                f'{i:2d}. {name:<20} {len(partition.data):>8} bytes{certs_info}'
            )
        print('-' * 50)

    except InvalidLkPartition as e:
        log.error(f'Partition parsing error: {e}')
        sys.exit(1)
    except Exception as e:
        log.error(f'Error processing image: {e}')
        sys.exit(1)


def add_partition(
    image_path: str,
    partition_name: str,
    data_file: str,
    output_path: Optional[str] = None,
    memory_address: int = 0,
    use_extended: bool = True,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Add a new partition to an LK image.

    Args:
        image_path: Path to the LK image file
        partition_name: Name for the new partition
        data_file: Path to file containing partition data
        output_path: Optional path for modified image
        memory_address: Load address for the partition
        use_extended: Use extended header format
        logger: Optional logger instance
    """
    log = logger or logging.getLogger(__name__)
    output_path = (
        output_path or os.path.splitext(image_path)[0] + '_modified.img'
    )

    try:
        if not os.path.exists(data_file):
            raise FileNotFoundError(f'Data file not found: {data_file}')

        with open(data_file, 'rb') as f:
            partition_data = f.read()

        lk_image = LkImage(image_path)
        log.info(f'Loaded image with {len(lk_image)} partitions')

        lk_image.add_partition(
            name=partition_name,
            data=partition_data,
            memory_address=memory_address,
            use_extended=use_extended,
        )

        log.info(
            f'Added partition: {partition_name} ({len(partition_data)} bytes)'
        )

        lk_image.save(output_path)
        log.info(f'Modified image saved: {output_path}')

    except ValueError as e:
        log.error(f'Invalid partition name: {e}')
        sys.exit(1)
    except Exception as e:
        log.error(f'Error adding partition: {e}')
        sys.exit(1)


def remove_partition(
    image_path: str,
    partition_name: str,
    output_path: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Remove a partition from an LK image.

    Args:
        image_path: Path to the LK image file
        partition_name: Name of partition to remove
        output_path: Optional path for modified image
        logger: Optional logger instance
    """
    log = logger or logging.getLogger(__name__)
    output_path = (
        output_path or os.path.splitext(image_path)[0] + '_modified.img'
    )

    try:
        lk_image = LkImage(image_path)
        log.info(f'Loaded image with {len(lk_image)} partitions')

        if partition_name not in lk_image.partitions:
            log.error(f'Partition not found: {partition_name}')
            list_partitions(image_path, log)
            sys.exit(1)

        lk_image.remove_partition(partition_name)
        log.info(f'Removed partition: {partition_name}')

        lk_image.save(output_path)
        log.info(f'Modified image saved: {output_path}')

    except KeyError as e:
        log.error(f'Partition not found: {e}')
        sys.exit(1)
    except Exception as e:
        log.error(f'Error removing partition: {e}')
        sys.exit(1)


def add_certificate(
    image_path: str,
    partition_name: str,
    cert_file: str,
    cert_type: str = 'cert1',
    output_path: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Add a certificate to a partition.

    Args:
        image_path: Path to the LK image file
        partition_name: Name of target partition
        cert_file: Path to certificate file
        cert_type: Certificate type ('cert1' or 'cert2')
        output_path: Optional path for modified image
        logger: Optional logger instance
    """
    log = logger or logging.getLogger(__name__)
    output_path = (
        output_path or os.path.splitext(image_path)[0] + '_modified.img'
    )

    try:
        if not os.path.exists(cert_file):
            raise FileNotFoundError(f'Certificate file not found: {cert_file}')

        with open(cert_file, 'rb') as f:
            cert_data = f.read()

        lk_image = LkImage(image_path)

        if partition_name not in lk_image.partitions:
            log.error(f'Partition not found: {partition_name}')
            sys.exit(1)

        partition = lk_image.partitions[partition_name]
        partition.add_certificate(cert_data, cert_type)

        log.info(
            f'Added {cert_type} to partition {partition_name} ({len(cert_data)} bytes)'
        )

        lk_image._rebuild_contents()
        lk_image.save(output_path)
        log.info(f'Modified image saved: {output_path}')

    except ValueError as e:
        log.error(f'Invalid certificate type: {e}')
        sys.exit(1)
    except Exception as e:
        log.error(f'Error adding certificate: {e}')
        sys.exit(1)


def main() -> None:
    """
    Main script entry point.
    """
    parser = argparse.ArgumentParser(
        description='Manage partitions in LK bootloader images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s list image.img
  %(prog)s add image.img new_part data.bin -a 0x41000000
  %(prog)s remove image.img unwanted_part
  %(prog)s cert image.img lk cert1.der --cert-type cert1""",
    )

    parser.add_argument(
        'action',
        choices=['list', 'add', 'remove', 'cert'],
        help='Action to perform',
    )
    parser.add_argument('image_path', help='Path to the LK image file')
    parser.add_argument(
        'partition_name',
        nargs='?',
        help='Partition name (required for add/remove/cert)',
    )
    parser.add_argument(
        'data_file', nargs='?', help='Data file path (required for add/cert)'
    )

    parser.add_argument('-o', '--output', help='Output path for modified image')
    parser.add_argument(
        '-a',
        '--address',
        type=lambda x: int(x, 0),
        default=0,
        help='Memory address for new partition (hex or decimal)',
    )
    parser.add_argument(
        '--legacy',
        action='store_true',
        help='Use legacy header format (default: extended)',
    )
    parser.add_argument(
        '--cert-type',
        choices=['cert1', 'cert2'],
        default='cert1',
        help='Certificate type (default: cert1)',
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose logging'
    )

    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    try:
        validated_path = validate_image_path(args.image_path)

        if args.action == 'list':
            list_partitions(validated_path, logger)

        elif args.action == 'add':
            if not args.partition_name or not args.data_file:
                parser.error('add action requires partition_name and data_file')
            add_partition(
                validated_path,
                args.partition_name,
                args.data_file,
                args.output,
                args.address,
                not args.legacy,
                logger,
            )

        elif args.action == 'remove':
            if not args.partition_name:
                parser.error('remove action requires partition_name')
            remove_partition(
                validated_path, args.partition_name, args.output, logger
            )

        elif args.action == 'cert':
            if not args.partition_name or not args.data_file:
                parser.error(
                    'cert action requires partition_name and data_file'
                )
            add_certificate(
                validated_path,
                args.partition_name,
                args.data_file,
                args.cert_type,
                args.output,
                logger,
            )

    except Exception as e:
        logger.error(f'Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
