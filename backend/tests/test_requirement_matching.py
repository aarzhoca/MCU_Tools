"""Synthetic orchestration/schema tests; no datasheet claims or HTTP server."""
import unittest
from unittest.mock import Mock
from pydantic import ValidationError
from app.models import MatchResult
from app.requirement_schemas import RequirementsMatchRequest
from app.requirement_matching import match_with_requirements


def chip(part="SOURCE", **overrides):
    item = dict(part_number=part, manufacturer="Synthetic", family="Test", core="Cortex-M0",
        cpu_freq_mhz=48, flash_kb=32, ram_kb=8, gpio=40, adc_bits=12, adc_channels=8,
        uart=2, spi=1, i2c=1, usb=0, can=0, temp_max_c=105,
        vcc_min=1.8, vcc_max=3.6, package="LQFP48")
    item.update(overrides)
    return item


def ranked(candidate, score=1.0):
    return MatchResult(nuvoton_part=candidate, score=score, similarity_pct=score*100,
        comparison=[], meets_all=True)


def request(rules=None, **extra):
    return RequirementsMatchRequest(part_number="SOURCE", characteristics=["flash_kb"],
        requirements=[] if rules is None else rules, **extra)


def rule(field="cpu_freq_mhz", value=48, operator="gte"):
    return dict(field=field, value=value, operator=operator)


class IntegrationTests(unittest.TestCase):
    def test_legacy_path_keeps_ranker_arguments(self):
        catalog = [chip("A")]
        ranker = Mock(return_value=[ranked(catalog[0])])
        result = match_with_requirements(chip(), catalog, request(), ranker)
        ranker.assert_called_once_with(chip(), catalog, ["flash_kb"], top_k=5)
        self.assertEqual(result.matches[0].eligibility, "NOT_EVALUATED")
        self.assertEqual(result.matches[0].score, 1.0)

    def test_filter_before_limit_and_do_not_rank_failed_or_unknown(self):
        catalog = [chip("FAIL", cpu_freq_mhz=24), chip("UNKNOWN", cpu_freq_mhz=None), chip("PASS")]
        ranker = Mock(side_effect=lambda source, items, keys, top_k: [ranked(items[0])])
        result = match_with_requirements(chip(), catalog, request([rule()], top_k=1), ranker)
        self.assertEqual([m.nuvoton_part.part_number for m in result.matches], ["PASS"])
        self.assertEqual(result.eligibility_counts, {"PASS":1, "FAIL":1, "UNKNOWN":1})
        self.assertEqual(ranker.call_count, 1)
        self.assertEqual(ranker.call_args.args[1][0]["part_number"], "PASS")

    def test_missing_feature_not_model_default(self):
        result = match_with_requirements(chip(), [chip("A")], request([rule("can_fd", 1)]), Mock())
        self.assertFalse(result.matches)
        self.assertEqual(result.unknown_candidates[0].requirement_checks[0].actual_value, None)

    def test_counts_before_diagnostic_limit(self):
        result = match_with_requirements(chip(), [chip(str(i), cpu_freq_mhz=24) for i in range(3)],
            request([rule()], top_k=1), Mock())
        self.assertEqual(result.eligibility_counts["FAIL"], 3)
        self.assertEqual(len(result.failed_candidates), 1)
        self.assertIsNotNone(result.message)

    def test_rank_passing_candidates_by_existing_scores(self):
        def ranker(source, items, keys, top_k):
            return [ranked(items[0], items[0]["flash_kb"]/128)]
        result = match_with_requirements(chip(), [chip("A"), chip("B", flash_kb=64)],
            request([rule()], top_k=1), ranker)
        self.assertEqual(result.matches[0].nuvoton_part.part_number, "B")
        self.assertEqual(result.eligibility_counts["PASS"], 2)

    def test_malformed_quality_and_nan_are_safe_unknowns(self):
        for values in [{"field_quality": []}, {"field_quality": {"cpu_freq_mhz": []}},
                       {"cpu_freq_mhz": float("nan")}, {"cpu_freq_mhz": {}}]:
            with self.subTest(values=values):
                result = match_with_requirements(chip(), [chip("A", **values)], request([rule()]), Mock())
                self.assertEqual(result.unknown_candidates[0].eligibility, "UNKNOWN")
                result.model_dump_json()

    def test_strict_validation(self):
        for invalid in [rule("typo"), rule(value=True), rule(value="48"),
                        rule(value=-1), rule(value=float("inf")), rule(operator="bad"),
                        rule("package", "LQFP48"), dict(rule(), mode="preferred")]:
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                request([invalid])
        for limit in [0, -1, 101, True, "5"]:
            with self.subTest(limit=limit), self.assertRaises(ValidationError):
                request(top_k=limit)

    def test_more_than_five_required_checks(self):
        rules = [rule("cpu_freq_mhz", 48), rule("flash_kb", 32), rule("ram_kb", 8),
                 rule("package", "LQFP48", "eq"), rule("vcc_min", 1.8, "lte"),
                 rule("vcc_max", 3.6), rule("temp_max_c", 105)]
        ranker = Mock(side_effect=lambda source, items, keys, top_k: [ranked(items[0])])
        result = match_with_requirements(chip(), [chip("A")], request(rules), ranker)
        self.assertEqual(len(result.matches[0].requirement_checks), 7)

    def test_missing_min_temperature_prevents_pass(self):
        ranker = Mock()
        result = match_with_requirements(chip(), [chip("A")],
            request([rule("temp_min_c", -40, "lte")]), ranker)
        ranker.assert_not_called()
        self.assertEqual(result.eligibility_counts["UNKNOWN"], 1)

    def test_empty_catalog(self):
        result = match_with_requirements(chip(), [], request([rule()]), Mock())
        self.assertEqual(result.eligibility_counts, {"PASS":0, "FAIL":0, "UNKNOWN":0})
        self.assertFalse(result.matches)
