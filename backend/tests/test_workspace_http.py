"""HTTP workspace tests with real evaluator/matcher; synthetic catalog I/O."""
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.st_preview import router
from test_requirement_matching import chip


class WorkspaceHTTPTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI(); app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.source = chip("UPLOADED", package_size_mm2=49, usb=None,
            source={"file":"test.xlsx", "row":2})

    def post(self, **options):
        body = {"source":self.source, **options}
        with patch("app.routers.st_preview.get_nuvoton_parts", return_value=[chip("CANDIDATE", package_size_mm2=49)]):
            return self.client.post("/api/workspace/match", json=body)

    def test_match_unknowns_preserved_no_catalog_save(self):
        with patch("app.routers.chips._save_catalog") as save:
            response = self.post(requirements=[{"field":"cpu_freq_mhz", "operator":"gte", "value":48}])
        self.assertEqual(response.status_code, 200)
        save.assert_not_called()
        body = response.json()
        self.assertIsNone(body["source"]["usb"])
        self.assertEqual(body["source"]["part_number"], "UPLOADED")
        self.assertEqual(body["matches"][0]["eligibility"], "PASS")

    def test_customer_requirement_not_source_rewrite(self):
        response = self.post(requirements=[{"field":"cpu_freq_mhz", "operator":"gte", "value":72}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["matches"], [])
        self.assertEqual(response.json()["source"]["cpu_freq_mhz"], 48)
        self.assertEqual(response.json()["eligibility_counts"]["FAIL"], 1)

    def test_missing_base_and_bad_rule_422(self):
        self.source["gpio"] = None
        self.assertEqual(self.post().status_code, 422)
        self.assertEqual(self.post(requirements=[{"field":"typo", "operator":"gte", "value":1}]).status_code, 422)

    def test_no_source_lookup_or_saved_workspace(self):
        with patch("app.data_loader.find_competitor_part") as lookup:
            first = self.post()
            self.source["part_number"] = "SECOND"
            second = self.post()
        lookup.assert_not_called()
        self.assertEqual(first.json()["source"]["part_number"], "UPLOADED")
        self.assertEqual(second.json()["source"]["part_number"], "SECOND")
