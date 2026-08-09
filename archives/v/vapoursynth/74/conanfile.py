#!/usr/bin/env python3
"""Conan recipe for VapourSynth 74."""

import glob
import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
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
        "python_module": True,
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
        meson.build()

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
        has_cython = False
        try:
            subprocess.run(
                [
                    "python3",
                    "-c",
                    (
                        "import Cython; "
                        "version = tuple(int(part) for part in Cython.__version__.split('.')[:2]); "
                        "raise SystemExit(0 if version >= (3, 1) else 1)"
                    ),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            has_cython = True
        except (OSError, subprocess.CalledProcessError):
            pass
        if not has_cython:
            self.run("python3 -m pip install --user Cython==3.1.2")
        self._prepend_cython_wrapper()

    def _prepend_cython_wrapper(self):
        wrapper_dir = os.path.join(self.generators_folder, "cython-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        shell = "/system/bin/sh" if os.path.exists("/system/bin/sh") else "/bin/sh"
        for name in ("cython", "cython3"):
            wrapper = os.path.join(wrapper_dir, name)
            with open(wrapper, "w", encoding="utf-8") as handle:
                handle.write("#!{}\nexec python3 -m cython \"$@\"\n".format(shell))
            os.chmod(wrapper, 0o755)
        os.environ["PATH"] = wrapper_dir + os.pathsep + os.environ.get("PATH", "")

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
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not os.path.exists(objcopy) or not os.path.exists(signer):
            return
        for shared_lib in glob.glob(os.path.join(self.package_folder, "**", "*.so*"), recursive=True):
            if os.path.islink(shared_lib):
                continue
            signed = shared_lib + ".signed"
            self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, shared_lib), quiet=True)
            self.run(
                '{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, shared_lib, signed),
                quiet=True,
            )
            os.replace(signed, shared_lib)

    def _ensure_shared_library_permissions(self):
        if self.settings.os != "OHOS":
            return
        for shared_lib in glob.glob(os.path.join(self.package_folder, "**", "*.so*"), recursive=True):
            if not os.path.islink(shared_lib):
                os.chmod(shared_lib, 0o755)
                self.run("chmod 755 {}".format(shlex.quote(shared_lib)), quiet=True)

    def _find_ohos_tool(self, name):
        found = shutil.which(name)
        if found:
            return found
        for prefix in ("/storage/Users/currentUser/usr/local/bin", "/data/service/hnp/bin"):
            candidate = os.path.join(prefix, name)
            if os.path.exists(candidate):
                return candidate
        return name

    @staticmethod
    def _ohos_sdk_runtime_dirs():
        runtime_dirs = []
        for candidate in glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"):
            if os.path.isdir(candidate):
                runtime_dirs.append(candidate)
        return runtime_dirs
