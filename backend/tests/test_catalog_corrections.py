"""Targeted correction tests with synthetic records and temporary catalog files."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.catalog_corrections import apply_catalog_corrections
from app.data_loader import get_nuvoton_parts, reload_data
from app.requirements import evaluate_requirements

CORRECTION = {"part_number":"M031LC2AE", "field":"temp_min_c", "value":-40,
    "source":{"url":"https://www.nuvoton.com/products/microcontrollers/arm-cortex-m0-mcus/m031-series/m031lc2ae/",
              "quote":"Temperature range: - 40°C to +105°C"}}
RULES = [{"field":field,"operator":op,"value":value} for field,op,value in [
    ("cpu_freq_mhz","gte",48), ("flash_kb","gte",32), ("ram_kb","gte",8),
    ("package","eq","LQFP48"), ("vcc_min","lte",1.8), ("vcc_max","gte",3.6),
    ("temp_min_c","lte",-40), ("temp_max_c","gte",105)]]


def sample():
    return dict(part_number="M031LC2AE", cpu_freq_mhz=48, flash_kb=32, ram_kb=8,
                package="LQFP48", vcc_min=1.8, vcc_max=3.6, temp_max_c=105)


class CorrectionTests(unittest.TestCase):
    def test_missing_temperature_corrected_with_source(self):
        result = apply_catalog_corrections([sample()], [CORRECTION])[0]
        self.assertEqual(result["temp_min_c"], -40)
        self.assertEqual(result["field_quality"]["temp_min_c"], "verified")
        self.assertEqual(result["field_sources"]["temp_min_c"]["url"], CORRECTION["source"]["url"])

    def test_eight_requirements_pass(self):
        result = apply_catalog_corrections([sample()], [CORRECTION])[0]
        self.assertEqual(evaluate_requirements(result, RULES)["eligibility"], "PASS")

    def test_removing_temperature_restores_unknown(self):
        result = apply_catalog_corrections([sample()], [CORRECTION])[0]
        del result["temp_min_c"]
        self.assertEqual(evaluate_requirements(result, RULES)["eligibility"], "UNKNOWN")

    def test_other_parts_not_corrected(self):
        other = dict(sample(), part_number="M032LC2AE")
        result = apply_catalog_corrections([other], [CORRECTION])
        self.assertEqual(result, [other])
        self.assertNotIn("temp_min_c", result[0])

    def test_conflict_preserved_and_unverified(self):
        original = dict(sample(), temp_min_c=-20)
        result = apply_catalog_corrections([original], [CORRECTION])[0]
        self.assertEqual(result["temp_min_c"], -20)
        self.assertEqual(result["field_quality"]["temp_min_c"], "unverified")
        self.assertTrue(result["catalog_correction_conflicts"])
        self.assertEqual(evaluate_requirements(result, RULES)["eligibility"], "UNKNOWN")

    def test_input_not_mutated_and_same_value_idempotent(self):
        parts, correction = [sample()], copy.deepcopy(CORRECTION)
        before = copy.deepcopy(parts)
        once = apply_catalog_corrections(parts, [correction])
        twice = apply_catalog_corrections(once, [correction])
        self.assertEqual(parts, before)
        self.assertEqual(correction, CORRECTION)
        self.assertEqual(once, twice)

    def test_unrelated_metadata_preserved(self):
        original = dict(sample(), field_quality={"gpio":"estimated"}, notes="keep")
        result = apply_catalog_corrections([original], [CORRECTION])[0]
        self.assertEqual(result["field_quality"]["gpio"], "estimated")
        self.assertEqual(result["notes"], "keep")

    def test_invalid_correction_rejected(self):
        for changed in [{"field":"temp_max_c"}, {"value":True}, {"value":float("nan")}, {"source":{}}]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                apply_catalog_corrections([sample()], [{**CORRECTION, **changed}])

    def test_loader_preserves_correction_after_catalog_regeneration(self):
        with tempfile.TemporaryDirectory() as folder, patch("app.data_loader.DATA_DIR", folder):
            root = Path(folder)
            path = root / "nuvoton_parts.json"
            path.write_text(json.dumps([sample()]), encoding="utf-8")
            (root / "nuvoton_corrections.json").write_text(json.dumps([CORRECTION]), encoding="utf-8")
            reload_data()
            try:
                self.assertEqual(get_nuvoton_parts()[0]["temp_min_c"], -40)
                path.write_text(json.dumps([sample()]), encoding="utf-8")
                reload_data()
                self.assertEqual(get_nuvoton_parts()[0]["temp_min_c"], -40)
                self.assertNotIn("temp_min_c", json.loads(path.read_text(encoding="utf-8"))[0])
            finally:
                reload_data()
