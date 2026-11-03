"""Checks the committed correction against the real local candidate catalog."""
import copy
import unittest
from app.data_loader import get_nuvoton_parts, reload_data
from app.requirements import evaluate_requirements
from test_catalog_corrections import RULES


class ActualM031CorrectionTests(unittest.TestCase):
    def setUp(self):
        reload_data()
        self.addCleanup(reload_data)
        matches = [part for part in get_nuvoton_parts() if part["part_number"] == "M031LC2AE"]
        self.assertEqual(len(matches), 1)
        self.part = matches[0]

    def test_real_record_passes_eight_checked_requirements(self):
        self.assertEqual(self.part["temp_min_c"], -40)
        self.assertEqual(evaluate_requirements(self.part, RULES)["eligibility"], "PASS")
        self.assertIn("nuvoton.com", self.part["field_sources"]["temp_min_c"]["url"])

    def test_real_record_missing_value_still_unknown(self):
        part = copy.deepcopy(self.part)
        del part["temp_min_c"]
        self.assertEqual(evaluate_requirements(part, RULES)["eligibility"], "UNKNOWN")
