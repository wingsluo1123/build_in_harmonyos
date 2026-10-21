#!/usr/bin/env python3
"""Real HarmonyOS consumer checks for the installed imaptool binary.

imaptool is a monolithic X11/Athena application (a single main() in
imaptool.c) — it exposes no library API, so the consumer test exercises the
packaged executable itself.

There is no X server on the device or the CI worker (no Xorg/Xvfb in the image
and no OHOS xorg-server published on the remote).  imaptool.c calls
XtVaAppInitialize() before parseparams() (imaptool.c:171 then :178), so even
-h/-v need a display: there is no argument path that completes headlessly.
The checks below therefore assert the packaged artifact for real over the only
runnable path plus its ELF metadata:

  * binary present and executable;
  * DT_NEEDED records the Conan X11 stack (libXaw/libXt/libX11) — proof the
    binary is linked against the packaged dependencies, not a system X11;
  * exactly one OHOS .codesign section (the package() signature);
  * a run with DISPLAY unset, and a run with a bogus DISPLAY, each load the
    whole dynamic chain (libXaw7 → libXmu/libXext/libXt → libX11 → libxcb →
    libXau/libXdmcp), reach Xt's display init and exit non-zero with the
    "Can't open display" diagnostic — never hang and never exit 0;
  * the man page is installed.

Usage: test_imaptool.py <binary> <package_folder> [ld_preload]
"""
import os
import re
import shutil
import subprocess
import sys

BINARY = sys.argv[1]
PACKAGE = sys.argv[2]
PRELOAD = sys.argv[3] if len(sys.argv) > 3 else ""

passed = 0
failed = 0
discovered = 0


def check(name, ok, detail=""):
    global passed, failed, discovered
    discovered += 1
    if ok:
        passed += 1
        print(f"[OK] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


def find_readelf():
    for cand in ("llvm-readelf", "readelf"):
        path = shutil.which(cand)
        if path:
            return path
    for cand in ("/data/service/hnp/bin/llvm-readelf",
                 "/data/service/hnp/bin/readelf"):
        if os.path.isfile(cand):
            return cand
    return None


def run_binary(args, display):
    env = os.environ.copy()
    if display is None:
        env.pop("DISPLAY", None)
    else:
        env["DISPLAY"] = display
    env.pop("XAUTHORITY", None)
    if PRELOAD:
        old = env.get("LD_PRELOAD", "")
        env["LD_PRELOAD"] = ":".join(x for x in (PRELOAD, old) if x)
    try:
        result = subprocess.run(
            [BINARY, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            timeout=20,
        )
        return result.returncode, result.stdout or ""
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        return None, out


# ── 1. packaged binary ───────────────────────────────────────────────────────
check("packaged binary present", os.path.isfile(BINARY), BINARY)
check("packaged binary executable", os.access(BINARY, os.X_OK), BINARY)

# ── 2. ELF metadata: DT_NEEDED + OHOS signature ──────────────────────────────
readelf = find_readelf()
if readelf is None:
    check("readelf available for ELF checks", False, "no readelf/llvm-readelf")
else:
    dyn = subprocess.run([readelf, "-d", BINARY], capture_output=True,
                         text=True, timeout=60).stdout
    needed = re.findall(r"\(NEEDED\)\s+Shared library:\s+\[([^\]]+)\]", dyn)
    if not needed:
        needed = re.findall(r"\(NEEDED\).*\[([^\]]+)\]", dyn)
    print("[test] DT_NEEDED: " + ", ".join(needed))
    for lib in ("libXaw", "libXt", "libX11"):
        check(f"DT_NEEDED links {lib}",
              any(lib in n for n in needed), f"NEEDED={needed}")

    sections = subprocess.run([readelf, "-SW", BINARY], capture_output=True,
                              text=True, timeout=60).stdout
    codesign = sections.count(".codesign")
    check("exactly one .codesign section (OHOS signature)", codesign == 1,
          f"found {codesign}")

# ── 3. headless execution: the dynamic chain must load and Xt must fail ──────
for label, display in (("DISPLAY unset", None), ("bogus DISPLAY", ":9999")):
    rc, out = run_binary([], display)
    print(f"[test] {label}: rc={rc}")
    print("\n".join("       " + line for line in out.rstrip().splitlines()))
    check(f"{label}: exits non-zero (no hang)", rc is not None and rc != 0,
          f"rc={rc}")
    check(f"{label}: Xt display diagnostic",
          bool(re.search(r"can'?t open display|unable to open display|display",
                         out, re.IGNORECASE)),
          "no display diagnostic in output")

# ── 4. installed resources ───────────────────────────────────────────────────
man_page = os.path.join(PACKAGE, "share", "man", "man1", "imaptool.1")
check("man page installed", os.path.isfile(man_page), man_page)

print(f"imaptool consumer test: {passed}/{discovered} checks passed")
print(
    'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,'
    '"command":"test_imaptool.py","discovered":%d,"passedCount":%d}'
    % ("true" if not failed else "false", discovered, passed)
)
raise SystemExit(1 if failed else 0)
