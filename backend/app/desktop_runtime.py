"""Desktop resource, per-user catalog and loopback helpers (no GUI imports)."""
import hashlib
import json
import os
from pathlib import Path
import socket

CATALOG_FILES = ("competitor_parts.json", "nuvoton_parts.json", "nuvoton_corrections.json")


def resource_paths(root):
    root = Path(root).resolve()
    web = root / "frontend" / "dist"
    seeds = root / "seed_data" if (root / "seed_data").is_dir() else root / "backend" / "data"
    if not (web / "index.html").is_file() or not (web / "assets").is_dir():
        raise RuntimeError("Built frontend missing. Rebuild the Windows package.")
    for name in CATALOG_FILES:
        if not (seeds / name).is_file():
            raise RuntimeError("Bundled catalog missing: " + name)
    return web, seeds


def seed_user_catalogs(seeds, user_root):
    digest = hashlib.sha256()
    blobs = {}
    for name in CATALOG_FILES:
        blob = (Path(seeds) / name).read_bytes()
        if not isinstance(json.loads(blob), list):
            raise ValueError("Catalog must be a JSON list: " + name)
        digest.update(name.encode("utf-8") + b"\0" + blob)
        blobs[name] = blob
    target = Path(user_root) / "data" / digest.hexdigest()[:16]
    target.mkdir(parents=True, exist_ok=True)
    for name, blob in blobs.items():
        path = target / name
        if not path.exists():
            with path.open("xb") as handle:
                handle.write(blob)
        if not isinstance(json.loads(path.read_text(encoding="utf-8")), list):
            raise ValueError("Local catalog is invalid: " + str(path))
    return target


def loopback_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        sock.setblocking(False)
        return sock
    except BaseException:
        sock.close()
        raise


class WindowsInstanceLock:
    def __init__(self, path):
        self.path = Path(path)
        self.handle = None

    def acquire(self):
        if os.name != "nt":
            raise RuntimeError("Desktop launcher supports Windows only")
        import msvcrt
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            if self.path.stat().st_size == 0:
                handle.write(b"0"); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            raise RuntimeError("The desktop tool is already running. Use its existing window or close it first.")
        self.handle = handle

    def close(self):
        if self.handle is not None:
            import msvcrt
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            self.handle.close()
            self.handle = None


def prepare_application(root, user_root):
    web, seeds = resource_paths(root)
    data = seed_user_catalogs(seeds, user_root)
    os.environ["MCU_XREF_FRONTEND_DIR"] = str(web)
    # Configure the existing module-level catalog paths before serving requests.
    from . import data_loader
    data_loader.DATA_DIR = str(data)
    data_loader.reload_data()
    from .main import app
    from .routers import chips
    chips.COMPETITOR_FILE = str(data / "competitor_parts.json")
    data_loader.get_nuvoton_parts()
    data_loader.get_competitor_parts()
    return app, data
