"""Run with project requirements-dev.txt; uses real XLSX parser via HTTP."""
import io
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.st_preview import router
from test_st_xlsx import workbook_bytes, example

URL = "/api/chips/competitor/st-xlsx-preview"


class STPreviewHTTPTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def upload(self, data=None, filename="test.xlsx", content=None):
        if content is None:
            content = workbook_bytes([example()])
        return self.client.post(URL, data=data or {}, files={"file":
            (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})

    def test_success_does_not_save_catalog(self):
        with patch("app.routers.chips._save_catalog") as save:
            response = self.upload()
        self.assertEqual(response.status_code, 200)
        save.assert_not_called()
        body = response.json()
        self.assertTrue(body["preview_only"])
        self.assertEqual(body["parsed_count"], 1)
        self.assertEqual(body["records"][0]["temp_min_c"], -40)
        self.assertNotIn("source_values", body["records"][0])

    def test_exact_not_found(self):
        response = self.upload(data={"part_number": "MISSING"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["records"], [])

    def test_bad_extension_or_workbook(self):
        self.assertEqual(self.upload(filename="bad.csv").status_code, 400)
        self.assertEqual(self.upload(content=b"not a workbook").status_code, 422)

    def test_missing_sheet_and_long_query(self):
        self.assertEqual(self.upload(data={"sheet": "Missing"}).status_code, 422)
        self.assertEqual(self.upload(data={"part_number": "A"*101}).status_code, 422)

    def test_oversize_upload(self):
        with patch("app.routers.st_preview.LIMIT", 10):
            self.assertEqual(self.upload(content=b"x"*11).status_code, 413)
