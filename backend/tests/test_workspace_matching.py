"""Workspace orchestration tests with mocked checks, ranking and ChipSpec validation."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from pydantic import ValidationError
from app.workspace_matching import WorkspaceRequest, match_workspace


def source(**values):
    item = dict(part_number="UPLOADED", core="Cortex-M0", cpu_freq_mhz=48, gpio=39,
        flash_kb=32, ram_kb=8, package="LQFP48", package_size_mm2=49, usb=None,
        source={"file":"test.xlsx", "row":2})
    item.update(values)
    return item


def candidate(name="A", **values):
    item = source(part_number=name)
    item.update(values)
    return item


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        checks = patch("app.workspace_matching._checks", side_effect=lambda part, rules:
            {"eligibility":part.get("evaluation", "PASS" if rules else "NOT_EVALUATED"), "checks":[]})
        validation = patch("app.workspace_matching.ChipSpec")
        checks.start(); self.validation = validation.start()
        self.addCleanup(checks.stop); self.addCleanup(validation.stop)
        self.ranker = Mock(side_effect=lambda uploaded, parts, keys, top_k:
            [SimpleNamespace(score=parts[0].get("test_score", 1.0), similarity_pct=100, comparison=[])])

    def match(self, uploaded=None, catalog=None, **options):
        req = WorkspaceRequest(source=source() if uploaded is None else uploaded, **options)
        return match_workspace(req, [candidate()] if catalog is None else catalog, self.ranker, {"Cortex-M0":2})

    def test_preserves_source_unknowns_and_provenance(self):
        uploaded = source()
        before = copy.deepcopy(uploaded)
        result = self.match(uploaded)
        self.assertEqual(uploaded, before)
        self.assertEqual(result["source"], uploaded)
        self.assertIsNone(result["source"]["usb"])
        self.assertIsNone(self.ranker.call_args.args[0]["usb"])
        self.assertTrue(result["temporary"])

    def test_missing_source_base_blocks_ranking(self):
        with self.assertRaisesRegex(ValueError, "gpio"):
            self.match(source(gpio=None))
        self.ranker.assert_not_called()

    def test_estimated_source_base_blocks_ranking(self):
        with self.assertRaises(ValueError):
            self.match(source(field_quality={"gpio":"estimated"}))

    def test_unknown_optional_source_field_omitted(self):
        result = self.match(characteristics=["cpu_freq_mhz", "usb"])
        self.assertEqual(result["omitted_source_fields"], ["usb"])
        self.assertNotIn("usb", self.ranker.call_args.args[2])

    def test_missing_candidate_base_unranked(self):
        result = self.match(catalog=[candidate(gpio=None)])
        self.assertEqual(result["unranked_count"], 1)
        self.assertEqual(result["matches"], [])
        self.ranker.assert_not_called()

    def test_fail_unknown_filtered_before_top_k(self):
        result = self.match(catalog=[candidate("F", evaluation="FAIL"), candidate("U", evaluation="UNKNOWN"), candidate("P")], top_k=1)
        self.assertEqual(result["matches"][0]["part_number"], "P")
        self.assertEqual(result["eligibility_counts"]["FAIL"], 1)
        self.assertEqual(result["eligibility_counts"]["UNKNOWN"], 1)
        self.assertEqual(self.ranker.call_count, 1)

    def test_legacy_ranker_score_order_retained(self):
        result = self.match(catalog=[candidate("A", test_score=.8), candidate("B", test_score=.9)], top_k=1)
        self.assertEqual(result["matches"][0]["part_number"], "B")
        self.assertEqual(result["ranked_count"], 2)

    def test_no_requirements_not_evaluated(self):
        result = self.match()
        self.assertEqual(result["matches"][0]["eligibility"], "NOT_EVALUATED")

    def test_invalid_candidate_schema_unranked(self):
        self.validation.side_effect = ValueError("invalid")
        result = self.match()
        self.assertEqual(result["unranked_count"], 1)
        self.ranker.assert_not_called()

    def test_invalid_request_rejected(self):
        for limit in [0, 21, True, "5"]:
            with self.subTest(limit=limit), self.assertRaises(ValidationError):
                WorkspaceRequest(source=source(), top_k=limit)
        for uploaded in [source(part_number=""), source(usb=float("nan"))]:
            with self.subTest(uploaded=uploaded), self.assertRaises(ValidationError):
                WorkspaceRequest(source=uploaded)

    def test_unknown_core_is_not_assigned_default_rank(self):
        result = self.match(source(core="Unrecognized"), characteristics=["core"])
        self.assertEqual(result["omitted_source_fields"], ["core"])

    def test_no_cross_request_workspace_state(self):
        first = self.match(source(part_number="FIRST"))
        second = self.match(source(part_number="SECOND"))
        self.assertEqual(first["source"]["part_number"], "FIRST")
        self.assertEqual(second["source"]["part_number"], "SECOND")
