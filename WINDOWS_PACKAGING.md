# Windows one-folder packaging pilot

## Scope

New build_windows.bat / build_windows.py, not the existing Docker-oriented
build_package.bat. Old start.bat/run_backend.py hard-coded paths are not used.
Target: Windows x64 with a Python 3.12 build environment. Recipients receive
an onedir executable bundle, built frontend and three JSON seed catalogs.
The runtime should not require Python, Node or Docker installed separately;
that expectation still needs clean-PC acceptance. No installer, signing,
automatic updates or hosted access are implemented.

## Build on your Windows PC

Use a short source folder (for example C:\MCU_Tools) if path lengths cause
problems. Moving source does not move a working venv; this builder creates
its own .venv-package using py -3.12. Node/npm are needed on the builder only.
Internet is needed to obtain dependencies and frontend packages at build time.

1. Update this feature branch, including backend/data/nuvoton_corrections.json.
2. From the project root, double-click build_windows.bat or run it in cmd.
3. It installs requirements-windows-build.txt, checks dependencies, runs the
   backend tests (expected 104 on Windows), rebuilds the frontend, and invokes
   PyInstaller. Dependency installation/build can take time and disk space.
4. Each build gets a new timestamped dist/windows directory; old build folders
   are not deleted. Generated PyInstaller work is under build/windows.
5. The builder runs the frozen EXE --self-test in isolated build storage.
   It verifies health, frontend response, characteristics, XLSX preview,
   workspace matching, Excel generation/readback and backend shutdown.
6. Only after that succeeds does it create ZIP + SHA-256 and BUILD_INFO.json.
   This automated smoke check does not exercise the actual browser or Tk UI.

PyInstaller is pinned to 6.22.3; runtime dependencies retain their existing
pins. Transitive packages are not fully locked; versions are recorded in
BUILD_INFO.json. Review third-party redistribution notices, company data
permissions, code signing, antivirus and IT policy before external rollout.
Never advise users to disable security products to run an unsigned binary.

## Runtime design

The launcher uses a reserved IPv4 loopback socket on an OS-assigned port,
not fixed 8000/8001 and never 0.0.0.0. One backend process preserves the
process-local export signing key. Tk provides startup status, Open browser,
Open logs and Stop and exit. A per-user Windows file lock prevents duplicate
desktop instances; unrelated developer servers are not killed or reused.
Closing the browser does not exit. Closing the control window requests graceful
shutdown and waits for active work; log errors rather than hiding failures.
No console window or administrator privileges are requested by the build.

Bundled resources are resolved from sys._MEIPASS when frozen. The launcher
sets MCU_XREF_FRONTEND_DIR before importing app.main. The runtime adapter sets
data_loader.DATA_DIR and clears caches, then points the existing chips router's
COMPETITOR_FILE at the same writable per-user copy before any requests run.
It eagerly checks both catalogs. This adapter leaves manual-development and
Docker defaults unchanged, but must be retested if legacy routes change.

Three seeds (Nuvoton, competitor, corrections) determine a content fingerprint.
Copies live in %LOCALAPPDATA%/Nuvoton/MCU-XRef-Pilot/data/<fingerprint>.
Existing local files for that fingerprint are preserved. Changed seeds get a
fresh directory; prior personal imports are retained in the old directory but
NOT automatically migrated. This is local per-user persistence, not a shared
hosted personal-workspace service. ST selection state remains browser memory.
Logs rotate under the same user root's logs directory. The original package
seeds are not written by the app; ordinary filesystem access is not prevented.

## Tests and limitations at preparation

Seven portable runtime-helper tests passed in the assistant environment.
The Windows locking test was skipped there. Two fresh-process integration
tests are added but NOT run there (FastAPI unavailable). Expected backend
suite is 104: 94 existing + 8 runtime tests + 2 source-mode integration tests.
Python syntax was checked. No Windows EXE was built, no PyInstaller invocation
was run, and no Tk/browser/clean-PC/offline pass is claimed by the assistant.

## Manual acceptance before distributor use

- Run the generated exe on the builder first; confirm the window and browser.
- Extract the entire ZIP on a separate clean Windows x64 PC/VM without Python,
  Node or Docker. Use a normal user, not administrator. Test a path with spaces.
- Disconnect internet; upload the ST workbook and reproduce M031LC2AE checks,
  candidate comparison and Excel download. External URLs may be unavailable.
- Check 127.0.0.1 URL, dynamic port, local logs, corrections and profile copies.
- Check second launch warning, browser reopen, Stop and exit, and successful
  relaunch. The previous URL should stop responding after exit.
- Confirm package seed files are unchanged after a legacy import into the
  local user copy. Inspect logs before sending them to support.
- Run two Windows accounts and confirm their writable data paths differ.

Desktop localhost is not a security boundary against other local processes
or malicious webpages. Existing CORS/authentication and legacy mutation routes
are not production hardened by packaging. Keep it a controlled local pilot.
