#!/usr/bin/env python3
"""Conan recipe — librnd 4.5.0 (custom scconfig Makefile)"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibrndConan(ConanFile):
    name = "librnd"
    version = "4.5.0"
    description = "Modular 2D CAD framework powering pcb-rnd and Ringdove EDA tools"
    license = "GPL-2.0-or-later"
    homepage = "http://repo.hu/projects/librnd"
    url = "http://repo.hu/projects/librnd"
    topics = ("cad", "eda", "pcb-rnd", "2d-graphics")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)
        # scconfig configure: not GNU autotools. It auto-disables GUI features
        # whose dependencies are missing (warnings only); the explicit
        # --disable-* flags below make the headless OHOS build deterministic.
        # NOTE: upstream only serves plain http (https handshake fails), so the
        # conandata URL intentionally uses the official http source.
        config_shell = os.environ.get("CONFIG_SHELL", "bash")
        configure_args = [
            "--prefix=/",
            "--disable-hid_gtk2_gdk",
            "--disable-hid_gtk2_gl",
            "--disable-hid_gtk4_gl",
            "--disable-hid_lesstif",
            "--disable-gd",
            "--disable-gd-gif",
            "--disable-gd-png",
            "--disable-gd-jpg",
            "--disable-stroke",
            "--disable-xrender",
            "--disable-xinerama",
        ]
        self._fix_helper_install(
            os.path.join(self.source_folder, "src", "Makefile.in")
        )
        self.run(
            "%s ./configure %s" % (config_shell, " ".join(configure_args)),
            cwd=self.source_folder,
        )
        # The generated src/Makefile is rendered from Makefile.in by
        # configure; rewrite it as well in case generation normalizes
        # whitespace around the helper install lines.
        self._fix_helper_install(
            os.path.join(self.source_folder, "src", "Makefile")
        )
        # R9: always -j1, never parallel.
        self.run("make -j1", cwd=self.source_folder)
        self._run_upstream_tests()

    def _fix_helper_install(self, path):
        # HMBS/OHOS: `make install` runs `../scconfig/sccbox install -f`
        # to copy the just-built ELF helpers (puplug/sphash/cquote and
        # sccbox itself). Preflight package() hit
        # `/bin/sh: ../scconfig/sccbox: Operation not permitted` + make
        # Error 126 on the sccbox self-copy line: exec of the freshly
        # built sccbox from the conan cache is denied on HMDFS (E077
        # family; platform caps report chmod:0/hardlink:0). Header and
        # archive copies via sccbox kept working, so only the 4 ELF
        # helper lines are rewritten to `cp -p` + best-effort
        # `chmod 755 || true` (chmod is a no-op where unsupported).
        # Done here in Python (not as a conandata patch) because the
        # conan patcher verifies hunk context strictly and rejected the
        # equivalent Makefile.in patch on-device.
        import io
        try:
            with io.open(path, "r", encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines(True)
        except OSError:
            return
        repl = {
            "../src_3rd/puplug/util/puplug": (
                '../src_3rd/puplug/util/puplug',
                '"$(HL_LIBDIR)/librnd4/puplug"',
            ),
            "$(SPHASH)": (
                '"$(SPHASH)"',
                '"$(HL_LIBDIR)/librnd4/sphash"',
            ),
            "../scconfig/cquote": (
                '"../scconfig/cquote"',
                '"$(HL_LIBDIR)/librnd4/scconfig/cquote"',
            ),
            "../scconfig/sccbox": (
                '"../scconfig/sccbox"',
                '"$(HL_LIBDIR)/librnd4/scconfig/sccbox"',
            ),
        }
        changed = 0
        out = []
        for line in lines:
            stripped = line.lstrip()
            indent = line[: len(line) - len(stripped)]
            if "$(SCCBOX)" in stripped and "$(HOW)" in stripped:
                hit = None
                for key in repl:
                    if key in stripped:
                        hit = key
                        break
                if hit is not None:
                    src, dst = repl[hit]
                    if not src.startswith('"'):
                        src = '"%s"' % src
                    out.append(
                        "%scp -p %s %s; chmod 755 %s || true\n"
                        % (indent, src, dst, dst)
                    )
                    changed += 1
                    continue
            out.append(line)
        if changed:
            with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.writelines(out)
        self.output.info(
            "librnd helper-install rewrite: %d line(s) in %s" % (changed, path)
        )

    def _run_upstream_tests(self):
        # Upstream unit: the 5 subdirectories run by tests/Makefile's
        # `test` target (rnd_printf, remote, librnd, conf, base64).
        # Four suites print "*** QC PASS ***" on success (rnd_printf with
        # "pcb-printf:" prefix, remote with "remote:", conf with "conf:",
        # base64 as a bare "*** QC PASS ***" line). tests/librnd/Makefile's
        # `test` target has NO QC line — it just runs ./librnd_test --gui
        # batch && ./librnd_includes and relies on exit code 0. The top-level
        # tests/Makefile runs the 5 suites sequentially and only prints the
        # final "All tests passed, librnd is safe to install." banner when
        # every prior suite succeeded, so that banner (plus the presence of
        # downstream conf/base64 QC lines, which prove make got past the
        # librnd stage) is the deterministic log evidence for the librnd
        # suite — not a returncode-based guess.
        log_path = os.path.join(self.build_folder, "upstream-make-test.log")
        command = 'make test > "%s" 2>&1' % log_path
        error = None
        try:
            self.run(command, cwd=self.source_folder)
        except Exception as exc:
            error = exc

        content = ""
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            self.output.info("Upstream make test output:\n%s" % content)

        lines = content.splitlines()
        rnd_ok = any("pcb-printf:" in l and "*** QC PASS ***" in l for l in lines)
        remote_ok = any("remote:" in l and "*** QC PASS ***" in l for l in lines)
        conf_ok = any("conf:" in l and "*** QC PASS ***" in l for l in lines)
        base64_ok = any(l.strip() == "*** QC PASS ***" for l in lines)
        banner_ok = "All tests passed" in content
        # librnd suite evidence: final banner, or proof that make proceeded
        # to conf/base64 after the librnd stage. The `error is None and 4
        # QCs` clause only fires when every QC suite passed and make exited
        # 0, which by make's sequential semantics means librnd also passed.
        librnd_ok = bool(
            banner_ok
            or conf_ok
            or base64_ok
            # make runs suites sequentially; reaching the conf/base64 stage
            # proves the librnd stage exited 0 even when a later suite fails.
            or "cd conf" in content
            or "cd base64" in content
            or (
                error is None
                and rnd_ok
                and remote_ok
                and conf_ok
                and base64_ok
            )
        )
        passed = sum([rnd_ok, remote_ok, librnd_ok, conf_ok, base64_ok])
        discovered = 5
        failed = 0 if error is None else 1
        if passed > discovered:
            passed = discovered
        executed = passed + failed
        skipped = discovered - executed
        if skipped < 0:
            skipped = 0
            executed = discovered
        result = {
            "status": "passed" if error is None and passed == discovered else "failed",
            "framework": "make",
            "command": "make test",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
        print(marker, flush=True)
        self.output.info(marker)
        if error is not None:
            raise ConanException("upstream make test failed: %s" % error)
        if passed != discovered:
            raise ConanException(
                "upstream make test evidence mismatch: expected %d QC PASS, got %d"
                % (discovered, passed)
            )

    def _ensure_helper_exec(self):
        # HMBS/OHOS: just-built sccbox/cquote/puplug/sphash are ELF helpers
        # executed from the conan cache during `make install`. On HMDFS they
        # need +x and a valid .codesign (E077 family); preflight package()
        # hit `/bin/sh: ../scconfig/sccbox: Operation not permitted` (Error
        # 126). Best-effort chmod + self-sign; the 4 ELF helper install
        # lines are additionally rewritten to cp in _fix_helper_install,
        # so install still works even if the sccbox exec stays denied.
        import shutil
        helpers = [
            os.path.join(self.source_folder, "scconfig", "sccbox"),
            os.path.join(self.source_folder, "scconfig", "cquote"),
            os.path.join(self.source_folder, "src_3rd", "puplug", "util", "puplug"),
            os.path.join(self.source_folder, "src_3rd", "sphash", "sphash"),
        ]
        for path in helpers:
            if not os.path.isfile(path):
                continue
            try:
                os.chmod(path, 0o755)
            except Exception:
                pass
            try:
                sign_tool = shutil.which("binary-sign-tool")
                objcopy = shutil.which("llvm-objcopy")
                if sign_tool and objcopy:
                    self.run(
                        'llvm-objcopy --remove-section .codesign "%s" 2>/dev/null || true' % path,
                        cwd=self.source_folder,
                    )
                    self.run(
                        '%s sign -inFile "%s" -outFile "%s.signed" -selfSign 1' % (sign_tool, path, path),
                        cwd=self.source_folder,
                    )
                    try:
                        os.replace(path + ".signed", path)
                    except Exception:
                        pass
                    try:
                        os.chmod(path, 0o755)
                    except Exception:
                        pass
            except Exception:
                pass

    def package(self):
        # scconfig install honors DESTDIR + PREFIX (see tests/librnd/Makefile
        # staged-install usage). PREFIX=/ puts headers under include/librnd4
        # and libraries under lib inside the package folder.
        self._ensure_helper_exec()
        self.run(
            "make install DESTDIR=%s PREFIX=/" % self.package_folder,
            cwd=self.source_folder,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = [
            "librnd-hid",
            "librnd-font2",
            "librnd-font",
            "librnd-polybool2",
            "librnd-polybool",
            "librnd-poly",
            "librnd-core",
            "librnd-3rd",
        ]
        # Headers install to include/librnd4/librnd/... and upstream code
        # includes them as <librnd/core/xxx.h> (see librnd.mak LIBRND_INCDIR).
        self.cpp_info.includedirs = ["include/librnd4"]
        self.cpp_info.set_property("cmake_file_name", "librnd")
        self.cpp_info.set_property("cmake_target_name", "librnd::librnd")
        self.cpp_info.set_property("pkg_config_name", "librnd")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
