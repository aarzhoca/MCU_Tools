"""Preview response tests with a mocked parser; no HTTP dependencies."""
import unittest
from unittest.mock import patch
from app.st_preview import build_st_preview


def record(name):
    return {"part_number": name, "temp_min_c": -40, "ram_kb": None,
            "source_values": {"raw": "not returned"},
            "field_quality": {"ram_kb": "unknown"},
            "source": {"file": "test.xlsx", "sheet": "ProductsList", "row": 2}}


def parsed(records):
    return {"records": records, "parsed_count": len(records), "errors": [],
            "warnings": ["Preview only"], "sheet": "ProductsList"}


class PreviewTests(unittest.TestCase):
    def run_preview(self, data, query=""):
        with patch("app.st_preview.parse_st_xlsx", return_value=data):
            return build_st_preview(b"workbook", "test.xlsx", part_number=query)

    def test_limit_first_twenty(self):
        result = self.run_preview(parsed([record(str(i)) for i in range(25)]))
        self.assertEqual(result["parsed_count"], 25)
        self.assertEqual(result["matched_count"], 25)
        self.assertEqual(len(result["records"]), 20)

    def test_exact_search_case_and_spaces(self):
        result = self.run_preview(parsed([record("STM32F051C6T6"), record("STM32F051C6T7")]),
                                  " stm32f051c6t6 ")
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["records"][0]["part_number"], "STM32F051C6T6")

    def test_no_fuzzy_fallback(self):
        result = self.run_preview(parsed([record("STM32F051C6T7")]), "STM32F051C6T6")
        self.assertEqual(result["matched_count"], 0)
        self.assertEqual(result["records"], [])

    def test_raw_values_omitted_without_mutating_input(self):
        item = record("A")
        result = self.run_preview(parsed([item]))
        self.assertNotIn("source_values", result["records"][0])
        self.assertIn("source_values", item)
        self.assertIsNone(result["records"][0]["ram_kb"])
        self.assertEqual(result["records"][0]["temp_min_c"], -40)

    def test_error_count_not_truncated(self):
        data = parsed([])
        data["errors"] = [{"row": i, "part": "A", "error": "bad"} for i in range(25)]
        result = self.run_preview(data)
        self.assertEqual(result["error_count"], 25)
        self.assertEqual(len(result["errors"]), 20)
        self.assertTrue(result["preview_only"])

    def test_mapping_and_parser_arguments(self):
        with patch("app.st_preview.parse_st_xlsx", return_value=parsed([])) as parser:
            result = build_st_preview(b"data", "input.xlsx", "Sheet2", "A")
        parser.assert_called_once_with(b"data", "input.xlsx", "Sheet2")
        self.assertEqual(result["mapping"]["core"], "Core + FPU")

    def test_parser_error_propagates_for_route_handling(self):
        with patch("app.st_preview.parse_st_xlsx", side_effect=ValueError("bad")):
            with self.assertRaises(ValueError):
                build_st_preview(b"data", "bad.xlsx")
