"""
MCU cross-reference scoring.

Scoring approach (per reference design doc):
  - Numeric parameters: ratio score — nuvoton/competitor capped at 1.0,
    so meeting or exceeding scores full marks; falling short penalises linearly.
  - Boolean parameters (USB, CAN, Ethernet): 1.0 if met, 0.0 if not.
  - Core class: hierarchical rank comparison.
  - Package: exact match=1.0, same family=0.7, different family=0.0.

Total score = mean of per-parameter scores, converted to 0-100%.
"""

import re
from typing import List, Dict, Tuple, Optional

from .models import ChipSpec, MatchResult, ComparisonRow, Characteristic

# ── Core class rank table ──────────────────────────────────────────────────
# Hierarchy (low -> high), per sales guidance (2026-07):
#   8051/PIC < M0/AVR8/MSP430 < M0+ < M23/RISC-V/MIPS32 < M3 < M4/Xtensa LX7
#   < M33 < M55 < M7 < M55+U55 (NPU)
# Nuvoton has no M3 or M7 parts of its own - those ranks exist purely so
# competitor parts built on those cores compare fairly against Nuvoton's
# M0/M23/M4/M33/M55 catalog. M55+U55 (M55M1, up to 220MHz + NPU/Helium)
# outranks plain M7 (Nuvoton's M7 parts top out at 160MHz, no NPU).
CORE_RANK: Dict[str, int] = {
    "8051":        1,
    "PIC":         1,
    "Cortex-M0":   2,
    "AVR8":        2,
    "MSP430":      2,
    "Cortex-M0+":  3,
    "Cortex-M23":  4,
    "RISC-V":      4,
    "MIPS32":      4,
    "Cortex-M3":   5,
    "Cortex-M4":   6,
    "Cortex-M4F":  6,
    "Xtensa LX7":  6,
    "Cortex-M33":  7,
    "Cortex-M55":  8,
    "Cortex-M7":   9,
    "Cortex-M55+U55": 10,  # with NPU
    # "Arm Cortex-*" variants found in some competitor data entries
    "Arm Cortex-M0":  2,
    "Arm Cortex-M0+": 3,
    "Arm Cortex-M23": 4,
    "Arm Cortex-M3":  5,
    "Arm Cortex-M4":  6,
    "Arm Cortex-M4F": 6,
    "Arm Cortex-M33": 7,
    "Arm Cortex-M55": 8,
    "Arm Cortex-M7":  9,
}

# ── Available comparison characteristics ─────────────────────────────────
CHARACTERISTICS: List[Characteristic] = [
    Characteristic(key="core",          label="CPU Core Class",     unit="class", numeric=False),
    Characteristic(key="cpu_freq_mhz",  label="CPU Frequency",     unit="MHz"),
    Characteristic(key="ram_kb",        label="RAM",                unit="KB"),
    Characteristic(key="flash_kb",      label="Flash",              unit="KB"),
    Characteristic(key="gpio",          label="GPIO Count",         unit="pins"),
    Characteristic(key="adc_bits",      label="ADC Resolution",     unit="bits"),
    Characteristic(key="adc_channels",  label="ADC Channels",       unit="ch"),
    Characteristic(key="uart",          label="UART Count",         unit=""),
    Characteristic(key="spi",           label="SPI Count",          unit=""),
    Characteristic(key="i2c",           label="I2C Count",          unit=""),
    Characteristic(key="usb",           label="USB FS",             unit="", numeric=False),
    Characteristic(key="usb_hs",        label="USB High-Speed",     unit="", numeric=False),
    Characteristic(key="can",           label="CAN (classic)",      unit="", numeric=False),
    Characteristic(key="can_fd",        label="CAN FD",             unit="", numeric=False),
    Characteristic(key="ethernet",      label="Ethernet",           unit="", numeric=False),
    Characteristic(key="crypto",        label="Hardware Crypto",    unit="", numeric=False),
    Characteristic(key="temp_max_c",    label="Max Temp",           unit="°C"),
    Characteristic(key="vcc_min",       label="Min Supply Voltage", unit="V"),
    Characteristic(key="package",       label="Package Type",       unit="", numeric=False),
]

