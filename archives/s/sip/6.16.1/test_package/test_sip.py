#!/usr/bin/env python3
"""Consumer test for the packaged sip.

Runs against the installed package (not the source tree) to prove the
site-packages layout plus the generated bin/ entry points actually work:
the module must import and the CLIs must execute.
"""
import os
import subprocess
import sys


def main(pkg):
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    assert os.path.isdir(site), site
    sys.path.insert(0, site)

    import sipbuild
    from sipbuild.version import SIP_VERSION, SIP_VERSION_STR

    print("sip version:", SIP_VERSION_STR)
    assert SIP_VERSION_STR.startswith("6.16"), SIP_VERSION_STR
    # The public API surface used by PyQt-builder.
    from sipbuild import Bindings, Project, UserException  # noqa: F401
    from sipbuild.api import build_wheel, build_sdist  # noqa: F401
    print("sipbuild public API importable")

    bindir = os.path.join(pkg, "bin")
    tools = ("sip-build", "sip-install", "sip-wheel", "sip-sdist",
             "sip-module", "sip-distinfo")
    env = dict(os.environ)
    # Keep the inherited PYTHONPATH (the graph deps' site-packages — the CI
    # interpreter lacks setuptools/packaging globally) and add ours on top.
    env["PYTHONPATH"] = os.pathsep.join(
        [site] + [p for p in [env.get("PYTHONPATH", "")] if p])
    for t in tools:
        exe = os.path.join(bindir, t)
        assert os.path.isfile(exe), exe
        assert os.access(exe, os.X_OK), "%s not executable" % exe
        r = subprocess.run([exe, "--help"], capture_output=True, text=True,
                           env=env, timeout=120)
        blob = r.stdout + r.stderr
        assert r.returncode == 0, (t, r.returncode, blob[:400])
        assert "usage" in blob.lower(), (t, blob[:200])
    print("all 6 sip CLI tools execute (%d checked)" % len(tools))

    print("SIP-CONSUMER-OK")


main(sys.argv[1] if len(sys.argv) > 1 else sys.argv[0])
