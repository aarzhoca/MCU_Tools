"""
Import Nuvoton parametric XLS files into nuvoton_parts.json.

Usage:
    python scripts/import_xls.py

The script reads all .xls files in the 'Nuvoton mcu datasheet' folder,
maps columns to the unified schema, and writes backend/data/nuvoton_parts.json.

Column mapping — adjust COLUMN_MAP if your XLS headers differ.
"""

import json
import os
import sys
import xlrd

DATASHEET_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "Nuvoton mcu datasheet"
)
OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "nuvoton_parts.json"
)

# Maps lowercase header variants → unified field name
COLUMN_MAP = {
    "part no": "part_number",
    "part number": "part_number",
    "part no.": "part_number",
    "part": "part_number",
    "core": "core",
    "cpu": "core",
    "cpu core": "core",
    "max freq": "cpu_freq_mhz",
    "freq (mhz)": "cpu_freq_mhz",
    "cpu freq": "cpu_freq_mhz",
    "max cpu frequency (mhz)": "cpu_freq_mhz",
    "aprom (kb)": "flash_kb",
    "flash (kb)": "flash_kb",
    "rom": "flash_kb",
    "rom (kb)": "flash_kb",
    "flash": "flash_kb",
    "sram (kb)": "ram_kb",
    "ram (kb)": "ram_kb",
    "ram": "ram_kb",
    "sram": "ram_kb",
    "i/o": "gpio",
    "gpio": "gpio",
    "i/o count": "gpio",
    "gpio count": "gpio",
    "adc (ch)": "adc_channels",
    "adc channels": "adc_channels",
    "adc resolution": "adc_bits",
    "adc (bits)": "adc_bits",
    "uart": "uart",
    "spi": "spi",
    "i2c": "i2c",
    "usb": "usb",
    "can": "can",
    "ethernet": "ethernet",
    "operating temp": "temp_range",
    "temp (°c)": "temp_range",
    "temperature": "temp_range",
    "vcc": "vcc_range",
    "vcc (v)": "vcc_range",
    "supply voltage": "vcc_range",
    "package": "package",
    "pkg": "package",
}

FAMILY_CORE_MAP = {
    "m0": "Cortex-M0",
    "m23": "Cortex-M23",
    "m4": "Cortex-M4F",
    "m55": "Cortex-M55",
    "8051": "8051",
}


def parse_temp_range(val: str):
    """Returns (temp_min, temp_max) from strings like '-40..105' or '-40 to 105'."""
    if not isinstance(val, str):
        return -40, 85
    val = val.replace("to", "..").replace("~", "..")
    parts = val.split("..")
    if len(parts) == 2:
        try:
            return float(parts[0].strip()), float(parts[1].strip())
        except ValueError:
            pass
    return -40, 85


def parse_vcc(val: str):
    """Returns (vcc_min, vcc_max) from strings like '1.8..3.6'."""
    if not isinstance(val, str):
        return 1.8, 3.6
    val = val.replace("to", "..").replace("~", "..")
    parts = val.split("..")
    if len(parts) == 2:
        try:
            return float(parts[0].strip()), float(parts[1].strip())
        except ValueError:
            pass
    return 1.8, 3.6


def parse_bool(val) -> int:
    if isinstance(val, (int, float)):
        return 1 if val > 0 else 0
    if isinstance(val, str):
        return 1 if val.strip().upper() not in ("", "0", "N", "NO", "NONE", "-") else 0
    return 0


def read_xls(filepath: str, family_tag: str) -> list:
    wb = xlrd.open_workbook(filepath)
    ws = wb.sheet_by_index(0)

    # Find header row (first row with recognizable columns)
    header_row_idx = 0
    headers = []
    for r in range(min(5, ws.nrows)):
        row = [str(ws.cell_value(r, c)).strip().lower() for c in range(ws.ncols)]
        mapped = [COLUMN_MAP.get(h) for h in row]
        if sum(1 for m in mapped if m is not None) >= 3:
            headers = row
            header_row_idx = r
            break

    if not headers:
        print(f"  WARNING: Could not find header row in {filepath}")
        return []

    col_to_field = {c: COLUMN_MAP.get(headers[c]) for c in range(len(headers))}
    core_name = FAMILY_CORE_MAP.get(family_tag.lower(), "Unknown")

    parts = []
    for r in range(header_row_idx + 1, ws.nrows):
        row_data = {}
        for c, field in col_to_field.items():
            if field and c < ws.ncols:
                val = ws.cell_value(r, c)
                row_data[field] = val

        part_number = str(row_data.get("part_number", "")).strip()
        if not part_number or part_number.lower() in ("", "part no", "n/a"):
            continue

        # Parse temp range
        temp_min, temp_max = parse_temp_range(str(row_data.get("temp_range", "-40..105")))
        vcc_min, vcc_max = parse_vcc(str(row_data.get("vcc_range", "1.8..3.6")))

        part = {
            "part_number": part_number,
            "manufacturer": "Nuvoton",
            "family": family_tag.upper(),
            "core": str(row_data.get("core", core_name)).strip() or core_name,
            "cpu_freq_mhz": float(row_data.get("cpu_freq_mhz", 0) or 0),
            "ram_kb": float(row_data.get("ram_kb", 0) or 0),
            "flash_kb": float(row_data.get("flash_kb", 0) or 0),
            "gpio": int(float(row_data.get("gpio", 0) or 0)),
            "adc_bits": int(float(row_data.get("adc_bits", 12) or 12)),
            "adc_channels": int(float(row_data.get("adc_channels", 0) or 0)),
            "uart": int(float(row_data.get("uart", 0) or 0)),
            "spi": int(float(row_data.get("spi", 0) or 0)),
            "i2c": int(float(row_data.get("i2c", 0) or 0)),
            "usb": parse_bool(row_data.get("usb", 0)),
            "can": parse_bool(row_data.get("can", 0)),
            "ethernet": parse_bool(row_data.get("ethernet", 0)),
            "temp_max_c": temp_max,
            "vcc_min": vcc_min,
            "vcc_max": vcc_max,
            "package": str(row_data.get("package", "")).strip(),
        }
        parts.append(part)

    return parts


def main():
    if not os.path.isdir(DATASHEET_DIR):
        print(f"ERROR: Datasheet directory not found: {DATASHEET_DIR}")
        sys.exit(1)

    all_parts = []
    xls_files = [f for f in os.listdir(DATASHEET_DIR) if f.lower().endswith(".xls")]

    if not xls_files:
        print("No .xls files found in datasheet directory.")
        sys.exit(1)

    for filename in xls_files:
        filepath = os.path.join(DATASHEET_DIR, filename)
        # Derive family tag from filename (e.g. "Nuvoton_M23_20260218.xls" → "M23")
        name_parts = filename.replace(".xls", "").split("_")
        family_tag = next((p for p in name_parts if p.upper() in ("M0", "M4", "M23", "M55", "8051")), "Unknown")

        print(f"Reading {filename} (family: {family_tag}) ...")
        parts = read_xls(filepath, family_tag)
        print(f"  Found {len(parts)} parts")
        all_parts.extend(parts)

    if not all_parts:
        print("No parts extracted. Check column headers in the XLS files.")
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_parts, f, indent=2)

    print(f"\nDone. Wrote {len(all_parts)} Nuvoton parts to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
