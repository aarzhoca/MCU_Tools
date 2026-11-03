"""Synthetic ST XLSX regression tests; no master catalog writes."""
import io
import unittest
from openpyxl import Workbook
from app.st_xlsx import parse_st_xlsx

HEADERS = ["Part Number", "Core", "Operating Frequency (MHz)", "Flash Size (kB) (Prog)",
    "RAM Size (kB)", "Operating Temperature (°C) min", "Operating Temperature (°C) max",
    "Supply Voltage (V) min", "Supply Voltage (V) max", "Package", "FPU", "UART Total"]


def workbook_bytes(rows, headers=HEADERS):
    workbook = Workbook()
    ws = workbook.active
    ws.title = "ProductsList"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def example(**overrides):
    data = dict(zip(HEADERS, ["TEST", "Arm Cortex-M0", "48", "32", "8", "-40", "85",
        "2", "3.6", "LQFP 48 7x7x1.4 mm", "-", "2"]))
    data.update(overrides)
    return [data[h] for h in HEADERS]


class STXLSXTests(unittest.TestCase):
    def parse_one(self, **overrides):
        return parse_st_xlsx(workbook_bytes([example(**overrides)]))["records"][0]

    def test_signed_temperature_and_package(self):
        record = self.parse_one()
        self.assertEqual(record["temp_min_c"], -40)
        self.assertEqual(record["temp_max_c"], 85)
        self.assertEqual(record["vcc_min"], 2)
        self.assertEqual(record["package"], "LQFP48")
        self.assertEqual(record["package_width_mm"], 7)
        self.assertEqual(record["package_size_mm2"], 49)

    def test_missing_numeric_is_unknown_not_default(self):
        record = self.parse_one(**{"Supply Voltage (V) min": "-", "RAM Size (kB)": "N/A"})
        self.assertIsNone(record["vcc_min"])
        self.assertIsNone(record["ram_kb"])
        self.assertEqual(record["field_quality"]["ram_kb"], "unknown")

    def test_fpu_normalization(self):
        record = self.parse_one(**{"Core": "Arm Cortex-M4", "FPU": "Single-precision FPU"})
        self.assertEqual(record["core"], "Cortex-M4F")
        self.assertEqual(self.parse_one(**{"Core": "Arm Cortex-M4"})["core"], "Cortex-M4")

    def test_provenance_and_raw_values(self):
        record = self.parse_one()
        self.assertEqual(record["source"]["row"], 2)
        self.assertEqual(len(record["source"]["sha256"]), 64)
        self.assertEqual(record["source_values"]["Operating Temperature (°C) min"], "-40")

    def test_blank_rows_and_duplicates(self):
        result = parse_st_xlsx(workbook_bytes([[], example(), example()]))
        self.assertEqual(result["parsed_count"], 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["records"][0]["source"]["row"], 3)

    def test_formula_row_skipped(self):
        result = parse_st_xlsx(workbook_bytes([example(**{"Operating Frequency (MHz)": "=24*2"})]))
        self.assertEqual(result["parsed_count"], 0)
        self.assertEqual(len(result["errors"]), 1)

    def test_unsupported_packages_and_features_unknown(self):
        record = self.parse_one(**{"Package": "Unrecognised package"})
        self.assertIsNone(record["package"])
        self.assertIsNone(record["usb"])
        self.assertIsNone(record["adc_bits"])

    def test_invalid_numeric_and_reversed_ranges(self):
        record = self.parse_one(**{"Operating Frequency (MHz)": "bad",
            "Supply Voltage (V) min": "5", "Supply Voltage (V) max": "3.6"})
        self.assertIsNone(record["cpu_freq_mhz"])
        self.assertIsNone(record["vcc_min"])
        self.assertIsNone(record["vcc_max"])

    def test_wrong_headers_sheet_and_extension(self):
        for content, options in [(workbook_bytes([], ["Wrong"]), {}),
            (workbook_bytes([]), {"sheet":"Missing"}),
            (workbook_bytes([]), {"filename":"data.xls"})]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                parse_st_xlsx(content, **options)

    def test_duplicate_headers_rejected(self):
        with self.assertRaises(ValueError):
            parse_st_xlsx(workbook_bytes([], HEADERS + ["Part Number"]))
