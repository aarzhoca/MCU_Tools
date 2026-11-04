"""Portable resource tests plus Windows-only instance locking."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from app.desktop_runtime import resource_paths, seed_user_catalogs, loopback_socket, WindowsInstanceLock, CATALOG_FILES


def fixture(root):
    root = Path(root)
    web = root / "frontend" / "dist"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<html>Packaging fixture</html>", encoding="utf-8")
    seeds = root / "seed_data"; seeds.mkdir()
    for name in CATALOG_FILES:
        (seeds / name).write_text("[]", encoding="utf-8")
    return web, seeds


class DesktopRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.web, self.seeds = fixture(self.root)
        self.user = self.root / "user"

    def test_resource_paths(self):
        self.assertEqual(resource_paths(self.root), (self.web, self.seeds))

    def test_missing_frontend_rejected(self):
        (self.web / "index.html").unlink()
        with self.assertRaises(RuntimeError):
            resource_paths(self.root)

    def test_all_three_catalogs_seeded(self):
        data = seed_user_catalogs(self.seeds, self.user)
        self.assertEqual({path.name for path in data.iterdir()}, set(CATALOG_FILES))
        self.assertEqual(data, seed_user_catalogs(self.seeds, self.user))

    def test_personal_catalog_not_overwritten(self):
        data = seed_user_catalogs(self.seeds, self.user)
        personal = [{"part_number":"PERSONAL"}]
        (data / "competitor_parts.json").write_text(json.dumps(personal), encoding="utf-8")
        seed_user_catalogs(self.seeds, self.user)
        self.assertEqual(json.loads((data / "competitor_parts.json").read_text()), personal)
        self.assertEqual((self.seeds / "competitor_parts.json").read_text(), "[]")

    def test_changed_seed_gets_new_directory(self):
        first = seed_user_catalogs(self.seeds, self.user)
        (self.seeds / "nuvoton_corrections.json").write_text('[{"test":1}]', encoding="utf-8")
        second = seed_user_catalogs(self.seeds, self.user)
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_dir())

    def test_missing_or_invalid_seed_rejected(self):
        (self.seeds / "nuvoton_parts.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            seed_user_catalogs(self.seeds, self.user)
        (self.seeds / "nuvoton_parts.json").unlink()
        with self.assertRaises(RuntimeError):
            resource_paths(self.root)

    def test_socket_is_reserved_on_loopback(self):
        one, two = loopback_socket(), loopback_socket()
        self.addCleanup(one.close); self.addCleanup(two.close)
        self.assertEqual(one.getsockname()[0], "127.0.0.1")
        self.assertNotEqual(one.getsockname()[1], two.getsockname()[1])

    @unittest.skipUnless(os.name == "nt", "Windows locking must be tested on Windows")
    def test_duplicate_instance_rejected_and_lock_released(self):
        one, two = WindowsInstanceLock(self.root / "instance.lock"), WindowsInstanceLock(self.root / "instance.lock")
        self.addCleanup(one.close); self.addCleanup(two.close)
        one.acquire()
        with self.assertRaises(RuntimeError):
            two.acquire()
        one.close(); two.acquire()
