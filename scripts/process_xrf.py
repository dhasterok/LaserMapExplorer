#!/usr/bin/env python3
"""
Process XRF/EDS BCF files with element identification and quantification.

This script provides a command-line interface to the XRFProcessor module.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.app.XRFProcessor import XRFProcessor, process_xrf_file


def main():
    """Main entry point for XRF processing script."""

    # Common rock-forming elements
    COMMON_ELEMENTS = ['O', 'Na', 'Mg', 'Al', 'Si', 'P', 'K', 'Ca', 'Ti', 'Mn', 'Fe']

    if len(sys.argv) < 2:
        print("XRF/EDS Data Processor")
        print("=" * 50)
        print("\nUsage:")
        print("  python process_xrf.py <bcf_file> [elements...]")
        print("\nExamples:")
        print("  # Use default rock-forming elements")
        print("  python process_xrf.py data.bcf")
        print()
        print("  # Specify custom elements")
        print("  python process_xrf.py data.bcf Si Fe Ca Mg Al")
        print()
        print(f"Default elements: {', '.join(COMMON_ELEMENTS)}")
        sys.exit(1)

    bcf_file = sys.argv[1]

    # Use provided elements or defaults
    if len(sys.argv) > 2:
        elements = sys.argv[2:]
    else:
        elements = COMMON_ELEMENTS
        print(f"Using default rock-forming elements: {', '.join(elements)}\n")

    # Process the file
    try:
        processor = process_xrf_file(bcf_file, elements)
        print("\n" + "=" * 50)
        print("✓ SUCCESS!")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
