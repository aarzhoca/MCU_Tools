"""Synthetic fixtures: test logic, not verified device specifications."""
import unittest
from app.requirements import evaluate_requirements


def req(field, value, operator="gte"):
    return {"field": field, "operator": operator, "value": value}


class RequirementTests(unittest.TestCase):
    def test_minimum_48_boundary(self):
        result = evaluate_requirements({"cpu_freq_mhz": 48}, [req("cpu_freq_mhz", 48)])
        self.assertEqual(result["eligibility"], "PASS")

    def test_72_rejection(self):
        self.assertEqual(evaluate_requirements({"cpu_freq_mhz": 48},
            [req("cpu_freq_mhz", 72)])["eligibility"], "FAIL")

    def test_missing_is_not_zero(self):
        for candidate, expected in [({}, "UNKNOWN"), ({"can_fd": None}, "UNKNOWN"),
                                    ({"can_fd": 0}, "FAIL"), ({"can_fd": 1}, "PASS")]:
            with self.subTest(candidate=candidate):
                self.assertEqual(evaluate_requirements(candidate,
                    [req("can_fd", 1)])["eligibility"], expected)

    def test_estimated_field_unknown(self):
        self.assertEqual(evaluate_requirements({"gpio": 40,
            "field_quality": {"gpio": "estimated"}}, [req("gpio", 32)])["eligibility"], "UNKNOWN")

    def test_range_coverage(self):
        candidate = {"vcc_min": 1.8, "vcc_max": 3.6, "temp_min_c": -40, "temp_max_c": 105}
        checks = [req("vcc_min", 1.8, "lte"), req("vcc_max", 3.6),
                  req("temp_min_c", -40, "lte"), req("temp_max_c", 105)]
        self.assertEqual(evaluate_requirements(candidate, checks)["eligibility"], "PASS")
        candidate["vcc_min"] = 2.0
        self.assertEqual(evaluate_requirements(candidate, checks)["eligibility"], "FAIL")

    def test_package_exact_not_family(self):
        self.assertEqual(evaluate_requirements({"package": "LQFP64"},
            [req("package", "LQFP48", "eq")])["eligibility"], "FAIL")

    def test_fpu_not_inferred_from_hierarchy(self):
        self.assertEqual(evaluate_requirements({"core": "Cortex-M4"},
            [req("core", "Cortex-M4F", "eq")])["eligibility"], "FAIL")

    def test_fail_dominates_unknown(self):
        self.assertEqual(evaluate_requirements({"flash_kb": 16},
            [req("flash_kb", 32), req("can_fd", 1)])["eligibility"], "FAIL")

    def test_no_requirements(self):
        self.assertEqual(evaluate_requirements({}, [])["eligibility"], "NOT_EVALUATED")

    def test_invalid_requirements_rejected(self):
        for check in [req("typo", 1), req("flash_kb", -1), req("flash_kb", True),
                      req("flash_kb", float("nan")), req("flash_kb", 1, "bad"),
                      req("package", "LQFP48"), req("core", "", "eq")]:
            with self.subTest(check=check), self.assertRaises(ValueError):
                evaluate_requirements({}, [check])

    def test_invalid_actual_unknown(self):
        for value in [True, "32", -1, float("nan"), float("inf")]:
            with self.subTest(value=value):
                self.assertEqual(evaluate_requirements({"flash_kb": value},
                    [req("flash_kb", 32)])["eligibility"], "UNKNOWN")

    def test_input_not_mutated(self):
        candidate, checks = {"flash_kb": 32}, [req("flash_kb", 32)]
        evaluate_requirements(candidate, checks)
        self.assertEqual(candidate, {"flash_kb": 32})
        self.assertEqual(checks, [req("flash_kb", 32)])
