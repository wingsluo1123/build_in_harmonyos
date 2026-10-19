#!/usr/bin/env python3
"""Run meinproc6/checkXML6 on HarmonyOS and verify real DocBook behaviour.

Cases:
  1. packaged meinproc6 and checkXML6 exist and are executable
  2. meinproc6 --version runs
  3. installed KDocTools customization data (catalog.xml, dtd, xsl) is present
  4. installed all-l10n.xml catalog is non-empty (docbookl10nhelper
     output under the installed customization root; patch 0004 writes a
     minimal fallback stub when the DocBook XSL data is absent)
  5. a real DocBook XML -> HTML transform with the identity stylesheet
     produces the expected marker
  6. checkXML6 accepts valid XML (embedded DTD)
  7. checkXML6 rejects malformed XML (non-zero exit)
"""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MARKER = "HARMONYOS_KDOCTOOLS6_DOCBOOK_TRANSFORM_OK"

_results = []


def record(name, ok, detail=""):
    _results.append((name, bool(ok)))
    print(
        "{} {} — {}".format("TEST PASS:" if ok else "TEST FAIL:", name, detail)
    )
    return bool(ok)


def _run(cmd, env, cwd, timeout=60):
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _first_line(text):
    text = text.strip()
    return text.splitlines()[0] if text else "no output"


def _main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_ohos_docbook.py PACKAGE_FOLDER")

    system = platform.uname()
    if system.system != "HarmonyOS" and "HongMeng" not in system.version:
        raise RuntimeError(
            "This integration test must execute on a HarmonyOS device; "
            "reported system={!r}, version={!r}".format(system.system, system.version)
        )

    package = Path(sys.argv[1]).resolve()
    meinproc = package / "bin" / "meinproc6"
    checkxml = package / "bin" / "checkXML6"

    # HarmonyOS PC SSH users may not have permission to write /data/local/tmp.
    # Prefer the caller's TMPDIR, then the writable per-user tmp directory and
    # finally Python's platform-selected temporary directory.
    candidates = [
        Path(os.environ["TMPDIR"]) if os.environ.get("TMPDIR") else None,
        Path.home() / "tmp",
        Path(tempfile.gettempdir()),
    ]
    temp_root = next(
        (
            candidate
            for candidate in candidates
            if candidate is not None
            and candidate.is_dir()
            and os.access(candidate, os.W_OK)
        ),
        None,
    )
    if temp_root is None:
        raise RuntimeError("No writable HarmonyOS temporary directory was found")
    work = Path(tempfile.mkdtemp(prefix="kdoctools6-ohos-", dir=str(temp_root)))

    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([str(package / "bin"), env.get("PATH", "")])
    env["TMPDIR"] = str(work)
    env["XDG_DATA_HOME"] = str(work / "xdg-data")
    env["XDG_DATA_DIRS"] = os.pathsep.join(
        part
        for part in (str(package / "share"), env.get("XDG_DATA_DIRS", ""))
        if part
    )

    fixtures = Path(__file__).resolve().parent / "fixtures"

    try:
        record(
            "packaged meinproc6 and checkXML6 are executable",
            meinproc.is_file()
            and os.access(meinproc, os.X_OK)
            and checkxml.is_file()
            and os.access(checkxml, os.X_OK),
            "{} / {}".format(meinproc, checkxml),
        )

        version = _run([str(meinproc), "--version"], env, work)
        record(
            "meinproc6 --version runs",
            version.returncode == 0
            and bool((version.stdout + version.stderr).strip()),
            _first_line(version.stdout + version.stderr),
        )

        catalogs = [
            path
            for path in package.rglob("catalog.xml")
            if path.parent.name == "customization"
            and path.parent.parent.name == "kdoctools"
        ]
        kdoctools_data = catalogs[0].parent.parent if catalogs else None
        record(
            "installed KDocTools customization data is present",
            kdoctools_data is not None
            and (kdoctools_data / "customization" / "dtd").is_dir()
            and (kdoctools_data / "customization" / "xsl").is_dir(),
            str(kdoctools_data),
        )

        l10n = (
            kdoctools_data / "customization" / "xsl" / "all-l10n.xml"
            if kdoctools_data is not None
            else None
        )
        l10n_ok = l10n is not None and l10n.is_file() and l10n.stat().st_size > 0
        l10n_detail = (
            "{} bytes".format(l10n.stat().st_size)
            if l10n is not None and l10n.is_file()
            else "missing"
        )
        if l10n_ok:
            l10n_text = l10n.read_text(encoding="utf-8", errors="replace")
            # the helper roots the catalog at <l:i18n>; the data-absent
            # fallback written by patch 0004 is a minimal <l10n/> stub
            l10n_ok = "<l:i18n" in l10n_text or "<l10n" in l10n_text
        record("installed all-l10n.xml catalog is non-empty", l10n_ok, l10n_detail)

        if kdoctools_data is None:
            for name in (
                "DocBook XML -> HTML transform produces the marker",
                "checkXML6 accepts valid XML",
                "checkXML6 rejects malformed XML",
            ):
                record(name, False, "KDocTools customization data missing")
        else:
            output_html = work / "rendered.html"
            transform = _run(
                [
                    str(meinproc),
                    "--stylesheet",
                    str(fixtures / "identity.xsl"),
                    "--srcdir",
                    str(kdoctools_data),
                    "--output",
                    str(output_html),
                    str(fixtures / "article.xml"),
                ],
                env,
                work,
            )
            rendered = (
                output_html.read_text(encoding="utf-8", errors="replace")
                if output_html.is_file()
                else ""
            )
            record(
                "DocBook XML -> HTML transform produces the marker",
                transform.returncode == 0 and MARKER in rendered,
                "exit {}, output {} bytes".format(
                    transform.returncode, len(rendered)
                ),
            )

            valid = _run(
                [str(checkxml), str(fixtures / "checkxml-valid.xml")], env, work
            )
            record(
                "checkXML6 accepts valid XML",
                valid.returncode == 0,
                "exit {}, {}".format(valid.returncode, _first_line(valid.stderr)),
            )

            malformed = _run(
                [str(checkxml), str(fixtures / "checkxml-malformed.xml")], env, work
            )
            record(
                "checkXML6 rejects malformed XML",
                malformed.returncode != 0,
                "exit {}".format(malformed.returncode),
            )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    print(
        "TEST SUMMARY: {}/{} passed, {} failed".format(
            passed, total, total - passed
        )
    )
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    _main()