# ── Package family scoring ────────────────────────────────────────────────
_PKG_FAMILIES: Dict[str, str] = {}
for _f in ("LQFP", "TQFP", "QFP", "VQFP", "PQFP", "EQFP", "FQFP"):
    _PKG_FAMILIES[_f] = "QFP"
for _f in ("QFN", "MLF", "LGA", "WQFN", "HVQFN", "VQFN", "UQFN", "UDFN", "DRQFN"):
    _PKG_FAMILIES[_f] = "QFN"
for _f in ("BGA", "TFBGA", "LFBGA", "FPBGA", "FBGA", "WLCSP", "CSP"):
    _PKG_FAMILIES[_f] = "BGA"
for _f in ("SOP", "SOIC", "TSOP", "TSSOP", "SSOP", "MSOP", "QSOP"):
    _PKG_FAMILIES[_f] = "SOP"
for _f in ("DIP", "PDIP", "SPDIP"):
    _PKG_FAMILIES[_f] = "DIP"


def _pkg_family(pkg: str) -> str:
    base = re.sub(r"\d+", "", pkg.upper()).strip()
    return _PKG_FAMILIES.get(base, base)


# Approximate package body area (width x height, mm^2), used when a part's
# actual "Package Size" isn't available (competitor data never has physical
# dimensions; a handful of Nuvoton rows are missing it too). Nuvoton's own
# rows carry a real measured size from the master table and always take
# priority over this table - see _resolve_package_size().
PACKAGE_SIZE_FALLBACK: Dict[str, float] = {
    "LQFP32": 49, "LQFP44": 100, "LQFP48": 49, "LQFP64": 100,
    "LQFP100": 196, "LQFP128": 196, "LQFP144": 400, "LQFP176": 576,
    "LQFP216": 784, "TQFP64": 100, "PQFP44": 100,
    "QFN20": 9, "QFN24": 9, "QFN32": 25, "QFN33": 25, "QFN48": 25,
    "QFN56": 64, "QFN68": 64, "QFN88": 100,
    "UFQFPN32": 25, "UFQFPN48": 49,
    "DIP28": 270, "PDIP28": 270, "DIP40": 795, "PDIP40": 795, "PDIP20": 198,
    "SOIC8": 20, "MAPBGA196": 196,
    "MSOP10": 9, "SOP16": 39, "SOP20": 99, "SOP28": 137,
    "SSOP20": 38, "TSSOP14": 22, "TSSOP20": 29, "TSSOP28": 43,
}

# Rough per-family default (mm^2) when the exact package string isn't in
# PACKAGE_SIZE_FALLBACK either - last-resort so scoring never divides by zero.
_PKG_FAMILY_DEFAULT: Dict[str, float] = {
    "QFP": 100, "QFN": 36, "BGA": 169, "SOP": 50, "DIP": 300,
}


def _normalize_pkg_type(pkg: str) -> str:
    return re.sub(r"[\s-].*$", "", pkg.upper().strip())  # drop "-EP" etc. and trailing space


def _resolve_package_size(pkg_type: str, explicit_mm2: Optional[float]) -> float:
    """Actual measured size wins; else lookup by package type; else family default."""
    if explicit_mm2 and explicit_mm2 > 0:
        return explicit_mm2
    norm = _normalize_pkg_type(pkg_type)
    if norm in PACKAGE_SIZE_FALLBACK:
        return PACKAGE_SIZE_FALLBACK[norm]
    return _PKG_FAMILY_DEFAULT.get(_pkg_family(norm), 100.0)


def _package_score(comp_size: float, nuv_size: float) -> float:
    """Smaller-or-equal footprint than the competitor = full marks; larger is
    penalised proportionally (favors board-space savings, per sales guidance)."""
    if comp_size <= 0:
        return 1.0
    if nuv_size <= comp_size:
        return 1.0
    return min(1.0, comp_size / nuv_size)

CHAR_MAP: Dict[str, Characteristic] = {c.key: c for c in CHARACTERISTICS}

# ── Per-parameter scoring functions ──────────────────────────────────────

