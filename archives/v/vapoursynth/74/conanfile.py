#!/usr/bin/env python3
"""Conan recipe for VapourSynth 74."""

import glob
import os
import re
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class VapoursynthConan(ConanFile):
    name = "vapoursynth"
    version = "74"
    description = "A video processing framework with simplicity in mind"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.vapoursynth.com/"
    url = "https://github.com/vapoursynth/vapoursynth"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "vsscript": [True, False],
        "python_module": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "vsscript": False,
        "python_module": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("zimg/3.0.6")

    def generate(self):
        if self.options.python_module:
            self._ensure_python_build_tools()

        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["enable_core"] = True
        tc.project_options["enable_guard_pattern"] = False
        tc.project_options["enable_x86_asm"] = False
        tc.project_options["enable_vsscript"] = bool(self.options.vsscript)
        tc.project_options["enable_vspipe"] = False
        tc.project_options["enable_python_module"] = bool(self.options.python_module)
        tc.project_options["build_wheel"] = False
        tc.generate()
        if self.options.python_module:
            self._inject_meson_cython()
        self._inject_meson_archiver()
        self._inject_meson_pkg_config()
        self._wrap_nonexecutable_meson_compilers()
        self._prepend_ohos_sdk_runtime_paths()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        self._meson_compile()

    def _meson_compile(self):
        """Run ``meson compile`` with a bounded job count.

        Conan's Meson helper defaults to one job per CPU, which is 20 on the CI
        workers. Those workers run under a sandboxed uid with a tight process
        budget, and a 20-way fan-out makes ninja fail with

            ninja: fatal: posix_spawn: Resource temporarily unavailable

        (the same limit that other recipes in this repository work around with
        ``tools.build:jobs``/``-j1``). Honour ``tools.build:jobs`` when the
        profile sets it and otherwise keep the fan-out small.
        """
        jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
        if not jobs:
            jobs = max(1, min(8, os.cpu_count() or 2))
        self.output.info("Meson compile job fan-out capped at -j{}".format(jobs))
        self.run('meson compile -C "{}" -j{}'.format(self.build_folder, jobs))

    def package(self):
        copy(self, "COPYING.LESSER", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        Meson(self).install()
        self._ensure_unversioned_shared_libraries()
        self._package_python_module()
        self._package_upstream_tests()
        self._sign_shared_libraries()
        self._ensure_shared_library_permissions()

    def package_info(self):
        self.cpp_info.libs = ["vapoursynth"]
        if self.options.vsscript:
            self.cpp_info.libs.append("vsscript")
        self.cpp_info.includedirs = ["include/vapoursynth", "include"]
        self.cpp_info.set_property("cmake_file_name", "vapoursynth")
        self.cpp_info.set_property("cmake_target_name", "vapoursynth::vapoursynth")
        self.cpp_info.set_property("pkg_config_name", "vapoursynth")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

        libdir = os.path.join(self.package_folder, "lib")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        pythondir = os.path.join(self.package_folder, "python")
        if os.path.isdir(pythondir):
            self.runenv_info.prepend_path("PYTHONPATH", pythondir)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(pythondir, "vapoursynth"))

    def _ensure_python_build_tools(self):
        interpreter = self._cython_interpreter()
        if not interpreter:
            # Do not pin an exact release: the CI worker mirror currently only
            # serves Cython 3.3.0 while developer devices still carry 3.1.2.
            target = (self._python_candidates() or ["python3"])[0]
            self.output.info(
                "installing Cython for {} because no candidate reports a usable Cython".format(target)
            )
            try:
                self.run('{} -m pip install --user "Cython>=3.1,<4"'.format(shlex.quote(target)))
            except Exception as error:  # noqa: BLE001 - reported by the wrapper probe below
                self.output.warning("Cython installation failed: {}".format(error))
            interpreter = self._cython_interpreter()
        if interpreter:
            self.output.info("Cython interpreter: {}".format(interpreter))
        else:
            raise ConanInvalidConfiguration(
                "python_module=True needs a python3 that can actually run Cython >= 3.1. "
                "On the CI worker every candidate fails with E212: hmmac refuses to dlopen "
                "Cython's own compiled modules from user paths (knowledge/doc/E212.md). "
                "Keep the default python_module=False for the core library, or enable this "
                "option on a machine that can run Cython."
            )
        self._prepend_cython_wrapper()

    def _cython_interpreter(self):
        for interpreter in self._python_candidates():
            version = self._cython_version(interpreter)
            if version:
                self.output.info("Cython {} available via {}".format(version, interpreter))
                return interpreter
        return ""

    @staticmethod
    def _cython_version(interpreter):
        """Return the Cython version only when the interpreter can really run it.

        A shallow ``import Cython`` is not enough: Cython ships compiled modules
        (for example ``Cython/Utils*.so``) that hmmac refuses to dlopen from user
        paths on the CI worker (knowledge/doc/E212.md), so the check must exercise
        the compiler entry point that the Meson wrapper uses.
        """
        try:
            completed = subprocess.run(
                [interpreter, "-m", "cython", "--version"],
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        if completed.returncode != 0:
            return ""
        output = ((completed.stdout or "") + (completed.stderr or "")).strip()
        match = re.search(r"(\d+)\.(\d+)", output)
        if not match:
            return ""
        major, minor = int(match.group(1)), int(match.group(2))
        if (major, minor) < (3, 1):
            return ""
        return "{}.{}".format(major, minor)

    def _python_candidates(self):
        candidates = [
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", "python3"),
            "/storage/Users/currentUser/usr/local/bin/python3",
            "/data/service/hnp/bin/python3",
            "/data/app/bin/python3",
            shutil.which("python3") or "",
        ]
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("cpp") or compilers.get("c") or ""
        if compiler and os.path.isabs(compiler):
            candidates.append(os.path.join(os.path.dirname(compiler), "python3"))
        candidates.extend([sys.executable or "", "python3"])

        ordered = []
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if candidate == "python3" or (os.path.isfile(candidate) and os.access(candidate, os.X_OK)):
                ordered.append(candidate)
        return ordered

    def _python_interpreter(self):
        for path in self._python_candidates():
            if path != "python3":
                return path
        return shutil.which("python3") or ""

    def _prepend_cython_wrapper(self):
        wrapper_dir = os.path.join(self.generators_folder, "cython-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        shell = "/system/bin/sh" if os.path.exists("/system/bin/sh") else "/bin/sh"
        candidates = self._python_candidates()
        lines = ["#!{}".format(shell)]
        if candidates:
            lines.append(
                "for candidate in {}; do".format(
                    " ".join(shlex.quote(candidate) for candidate in candidates)
                )
            )
            lines.append("    if \"$candidate\" -c 'import Cython' >/dev/null 2>&1; then")
            lines.append("        exec \"$candidate\" -m cython \"$@\"")
            lines.append("    fi")
            lines.append("done")
        lines.append("for fallback in \"$HOME/.local/bin/cython\" \"$HOME/usr/local/bin/cython\"; do")
        lines.append("    if [ -x \"$fallback\" ]; then exec \"$fallback\" \"$@\"; fi")
        lines.append("done")
        lines.append("echo 'cython wrapper: no python3 with Cython >= 3.1 found' >&2")
        lines.append("exit 1")
        content = "\n".join(lines) + "\n"

        for name in ("cython", "cython3"):
            wrapper = os.path.join(wrapper_dir, name)
            with open(wrapper, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.chmod(wrapper, 0o755)
        os.environ["PATH"] = wrapper_dir + os.pathsep + os.environ.get("PATH", "")
        self._verify_cython_wrapper(os.path.join(wrapper_dir, "cython"), shell)

    def _verify_cython_wrapper(self, wrapper, shell):
        probe_dir = os.path.join(self.generators_folder, "cython-wrapper", "probe")
        os.makedirs(probe_dir, exist_ok=True)
        source = os.path.join(probe_dir, "wrapper_probe.pyx")
        output = os.path.join(probe_dir, "wrapper_probe.cpp")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write("cdef int vs_wrapper_probe(int value):\n    return value + 1\n")
        if os.path.exists(output):
            os.remove(output)
        command = shlex.join([shell, wrapper, "-3", "--cplus", "-o", output, source])
        try:
            completed = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.SubprocessError) as error:
            self.output.warning("Cython wrapper probe could not run: {}".format(error))
            return False
        if completed.returncode == 0 and os.path.isfile(output) and os.path.getsize(output) > 0:
            self.output.info("Cython wrapper probe: transpiled a probe module successfully")
            return True
        detail = ((completed.stderr or "") + (completed.stdout or "")).strip().splitlines()
        self.output.warning(
            "Cython wrapper probe failed (exit {}): {}".format(
                completed.returncode,
                detail[-1] if detail else "no output",
            )
        )
        return False

    def _inject_meson_cython(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        cython = os.path.join(self.generators_folder, "cython-wrapper", "cython")
        if not os.path.isfile(native_file) or not os.path.isfile(cython):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content or "\ncython =" in content:
            return
        shell = "/system/bin/sh" if os.path.exists("/system/bin/sh") else "/bin/sh"
        insertion = "[binaries]\ncython = ['{}', '{}']\n".format(
            shell.replace("\\", "/"),
            cython.replace("\\", "/"),
        )
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insertion, 1))

    def _inject_meson_archiver(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        insertion = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib:
            insertion += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insertion, 1))

    def _inject_meson_pkg_config(self):
        pkg_config = self._pkg_config_binary_entry()
        if not pkg_config:
            return

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content:
            return
        if "\npkg-config =" not in content and "\npkgconfig =" not in content:
            insertion = "[binaries]\npkg-config = {}\n".format(pkg_config)
            content = content.replace("[binaries]\n", insertion, 1)
        if "pkg_config_path =" not in content and "[built-in options]" in content:
            pc_path = self.generators_folder.replace("\\", "/")
            content = content.replace(
                "[built-in options]\n",
                "[built-in options]\npkg_config_path = ['{}']\n".format(pc_path),
                1,
            )
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _pkg_config_binary_entry(self):
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if pkg_config and os.path.isfile(str(pkg_config)):
            return "'{}'".format(str(pkg_config).replace("\\", "/"))
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if pkg_config:
            return "'{}'".format(pkg_config.replace("\\", "/"))
        wrapper = self._write_pkg_config_wrapper()
        if not wrapper:
            return ""
        shell = "/system/bin/sh" if os.path.exists("/system/bin/sh") else "/bin/sh"
        if not os.path.exists(shell):
            return ""
        return "['{}', '{}']".format(shell.replace("\\", "/"), wrapper.replace("\\", "/"))

    def _write_pkg_config_wrapper(self):
        wrapper_dir = os.path.join(self.generators_folder, "pkg-config-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        script = os.path.join(wrapper_dir, "pkg_config_wrapper.py")
        launcher = os.path.join(wrapper_dir, "pkg-config")
        code = r'''#!/usr/bin/env python3
import os
import re
import shlex
import sys

DEFAULT_PATHS = "@@PKG_CONFIG_PATH@@".split(os.pathsep)
OPERATORS = {"=", "==", "!=", "<", ">", "<=", ">="}
FIELD_RE = re.compile(r"\$\{([^}]+)\}")


def unique_paths(paths):
    seen = set()
    result = []
    for path in paths:
        if path and path not in seen and os.path.isdir(path):
            result.append(path)
            seen.add(path)
    return result


def search_paths():
    env = os.environ.get("PKG_CONFIG_LIBDIR") or os.environ.get("PKG_CONFIG_PATH", "")
    return unique_paths(env.split(os.pathsep) + DEFAULT_PATHS)


def expand(value, variables):
    for _ in range(20):
        updated = FIELD_RE.sub(lambda match: variables.get(match.group(1), ""), value)
        if updated == value:
            return updated
        value = updated
    return value


def parse_pc(path, overrides):
    variables = {"pcfiledir": os.path.dirname(path)}
    variables.update(overrides)
    fields = {}
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            colon = line.find(":")
            equal = line.find("=")
            if equal != -1 and (colon == -1 or equal < colon):
                key, value = line.split("=", 1)
                variables[key.strip()] = expand(value.strip(), variables)
                continue
            if colon != -1:
                key, value = line.split(":", 1)
                fields[key.strip().lower()] = expand(value.strip(), variables)
    return variables, fields


def find_pc(module):
    for base in search_paths():
        candidate = os.path.join(base, module + ".pc")
        if os.path.isfile(candidate):
            return candidate
    for base in search_paths():
        for name in os.listdir(base):
            if not name.endswith(".pc"):
                continue
            path = os.path.join(base, name)
            _, fields = parse_pc(path, {})
            if fields.get("name") == module:
                return path
    return ""


def version_parts(version):
    parts = []
    for item in re.split(r"[^0-9A-Za-z]+", version):
        if not item:
            continue
        parts.append(int(item) if item.isdigit() else item)
    return parts


def compare_version(actual, expected):
    left = version_parts(actual)
    right = version_parts(expected)
    for index in range(max(len(left), len(right))):
        lhs = left[index] if index < len(left) else 0
        rhs = right[index] if index < len(right) else 0
        if lhs == rhs:
            continue
        if isinstance(lhs, int) and isinstance(rhs, int):
            return -1 if lhs < rhs else 1
        lhs = str(lhs)
        rhs = str(rhs)
        return -1 if lhs < rhs else 1
    return 0


def flag_filter(flags, mode):
    tokens = shlex.split(flags)
    if mode == "all":
        return tokens
    if mode == "lib_dirs":
        return [token for token in tokens if token.startswith("-L")]
    if mode == "libs":
        return [token for token in tokens if token.startswith("-l")]
    if mode == "lib_other":
        return [token for token in tokens if not token.startswith(("-L", "-l"))]
    if mode == "include_dirs":
        return [token for token in tokens if token.startswith("-I")]
    if mode == "cflags_other":
        return [token for token in tokens if not token.startswith("-I")]
    return []


def module_args(args):
    modules = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in OPERATORS:
            skip = True
            continue
        if any(arg.startswith(op) for op in ("<=", ">=", "==", "!=", "<", ">")):
            continue
        modules.append(arg)
    return modules


def main():
    args = sys.argv[1:]
    if "--version" in args:
        print("0.29.2")
        return 0

    overrides = {}
    queries = []
    positional = []
    static = False
    atleast_version = None
    variable = None
    for arg in args:
        if arg.startswith("--define-variable="):
            item = arg.split("=", 1)[1]
            if "=" in item:
                key, value = item.split("=", 1)
                overrides[key] = value
            continue
        if arg == "--static":
            static = True
            continue
        if arg in ("--print-errors", "--silence-errors", "--errors-to-stdout", "--short-errors"):
            continue
        if arg == "--exists":
            queries.append("exists")
            continue
        if arg.startswith("--atleast-version="):
            atleast_version = arg.split("=", 1)[1]
            queries.append("atleast")
            continue
        if arg == "--modversion":
            queries.append("modversion")
            continue
        if arg.startswith("--variable="):
            variable = arg.split("=", 1)[1]
            queries.append("variable")
            continue
        mapping = {
            "--cflags": "cflags",
            "--cflags-only-I": "cflags_i",
            "--cflags-only-other": "cflags_other",
            "--libs": "libs",
            "--libs-only-L": "libs_l_dirs",
            "--libs-only-l": "libs_l",
            "--libs-only-other": "libs_other",
            "--path": "path",
        }
        if arg in mapping:
            queries.append(mapping[arg])
            continue
        if arg.startswith("-"):
            continue
        positional.append(arg)

    modules = module_args(positional)
    if not modules:
        return 0

    loaded = []
    for module in modules:
        pc_path = find_pc(module)
        if not pc_path:
            return 1
        variables, fields = parse_pc(pc_path, overrides)
        loaded.append((pc_path, variables, fields))

    if not queries:
        queries = ["exists"]
    output = []
    for query in queries:
        if query == "exists":
            continue
        if query == "atleast":
            version = loaded[0][2].get("version", "0")
            if compare_version(version, atleast_version or "0") < 0:
                return 1
            continue
        if query == "modversion":
            output.extend(item[2].get("version", "") for item in loaded)
            continue
        if query == "variable":
            pc_path, variables, fields = loaded[0]
            output.append(variables.get(variable, fields.get(variable, "")))
            continue
        if query == "path":
            output.extend(item[0] for item in loaded)
            continue
        for _, _, fields in loaded:
            libs = fields.get("libs", "")
            if static and fields.get("libs.private"):
                libs = libs + " " + fields.get("libs.private", "")
            cflags = fields.get("cflags", "")
            if query == "cflags":
                output.extend(flag_filter(cflags, "all"))
            elif query == "cflags_i":
                output.extend(flag_filter(cflags, "include_dirs"))
            elif query == "cflags_other":
                output.extend(flag_filter(cflags, "cflags_other"))
            elif query == "libs":
                output.extend(flag_filter(libs, "all"))
            elif query == "libs_l_dirs":
                output.extend(flag_filter(libs, "lib_dirs"))
            elif query == "libs_l":
                output.extend(flag_filter(libs, "libs"))
            elif query == "libs_other":
                output.extend(flag_filter(libs, "lib_other"))

    if output:
        print(" ".join(item for item in output if item))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
        code = code.replace("@@PKG_CONFIG_PATH@@", self.generators_folder.replace("\\", "/"))
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(code)
        python = sys.executable.replace("\\", "/")
        with open(launcher, "w", encoding="utf-8") as handle:
            handle.write("#!/system/bin/sh\nexec \"{}\" \"{}\" \"$@\"\n".format(python, script.replace("\\", "/")))
        os.chmod(script, 0o755)
        os.chmod(launcher, 0o755)
        return launcher

    def _wrap_nonexecutable_meson_compilers(self):
        if self.settings.os != "OHOS":
            return
        shell = "/system/bin/sh"
        if not os.path.exists(shell):
            return

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            lines = handle.readlines()

        changed = False
        for idx, line in enumerate(lines):
            stripped = line.strip()
            for key in ("c", "cpp"):
                prefix = "{} = '".format(key)
                if not stripped.startswith(prefix) or not stripped.endswith("'"):
                    continue
                compiler = stripped[len(prefix):-1]
                if os.path.exists(compiler) and not self._can_execute(compiler):
                    lines[idx] = "{} = ['{}', '{}']\n".format(key, shell, compiler)
                    changed = True

        if changed:
            with open(native_file, "w", encoding="utf-8") as handle:
                handle.writelines(lines)

    def _prepend_ohos_sdk_runtime_paths(self):
        if self.settings.os != "OHOS":
            return
        runtime_dirs = self._ohos_sdk_runtime_dirs()
        if not runtime_dirs:
            return
        current = os.environ.get("LD_LIBRARY_PATH", "")
        parts = runtime_dirs + ([current] if current else [])
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(parts)

    @staticmethod
    def _can_execute(path):
        try:
            subprocess.run(
                [path, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return True
        except OSError:
            return False

    def _ensure_unversioned_shared_libraries(self):
        if not self.options.shared:
            return
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        unversioned = os.path.join(libdir, "libvapoursynth.so")
        versioned = os.path.join(libdir, "libvapoursynth.so.4")
        if not os.path.exists(versioned):
            matches = glob.glob(os.path.join(self.package_folder, "**", "libvapoursynth.so.4"), recursive=True)
            for match in matches:
                if os.path.normpath(match) != os.path.normpath(versioned):
                    shutil.copy2(match, versioned)
                    break
        if os.path.exists(versioned) and not os.path.exists(unversioned):
            shutil.copy2(versioned, unversioned)

    def _package_python_module(self):
        if not self.options.python_module:
            return
        pythondir = os.path.join(self.package_folder, "python", "vapoursynth")
        os.makedirs(pythondir, exist_ok=True)
        for source_root, _, files in os.walk(self.package_folder):
            if os.path.normpath(source_root).startswith(os.path.normpath(pythondir)):
                continue
            if os.path.basename(source_root) != "vapoursynth":
                continue
            for filename in files:
                if filename.endswith((".py", ".pyi", ".so")) or filename.startswith("libvapoursynth.so"):
                    shutil.copy2(os.path.join(source_root, filename), os.path.join(pythondir, filename))
        if not glob.glob(os.path.join(pythondir, "vapoursynth*.so")):
            raise RuntimeError("Python module was requested but vapoursynth extension was not packaged")
        versioned = os.path.join(pythondir, "libvapoursynth.so.4")
        unversioned = os.path.join(pythondir, "libvapoursynth.so")
        if os.path.exists(versioned) and not os.path.exists(unversioned):
            shutil.copy2(versioned, unversioned)

    def _package_upstream_tests(self):
        tests_dir = os.path.join(self.package_folder, "tests", "upstream")
        copy(self, "*", src=os.path.join(self.source_folder, "test"), dst=tests_dir)
        expr_src = os.path.join(self.source_folder, "src", "core", "expr")
        expr_dst = os.path.join(self.package_folder, "tests", "exprdebugger", "src", "core", "expr")
        copy(self, "expr.cpp", src=expr_src, dst=expr_dst)
        copy(self, "expr.h", src=expr_src, dst=expr_dst)
        copy(self, "main.cpp", src=expr_src, dst=expr_dst)

    def _sign_shared_libraries(self):
        if self.settings.os != "OHOS":
            return
        shared_libs = self._package_shared_libraries()
        if not shared_libs:
            return
        tools = self._ohos_signing_tools(required=True)
        for shared_lib in shared_libs:
            self._sign_elf_atomically(shared_lib, tools)

    def _package_shared_libraries(self):
        return sorted(
            path
            for path in glob.glob(os.path.join(self.package_folder, "**", "*.so*"), recursive=True)
            if os.path.isfile(path) and not os.path.islink(path)
        )

    def _ohos_signing_tools(self, required):
        objcopy_candidates = self._ohos_tool_candidates("llvm-objcopy")
        signer_candidates = self._ohos_tool_candidates("binary-sign-tool")
        if not objcopy_candidates or not signer_candidates:
            message = (
                "OHOS shared libraries require llvm-objcopy and binary-sign-tool "
                "(llvm-objcopy candidates: {}; binary-sign-tool candidates: {})".format(
                    ", ".join(objcopy_candidates) or "none",
                    ", ".join(signer_candidates) or "none",
                )
            )
            if required:
                raise ConanInvalidConfiguration(message)
            self.output.warning(message)
            return {}
        tools = {"objcopy": objcopy_candidates[0], "signer": signer_candidates[0]}
        self.output.info(
            "OHOS signing tools: llvm-objcopy={}, binary-sign-tool={}".format(
                tools["objcopy"],
                tools["signer"],
            )
        )
        return tools

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

    def _sign_elf_atomically(self, path, tools):
        original_mode = os.stat(path).st_mode & 0o7777
        clean = "{}.codesign-clean-{}".format(path, os.getpid())
        signed = "{}.codesign-signed-{}".format(path, os.getpid())
        try:
            self.run(
                shlex.join([tools["objcopy"], "--remove-section", ".codesign", path, clean]),
                quiet=True,
            )
            self.run(
                shlex.join(
                    [
                        tools["signer"],
                        "sign",
                        "-inFile",
                        clean,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ]
                    + list(tools.get("args") or [])
                ),
                quiet=True,
            )
            codesign_size = self._verify_codesign_section(signed, tools["objcopy"])
            os.chmod(signed, original_mode | 0o755)
            os.replace(signed, path)
            self.output.info(
                "OHOS signed shared library: {} (.codesign {} bytes)".format(
                    os.path.relpath(path, self.package_folder),
                    codesign_size,
                )
            )
        finally:
            for temporary in (clean, signed):
                if os.path.exists(temporary):
                    os.remove(temporary)

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

    def _ensure_shared_library_permissions(self):
        if self.settings.os != "OHOS":
            return
        for shared_lib in glob.glob(os.path.join(self.package_folder, "**", "*.so*"), recursive=True):
            if not os.path.islink(shared_lib):
                os.chmod(shared_lib, 0o755)
                self.run("chmod 755 {}".format(shlex.quote(shared_lib)), quiet=True)

    @staticmethod
    def _ohos_sdk_runtime_dirs():
        runtime_dirs = []
        for candidate in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"):
            if os.path.isdir(candidate):
                runtime_dirs.append(candidate)
        return runtime_dirs
