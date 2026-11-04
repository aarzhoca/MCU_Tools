"""Real match-to-snapshot-to-XLSX HTTP tests with synthetic catalog I/O."""
import io
import unittest
from unittest.mock import patch
from openpyxl import load_workbook
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.st_preview import router
from test_requirement_matching import chip


class ComparisonHTTPTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI(); app.include_router(router)
        self.client = TestClient(app); self.addCleanup(self.client.close)
        self.catalog = [chip("CANDIDATE", package_size_mm2=49)]
        with patch("app.routers.st_preview.get_nuvoton_parts", return_value=self.catalog):
            response = self.client.post("/api/workspace/match", json={
                "source":chip("UPLOADED", package_size_mm2=49, usb=None),
                "requirements":[{"field":"cpu_freq_mhz","operator":"gte","value":48}]})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.payload = {"snapshot_json":body["comparison_snapshot_json"],
                        "token":body["snapshot_token"], "selected":["CANDIDATE"]}

    def test_export_uses_snapshot_not_current_catalog(self):
        with patch("app.routers.st_preview.get_nuvoton_parts", side_effect=AssertionError("must not reload")):
            response = self.client.post("/api/workspace/export-xlsx", json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response.headers["content-type"])
        book = load_workbook(io.BytesIO(response.content)); self.addCleanup(book.close)
        row = next(row for row in book["Comparison"].values if row[0] == "CPU frequency")
        self.assertEqual(row[3], 48)
        self.assertEqual(row[5], 48)
        self.assertEqual(book.sheetnames, ["Summary","Comparison","Sources"])

    def test_changed_snapshot_rejected(self):
        changed = {**self.payload, "snapshot_json":self.payload["snapshot_json"] + " "}
        self.assertEqual(self.client.post("/api/workspace/export-xlsx", json=changed).status_code, 422)

    def test_unknown_candidate_or_too_many_rejected(self):
        for selected in [["OTHER"], [], ["A","B","C","D"]]:
            with self.subTest(selected=selected):
                self.assertEqual(self.client.post("/api/workspace/export-xlsx",
                    json={**self.payload,"selected":selected}).status_code, 422)

    def test_invalid_or_oversize_body_rejected(self):
        self.assertEqual(self.client.post("/api/workspace/export-xlsx", content=b"bad").status_code, 422)
        self.assertEqual(self.client.post("/api/workspace/export-xlsx", content=b"x"*1_000_001).status_code, 413)
