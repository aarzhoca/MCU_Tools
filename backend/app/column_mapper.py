"""
Auto-detect column mappings from arbitrary competitor CSV files.

Supports major MCU vendors: ST, NXP, Microchip, Renesas, Espressif, TI, Infineon.
Falls back to fuzzy character-similarity for unrecognised headers.
"""

import re
from typing import Dict, List, Tuple, Optional

# ── Alias dictionary ──────────────────────────────────────────────────────
# Maps each target template field → list of known source column name variants
ALIASES: Dict[str, List[str]] = {
    "part_number": [
        "part number", "part no", "part no.", "part", "pn", "device",
        "product", "orderable part number", "mcu part number", "part_number",
        "part num", "article", "mpn",
    ],
    "manufacturer": [
        "manufacturer", "vendor", "brand", "company", "mfr", "supplier",
    ],
    "family": [
        "family", "product family", "series", "product series", "line",
        "lines", "product line", "subfamily", "device family",
    ],
    "core": [
        "core", "cpu", "cpu core", "processor", "cpu type", "core type",
        "arm core", "mcu core", "processor core", "cpu architecture",
        "instruction set",
    ],
    "cpu_freq_mhz": [
        "operating frequency (mhz)", "max freq", "cpu freq", "frequency",
        "cpu frequency", "max frequency", "max cpu frequency (mhz)",
        "max operating frequency", "core frequency", "clock frequency",
        "cpu speed", "operating frequency max (mhz)", "freq (mhz)",
        "max frequency (mhz)", "maximum core frequency (mhz)",
        "cpu freq max (mhz)", "max cpu speed (mhz)", "system clock (mhz)",
        "clk max", "speed (mhz)", "cpu speed (mhz)", "frequency max",
    ],
    "flash_kb": [
        "flash size (kb) (prog)", "flash (kb)", "flash", "rom", "rom (kb)",
        "flash size", "aprom (kb)", "program memory", "code flash",
        "flash memory (kb)", "flash (kbytes)", "program flash (kb)",
        "on-chip flash (kb)", "flash kb", "flash size (kbytes)",
        "flash (kbyte)", "code memory (kb)", "program flash size (kb)",
        "internal flash (kb)",
    ],
    "ram_kb": [
        "ram size (kb)", "ram (kb)", "ram", "sram", "sram (kb)",
        "sram size (kb)", "data memory", "data sram (kb)", "ram size",
        "on-chip ram (kb)", "ram (kbytes)", "sram (kbyte)",
        "data memory (kb)", "internal sram (kb)", "working ram (kb)",
    ],
    "gpio": [
        "i/o", "gpio", "i/o count", "gpio count", "number of ios",
        "i/os (high current)", "general purpose io", "total gpio",
        "number of gpio", "i/o pins", "gpio pins", "total i/o",
        "number of i/o", "io pins",
    ],
    "adc_bits": [
        "adc resolution", "adc (bits)", "adc resolution (bits)",
        "a/d converters 12-bit", "a/d converters 16-bit",
        "adc bit", "adc resolution bits", "adc bits",
    ],
    "adc_channels": [
        "adc (ch)", "adc channels", "number of a/d converters typ",
        "number of channels typ", "adc channel count", "adc inputs",
        "number of adc channels", "adc ch", "total adc channels",
        "adc channel", "a/d channels",
    ],
    "uart": [
        "uart", "uart total", "usart typ", "uart typ", "number of uarts",
        "uart count", "uart/usart", "sci", "uart channels",
    ],
    "spi": [
        "spi", "spi typ", "spi total", "number of spis", "spi count",
        "spi channels", "spi interfaces",
    ],
    "i2c": [
        "i2c", "i2c typ", "i2c total", "number of i2cs", "i2c count",
        "i2c channels", "iic",
    ],
    "usb": [
        "usb", "usb total", "usb fs", "usb (fs)", "usb device",
        "usb full speed", "has usb", "usb type", "usb interface",
        "usb 2.0",
    ],
    "usb_hs": [
        "usb hs", "usb high speed", "usb hs total", "usb high-speed",
        "usb (hs)", "usb2.0 hs",
    ],
    "can": [
        "can", "can total", "can bus", "number of can",
        "can interfaces", "can channels", "can (classic)",
    ],
    "can_fd": [
        "can fd", "can-fd", "canfd", "can (fd)", "can fd total",
        "number of can fd", "can fd interfaces", "fdcan",
    ],
    "crypto": [
        "crypto", "hardware crypto", "hw crypto", "security",
        "cryptographic engine", "crypto engine", "aes", "encryption",
        "hardware security", "pka", "tdes",
    ],
    "ethernet": [
        "ethernet", "eth", "mac", "ethernet ports typ", "10/100 ethernet",
        "has ethernet", "ethernet interface", "enet",
    ],
    "temp_max_c": [
        "operating temperature (°c) max", "temp max", "max temp",
        "max operating temp", "operating temp max", "temperature max",
        "max temperature (c)", "operating temperature max",
        "ambient temp max (c)", "ta max",
    ],
    "vcc_min": [
        "supply voltage (v) min", "vcc min", "vdd min", "supply voltage min",
        "operating voltage min", "min supply voltage", "vcc (min)",
        "vdd min (v)", "power supply min (v)",
    ],
    "vcc_max": [
        "supply voltage (v) max", "vcc max", "vdd max", "supply voltage max",
        "operating voltage max", "max supply voltage", "vcc (max)",
        "vdd max (v)", "power supply max (v)",
    ],
    "package": [
        "package", "pkg", "package type", "package name",
        "package description", "case", "outline",
    ],
    "notes": [
        "notes", "features", "description", "general description",
        "special features", "remarks", "comments", "highlights",
    ],
}

