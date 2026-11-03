"""ST ProductsList XLSX dry-run parser. Never writes catalog data.

Output is a staging format, not legacy ChipSpec; do not send it to /bulk.
"""
import hashlib
import io
import math
import re
import zipfile
from openpyxl import load_workbook

COLUMNS = {
    "cpu_freq_mhz": "Operating Frequency (MHz)",
    "flash_kb": "Flash Size (kB) (Prog)", "ram_kb": "RAM Size (kB)",
    "gpio": "I/Os (High Current)", "uart": "UART Total", "spi": "SPI Total",
    "i2c": "I2C Total", "temp_min_c": "Operating Temperature (°C) min",
    "temp_max_c": "Operating Temperature (°C) max",
    "vcc_min": "Supply Voltage (V) min", "vcc_max": "Supply Voltage (V) max",
}
MISSING = {"", "-", "n/a", "none"}


def _number(value, field):
    text = str(value).strip().replace("−", "-") if value is not None else ""
    if text.lower() in MISSING:
        return None
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text):
        return None
    result = float(text)
    if not math.isfinite(result) or (not field.startswith("temp_") and result < 0):
        return None
    if field in {"gpio", "uart", "spi", "i2c"} and not result.is_integer():
        return None
    return result


def parse_st_xlsx(content, filename="upload.xlsx", sheet="ProductsList"):
    """Parse explicit ST headers; preserve unknowns without guessed defaults.

    Limits: 20 MiB compressed, 100 MiB expanded, 10,000 physical data rows,
    200 columns. Formula cells are rejected per row, never evaluated.
    These are parser bounds, not a full untrusted-file security guarantee.
    """
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("ST parser accepts .xlsx only")
    if len(content) > 20 * 1024 * 1024:
        raise ValueError("Workbook exceeds 20 MiB")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        if sum(info.file_size for info in archive.infolist()) > 100 * 1024 * 1024:
            raise ValueError("Expanded workbook exceeds 100 MiB")
    digest = hashlib.sha256(content).hexdigest()
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
    try:
        if sheet not in workbook.sheetnames:
            raise ValueError("Select an available sheet: " + ", ".join(workbook.sheetnames))
        ws = workbook[sheet]
        if (ws.max_row or 0) > 10001 or (ws.max_column or 0) > 200:
            raise ValueError("Sheet exceeds row/column limits")
        rows = ws.iter_rows(values_only=True)
        headers = [str(value).strip() if value is not None else "" for value in next(rows, ())]
        named = [header for header in headers if header]
        if len(set(named)) != len(named):
            raise ValueError("Duplicate named headers need review")
        if not {"Part Number", "Core", "Operating Frequency (MHz)"}.issubset(named):
            raise ValueError("Expected ST header row at row 1")
        records, errors, seen = [], [], set()
        for row_number, values in enumerate(rows, 2):
            if row_number > 10001:
                raise ValueError("Sheet exceeds row limit")
            if len(values) > 200:
                raise ValueError("Sheet exceeds column limit")
            row = dict(zip(headers, values))
            part = str(row.get("Part Number") or "").strip()
            if not part:
                continue
            if any(isinstance(value, str) and value.startswith("=") for value in values):
                errors.append({"row": row_number, "part": part, "error": "Formula cell: row skipped"})
                continue
            if part.upper() in seen:
                errors.append({"row": row_number, "part": part, "error": "Duplicate part: row skipped"})
                continue
            seen.add(part.upper())
            record = {"part_number": part, "manufacturer": "STMicroelectronics"}
            for field, header in COLUMNS.items():
                record[field] = _number(row.get(header), field)
            for low, high in (("vcc_min", "vcc_max"), ("temp_min_c", "temp_max_c")):
                if record[low] is not None and record[high] is not None and record[low] > record[high]:
                    record[low] = record[high] = None
            core = re.sub(r"^Arm\s+", "", str(row.get("Core") or "").strip(), flags=re.I)
            fpu = str(row.get("FPU") or "").strip()
            if core == "Cortex-M4" and "single-precision" in fpu.lower():
                core = "Cortex-M4F"
            record["core"] = None if core.lower() in MISSING else core
            record["fpu_source"] = fpu or None
            package = str(row.get("Package") or "").strip()
            match = re.fullmatch(r"LQFP\s*(\d+)\s+(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)\s*mm", package, re.I)
            record.update(package=None, package_width_mm=None, package_height_mm=None,
                          package_size_mm2=None, package_source=package or None)
            if match:
                record["package"] = "LQFP" + match[1]
                record["package_width_mm"] = float(match[2])
                record["package_height_mm"] = float(match[3])
                record["package_size_mm2"] = float(match[2]) * float(match[3])
            # Peripheral semantics are deliberately not guessed from USB Total,
            # ADC channel columns, security text, or combined CAN counts.
            for field in ("usb", "usb_hs", "can", "can_fd", "ethernet", "crypto", "adc_bits", "adc_channels"):
                record[field] = None
            record["field_quality"] = {key: "unknown" if value is None else "catalog"
                for key, value in record.items() if key not in {"part_number", "manufacturer"}}
            record["source"] = {"file": filename, "sheet": sheet, "row": row_number,
                                "sha256": digest}
            record["source_values"] = {key: value for key, value in row.items() if key}
            records.append(record)
        return {"format": "st-xlsx-staging-v1", "sheet": sheet, "records": records,
                "errors": errors, "parsed_count": len(records),
                "warnings": ["Preview only: no catalog has been changed.",
                    "Catalog data is not independent datasheet verification.",
                    "Unmapped peripherals and unsupported package formats remain unknown."]}
    finally:
        workbook.close()
