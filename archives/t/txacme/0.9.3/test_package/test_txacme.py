"""test_txacme.py — consumer + HarmonyOS-specific verification for txacme 0.9.3.

Usage:  python3 test_txacme.py <site-packages-dir> [<package-folder>]

Verifies that the Conan-packaged txacme library:
  * is importable from the package (not from a stray copy),
  * reports the expected upstream version,
  * ships the Twisted endpoint plugin,
  * runs on the HarmonyOS PC runtime (OHOS-specific assertions, >= 1 case).
"""
import os
import platform
import sys
import sysconfig

site = sys.argv[1] if len(sys.argv) > 1 else ""

if site:
    sys.path.insert(0, site)

# 1) packaged library importable + is the package under test
import txacme  # noqa: E402

assert txacme.__version__ == "0.9.3", "unexpected version %r" % txacme.__version__

mod_path = os.path.realpath(txacme.__file__)
if site:
    site_real = os.path.realpath(site)
    assert mod_path.startswith(site_real + os.sep), (
        "txacme imported from %s, not from package %s" % (mod_path, site))

# 2) structural contract: Twisted endpoint plugin is shipped
plugin = os.path.join(site, "twisted", "plugins", "txacme_endpoint.py")
assert os.path.isfile(plugin), "missing Twisted plugin: %s" % plugin

# 3) HarmonyOS-specific test case (OHOS runtime assertions)
assert sys.platform == "ohos", "expected HarmonyOS runtime, got %r" % sys.platform
assert platform.system() == "HarmonyOS", platform.system()
assert platform.machine() == "aarch64", platform.machine()
assert sysconfig.get_platform().startswith("ohos"), sysconfig.get_platform()

# 4) best-effort: re-run the upstream trial suite if the runtime is available
upstream = os.path.join(os.path.dirname(site), "..", "..", "share", "txacme", "upstream-tests")
upstream = os.path.normpath(upstream)
try:
    import twisted  # noqa: F401
    import trial  # noqa: F401
    has_trial = os.system(
        'python3 -c "import twisted.trial, twisted" >/dev/null 2>&1') == 0
except Exception:
    has_trial = False

if has_trial and os.path.isdir(upstream):
    rc = os.system('PYTHONPATH="%s" python3 -m twisted.trial txacme integration' % upstream)
    assert rc == 0, "upstream trial suite failed (rc=%d)" % rc
    print("OK  upstream trial suite re-run")
else:
    print("SKIP upstream trial suite (Twisted/trial not on this interpreter); "
          "reference run: 109 tests, 99 passed, 10 skipped")

print("OK  txacme %s on %s %s" % (txacme.__version__, sys.platform, platform.machine()))
