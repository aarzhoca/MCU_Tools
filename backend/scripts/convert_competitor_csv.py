"""
Convert any competitor CSV to the Nuvoton cross-reference template format.

Usage:
    python scripts/convert_competitor_csv.py <input.csv> [output.csv]

If output is omitted, writes <input>_converted.csv next to the input file.

The script auto-detects column names for ST, NXP, Microchip, Renesas, Espressif,
TI, Infineon, and many other vendors. Unknown columns are matched by similarity.

After conversion, review the output CSV in Excel, then upload it via the
"Add competitor parts → Upload CSV" tab in the dashboard.
"""

import csv
import os
import sys

# Allow running from the backend/ directory or project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.column_mapper import detect_mapping, convert_row, ALIASES

TEMPLATE_FIELDS = [
    "part_number", "manufacturer", "family", "core",
    "cpu_freq_mhz", "ram_kb", "flash_kb", "gpio",
    "adc_bits", "adc_channels", "uart", "spi", "i2c",
    "usb", "usb_hs", "can", "ethernet",
    "temp_max_c", "vcc_min", "vcc_max", "package", "notes",
]


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    input_path = args[0]
    if not os.path.isfile(input_path):
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    if len(args) >= 2:
        output_path = args[1]
    else:
        base, _ = os.path.splitext(input_path)
        output_path = base + "_converted.csv"

    # Read input
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        source_headers = reader.fieldnames or []
        rows = list(reader)

    if not rows:
        print("ERROR: Input file is empty or has no data rows.")
        sys.exit(1)

    # Detect column mapping
    mapping = detect_mapping(source_headers)

    # Report what was found
    print(f"\nInput:  {input_path}  ({len(rows)} rows, {len(source_headers)} columns)")
    print(f"Output: {output_path}\n")

    print("Column mapping detected:")
    mapped_fields = set(mapping.values())
    for src, tgt in mapping.items():
        print(f"  '{src}'  →  {tgt}")

    unmatched = [h for h in source_headers if h not in mapping]
    if unmatched:
        print(f"\nIgnored columns (no match found):")
        for h in unmatched:
            print(f"  '{h}'")

    missing = [f for f in TEMPLATE_FIELDS[:4] if f not in mapped_fields]  # required fields
    if missing:
        print(f"\nWARNING: Required fields not detected: {missing}")
        print("Check the column headers in your CSV match the aliases list.")

    # Convert rows
    converted = []
    skipped = 0
    for row in rows:
        result = convert_row(row, mapping)
        if result:
            converted.append(result)
        else:
            skipped += 1

    # Write output
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TEMPLATE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(converted)

    print(f"\nConverted {len(converted)} parts  ({skipped} skipped — missing part number)")
    print(f"Saved to: {output_path}")
    print("\nNext step: Upload the converted CSV via the dashboard Import tab.")


if __name__ == "__main__":
    main()
