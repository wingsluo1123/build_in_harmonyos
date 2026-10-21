import json
import os

from conan import ConanFile


def _pick_shell(conanfile):
    # OHOS /system/bin/sh (mksh) cannot execute ELF binaries (exit 127),
    # so prefer a real bash. HMBS injects SHELL=/bin/sh, which defeats the
    # template default `CONFIG_SHELL or hnp-bash` when CONFIG_SHELL=/bin/sh.
    candidates = [
        "/data/service/hnp/bin/bash",
        os.environ.get("CONFIG_SHELL", ""),
        os.environ.get("SHELL", ""),
        "/bin/sh",
        "bash",
        "sh",
    ]
    hnp_bash = "/data/service/hnp/bin/bash"
    if os.path.isfile(hnp_bash) and os.access(hnp_bash, os.X_OK):
        conanfile.output.info("test shell: %s (preferred hnp bash)" % hnp_bash)
        return hnp_bash
    for cand in candidates:
        if not cand:
            continue
        if os.path.isabs(cand):
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                conanfile.output.info("test shell: %s" % cand)
                return cand
        else:
            conanfile.output.info("test shell: %s (PATH lookup)" % cand)
            return cand
    return "/bin/sh"


def _script_path(conanfile):
    # Do not rely on cwd containing test.sh; resolve an absolute path.
    for cand in (
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh"),
        os.path.join(getattr(conanfile, "source_folder", "") or "", "test.sh"),
        "test.sh",
    ):
        if os.path.isfile(cand):
            return cand
    return "test.sh"


class MfocTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = _pick_shell(self)
        script = _script_path(self)
        self.output.info("test script: %s" % script)
        mfoc_bin = ""
        try:
            ref_name = self.tested_reference_str.split("/")[0]
            dep = self.dependencies[ref_name]
            candidates = [
                os.path.join(dep.package_folder, "bin", "mfoc"),
                os.path.join(dep.package_folder, "mfoc"),
            ]
            for cand in candidates:
                if os.path.isfile(cand):
                    mfoc_bin = cand
                    self.output.info("mfoc candidate found: %s" % cand)
                    break
            if not mfoc_bin or not os.path.exists(mfoc_bin):
                self.output.warning("mfoc not found in package_folder %s" % dep.package_folder)
                try:
                    for root, dirs, files in os.walk(dep.package_folder):
                        self.output.info("  %s: %s" % (root, files))
                        if root.count(os.sep) - dep.package_folder.count(os.sep) > 2:
                            break
                except Exception as e:
                    self.output.warning("walk failed: %s" % e)
            else:
                try:
                    os.chmod(mfoc_bin, 0o755)
                except Exception:
                    pass
                self.output.info("using mfoc via package_folder: %s" % mfoc_bin)
        except Exception as e:
            self.output.warning("could not resolve mfoc package_folder: %s" % e)

        actual_cmd = '%s "%s" "%s"' % (bash, script, mfoc_bin) if (mfoc_bin and os.path.isfile(mfoc_bin)) else '%s "%s"' % (bash, script)
        discovered = 1
        passed = 0
        try:
            if mfoc_bin and os.path.isfile(mfoc_bin):
                os.environ["CONAN_MFOC_BIN"] = mfoc_bin
                self.run('%s "%s" "%s"' % (bash, script, mfoc_bin), env="conanrun")
            else:
                self.output.warning("falling back to PATH search in test.sh")
                self.run('%s "%s"' % (bash, script), env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: %s" % exc)
            raise
        finally:
            try:
                tp_marker = {
                    "executed": True,
                    "passed": passed == discovered,
                    "command": actual_cmd,
                    "discovered": discovered,
                    "passedCount": passed,
                }
                tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False)
                print(tp_msg, flush=True)
                self.output.info(tp_msg)
            except Exception:
                pass
            try:
                upstream = {
                    "status": "no_tests",
                    "framework": "autotools",
                    "command": "make check",
                    "discovered": 0,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "mfoc-0.10.7-git20180724 audited: configure.ac/Makefile.am/src/Makefile.am have no TESTS/check_PROGRAMS; tarball ba072f1 contains no tests/ dir and no test source files; make check is automake default empty target",
                }
                up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
                print(up_msg, flush=True)
                self.output.info(up_msg)
            except Exception:
                pass
        if passed != discovered:
            from conan.errors import ConanException

            raise ConanException("test_package smoke tests failed")
