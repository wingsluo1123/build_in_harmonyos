#!/usr/bin/env python3
"""Exercise packaged WOFF fonts in the HarmonyOS PC system browser over HDC."""

import argparse
import http.server
import json
import pathlib
import shutil
import socket
import subprocess
import sys
import threading
import time


FACES = (
    ("FiraCode-Light.woff", "FiraCodeLight"),
    ("FiraCode-Regular.woff", "FiraCodeRegular"),
    ("FiraCode-Medium.woff", "FiraCodeMedium"),
    ("FiraCode-SemiBold.woff", "FiraCodeSemiBold"),
    ("FiraCode-Bold.woff", "FiraCodeBold"),
    ("FiraCode-VF.woff", "FiraCodeVariable"),
)

HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>HarmonyOS WOFF font test</title></head>
<body><pre id="result">Loading WOFF files in the HarmonyOS browser…</pre>
<script>
const faces = __FACES__;
const sample = "const main = (x) => x != null && x >= 0; // Fira Code 0123456789";
function raster(family) {
  const canvas = document.createElement("canvas");
  canvas.width = 1400;
  canvas.height = 72;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#000";
  context.textBaseline = "top";
  context.font = '32px "' + family + '"';
  context.fillText(sample, 2, 2);
  return context.getImageData(0, 0, canvas.width, canvas.height).data;
}
function pixelDifference(left, right) {
  let changed = 0;
  let painted = 0;
  for (let i = 0; i < left.length; i += 4) {
    if (left[i + 3] !== 0) painted++;
    if (left[i] !== right[i] || left[i + 1] !== right[i + 1] ||
        left[i + 2] !== right[i + 2] || left[i + 3] !== right[i + 3]) changed++;
  }
  return { changedPixels: changed, paintedPixels: painted };
}
async function report(result) {
  document.getElementById("result").textContent = JSON.stringify(result, null, 2);
  try {
    await fetch("/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result)
    });
  } catch (error) {
    document.getElementById("result").textContent += " Report delivery failed: " + error;
  }
}
async function run() {
  const outcomes = [];
  try {
    for (const face of faces) {
      const loaded = await new FontFace(face.family, 'url("/fonts/' + face.file + '")').load();
      document.fonts.add(loaded);
      await document.fonts.load('32px "' + face.family + '"', sample);
      const pixels = pixelDifference(raster(face.family), raster("monospace"));
      outcomes.push({
        file: face.file,
        loaded: document.fonts.check('32px "' + face.family + '"', sample),
        changedPixels: pixels.changedPixels,
        paintedPixels: pixels.paintedPixels
      });
    }
    await report({
      title: document.title,
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      outcomes: outcomes
    });
  } catch (error) {
    await report({
      title: document.title,
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      outcomes: outcomes,
      error: String(error),
      stack: error && error.stack ? String(error.stack) : ""
    });
  }
}
run();
</script></body></html>
"""


def run_hdc(hdc, serial, *args, timeout=20):
    command = [hdc, "-t", serial, *args]
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, check=False
    )
    if result.returncode:
        raise RuntimeError(
            f"HDC command failed ({result.returncode}): {command!r}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result.stdout.strip()


def find_hdc(value):
    if value:
        return value
    located = shutil.which("hdc")
    if located:
        return located
    candidates = (
        pathlib.Path.home() / "AppData/Local/OpenHarmony/Sdk/26.0.0/toolchains/hdc.exe",
        pathlib.Path.home() / "AppData/Local/OpenHarmony/Sdk/Current/toolchains/hdc.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("hdc was not found; pass --hdc <path-to-hdc>")


class FontTestHandler(http.server.BaseHTTPRequestHandler):
    font_dir = None
    html = None
    report = None
    report_event = None

    def log_message(self, format_string, *args):
        print("[http] " + format_string % args)

    def do_GET(self):
        if self.path == "/":
            body = self.html.encode("utf-8")
            content_type = "text/html; charset=utf-8"
        elif self.path.startswith("/fonts/"):
            name = self.path.removeprefix("/fonts/")
            if name not in {filename for filename, _ in FACES}:
                self.send_error(404)
                return
            font_path = self.font_dir / name
            if not font_path.is_file():
                self.send_error(404, f"font is absent: {name}")
                return
            body = font_path.read_bytes()
            content_type = "font/woff"
        else:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/report":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        if size <= 0 or size > 65536:
            self.send_error(413)
            return
        try:
            report = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            self.send_error(400, str(error))
            return
        type(self).report = report
        type(self).report_event.set()
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir", required=True, type=pathlib.Path)
    parser.add_argument("--serial", required=True, help="USB HDC serial from hdc list targets")
    parser.add_argument("--hdc", help="Path to hdc executable; defaults to PATH/DevEco SDK")
    parser.add_argument("--timeout", type=int, default=120, help="Seconds to wait for browser results")
    args = parser.parse_args()

    font_dir = args.font_dir.resolve()
    if not font_dir.is_dir():
        parser.error(f"font directory does not exist: {font_dir}")
    missing = [name for name, _ in FACES if not (font_dir / name).is_file()]
    if missing:
        parser.error(f"missing packaged font files: {', '.join(missing)}")

    hdc = find_hdc(args.hdc)
    uname = run_hdc(hdc, args.serial, "shell", "uname", "-a")
    machine = run_hdc(hdc, args.serial, "shell", "uname", "-m").lower()
    print(f"DEVICE_UNAME={uname}")
    if "harmony" not in uname.lower() or machine not in ("aarch64", "arm64"):
        raise RuntimeError(f"expected a HarmonyOS aarch64 device; uname -m returned {machine!r}")

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    faces = [{"file": filename, "family": family} for filename, family in FACES]
    handler = type("Handler", (FontTestHandler,), {})
    handler.font_dir = font_dir
    handler.html = HTML.replace("__FACES__", json.dumps(faces))
    handler.report = None
    handler.report_event = threading.Event()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    mapped = False
    try:
        run_hdc(hdc, args.serial, "rport", f"tcp:{port}", f"tcp:{port}")
        mapped = True
        url = f"http://127.0.0.1:{port}/"
        print(f"BROWSER_TEST_URL={url}")
        start = run_hdc(
            hdc, args.serial, "shell", "aa", "start",
            "-a", "MainAbility", "-b", "com.huawei.hmos.browser", "-U", url
        )
        print(f"BROWSER_START={start}")

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if handler.report_event.wait(timeout=min(1.0, max(0.0, deadline - time.monotonic()))):
                break
        result = handler.report
        if not result:
            raise RuntimeError(
                f"system browser did not report a result within {args.timeout}s; "
                "check that the browser opened the test URL"
            )
        if result.get("error"):
            raise RuntimeError(f"browser-side font test error: {result['error']}\n{result.get('stack', '')}")
        outcomes = result.get("outcomes", [])
        expected = {filename for filename, _ in FACES}
        actual = {item.get("file") for item in outcomes}
        if actual != expected or len(outcomes) != len(FACES):
            raise RuntimeError(f"browser reported an incomplete face set: {outcomes!r}")
        failures = [
            item for item in outcomes
            if not item.get("loaded")
            or item.get("changedPixels", 0) <= 0
            or item.get("paintedPixels", 0) <= 0
        ]
        print("BROWSER_USER_AGENT=" + str(result.get("userAgent", "")))
        for item in outcomes:
            print(
                f"[{'PASS' if item not in failures else 'FAIL'}] {item['file']}: "
                f"loaded={item.get('loaded')}, changedPixels={item.get('changedPixels')}, "
                f"paintedPixels={item.get('paintedPixels')}"
            )
        if failures:
            raise RuntimeError(f"font loading or rasterization failed: {failures!r}")
        print("HARMONY_TEST_PASS=1/1 (six WOFF faces decoded and rasterized on device)")
    finally:
        server.shutdown()
        server.server_close()
        if mapped:
            try:
                run_hdc(hdc, args.serial, "fport", "rm", f"tcp:{port}", f"tcp:{port}")
                print(f"HDC_REVERSE_PORT_REMOVED={port}")
            except (RuntimeError, subprocess.TimeoutExpired) as error:
                print(f"WARNING: could not remove HDC port mapping: {error}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"HARMONY_TEST_FAIL={error}", file=sys.stderr)
        raise SystemExit(1)
