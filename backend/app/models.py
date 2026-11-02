from pydantic import BaseModel
from typing import Optional, List, Union


class ChipSpec(BaseModel):
    part_number: str
    manufacturer: str
    family: str
    core: str
    cpu_freq_mhz: float
    ram_kb: float
    flash_kb: float
    gpio: int
    adc_bits: int
    adc_channels: int
    uart: int
    spi: int
    i2c: int
    usb: int        # USB FS
    usb_hs: int = 0 # USB High-Speed (separate from FS)
    can: int
    can_fd: int = 0 # CAN FD instances (M3xxx/M46x/M2354 use CAN FD, not classic CAN)
    ethernet: int = 0
    crypto: int = 0 # hardware crypto engine (AES/SHA/ECC)
    temp_max_c: float
    vcc_min: float
    vcc_max: float
    package: str
    package_size_mm2: Optional[float] = None  # body area (width x height), None = unknown
    price_1k_usd: Optional[float] = None  # Est. 1k unit price (USD), None = N/A
    status: str = "MP"  # MP, Preview, or a quarter tag (e.g. "1Q25") for upcoming parts
    notes: Optional[str] = None


class Characteristic(BaseModel):
    key: str
    label: str
    unit: str
    numeric: bool = True


class ComparisonRow(BaseModel):
    key: str
    label: str
    unit: str
    competitor_value: Union[float, int]
    nuvoton_value: Union[float, int]
    competitor_display: Optional[str] = None   # human-readable for non-numeric fields
    nuvoton_display: Optional[str] = None
    similarity_pct: float
    nuvoton_better: bool       # True = meets or exceeds competitor
    ratio: float               # nuvoton / competitor (capped display at 2.0)


class MatchResult(BaseModel):
    nuvoton_part: ChipSpec
    score: float
    similarity_pct: float
    comparison: List[ComparisonRow]
    meets_all: bool            # True if Nuvoton meets every selected parameter


class MatchRequest(BaseModel):
    part_number: str
    characteristics: List[str]
    top_k: int = 5


class MatchResponse(BaseModel):
    competitor_part: ChipSpec
    matches: List[MatchResult]
    characteristics_used: List[str]
