import csv
import io
import json
import os
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Body
from typing import List

from ..data_loader import (
    get_nuvoton_parts,
    get_competitor_parts,
    find_competitor_part,
    search_competitor_parts,
    reload_data,
)
from ..models import ChipSpec
from ..column_mapper import detect_mapping, convert_row, ALIASES, TEMPLATE_FIELDS
from ..matcher import CHARACTERISTICS

router = APIRouter(prefix="/api", tags=["chips"])

COMPETITOR_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "competitor_parts.json"
)

INT_FIELDS   = ["gpio", "adc_bits", "adc_channels", "uart", "spi", "i2c",
                "usb", "usb_hs", "can", "can_fd", "ethernet", "crypto"]
FLOAT_FIELDS = ["cpu_freq_mhz", "ram_kb", "flash_kb", "temp_max_c", "vcc_min", "vcc_max"]
DEFAULTS = {
    "gpio": 0, "adc_bits": 12, "adc_channels": 0,
    "uart": 0, "spi": 0, "i2c": 0,
    "usb": 0, "usb_hs": 0, "can": 0, "can_fd": 0, "ethernet": 0, "crypto": 0,
    "cpu_freq_mhz": 0.0, "ram_kb": 0.0, "flash_kb": 0.0,
    "temp_max_c": 85.0, "vcc_min": 1.8, "vcc_max": 3.6,
    "package": "", "notes": "",
}


def _parse_bool(val: str) -> int:
    return 0 if str(val).strip().lower() in ("", "0", "no", "false", "n", "-") else 1


def _parse_csv_row(row: dict) -> dict:
    part = {}
    for f in ["part_number", "manufacturer", "family", "core", "package", "notes"]:
        part[f] = row.get(f, "").strip()
    for f in FLOAT_FIELDS:
        raw = row.get(f, "").strip()
        part[f] = float(raw) if raw else DEFAULTS[f]
    for f in INT_FIELDS:
        raw = row.get(f, "").strip()
        if f in ("usb", "usb_hs", "can", "can_fd", "ethernet", "crypto"):
            part[f] = _parse_bool(raw) if raw else DEFAULTS[f]
        else:
            part[f] = int(float(raw)) if raw else DEFAULTS[f]
    return part


def _save_catalog(parts: list) -> None:
    with open(COMPETITOR_FILE, "w", encoding="utf-8") as f:
        json.dump(parts, f, indent=2)
    reload_data()


# ── Routes ────────────────────────────────────────────────────────────────

@router.get("/characteristics")
def list_characteristics():
    return CHARACTERISTICS


@router.get("/chips/nuvoton", response_model=List[ChipSpec])
def list_nuvoton_parts():
    return get_nuvoton_parts()


@router.get("/chips/competitor", response_model=List[ChipSpec])
def list_competitor_parts():
    return get_competitor_parts()


@router.get("/chips/competitor/search", response_model=List[ChipSpec])
def search_parts(q: str = Query(default="", description="Part number or manufacturer search")):
    return search_competitor_parts(q)


@router.get("/chips/competitor/{part_number}", response_model=ChipSpec)
def get_competitor_part(part_number: str):
    part = find_competitor_part(part_number)
    if not part:
        raise HTTPException(status_code=404, detail=f"Part '{part_number}' not found")
    return part


@router.post("/chips/competitor", response_model=ChipSpec, status_code=201)
def add_or_update_competitor_part(part: ChipSpec):
    """Add or update a single competitor part."""
    parts = list(get_competitor_parts())
    idx = next((i for i, p in enumerate(parts)
                if p["part_number"].upper() == part.part_number.upper()), None)
    part_dict = part.model_dump()
    if idx is not None:
        parts[idx] = part_dict
    else:
        parts.append(part_dict)
    _save_catalog(parts)
    return part


@router.post("/chips/competitor/import-csv")
async def import_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file to bulk-import competitor parts.
    Accepts the same column layout as competitor_template.csv.
    Merges with existing catalog (new parts added, existing updated by part_number).
    Returns counts of added/updated parts and a preview of what was imported.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")   # strips BOM if present
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    incoming = []
    errors = []
    for i, row in enumerate(reader, start=2):
        pn = row.get("part_number", "").strip()
        if not pn:
            continue
        try:
            incoming.append(_parse_csv_row(row))
        except Exception as e:
            errors.append(f"Row {i} ({pn}): {e}")

    if not incoming:
        raise HTTPException(status_code=422,
                            detail="No valid rows found. Check the CSV column headers match the template.")

    existing = list(get_competitor_parts())
    catalog = {p["part_number"].upper(): p for p in existing}
    added, updated = 0, 0
    for p in incoming:
        key = p["part_number"].upper()
        if key in catalog:
            updated += 1
        else:
            added += 1
        catalog[key] = p

    _save_catalog(list(catalog.values()))

    return {
        "added": added,
        "updated": updated,
        "total_in_catalog": len(catalog),
        "imported": incoming,
        "errors": errors,
    }


@router.post("/chips/competitor/convert-preview")
async def convert_csv_preview(file: UploadFile = File(...)):
    """
    Upload any vendor CSV (ST, NXP, Renesas, Microchip, etc.).
    Returns auto-detected column mapping + converted preview rows.
    Does NOT import anything — call /bulk after user confirms.
    """
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    source_headers = reader.fieldnames or []
    all_rows = list(reader)

    if not all_rows:
        raise HTTPException(status_code=422, detail="CSV file is empty or has no data rows.")

    mapping = detect_mapping(source_headers)
    if not mapping:
        raise HTTPException(
            status_code=422,
            detail="Could not detect any matching columns. Check that the CSV has recognisable headers."
        )

    converted, errors = [], []
    for i, row in enumerate(all_rows, start=2):
        result = convert_row(row, mapping)
        if result:
            converted.append(result)
        else:
            errors.append(f"Row {i}: no part_number detected — skipped")

    unmatched = [h for h in source_headers if h not in mapping]

    return {
        "mapping": mapping,            # {source_col: target_field}
        "unmatched_columns": unmatched,
        "preview": converted[:5],      # first 5 rows for review
        "total_rows": len(all_rows),
        "convertible": len(converted),
        "errors": errors[:10],
        # Full converted payload ready to pass to /bulk
        "converted": converted,
    }


@router.post("/chips/competitor/bulk", status_code=200)
def bulk_import(parts: List[ChipSpec]):
    """
    Import a list of ChipSpec objects (e.g. from the convert-preview response).
    Merges with existing catalog.
    """
    existing = list(get_competitor_parts())
    catalog = {p["part_number"].upper(): p for p in existing}
    added, updated = 0, 0
    imported_dicts = []
    for part in parts:
        key = part.part_number.upper()
        part_dict = part.model_dump()
        if key in catalog:
            updated += 1
        else:
            added += 1
        catalog[key] = part_dict
        imported_dicts.append(part_dict)

    _save_catalog(list(catalog.values()))
    return {
        "added": added,
        "updated": updated,
        "total_in_catalog": len(catalog),
        "imported": imported_dicts,
        "errors": [],
    }


@router.delete("/chips/competitor/{part_number}", status_code=204)
def delete_competitor_part(part_number: str):
    """Remove a competitor part."""
    parts = list(get_competitor_parts())
    new_parts = [p for p in parts if p["part_number"].upper() != part_number.upper()]
    if len(new_parts) == len(parts):
        raise HTTPException(status_code=404, detail=f"Part '{part_number}' not found")
    _save_catalog(new_parts)
