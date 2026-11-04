"""Synthetic snapshot and actual XLSX readback tests; no live MCU claims."""
import copy
from datetime import datetime, timedelta, timezone
import io
import json
import unittest
from unittest.mock import patch
from openpyxl import load_workbook
from app.comparison_export import create_snapshot, export_xlsx, validate_selection

def sample_data():
    source = {"part_number":"STM32F051C6T6", "cpu_freq_mhz":48.0, "temp_min_c":-40,
              "source":{"file":"sample.xlsx", "sheet":"ProductsList", "row":2, "sha256":"fixture"}}
    catalog = [{"part_number":"M031LC2AE", "cpu_freq_mhz":48.0, "temp_min_c":-40,
        "field_quality":{"temp_min_c":"verified"},
        "field_sources":{"temp_min_c":{"url":"https://www.nuvoton.com/", "quote":"Synthetic test evidence"}}},
        {"part_number":"OTHER", "cpu_freq_mhz":48, "temp_min_c":None}]
    check = {"field":"temp_min_c", "operator":"lte", "required_value":-40,
             "actual_value":-40, "status":"PASS", "reason":"test", "evidence":"verified"}
    result = {"source":source, "requirements_used":[{"field":"temp_min_c","operator":"lte","value":-40}],
        "matches":[{"part_number":"M031LC2AE", "eligibility":"PASS", "similarity_pct":99.9,
                    "requirement_checks":[check]}],
        "unknown_candidates":[{"part_number":"OTHER", "eligibility":"UNKNOWN",
            "requirement_checks":[{**check, "actual_value":None,"status":"UNKNOWN"}]}],
        "ranking_mode":"existing-matcher-with-explicit-base-data"}
    return result, catalog


class ComparisonExportTests(unittest.TestCase):
    def setUp(self):
        self.result, self.catalog = sample_data()
        self.payload, self.token = create_snapshot(self.result, self.catalog)

    def workbook(self, selected=None):
        book = load_workbook(io.BytesIO(export_xlsx(self.payload, self.token,
            ["M031LC2AE"] if selected is None else selected)))
        self.addCleanup(book.close)
        return book

    def test_snapshot_freezes_source_and_catalog(self):
        self.result["source"]["cpu_freq_mhz"] = 999
        self.catalog[0]["temp_min_c"] = 0
        snapshot = validate_selection(self.payload, self.token, ["M031LC2AE"])
        self.assertEqual(snapshot["source"]["cpu_freq_mhz"], 48)
        self.assertEqual(snapshot["candidates"][0]["values"]["temp_min_c"], -40)

    def test_unknown_status_and_value_preserved(self):
        snapshot = json.loads(self.payload)
        row = next(row for row in snapshot["rows"] if row["field"] == "temp_min_c")
        self.assertIsNone(row["candidates"][1]["value"])
        self.assertEqual(row["candidates"][1]["status"], "UNKNOWN")

    def test_not_checked_not_promoted_to_pass(self):
        row = next(row for row in json.loads(self.payload)["rows"] if row["field"] == "cpu_freq_mhz")
        self.assertEqual(row["candidates"][0]["status"], "NOT_CHECKED")

    def test_tampering_rejected(self):
        changed = json.loads(self.payload)
        changed["candidates"][0]["eligibility"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            export_xlsx(json.dumps(changed), self.token, ["M031LC2AE"])

    def test_wrong_process_token_rejected(self):
        with self.assertRaises(ValueError):
            export_xlsx(self.payload, "0"*64, ["M031LC2AE"])

    def test_invalid_selection_rejected(self):
        for names in [[], ["NO_SUCH_PART"], ["OTHER", "OTHER"], ["A", "B", "C", "D"]]:
            with self.subTest(names=names), self.assertRaises(ValueError):
                export_xlsx(self.payload, self.token, names)

    def test_expiration(self):
        with patch("app.comparison_export.datetime") as clock:
            clock.fromisoformat.side_effect = datetime.fromisoformat
            clock.now.return_value = datetime.now(timezone.utc) + timedelta(hours=9)
            with self.assertRaises(ValueError):
                export_xlsx(self.payload, self.token, ["M031LC2AE"])

    def test_sheets_headers_and_numeric_temperature(self):
        book = self.workbook(["M031LC2AE", "OTHER"])
        self.assertEqual(book.sheetnames, ["Summary", "Comparison", "Sources"])
        rows = list(book["Comparison"].values)
        self.assertEqual(rows[0][0], "Parameter")
        row = next(row for row in rows if row[0] == "Minimum operating temperature")
        self.assertEqual(row[3], -40)
        self.assertEqual(row[5:8], (-40, "PASS", "verified"))
        self.assertEqual(row[8:11], ("Unknown", "UNKNOWN", "unknown"))

    def test_source_evidence_exported(self):
        cells = [cell.value for row in self.workbook()["Sources"] for cell in row]
        self.assertTrue(any("Synthetic test evidence" in str(value) for value in cells))

    def test_formula_like_text_remains_literal(self):
        self.result["source"]["part_number"] = '=HYPERLINK("https://example.invalid","test")'
        payload, token = create_snapshot(self.result, self.catalog)
        book = load_workbook(io.BytesIO(export_xlsx(payload, token, ["M031LC2AE"])))
        self.addCleanup(book.close)
        strings = [cell for sheet in book for row in sheet for cell in row
                   if isinstance(cell.value, str) and cell.value.startswith("=")]
        self.assertTrue(strings)
        self.assertTrue(all(cell.data_type == "s" for cell in strings))
        self.assertFalse(any(cell.data_type == "f" for sheet in book for row in sheet for cell in row))

    def test_selection_limits_export_columns(self):
        rows = list(self.workbook()["Comparison"].values)
        self.assertEqual(len(rows[0]), 8)
        self.assertNotIn("OTHER value", rows[0])

    def test_snapshot_input_unchanged(self):
        before_result, before_catalog = copy.deepcopy(self.result), copy.deepcopy(self.catalog)
        create_snapshot(self.result, self.catalog)
        self.assertEqual(self.result, before_result)
        self.assertEqual(self.catalog, before_catalog)

    def test_no_browser_numeric_reserialization_needed(self):
        self.assertIn("48.0", self.payload)
        snapshot = validate_selection(self.payload, self.token, ["M031LC2AE"])
        self.assertEqual(snapshot["source"]["cpu_freq_mhz"], 48)

    def test_three_candidates_supported(self):
        third = copy.deepcopy(self.catalog[0]); third["part_number"] = "THIRD"
        self.catalog.append(third)
        third_match = copy.deepcopy(self.result["matches"][0]); third_match["part_number"] = "THIRD"
        self.result["matches"].append(third_match)
        payload, token = create_snapshot(self.result, self.catalog)
        book = load_workbook(io.BytesIO(export_xlsx(payload, token, ["M031LC2AE", "OTHER", "THIRD"])))
        self.addCleanup(book.close)
        self.assertEqual(book["Comparison"].max_column, 14)
