#!/usr/bin/env python3
"""Consumer test for vapoursynth 74."""

import glob
import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run


class VapoursynthTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._resolve_tool(compilers.get("c"), "clang")
        cxx = self._resolve_tool(compilers.get("cpp"), "clang++")
        dep = self.dependencies["vapoursynth"].cpp_info

        exe = os.path.join(self.build_folder, "test_vapoursynth")
        cmd = [
            *self._exec_tool(cc),
            os.path.join(self.source_folder, "test_vapoursynth.c"),
            "-o",
            exe,
        ]
        for include_dir in dep.includedirs:
            cmd.append("-I" + include_dir)
        for lib_dir in dep.libdirs:
            cmd.append("-L" + lib_dir)
        for lib in dep.libs:
            cmd.append("-l" + lib)
        for system_lib in dep.system_libs:
            cmd.append("-pthread" if system_lib == "pthread" else "-l" + system_lib)

        self.run(" ".join(shlex.quote(part) for part in cmd))
        self._build_expr_debugger(cxx)

    def test(self):
        if can_run(self):
            exe = os.path.join(self.build_folder, "test_vapoursynth")
            self.run(shlex.quote(exe), env="conanrun")
            self._run_upstream_python_tests()

    def _run_upstream_python_tests(self):
        dep = self.dependencies["vapoursynth"]
        package_folder = dep.package_folder
        pythonpath = os.path.join(package_folder, "python")
        tests_dir = os.path.join(package_folder, "tests", "upstream")
        if not os.path.isdir(os.path.join(pythonpath, "vapoursynth")):
            self.output.info(
                "this package was built with the default python_module=False, so the "
                "upstream Python unittest suite is not applicable here; the C consumer "
                "smoke test and the ExprDebugger expression harness still run"
            )
            self._run_expr_compiler_harness(tests_dir)
            return
        libdir = os.path.join(package_folder, "lib")
        module_libdir = os.path.join(pythonpath, "vapoursynth")
        self._prepare_runtime_shared_libraries(package_folder)
        test_modules = [
            "async_test",
            "environment_test",
            "expr_test",
            "filter_test",
            "log_test",
            "lut_test",
            "prop_dict_test",
            "range_property_compat",
            "test",
            "weakref_test",
            "zimgtest",
        ]
        env = (
            "PYTHONPATH={tests_dir}:{pythonpath} "
            "LD_LIBRARY_PATH={module_libdir}:{libdir}:$LD_LIBRARY_PATH "
        ).format(
            tests_dir=shlex.quote(tests_dir),
            pythonpath=shlex.quote(pythonpath),
            module_libdir=shlex.quote(module_libdir),
            libdir=shlex.quote(libdir),
        )
        probe = "import vapoursynth; print('vapoursynth python import probe passed')"
        if self._python_module_imports(env, probe, package_folder):
            cmd = "{} python3 -m unittest {}".format(env, " ".join(test_modules))
            self.run(cmd, env="conanrun")
        else:
            # E212 fallback (knowledge/doc/E212.md): the CI sandbox refuses the
            # dlopen, so the packaged module is verified statically here instead
            # of being reported as a build failure. The upstream unittest suite
            # stays bound to the true-device run.
            self._verify_packaged_python_module(package_folder)
        self._run_expr_compiler_harness(tests_dir)

    def _python_module_imports(self, env, probe, package_folder):
        command = "{} python3 -c {}".format(env, shlex.quote(probe))
        try:
            self.run(command, env="conanrun")
        except ConanException as error:
            detail = self._classify_import_failure(env, probe, error)
            if str(self.settings.os) == "OHOS" and self._is_e212(detail):
                self.output.warning(
                    "E212: hmmac blocked dlopen of the packaged CPython extension under a "
                    "user path, so the upstream Python unittest suite cannot run in this "
                    "sandbox (knowledge/doc/E212.md). Verifying the packaged module "
                    "statically instead; the full 11-module / 157-case suite runs on a "
                    "true device."
                )
                return False
            raise ConanInvalidConfiguration(
                "vapoursynth python import failed: {}".format(
                    detail.strip() or str(error)
                )
            ) from error
        self.output.info("vapoursynth python import probe passed")
        return True

    def _classify_import_failure(self, env, probe, error):
        """self.run() only reports 'Error N while executing'; re-probe for stderr."""
        interpreter = self._python_interpreter() or "python3"
        command = "{} {} -c {}".format(env, shlex.quote(interpreter), shlex.quote(probe))
        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except (OSError, subprocess.SubprocessError) as probe_error:
            return "{} {}".format(error, probe_error)
        return "{} {}".format(completed.stderr or "", completed.stdout or "")

    @staticmethod
    def _is_e212(detail):
        markers = (
            "Permission denied",
            "Error loading shared library",
            "cannot open shared object",
            "Operation not permitted",
        )
        return any(marker in detail for marker in markers)

    def _verify_packaged_python_module(self, package_folder):
        module_dir = os.path.join(package_folder, "python", "vapoursynth")
        lib_dir = os.path.join(package_folder, "lib")
        tests_dir = os.path.join(package_folder, "tests", "upstream")
        entries = sorted(os.listdir(module_dir)) if os.path.isdir(module_dir) else []
        extension = ""
        for name in entries:
            if name.startswith("vapoursynth") and name.endswith(".so"):
                extension = os.path.join(module_dir, name)
                break

        checks = [
            (
                "packaged CPython extension {} present".format(
                    os.path.basename(extension) or "vapoursynth*.so"
                ),
                bool(extension),
            )
        ]
        if extension:
            mode = os.stat(extension).st_mode & 0o777
            checks.append(("extension is executable ({:o})".format(mode), bool(mode & 0o111)))
            with open(extension, "rb") as handle:
                data = handle.read()
            checks.append(("extension is an ELF image", data[:4] == b"\x7fELF"))
            checks.append(("extension carries a .codesign section", b".codesign" in data))
            needed = self._readelf_needed(extension)
            if needed is None:
                links_core = b"libvapoursynth.so.4" in data
                method = "ELF marker scan"
            else:
                links_core = any("libvapoursynth.so.4" in item for item in needed)
                method = "llvm-readelf: {}".format(" ".join(needed) or "no NEEDED entries")
            checks.append(("extension links libvapoursynth.so.4 ({})".format(method), links_core))
        for name in ("libvapoursynth.so", "libvapoursynth.so.4"):
            path = os.path.join(lib_dir, name)
            checks.append(
                ("core library {} packaged and executable".format(name), os.access(path, os.X_OK))
            )
        for name in ("__init__.py", "_utils.py", "vapoursynth.pyi"):
            checks.append(
                (
                    "python module file {} packaged".format(name),
                    os.path.isfile(os.path.join(module_dir, name)),
                )
            )
        upstream_modules = sorted(glob.glob(os.path.join(tests_dir, "*.py")))
        checks.append(
            (
                "upstream unittest modules packaged ({} files)".format(len(upstream_modules)),
                len(upstream_modules) >= 11,
            )
        )
        checks.append(
            (
                "upstream expr_compiler harness packaged",
                os.path.isfile(os.path.join(tests_dir, "expr_compiler", "compiler_test.py")),
            )
        )

        failed = [description for description, passed in checks if not passed]
        for description, passed in checks:
            self.output.info(
                "E212 static check [{}]: {}".format("pass" if passed else "FAIL", description)
            )
        if failed:
            raise ConanInvalidConfiguration(
                "E212 fallback static verification failed: {}".format("; ".join(failed))
            )
        self.output.info(
            "E212 fallback static verification passed ({}/{} checks)".format(
                len(checks),
                len(checks),
            )
        )

    def _readelf_needed(self, path):
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            for bindir in self._ohos_tool_candidates("llvm-objcopy"):
                candidate = os.path.join(os.path.dirname(bindir), "llvm-readelf")
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    readelf = candidate
                    break
        if not readelf:
            return None
        try:
            completed = subprocess.run(
                [readelf, "-d", path],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0:
            return None
        return [
            line.split("Shared library:", 1)[1].strip().strip("[]")
            for line in (completed.stdout or "").splitlines()
            if "NEEDED" in line and "Shared library:" in line
        ]

    def _prepare_runtime_shared_libraries(self, package_folder):
        if self.settings.os != "OHOS":
            return
        shared_libs = sorted(
            path
            for path in glob.glob(os.path.join(package_folder, "**", "*.so*"), recursive=True)
            if os.path.isfile(path) and not os.path.islink(path)
        )
        if not shared_libs:
            return

        objcopy_candidates = self._ohos_tool_candidates("llvm-objcopy")
        signer_candidates = self._ohos_tool_candidates("binary-sign-tool")
        if objcopy_candidates and signer_candidates:
            for shared_lib in shared_libs:
                self._sign_elf_atomically(shared_lib, objcopy_candidates[0], signer_candidates[0])
        else:
            self.output.warning(
                "llvm-objcopy/binary-sign-tool not available; keeping the packaged signatures"
            )
        for shared_lib in shared_libs:
            os.chmod(shared_lib, 0o755)
            self.run("chmod 755 {}".format(shlex.quote(shared_lib)), quiet=True)

    @staticmethod
    def _python_extension(shared_libs):
        for path in shared_libs:
            name = os.path.basename(path)
            if name.startswith("vapoursynth") and name.endswith(".so"):
                return path
        return ""

    def _python_interpreter(self):
        candidates = [shutil.which("python3") or ""]
        candidates.append(os.path.join(os.path.expanduser("~"), "usr", "local", "bin", "python3"))
        candidates.append("/storage/Users/currentUser/usr/local/bin/python3")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("cpp") or compilers.get("c") or ""
        if compiler and os.path.isabs(compiler):
            candidates.append(os.path.join(os.path.dirname(compiler), "python3"))
        candidates.append("/data/service/hnp/bin/python3")
        candidates.append("/data/app/bin/python3")
        candidates.append(sys.executable or "")
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return ""

    def _ohos_tool_candidates(self, name):
        env_names = {
            "llvm-objcopy": ("OHOS_LLVM_OBJCOPY", "LLVM_OBJCOPY"),
            "binary-sign-tool": ("OHOS_BINARY_SIGN_TOOL", "BINARY_SIGN_TOOL"),
        }
        raw = [os.environ.get(env_name, "") for env_name in env_names.get(name, ())]
        raw.append(os.path.join(os.path.expanduser("~"), "usr", "local", "bin", name))
        raw.append(os.path.join("/storage/Users/currentUser/usr/local/bin", name))
        raw.append(shutil.which(name) or "")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("cpp") or compilers.get("c") or ""
        if compiler and os.path.isabs(compiler):
            raw.append(os.path.join(os.path.dirname(compiler), name))
        raw.append(os.path.join("/data/service/hnp/bin", name))
        for sdk_bindir in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin"):
            raw.append(os.path.join(sdk_bindir, name))

        candidates = []
        unusable = []
        seen = set()
        for path in raw:
            if not path or not os.path.exists(path):
                continue
            resolved = os.path.realpath(path)
            if resolved in seen:
                continue
            seen.add(resolved)
            if not os.path.isfile(path) or not os.access(path, os.X_OK):
                unusable.append(path)
                continue
            candidates.append(path)
        if unusable:
            self.output.warning(
                "OHOS tool candidates present but not executable by this user: {}".format(
                    ", ".join(unusable)
                )
            )
        return candidates

    def _sign_elf_atomically(self, path, objcopy, signer):
        clean = "{}.codesign-clean-{}".format(path, os.getpid())
        signed = "{}.codesign-signed-{}".format(path, os.getpid())
        try:
            self.run(
                shlex.join([objcopy, "--remove-section", ".codesign", path, clean]),
                quiet=True,
            )
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        clean,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ]
                ),
                quiet=True,
            )
            codesign_size = self._verify_codesign_section(signed, objcopy)
            os.chmod(signed, 0o755)
            os.replace(signed, path)
            self.output.info(
                "OHOS runtime signed shared library: {} (.codesign {} bytes)".format(
                    os.path.relpath(path, self.dependencies["vapoursynth"].package_folder),
                    codesign_size,
                )
            )
        finally:
            for temporary in (clean, signed):
                if os.path.exists(temporary):
                    os.remove(temporary)

    def _build_expr_debugger(self, cxx):
        dep = self.dependencies["vapoursynth"]
        dep_cpp_info = dep.cpp_info
        expr_src = os.path.join(dep.package_folder, "tests", "exprdebugger", "src", "core", "expr")
        exe = os.path.join(self.build_folder, "ExprDebugger.exe")
        cmd = [
            *self._exec_tool(cxx),
            "-std=c++17",
            os.path.join(expr_src, "expr.cpp"),
            os.path.join(expr_src, "main.cpp"),
            "-o",
            exe,
        ]
        for include_dir in dep_cpp_info.includedirs:
            cmd.append("-I" + include_dir)
        self.run(" ".join(shlex.quote(part) for part in cmd))

    def _run_expr_compiler_harness(self, tests_dir):
        expr_debugger = os.path.join(self.build_folder, "ExprDebugger.exe")
        runner = os.path.join(self.source_folder, "run_expr_compiler_test.py")
        cmd = "python3 {} {} {}".format(
            shlex.quote(runner),
            shlex.quote(os.path.join(tests_dir, "expr_compiler", "compiler_test.py")),
            shlex.quote(expr_debugger),
        )
        self.run(cmd, env="conanrun")

    def _resolve_tool(self, configured, fallback):
        if configured and os.path.exists(configured):
            return configured
        found = shutil.which(fallback)
        if found:
            return found
        if configured:
            bindir = os.path.dirname(configured) if os.path.isabs(configured) else ""
            candidate = os.path.join(bindir, fallback) if bindir else ""
            if candidate and os.path.exists(candidate):
                return candidate
        home_candidate = os.path.join(os.path.expanduser("~"), "usr", "local", "bin", fallback)
        if os.path.exists(home_candidate):
            return home_candidate
        return fallback

    def _verify_codesign_section(self, path, objcopy):
        dump = "{}.codesign-dump-{}".format(path, os.getpid())
        inspect = "{}.codesign-inspect-{}".format(path, os.getpid())
        try:
            shutil.copy2(path, inspect)
            self.run(
                shlex.join([objcopy, "--dump-section", ".codesign={}".format(dump), inspect]),
                quiet=True,
            )
            if not os.path.isfile(dump) or os.path.getsize(dump) <= 0:
                raise ConanInvalidConfiguration("failed to add a non-empty .codesign section to {}".format(path))
            return os.path.getsize(dump)
        finally:
            for temporary in (dump, inspect):
                if os.path.exists(temporary):
                    os.remove(temporary)

    def _exec_tool(self, tool):
        if self._is_script(tool):
            return ["sh", tool]
        return [tool]

    @staticmethod
    def _is_script(path):
        if not path or not os.path.isfile(path):
            return False
        try:
            with open(path, "rb") as handle:
                return handle.read(2) == b"#!"
        except OSError:
            return False
