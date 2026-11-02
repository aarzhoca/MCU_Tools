"""
One-off: build the optimized, lean master table from the full 106-column
Nuvoton master table export.

Usage:
    python scripts/build_master_table.py

Reads:
    Nuvoton mcu datasheet/Nuvoton Master Table MCU v7-27-2026 to be optimized.xlsx
Writes:
    Nuvoton mcu datasheet/Nuvoton_MCU_Master_Table.xlsx

This trims ~106 columns down to the ~25 the matching engine actually uses,
and drops rows for MPU-class parts (Cortex-A35 application processors,
ARM926EJ-S parts) that don't fit the Cortex-M cross-reference model.
After this file is generated and verified, the legacy per-family .xls files
and the original "to be optimized" file are no longer needed.
"""

import os
import openpyxl

DATASHEET_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "Nuvoton mcu datasheet"
)
SOURCE_FILE = os.path.join(
    DATASHEET_DIR, "Nuvoton Master Table MCU v7-27-2026 to be optimized.xlsx"
)
OUTPUT_FILE = os.path.join(DATASHEET_DIR, "Nuvoton_MCU_Master_Table.xlsx")

# Cores that indicate an MPU-class part (application processor), not a
# Cortex-M/8-bit MCU comparable to the competitor catalog.
EXCLUDED_CORES = {"Dual Cortex-A35", "Dual Cortex-A35, M4", "ARM926EJ-S"}

# (new column name, source column name(s) — first non-empty wins)
COLUMN_SPEC = [
    ("Part Number", ["Full Part Number"]),
    ("Family", ["Family"]),
    ("Core", ["Core"]),
    ("Status", ["Status"]),
    ("Est 1k Price USD", ["Est. 1k (+25 points)"]),
    ("Freq MHz", ["Operating Frequency (MHz)"]),
    ("Vcc Min V", ["Operating Voltage (V) (min)"]),
    ("Vcc Max V", ["Operating Voltage (V)  (max)"]),
    ("Temp Max C", ["Operating Temperature (degC) (max)"]),
    ("GPIO", ["GPIO"]),
    ("Flash KB", ["APROM Flash (kB)"]),
    ("RAM KB", ["SRAM (kB)"]),
    ("ADC Bits", ["ADC Resolution (bits)", "EADC Resolution (bits)"]),
    ("ADC Channels", ["ADC Channels", "EADC Channels"]),
    ("UART", ["UART", "LPUART"]),
    ("SPI", ["SPI", "QSPI", "LPSPI"]),
    ("I2C", ["I²C", "LPI²C"]),
    ("USB Instances", ["USB Instances"]),
    ("USB Speed", ["USB Speed"]),
    ("CAN", ["CAN"]),
    ("CAN FD", ["CAN FD"]),
    ("Ethernet", ["Ethernet MAC"]),
    ("Crypto", ["Crypto"]),
    ("AES", ["AES"]),
    ("Package Type", ["Package Type"]),
    ("Package Size mm", ["Package Size"]),
]


def main():
    wb = openpyxl.load_workbook(SOURCE_FILE, read_only=True, data_only=True)
    ws = wb["Parameters"]

    rows = list(ws.iter_rows(min_row=1, values_only=True))
    header = rows[0]
    idx = {name: i for i, name in enumerate(header)}

    out_wb = openpyxl.Workbook()
    out_ws = out_wb.active
    out_ws.title = "Parameters"

    new_headers = [spec[0] for spec in COLUMN_SPEC]
    out_ws.append(new_headers)

    kept, dropped_mpu, dropped_blank = 0, 0, 0
    for row in rows[1:]:
        if row[0] is None:
            dropped_blank += 1
            continue
        core_val = str(row[idx["Core"]]) if row[idx["Core"]] is not None else ""
        if core_val in EXCLUDED_CORES:
            dropped_mpu += 1
            continue

        out_row = []
        for new_name, source_names in COLUMN_SPEC:
            val = None
            for src in source_names:
                if src not in idx:
                    continue
                v = row[idx[src]]
                if v not in (None, ""):
                    val = v
                    break
            out_row.append(val)
        out_ws.append(out_row)
        kept += 1

    out_wb.save(OUTPUT_FILE)
    print(f"Source rows: {len(rows) - 1}")
    print(f"Dropped (blank part number): {dropped_blank}")
    print(f"Dropped (MPU-class core): {dropped_mpu}")
    print(f"Kept: {kept}")
    print(f"Columns: {len(new_headers)} (was {len(header)})")
    print(f"Wrote: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
