import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class IfmailTestConan(ConanFile):
    """Consumer test for the packaged ifmail suite (14 executables).

    Two shell drivers run against the installed binaries through the conanrun
    environment:

      test_ifmail.sh      - CLI contract of every packaged executable, the
                            documented error exits, and an end-to-end nodelist
                            index round trip (ifindex -> nlookup) with a
                            byte-exact expected output. 20 check items.
      test_ifmail_ohos.sh - the two HarmonyOS-specific adaptation points:
                            ndbm served by libgdbm_compat on this filesystem,
                            and the K&R varargs -> C99 stdarg conversion
                            verified through four different format
                            signatures. 12 check items.

    Fixtures (config template, nodelist, expected nlookup output) are committed
    next to the scripts; both drivers take their work directory as an argument
    and never touch /tmp (read-only under HMDFS).

    When this recipe is built as a cross build the packaged binaries are OHOS
    ELF and cannot execute on the host, so the drivers are skipped after the
    package layout has been asserted (can_run() honours
    tools.build.cross_building:can_run, which the ohos-local dev profile sets
    to False; the native OHOS CI worker runs everything).
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_ifmail.sh", "test_ifmail_ohos.sh", "fixtures/*"

    # Same list as conanfile.py:_BINDIR_OBJS, spelled out so a missing or
    # renamed artifact fails here instead of silently passing.
    _EXPECTED_BINARIES = (
        "ifcico", "ifindex", "ifinfo", "ifreq", "ifroute", "nlpatch",
        "nlookup", "ifmail", "ifnews", "iftoss", "ifpack", "ifunpack",
        "ifstat", "make_new_ref",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    @staticmethod
    def _resolve_shell():
        """A shell that exists on the machine running the test.

        OHOS /system/bin/sh (mksh) cannot exec ELF binaries, so the drivers are
        wrapped with bash; CONFIG_SHELL is the repo-wide convention but the
        configured path only exists on the worker.
        """
        for cand in (os.environ.get("CONFIG_SHELL"),
                     "/data/service/hnp/bin/bash",
                     shutil.which("bash"),
                     "/bin/bash", "/bin/sh"):
            if cand and os.path.exists(cand):
                return cand
        return "sh"

    def test(self):
        package_folder = self.dependencies["ifmail"].package_folder
        bindir = os.path.join(package_folder, "bin")
        missing = [b for b in self._EXPECTED_BINARIES
                   if not os.path.isfile(os.path.join(bindir, b))]
        if missing:
            raise AssertionError(
                "missing packaged executables in %s: %s" % (bindir, ", ".join(missing))
            )
        # MAPTABDIR is baked into the binaries at compile time, so the charset
        # tables have to be exactly there.
        maptabs = os.path.join(package_folder, "share", "ifmail", "maptabs")
        if not os.path.isdir(maptabs) or not os.listdir(maptabs):
            raise AssertionError("maptabs not packaged at %s" % maptabs)
        self.output.info("package layout OK: %d executables in %s, maptabs present"
                         % (len(self._EXPECTED_BINARIES), bindir))

        if not can_run(self):
            self.output.warning(
                "can_run() is False in this configuration (OHOS binaries cannot "
                "execute on this host): package layout verified, the two test "
                "drivers are NOT executed here. The native OHOS CI worker runs "
                "test_ifmail.sh (20 items) and test_ifmail_ohos.sh (12 items)."
            )
            return

        bash = self._resolve_shell()
        for script in ("test_ifmail.sh", "test_ifmail_ohos.sh"):
            path = os.path.join(self.source_folder, script)
            work = os.path.join(
                self.build_folder, script[: -len(".sh")] + "-work"
            )
            self.run('"%s" "%s" "%s"' % (bash, path, work), env="conanrun")
