"""Source-mode desktop integration in fresh subprocesses (not a frozen EXE test)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_desktop_runtime import fixture
from test_requirement_matching import chip

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


class DesktopIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.resources = Path(self.temp.name) / "resources"
        _, seeds = fixture(self.resources)
        (seeds / "nuvoton_parts.json").write_text(json.dumps([chip("FIXTURE", package_size_mm2=49)]), encoding="utf-8")
        (seeds / "competitor_parts.json").write_text(json.dumps([chip("SOURCE")]), encoding="utf-8")
        self.user = Path(self.temp.name) / "user"

    def child(self, code):
        result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND,
            env=dict(os.environ, PYTHONUTF8="1"), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_redirects_catalogs_and_legacy_import_path(self):
        self.child("from app.desktop_runtime import prepare_application; "
            f"app,data=prepare_application({str(self.resources)!r},{str(self.user)!r}); "
            "from app import data_loader; from app.routers import chips; "
            "assert data_loader.DATA_DIR == str(data); "
            "assert chips.COMPETITOR_FILE == str(data / 'competitor_parts.json'); "
            "assert data_loader.get_nuvoton_parts()[0]['part_number'] == 'FIXTURE'; "
            "assert data_loader.get_competitor_parts()[0]['part_number'] == 'SOURCE'")

    def test_source_mode_smoke_upload_match_export_and_shutdown(self):
        self.child(f"import sys; sys.path.insert(0,{str(ROOT)!r}); "
            "from windows_launcher import run_smoke; "
            f"run_smoke({str(self.resources)!r},{str(self.user)!r})")
