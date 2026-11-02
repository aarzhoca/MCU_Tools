"""
Import the optimized Nuvoton master table into nuvoton_parts.json.

Usage:
    python scripts/import_master_table.py

Reads:
    Nuvoton mcu datasheet/Nuvoton_MCU_Master_Table.xlsx  (single source of
    truth - see scripts/build_master_table.py for how it's generated from
    the full vendor export)
Writes:
    backend/data/nuvoton_parts.json
"""

import json
import os
import re
import sys

import openpyxl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.matcher import _resolve_package_size  # noqa: E402

DATASHEET_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "Nuvoton mcu datasheet"
)
SOURCE_FILE = os.path.join(DATASHEET_DIR, "Nuvoton_MCU_Master_Table.xlsx")
OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "nuvoton_parts.json"
)


def _num(val, default=0):
    if val is None or val == "":
        return default
    return float(val)


def _int(val, default=0):
    return int(_num(val, default))


def _bool(val) -> int:
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return 1 if val > 0 else 0
    return 1 if str(val).strip().upper() not in ("", "0", "N", "NO", "NONE", "-") else 0


def _parse_package_size(val) -> float:
    """'7x7' -> 49.0, '4.4x6.5' -> 28.6, case-insensitive, whitespace-tolerant."""
    if not val:
        return 0.0
    m = re.match(r"\s*([\d.]+)\s*[xX]\s*([\d.]+)", str(val))
    if not m:
        return 0.0
    return round(float(m.group(1)) * float(m.group(2)), 1)


def main():
    wb = openpyxl.load_workbook(SOURCE_FILE, read_only=True, data_only=True)
    ws = wb["Parameters"]
    rows = list(ws.iter_rows(min_row=1, values_only=True))
    header = rows[0]
    idx = {name: i for i, name in enumerate(header)}

    def g(row, col):
        return row[idx[col]] if col in idx else None

    parts = []
    for row in rows[1:]:
        part_number = str(g(row, "Part Number") or "").strip()
        if not part_number:
            continue

        core_val = g(row, "Core")
        core = str(int(core_val)) if isinstance(core_val, (int, float)) else str(core_val or "").strip()

        pkg_type = str(g(row, "Package Type") or "").strip()
        measured_size = _parse_package_size(g(row, "Package Size mm"))
        package_size_mm2 = _resolve_package_size(pkg_type, measured_size)

        usb_speed = str(g(row, "USB Speed") or "").upper()
        usb_instances = _int(g(row, "USB Instances"))

        raw_price = g(row, "Est 1k Price USD")
        try:
            price_1k_usd = float(raw_price) if raw_price is not None else None
        except (TypeError, ValueError):
            price_1k_usd = None

        part = {
            "part_number": part_number,
            "manufacturer": "Nuvoton",
            "family": str(g(row, "Family") or "").strip(),
            "core": core,
            "status": str(g(row, "Status") or "MP").strip() or "MP",
            "cpu_freq_mhz": _num(g(row, "Freq MHz")),
            "ram_kb": _num(g(row, "RAM KB")),
            "flash_kb": _num(g(row, "Flash KB")),
            "gpio": _int(g(row, "GPIO")),
            "adc_bits": _int(g(row, "ADC Bits"), 12),
            "adc_channels": _int(g(row, "ADC Channels")),
            "uart": _int(g(row, "UART")),
            "spi": _int(g(row, "SPI")),
            "i2c": _int(g(row, "I2C")),
            "usb": 1 if usb_instances > 0 else 0,
            "usb_hs": 1 if "HS" in usb_speed else 0,
            "can": _int(g(row, "CAN")),
            "can_fd": _int(g(row, "CAN FD")),
            "ethernet": _bool(g(row, "Ethernet")),
            "crypto": 1 if (g(row, "Crypto") or g(row, "AES")) else 0,
            "temp_max_c": _num(g(row, "Temp Max C"), 85),
            "vcc_min": _num(g(row, "Vcc Min V"), 1.8),
            "vcc_max": _num(g(row, "Vcc Max V"), 3.6),
            "package": pkg_type,
            "package_size_mm2": package_size_mm2,
            "price_1k_usd": price_1k_usd,
        }
        parts.append(part)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(parts, f, indent=2)

    print(f"Wrote {len(parts)} Nuvoton parts to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
