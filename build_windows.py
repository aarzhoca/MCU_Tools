"""Build on Windows x64 / Python 3.12 via build_windows.bat."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
NAME = "MCU_Cross_Reference"


def main():
    if sys.platform != "win32" or sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8 or platform.machine().upper() not in ("AMD64", "X86_64"):
        raise RuntimeError("Build with Windows x64 Python 3.12")
    web = ROOT / "frontend" / "dist"
    if not (web / "index.html").is_file() or not (web / "assets").is_dir():
        raise RuntimeError("Run npm run build in frontend first")
    names = ("competitor_parts.json", "nuvoton_parts.json", "nuvoton_corrections.json")
    for name in names:
        if not (ROOT / "backend" / "data" / name).is_file():
            raise RuntimeError("Missing bundled catalog: " + name)
    tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    work = ROOT / "build" / "windows" / tag
    dist = ROOT / "dist" / "windows" / tag
    work.mkdir(parents=True); dist.mkdir(parents=True)
    import PyInstaller.__main__
    args = [str(ROOT / "windows_launcher.py"), "--name", NAME, "--onedir", "--windowed", "--noupx", "--clean", "--noconfirm",
        "--paths", str(ROOT / "backend"), "--workpath", str(work / "work"),
        "--specpath", str(work), "--distpath", str(dist),
        "--add-data", str(web) + ":frontend/dist", "--collect-submodules", "uvicorn",
        "--collect-submodules", "multipart", "--hidden-import", "h11"]
    for name in names:
        args.extend(["--add-data", str(ROOT / "backend" / "data" / name) + ":seed_data"])
    for package in ("fastapi", "pydantic", "uvicorn", "openpyxl"):
        args.extend(["--copy-metadata", package])
    PyInstaller.__main__.run(args)
    package = dist / NAME
    executable = package / (NAME + ".exe")
    if not executable.is_file():
        raise RuntimeError("PyInstaller did not produce the executable")
    environment = dict(os.environ, MCU_XREF_SELFTEST_DIR=str(work / "smoke"))
    subprocess.run([str(executable), "--self-test"], cwd=work, env=environment, check=True, timeout=180)
    manifest = {"build_utc":tag, "desktop_version":"pilot-v1", "python":sys.version,
        "platform":platform.platform(), "automated_smoke_test":"passed",
        "manual_clean_pc_acceptance":"not yet performed",
        "catalog_sha256":{name:hashlib.sha256((ROOT / "backend" / "data" / name).read_bytes()).hexdigest() for name in names},
        "dependencies":{distribution.metadata["Name"]:distribution.version
                        for distribution in importlib.metadata.distributions() if distribution.metadata["Name"]}}
    (package / "BUILD_INFO.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    shutil.copyfile(ROOT / "WINDOWS_QUICK_START.txt", package / "READ_ME_FIRST.txt")
    archive = Path(shutil.make_archive(str(dist / (NAME + "-win64-" + tag)), "zip", root_dir=dist, base_dir=NAME))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(checksum + "  " + archive.name + "\n", encoding="ascii")
    print("Executable:", executable)
    print("Distribute whole ZIP:", archive)
    print("SHA-256:", checksum)
    print("Build smoke test passed. Manual clean-PC/offline acceptance is still required.")


if __name__ == "__main__":
    main()
