export interface ChipSpec {
  part_number: string;
  manufacturer: string;
  family: string;
  core: string;
  cpu_freq_mhz: number;
  ram_kb: number;
  flash_kb: number;
  gpio: number;
  adc_bits: number;
  adc_channels: number;
  uart: number;
  spi: number;
  i2c: number;
  usb: number;
  usb_hs: number;
  can: number;
  can_fd?: number;
  ethernet: number;
  crypto?: number;
  temp_max_c: number;
  vcc_min: number;
  vcc_max: number;
  package: string;
  package_size_mm2?: number | null;
  price_1k_usd?: number | null;
  status?: string;
  notes?: string;
}

export interface Characteristic {
  key: string;
  label: string;
  unit: string;
  numeric?: boolean;
}

export interface ComparisonRow {
  key: string;
  label: string;
  unit: string;
  competitor_value: number;
  nuvoton_value: number;
  competitor_display?: string;   // human-readable for non-numeric fields (package, etc.)
  nuvoton_display?: string;
  similarity_pct: number;
  nuvoton_better: boolean;
  ratio: number;
}

export interface MatchResult {
  nuvoton_part: ChipSpec;
  score: number;
  similarity_pct: number;
  comparison: ComparisonRow[];
  meets_all: boolean;
}

export interface MatchResponse {
  competitor_part: ChipSpec;
  matches: MatchResult[];
  characteristics_used: string[];
}
