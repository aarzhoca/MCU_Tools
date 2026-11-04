"""Signed, process-local comparison snapshots and literal-text XLSX export."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import hmac
import io
import json
import secrets
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

_KEY = secrets.token_bytes(32)
MAX_BYTES = 400_000
DISCLAIMER = "Preliminary candidates only. PASS covers checked requirements, not pin, firmware, simultaneous operating conditions, or engineering approval."
FIELDS = [
    ("core", "Core", ""), ("cpu_freq_mhz", "CPU frequency", "MHz"),
    ("flash_kb", "Flash", "KB"), ("ram_kb", "RAM", "KB"), ("gpio", "GPIO", "pins"),
    ("package", "Package", ""), ("package_width_mm", "Body width", "mm"),
    ("package_height_mm", "Body height", "mm"), ("package_size_mm2", "Body area", "mm2"),
    ("vcc_min", "Minimum supply", "V"), ("vcc_max", "Maximum supply", "V"),
    ("temp_min_c", "Minimum operating temperature", "C"), ("temp_max_c", "Maximum operating temperature", "C"),
    ("uart", "UART", ""), ("spi", "SPI", ""), ("i2c", "I2C", ""),
    ("usb", "USB FS", ""), ("usb_hs", "USB HS", ""), ("can", "Classic CAN", ""),
    ("can_fd", "CAN FD", ""), ("ethernet", "Ethernet", ""), ("crypto", "Hardware crypto", ""),
    ("adc_bits", "ADC resolution", "bits"), ("adc_channels", "ADC channels", ""),
    ("price_1k_usd", "Estimated 1k price", "USD"),
]


def _canonical(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(payload) > MAX_BYTES:
        raise ValueError("Comparison snapshot exceeds size limit")
    return payload


def _quality(record, field):
    quality = record.get("field_quality") or {}
    if record.get(field) is None or not isinstance(quality, dict):
        return "unknown"
    return quality.get(field, "catalog")


def create_snapshot(result, catalog):
    candidates, seen = [], set()
    for group in ("matches", "failed_candidates", "unknown_candidates", "unranked_candidates"):
        for match in result.get(group, []):
            name = match["part_number"]
            if name in seen:
                continue
            records = [part for part in catalog if part.get("part_number") == name]
            if len(records) != 1:
                raise ValueError("Comparison requires unique catalog part numbers: " + name)
            seen.add(name)
            candidates.append({**deepcopy(match), "group": group,
                "values": {key: records[0].get(key) for key, _, _ in FIELDS},
                "field_quality": deepcopy(records[0].get("field_quality") or {}),
                "field_sources": deepcopy(records[0].get("field_sources") or {})})
    rows = []
    requirements = result.get("requirements_used", [])
    for field, label, unit in FIELDS:
        rules = [rule for rule in requirements if rule["field"] == field]
        cells = []
        for candidate in candidates:
            checks = [check for check in candidate["requirement_checks"] if check["field"] == field]
            statuses = {check["status"] for check in checks}
            status = "FAIL" if "FAIL" in statuses else "UNKNOWN" if "UNKNOWN" in statuses else "PASS" if checks else "NOT_CHECKED"
            cells.append({"part_number": candidate["part_number"], "value": candidate["values"][field],
                          "status": status, "quality": _quality({**candidate["values"], "field_quality":candidate["field_quality"]}, field)})
        rows.append({"field":field, "label":label, "unit":unit,
            "requirements":"; ".join(str(rule["operator"]) + " " + str(rule["value"]) for rule in rules) or "Not required",
            "source_value":result["source"].get(field), "source_quality":_quality(result["source"], field), "candidates":cells})
    catalog_hash = hashlib.sha256(json.dumps(catalog, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    snapshot = {"schema":"mcu-comparison-v1", "generated_at":datetime.now(timezone.utc).isoformat(),
        "application_version":"1.0.0", "comparison_version":"1", "ranking_version":"legacy-weighted-90-10/workspace-v1", "catalog_sha256":catalog_hash,
        "ranking_mode":result.get("ranking_mode"), "source":deepcopy(result["source"]),
        "requirements":deepcopy(requirements), "candidates":candidates, "rows":rows,
        "disclaimer":DISCLAIMER, "warnings":["Catalog values are not all independently verified.",
            "Missing dimensions do not establish physical compatibility.",
            "This signed snapshot expires after 8 hours or a backend restart."]}
    payload = _canonical(snapshot)
    token = hmac.new(_KEY, payload, hashlib.sha256).hexdigest()
    return payload.decode("utf-8"), token


def validate_selection(snapshot_json, token, selected):
    payload = snapshot_json.encode("utf-8")
    if len(payload) > MAX_BYTES:
        raise ValueError("Comparison snapshot exceeds size limit")
    expected = hmac.new(_KEY, payload, hashlib.sha256).hexdigest()
    if not isinstance(token, str) or not hmac.compare_digest(expected, token):
        raise ValueError("Snapshot changed or backend restarted; rerun matching")
    snapshot = json.loads(snapshot_json)
    stamp = datetime.fromisoformat(snapshot["generated_at"])
    age = (datetime.now(timezone.utc) - stamp).total_seconds()
    if age < -300 or age > 8 * 3600:
        raise ValueError("Snapshot expired; rerun matching")
    if not 1 <= len(selected) <= 3 or len(set(selected)) != len(selected):
        raise ValueError("Select one to three distinct candidates")
    allowed = {candidate["part_number"] for candidate in snapshot["candidates"]}
    if any(name not in allowed for name in selected):
        raise ValueError("Selected candidate is not in the displayed snapshot")
    return snapshot


def _append(sheet, values):
    row = sheet.max_row + 1 if sheet.cell(1, 1).value is not None else 1
    for index, value in enumerate(values, 1):
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if value is None:
            value = "Unknown"
        if isinstance(value, str) and (len(value) > 32767 or ILLEGAL_CHARACTERS_RE.search(value)):
            raise ValueError("Text is not representable in an Excel cell")
        cell = sheet.cell(row=row, column=index, value=value)
        if isinstance(value, str):
            cell.data_type = "s"


def export_xlsx(snapshot_json, token, selected):
    snapshot = validate_selection(snapshot_json, token, selected)
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    _append(summary, ["Field", "Value"])
    for key in ("generated_at", "application_version", "comparison_version", "ranking_version", "catalog_sha256", "ranking_mode", "disclaimer"):
        _append(summary, [key, snapshot.get(key)])
    _append(summary, ["Source part", snapshot["source"]["part_number"]])
    _append(summary, ["Requirements", snapshot["requirements"]])
    for candidate in snapshot["candidates"]:
        if candidate["part_number"] in selected:
            _append(summary, [candidate["part_number"], candidate["eligibility"], candidate.get("similarity_pct"), candidate.get("reason", "")])
    for warning in snapshot["warnings"]:
        _append(summary, ["Warning", warning])
    comparison = workbook.create_sheet("Comparison")
    headings = ["Parameter", "Unit", "Customer requirement", "Source value", "Source quality"]
    for name in selected:
        headings.extend([name + " value", name + " check", name + " quality"])
    _append(comparison, headings)
    for row in snapshot["rows"]:
        values = [row["label"], row["unit"], row["requirements"], row["source_value"], row["source_quality"]]
        cells = {cell["part_number"]:cell for cell in row["candidates"]}
        for name in selected:
            cell = cells[name]
            values.extend([cell["value"], cell["status"], cell["quality"]])
        _append(comparison, values)
    sources = workbook.create_sheet("Sources")
    _append(sources, ["Part", "Field", "Evidence / explanation"])
    _append(sources, [snapshot["source"]["part_number"], "Uploaded source", snapshot["source"].get("source", {})])
    for candidate in snapshot["candidates"]:
        if candidate["part_number"] not in selected:
            continue
        _append(sources, [candidate["part_number"], "Requirement checks", candidate["requirement_checks"]])
        for field, evidence in candidate["field_sources"].items():
            _append(sources, [candidate["part_number"], field, evidence])
        if not candidate["field_sources"]:
            _append(sources, [candidate["part_number"], "Evidence", "No per-field reference supplied; see quality labels"])
    for sheet in workbook:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="9D1535")
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = 26
        for row in sheet:
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()
