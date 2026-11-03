"""HTTP tests use the real matcher and mocked catalog I/O only.

Run in the project environment after installing requirements-dev.txt.
"""
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.match import router
from test_requirement_matching import chip, rule


class HTTPIntegrationTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.source = patch("app.routers.match.find_competitor_part", return_value=chip())
        self.source.start()
        self.addCleanup(self.source.stop)
        self.addCleanup(self.client.close)

    def test_http_filter_before_limit_with_real_matcher(self):
        catalog = [chip("FAIL", cpu_freq_mhz=24), chip("UNKNOWN", cpu_freq_mhz=None), chip("PASS")]
        with patch("app.routers.match.get_nuvoton_parts", return_value=catalog):
            response = self.client.post("/api/match", json={"part_number":"SOURCE",
                "characteristics":["cpu_freq_mhz"], "top_k":1, "requirements":[rule()]})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["matches"][0]["nuvoton_part"]["part_number"], "PASS")
        self.assertEqual(body["matches"][0]["eligibility"], "PASS")
        self.assertEqual(body["eligibility_counts"], {"PASS":1,"FAIL":1,"UNKNOWN":1})

    def test_http_validation(self):
        for invalid in [rule("typo"), rule(value=True), rule(value="48")]:
            with self.subTest(invalid=invalid):
                response = self.client.post("/api/match", json={"part_number":"SOURCE",
                    "characteristics":[], "requirements":[invalid]})
                self.assertEqual(response.status_code, 422)

    def test_http_no_pass_and_no_silent_relaxation(self):
        with patch("app.routers.match.get_nuvoton_parts", return_value=[chip("FAIL")]):
            response = self.client.post("/api/match", json={"part_number":"SOURCE",
                "characteristics":[], "requirements":[rule(value=72)]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["matches"], [])
        self.assertTrue(response.json()["message"])

    def test_legacy_http_response_preserves_matching_values(self):
        from app.matcher import find_matches
        catalog = [chip("A"), chip("B", flash_kb=64)]
        expected = [match.model_dump(mode="json") for match in
                    find_matches(chip(), catalog, ["flash_kb"], top_k=5)]
        with patch("app.routers.match.get_nuvoton_parts", return_value=catalog):
            response = self.client.post("/api/match", json={"part_number":"SOURCE",
                "characteristics":["flash_kb"]})
        self.assertEqual(response.status_code, 200)
        actual = response.json()["matches"]
        for match in actual:
            self.assertEqual(match.pop("eligibility"), "NOT_EVALUATED")
            self.assertEqual(match.pop("requirement_checks"), [])
        self.assertEqual(actual, expected)

    def test_missing_source_404(self):
        with patch("app.routers.match.find_competitor_part", return_value=None), \
             patch("app.routers.match.search_competitor_parts", return_value=[]):
            response = self.client.post("/api/match", json={"part_number":"MISSING", "characteristics":[]})
        self.assertEqual(response.status_code, 404)