def _numeric_ratio_score(comp_val: float, nuv_val: float) -> float:
    """0-1 score. Meets/exceeds → 1.0; below → linear penalty."""
    if comp_val <= 0:
        return 1.0
    ratio = nuv_val / comp_val
    return min(1.0, ratio)


def _bool_score(comp_val: int, nuv_val: int) -> float:
    """0-1 score for boolean features."""
    if comp_val == 0:
        return 1.0  # competitor doesn't have it — no requirement
    return 1.0 if nuv_val > 0 else 0.0


def _core_score(comp_core: str, nuv_core: str) -> float:
    """0-1 score based on core hierarchy rank."""
    comp_rank = CORE_RANK.get(comp_core, 3)
    nuv_rank = CORE_RANK.get(nuv_core, 3)
    if nuv_rank >= comp_rank:
        return 1.0
    return nuv_rank / comp_rank


def _score_field(key: str, comp_val: float, nuv_val: float, char: Characteristic) -> float:
    if key == "core":
        return _core_score(str(int(comp_val)), str(int(nuv_val)))
    if not char.numeric:
        return _bool_score(int(comp_val), int(nuv_val))
    # For vcc_min: smaller is better (lower min voltage = wider range)
    if key == "vcc_min":
        if comp_val <= 0:
            return 1.0
        ratio = comp_val / nuv_val if nuv_val > 0 else 0.0
        return min(1.0, ratio)
    return _numeric_ratio_score(comp_val, nuv_val)


# Memory is never penalised for being larger than required - the cost of the
# extra flash/RAM is its own natural check, so a bigger part shouldn't also
# lose match score for it (per sales guidance, 2026-07).
NO_OVERSIZE_PENALTY_KEYS = {"ram_kb", "flash_kb"}


def _proximity(key: str, comp_val: float, nuv_val: float) -> float:
    """Secondary closeness score [0,1]. Exact match = 1.0; excess penalised
    (except for memory - see NO_OVERSIZE_PENALTY_KEYS)."""
    if comp_val <= 0:
        return 1.0
    ratio = nuv_val / comp_val
    # Deficit: already penalised by primary score, don't double-penalise
    if ratio <= 1.0:
        return ratio
    if key in NO_OVERSIZE_PENALTY_KEYS:
        return 1.0
    # Excess: soft penalty — cap at ratio=2.0
    excess = min(ratio, 2.0) - 1.0  # 0..1
    return 1.0 - excess * 0.4       # partial penalty so proximity stays high


def _per_field_pct(key: str, comp_val: float, nuv_val: float, char: Characteristic) -> Tuple[float, float]:
    """Returns (similarity_pct, ratio) for display."""
    if not char.numeric:
        s = _bool_score(int(comp_val), int(nuv_val))
        return s * 100, float(nuv_val)
    if comp_val <= 0:
        return 100.0, 1.0
    ratio = nuv_val / comp_val if key != "vcc_min" else (comp_val / nuv_val if nuv_val > 0 else 0)
    return min(100.0, ratio * 100), round(ratio, 2)


# ── Always-on weighted factors ────────────────────────────────────────────
# These 5 always factor into every match, even if the customer didn't select
# them, and count double vs. whatever else the customer picked (per sales
# guidance, 2026-07): frequency, GPIO, package (size), flash, RAM are what
# reps say actually drive a real substitution decision.
CORE_WEIGHTED_KEYS = ["cpu_freq_mhz", "gpio", "package", "flash_kb", "ram_kb"]
CORE_WEIGHT = 2.0
OTHER_WEIGHT = 1.0


def _effective_keys(selected_keys: List[str]) -> List[str]:
    extras = [k for k in selected_keys if k not in CORE_WEIGHTED_KEYS]
    return CORE_WEIGHTED_KEYS + extras


# ── Main matching function ────────────────────────────────────────────────

