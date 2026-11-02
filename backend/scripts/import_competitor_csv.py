"""
Import competitor parts from a CSV file into competitor_parts.json.

Usage:
    python scripts/import_competitor_csv.py <path_to_csv>  [--replace]

Options:
    --replace   Overwrite the full catalog instead of merging.
                Default: merge (new parts added, existing parts updated by part_number).

CSV format: see backend/data/competitor_template.csv for the exact columns.
All columns except part_number, manufacturer, family, core are optional (default 0).

Examples:
    python scripts/import_competitor_csv.py data/my_stm32_parts.csv
    python scripts/import_competitor_csv.py data/nxp_parts.csv --replace
"""

import csv
import json
import os
import sys

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "competitor_parts.json")

INT_FIELDS   = ["gpio", "adc_bits", "adc_channels", "uart", "spi", "i2c",
                "usb", "usb_hs", "can", "ethernet"]
FLOAT_FIELDS = ["cpu_freq_mhz", "ram_kb", "flash_kb", "temp_max_c", "vcc_min", "vcc_max"]
STR_FIELDS   = ["part_number", "manufacturer", "family", "core", "package", "notes"]

DEFAULTS = {
    "gpio": 0, "adc_bits": 12, "adc_channels": 0,
    "uart": 0, "spi": 0, "i2c": 0,
    "usb": 0, "usb_hs": 0, "can": 0, "ethernet": 0,
    "cpu_freq_mhz": 0.0, "ram_kb": 0.0, "flash_kb": 0.0,
    "temp_max_c": 85.0, "vcc_min": 1.8, "vcc_max": 3.6,
    "package": "", "notes": "",
}


def parse_bool(val: str) -> int:
    """Accept 1/0/yes/no/true/false."""
    return 0 if str(val).strip().lower() in ("", "0", "no", "false", "n") else 1


def parse_row(row: dict) -> dict:
    part = {}
    for f in STR_FIELDS:
        part[f] = row.get(f, "").strip()
    for f in FLOAT_FIELDS:
        raw = row.get(f, "").strip()
        part[f] = float(raw) if raw else DEFAULTS[f]
    for f in INT_FIELDS:
        raw = row.get(f, "").strip()
        if f in ("usb", "usb_hs", "can", "ethernet"):
            part[f] = parse_bool(raw) if raw else DEFAULTS[f]
        else:
            part[f] = int(float(raw)) if raw else DEFAULTS[f]
    return part


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    csv_path = args[0]
    replace_mode = "--replace" in args

    if not os.path.isfile(csv_path):
        print(f"ERROR: File not found: {csv_path}")
        sys.exit(1)

    # Read incoming CSV
    incoming = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("part_number", "").strip():
                continue
            try:
                incoming.append(parse_row(row))
            except Exception as e:
                print(f"  WARNING: Skipping row {row.get('part_number','?')}: {e}")

    if not incoming:
        print("No valid rows found in CSV.")
        sys.exit(1)

    if replace_mode:
        merged = incoming
        print(f"Replace mode: writing {len(merged)} parts.")
    else:
        # Load existing catalog
        existing = []
        if os.path.isfile(OUTPUT_FILE):
            with open(OUTPUT_FILE, encoding="utf-8") as f:
                existing = json.load(f)

        # Merge: index by part_number, incoming wins on conflict
        catalog = {p["part_number"].upper(): p for p in existing}
        added, updated = 0, 0
        for p in incoming:
            key = p["part_number"].upper()
            if key in catalog:
                catalog[key] = p
                updated += 1
            else:
                catalog[key] = p
                added += 1
        merged = list(catalog.values())
        print(f"Merge mode: {added} new, {updated} updated -> {len(merged)} total parts.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    print(f"Saved to {OUTPUT_FILE}")
    print("\nImported parts:")
    for p in incoming:
        print(f"  {p['part_number']:<24} {p['manufacturer']} · {p['core']} · {p['cpu_freq_mhz']} MHz")


if __name__ == "__main__":
    main()
