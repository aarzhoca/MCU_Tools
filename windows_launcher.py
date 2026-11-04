"""Windows desktop launcher; --self-test runs an isolated backend smoke test."""
import io
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
from app.desktop_runtime import prepare_application, loopback_socket, WindowsInstanceLock


def http(url, payload=None, content_type="application/json"):
    request = urllib.request.Request(url, data=payload,
        headers={"Content-Type": content_type} if payload is not None else {})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=30) as response:
        return response.read()


class BackendSession:
    def __init__(self, resources, user_root):
        self.resources, self.user_root = resources, user_root
        self.server = None
        self.url = None
        self.error = None
        self.stop_requested = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=False)

    def run(self):
        sock = None
        try:
            app, data = prepare_application(self.resources, self.user_root)
            logging.info("Desktop data directory: %s", data)
            if self.stop_requested.is_set():
                return
            import uvicorn
            sock = loopback_socket()
            self.url = "http://127.0.0.1:" + str(sock.getsockname()[1])
            config = uvicorn.Config(app, host="127.0.0.1", loop="asyncio", http="h11",
                ws="none", lifespan="on", log_config=None, access_log=False,
                timeout_graceful_shutdown=5)
            self.server = uvicorn.Server(config)
            self.server.should_exit = self.stop_requested.is_set()
            self.server.run(sockets=[sock])
        except BaseException as error:
            self.error = str(error)
            logging.exception("Desktop backend failed")
        finally:
            if sock is not None:
                sock.close()

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_requested.set()
        if self.server is not None:
            self.server.should_exit = True

    def wait_ready(self, timeout=90):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.error or not self.thread.is_alive():
                raise RuntimeError(self.error or "Backend stopped before readiness")
            if self.server is not None and self.server.started:
                if json.loads(http(self.url + "/health")) == {"status":"ok"}:
                    return
            time.sleep(.1)
        raise RuntimeError("Startup timed out; inspect desktop.log")


def run_smoke(resources, user_root):
    session = BackendSession(resources, user_root)
    session.start()
    try:
        session.wait_ready()
        if not http(session.url + "/"):
            raise RuntimeError("Frontend response was empty")
        if not json.loads(http(session.url + "/api/characteristics")):
            raise RuntimeError("Characteristics were empty")
        from openpyxl import Workbook, load_workbook
        workbook = Workbook(); sheet = workbook.active; sheet.title = "ProductsList"
        sheet.append(["Part Number", "Core", "Operating Frequency (MHz)", "Flash Size (kB) (Prog)",
            "RAM Size (kB)", "I/Os (High Current)", "Package"])
        sheet.append(["PACKAGING_TEST", "Arm Cortex-M0", 48, 32, 8, 39, "LQFP 48 7x7x1.4 mm"])
        buffer = io.BytesIO(); workbook.save(buffer); workbook.close()
        boundary = "mcu" + uuid.uuid4().hex
        body = ("--" + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="smoke.xlsx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n').encode() + buffer.getvalue() + ("\r\n--" + boundary + "--\r\n").encode()
        preview = json.loads(http(session.url + "/api/chips/competitor/st-xlsx-preview", body, "multipart/form-data; boundary=" + boundary))
        source = preview["records"][0]
        result = json.loads(http(session.url + "/api/workspace/match", json.dumps({"source":source}).encode()))
        selected = [result["matches"][0]["part_number"]]
        content = http(session.url + "/api/workspace/export-xlsx", json.dumps({
            "snapshot_json":result["comparison_snapshot_json"], "token":result["snapshot_token"],
            "selected":selected}).encode())
        exported = load_workbook(io.BytesIO(content))
        try:
            if exported.sheetnames != ["Summary", "Comparison", "Sources"]:
                raise RuntimeError("Unexpected export sheets")
        finally:
            exported.close()
    finally:
        session.stop(); session.thread.join(timeout=30)
        if session.thread.is_alive():
            raise RuntimeError("Backend did not shut down after smoke test")


def desktop(resources, user_root):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk(); root.title("Nuvoton MCU Cross Reference - Local Pilot")
    root.geometry("620x300"); root.minsize(620, 300)
    session = BackendSession(resources, user_root)
    status = tk.StringVar(value="Starting local tool…")
    tk.Label(root, textvariable=status, wraplength=540, justify="left").pack(padx=20, pady=15)
    tk.Label(root, text="Keep this window open. Closing it stops the tool.\nClosing the browser tab does not stop the tool.").pack()
    open_button = tk.Button(root, text="Open browser", state="disabled", command=lambda: webbrowser.open(session.url))
    open_button.pack(pady=8)
    tk.Button(root, text="Open logs", command=lambda: os.startfile(str(Path(user_root) / "logs"))).pack()
    closing, opened = False, False
    started = time.monotonic()
    def close():
        nonlocal closing
        closing = True; status.set("Stopping. Finishing active requests…")
        open_button.config(state="disabled"); session.stop()
    root.protocol("WM_DELETE_WINDOW", close)
    tk.Button(root, text="Stop and exit", command=close).pack(pady=8)
    def poll():
        nonlocal opened
        if closing:
            if not session.thread.is_alive():
                root.destroy(); return
        elif session.error:
            status.set("Startup/runtime error: " + session.error + "\nSee logs, then Stop and exit.")
        elif not session.thread.is_alive():
            status.set("Backend stopped. See logs, then Stop and exit.")
        elif session.server is not None and session.server.started and not opened:
            opened = True; status.set("Running locally: " + session.url)
            open_button.config(state="normal")
            if not webbrowser.open(session.url):
                messagebox.showinfo("Open browser", "Open this address manually: " + session.url)
        elif not opened and time.monotonic() - started > 90:
            status.set("Startup is taking longer than expected. Check logs or Stop and exit.")
        root.after(200, poll)
    session.start(); root.after(200, poll)
    try:
        root.mainloop()
    finally:
        session.stop(); session.thread.join()


def main():
    self_test = "--self-test" in sys.argv
    resources = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    base = Path(os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")) / "Nuvoton" / "MCU-XRef-Pilot"
    user_root = Path(os.environ.get("MCU_XREF_SELFTEST_DIR", str(base / "self-test"))) if self_test else base
    logs = user_root / "logs"
    lock = None
    try:
        logs.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(logs / "desktop.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        logging.basicConfig(level=logging.INFO, handlers=[handler], force=True,
                            format="%(asctime)s %(levelname)s %(name)s %(message)s")
        lock = WindowsInstanceLock(user_root / "instance.lock")
        lock.acquire()
        if self_test:
            run_smoke(resources, user_root)
        else:
            desktop(resources, user_root)
        return 0
    except BaseException as error:
        logging.exception("Desktop launch failed")
        if not self_test:
            from tkinter import messagebox
            messagebox.showerror("MCU Cross Reference", str(error) + "\nLogs: " + str(logs))
        return 1
    finally:
        if lock is not None:
            lock.close()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