def find_matches(
    competitor: Dict,
    nuvoton_catalog: List[Dict],
    selected_keys: List[str],
    top_k: int = 5,
) -> List[MatchResult]:
    if not selected_keys:
        selected_keys = ["cpu_freq_mhz", "ram_kb", "flash_kb"]

    effective_keys = _effective_keys(selected_keys)
    results: List[MatchResult] = []

    for nuv in nuvoton_catalog:
        weighted_score_sum = 0.0
        weighted_proximity_sum = 0.0
        weight_total = 0.0
        rows: List[ComparisonRow] = []
        meets_all = True

        for key in effective_keys:
            weight = CORE_WEIGHT if key in CORE_WEIGHTED_KEYS else OTHER_WEIGHT
            weight_total += weight
            char = CHAR_MAP.get(key, Characteristic(key=key, label=key, unit=""))

            # "package" is a string field — score via package footprint (mm^2)
            if key == "package":
                comp_pkg = str(competitor.get("package", ""))
                nuv_pkg  = str(nuv.get("package", ""))
                comp_size = _resolve_package_size(comp_pkg, competitor.get("package_size_mm2"))
                nuv_size  = _resolve_package_size(nuv_pkg, nuv.get("package_size_mm2"))
                field_score = _package_score(comp_size, nuv_size)
                nuv_better  = nuv_size <= comp_size
                weighted_proximity_sum += weight * (1.0 if nuv_better else field_score)
                weighted_score_sum  += weight * field_score
                if not nuv_better and comp_pkg:
                    meets_all = False
                rows.append(ComparisonRow(
                    key=key, label=char.label, unit="",
                    competitor_value=comp_size, nuvoton_value=nuv_size,
                    competitor_display=comp_pkg or "—",
                    nuvoton_display=nuv_pkg or "—",
                    similarity_pct=round(field_score * 100, 1),
                    nuvoton_better=nuv_better,
                    ratio=round(nuv_size / comp_size, 2) if comp_size else 1.0,
                ))
                continue

            # "core" is a string field — score via rank table, store ranks as numeric values
            if key == "core":
                comp_str = str(competitor.get("core", ""))
                nuv_str = str(nuv.get("core", ""))
                field_score = _core_score(comp_str, nuv_str)
                comp_rank = float(CORE_RANK.get(comp_str, 3))
                nuv_rank = float(CORE_RANK.get(nuv_str, 3))
                nuv_better = nuv_rank >= comp_rank
                weighted_proximity_sum += weight * (1.0 if nuv_better else field_score)
                weighted_score_sum += weight * field_score
                if field_score < 1.0:
                    meets_all = False
                rows.append(ComparisonRow(
                    key=key, label=char.label, unit="class",
                    competitor_value=comp_rank, nuvoton_value=nuv_rank,
                    similarity_pct=round(field_score * 100, 1),
                    nuvoton_better=nuv_better,
                    ratio=round(nuv_rank / comp_rank if comp_rank else 1.0, 2),
                ))
                continue

            comp_val = float(competitor.get(key, 0))
            nuv_val = float(nuv.get(key, 0))

            field_score = _score_field(key, comp_val, nuv_val, char)
            weighted_score_sum += weight * field_score
            weighted_proximity_sum += weight * _proximity(key, comp_val, nuv_val)

            sim_pct, ratio = _per_field_pct(key, comp_val, nuv_val, char)
            nuv_better = nuv_val >= comp_val if key != "vcc_min" else nuv_val <= comp_val

            if field_score < 1.0:
                meets_all = False

            rows.append(ComparisonRow(
                key=key,
                label=char.label,
                unit=char.unit,
                competitor_value=comp_val,
                nuvoton_value=nuv_val,
                similarity_pct=round(sim_pct, 1),
                nuvoton_better=nuv_better,
                ratio=ratio,
            ))

        mean_score = weighted_score_sum / weight_total if weight_total else 0.0
        mean_proximity = weighted_proximity_sum / weight_total if weight_total else 0.0
        # Combined: primary is ratio score, secondary is proximity (no overkill)
        combined = mean_score * 0.9 + mean_proximity * 0.1
        score_pct = round(combined * 100, 1)

        results.append(MatchResult(
            nuvoton_part=ChipSpec(**nuv),
            score=round(combined, 4),
            similarity_pct=score_pct,
            comparison=rows,
            meets_all=meets_all,
        ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]