def _normalise(s: str) -> str:
    """Lowercase, strip punctuation/whitespace for comparison."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


# Build reverse lookup: normalised alias → field name
_REVERSE: Dict[str, str] = {}
for _field, _aliases in ALIASES.items():
    for _a in _aliases:
        _REVERSE[_normalise(_a)] = _field


def _char_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    shared = sum(min(a.count(c), b.count(c)) for c in set(a))
    return shared / max(len(a), len(b))


def detect_mapping(headers: List[str]) -> Dict[str, str]:
    """
    Given a list of CSV column headers, return a dict mapping
    source_column → template_field for every column that could be matched.
    """
    mapping: Dict[str, str] = {}
    already_mapped: set = set()  # prevent two source cols → same target

    for h in headers:
        norm = _normalise(h)
        if not norm:
            continue

        # 1. Exact alias match
        if norm in _REVERSE:
            field = _REVERSE[norm]
            if field not in already_mapped:
                mapping[h] = field
                already_mapped.add(field)
            continue

        # 2. Substring: alias contained in header or vice versa
        matched = None
        for alias_norm, field in _REVERSE.items():
            if field in already_mapped:
                continue
            if alias_norm in norm or norm in alias_norm:
                matched = field
                break
        if matched:
            mapping[h] = matched
            already_mapped.add(matched)
            continue

        # 3. Fuzzy fallback (character similarity)
        best_field, best_score = None, 0.0
        for alias_norm, field in _REVERSE.items():
            if field in already_mapped:
                continue
            score = _char_sim(norm, alias_norm)
            if score > best_score:
                best_score, best_field = score, field
        if best_score >= 0.72 and best_field:
            mapping[h] = best_field
            already_mapped.add(best_field)

    return mapping


TEMPLATE_FIELDS = [
    "part_number", "manufacturer", "family", "core",
    "cpu_freq_mhz", "ram_kb", "flash_kb", "gpio",
    "adc_bits", "adc_channels", "uart", "spi", "i2c",
    "usb", "usb_hs", "can", "can_fd", "ethernet", "crypto",
    "temp_max_c", "vcc_min", "vcc_max", "package", "notes",
]

INT_FIELDS   = {"gpio", "adc_bits", "adc_channels", "uart", "spi", "i2c",
                "usb", "usb_hs", "can", "can_fd", "ethernet", "crypto"}
FLOAT_FIELDS = {"cpu_freq_mhz", "ram_kb", "flash_kb", "temp_max_c",
                "vcc_min", "vcc_max"}
BOOL_FIELDS  = {"usb", "usb_hs", "can", "can_fd", "ethernet", "crypto"}

DEFAULTS: Dict[str, object] = {
    "manufacturer": "", "family": "", "core": "", "package": "", "notes": "",
    "gpio": 0, "adc_bits": 12, "adc_channels": 0,
    "uart": 0, "spi": 0, "i2c": 0,
    "usb": 0, "usb_hs": 0, "can": 0, "can_fd": 0, "ethernet": 0, "crypto": 0,
    "cpu_freq_mhz": 0.0, "ram_kb": 0.0, "flash_kb": 0.0,
    "temp_max_c": 85.0, "vcc_min": 1.8, "vcc_max": 3.6,
}


def _parse_bool(val: str) -> int:
    return 0 if str(val).strip().lower() in ("", "0", "no", "false", "n", "-", "none") else 1


def _parse_numeric(val: str) -> float:
    """Extract first number found in a string like '1 MByte' or '64 KB'."""
    val = str(val).strip()
    # Handle KB/MB unit conversions
    m = re.search(r"([\d]+(?:\.\d+)?)\s*(mb|mbyte|mbytes)", val, re.I)
    if m:
        return float(m.group(1)) * 1024
    m = re.search(r"([\d]+(?:\.\d+)?)", val)
    if m:
        return float(m.group(1))
    return 0.0


def convert_row(row: dict, mapping: Dict[str, str]) -> Optional[dict]:
    """Convert a single CSV row using the detected mapping. Returns None if no part_number."""
    out: dict = dict(DEFAULTS)

    for src_col, target_field in mapping.items():
        raw = str(row.get(src_col, "")).strip()
        if not raw or raw in ("-", "N/A", "n/a", ""):
            continue

        if target_field in BOOL_FIELDS:
            out[target_field] = _parse_bool(raw)
        elif target_field in FLOAT_FIELDS:
            out[target_field] = _parse_numeric(raw)
        elif target_field in INT_FIELDS:
            out[target_field] = int(_parse_numeric(raw))
        else:
            out[target_field] = raw

    pn = str(out.get("part_number", "")).strip()
    return out if pn else None
