#!/usr/bin/env python3
"""Conan test_package for kservice 6.28.0.

R34: exercises the real KF6Service C++ API (link + call + verify):
  - Case A: temporary KService round-trip (name/exec/icon accessors).
  - Case B: end-to-end service discovery: a desktop-file fixture is written
    into the isolated XDG applications directory (plus one under
    XDG_DATA_DIRS), KSycoca::setupTestMenu() stages the canonical minimal
    applications.menu, KService lookups drive the real KSycoca pipeline with
    a cold cache (in-process cache build), the fixture is verified through
    both the desktop-name and the entry-path indexes, and the materialised
    sycoca cache file must exist.

Package integrity (python side): the installed libKF6Service.so must carry
the bare DT_SONAME `libKF6Service.so` with no versioned symlink chain (the
OHOS no-versioned-soname emit; HMDFS rejects the symlink chain with E330)
and no absolute/relative paths in DT_NEEDED; the packaged kbuildsycoca6 tool
must have clean DT_NEEDED entries, must answer --version, and must complete
a real --testmode cache build. The consumer test binary is held to the
resolved tier: absolute entries inherited from SONAME-less published
packages must exist on this machine, relative entries stay fatal.
"""
import glob
import os
import struct

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


def _elf_dynamic_fields(path):
    """Return (needed, soname) of an ELF64 file, or None if it is not ELF."""
    with open(path, "rb") as handle:
        data = handle.read()
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return None
    if data[4] != 2:  # ELFCLASS64
        return None
    endian = "<" if data[5] == 1 else ">"
    (e_shoff,) = struct.unpack_from(endian + "Q", data, 0x28)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(endian + "HHH", data, 0x3A)
    if e_shoff == 0 or e_shnum == 0:
        return [], None

    def section(index):
        off = e_shoff + index * e_shentsize
        return struct.unpack_from(endian + "IIQQQQIIQQ", data, off)

    sections = [section(i) for i in range(e_shnum)]
    strtab_off = sections[e_shstrndx][4]

    def name_of(entry):
        start = strtab_off + entry[0]
        end = data.index(b"\x00", start)
        return data[start:end].decode("utf-8", "replace")

    dynamic = next((s for s in sections if name_of(s) == ".dynamic"), None)
    dynstr = next((s for s in sections if name_of(s) == ".dynstr"), None)
    if dynamic is None or dynstr is None:
        return [], None

    needed = []
    soname = None
    dyn_off, dyn_size = dynamic[4], dynamic[5]
    str_off = dynstr[4]
    for off in range(dyn_off, dyn_off + dyn_size, 16):
        tag, val = struct.unpack_from(endian + "qQ", data, off)
        if tag == 0:
            break
        if tag in (1, 14):  # DT_NEEDED, DT_SONAME
            start = str_off + val
            end = data.index(b"\x00", start)
            value = data[start:end].decode("utf-8", "replace")
            if tag == 1:
                needed.append(value)
            else:
                soname = value
    return needed, soname


def _is_bad_needed(name):
    return name.startswith("/") or name.startswith("../")


def _is_fatal_relative(name):
    return "/" in name and not name.startswith("/")


class KserviceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0.1")
        self.requires("kcoreaddons/6.26.0.1")
        self.requires("ki18n/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")'
                )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _sdk_llvm_libdir(self):
        # The OHOS SDK root is environment specific, so prefer the llvm/lib
        # directory implied by the profile's compiler and fall back to globbing
        # the installed SDK. The version stays unpinned: a CI image ships
        # whatever SDK release it was built with.
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        if cxx:
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            )
        )
        for candidate in dict.fromkeys(candidates):
            if os.path.isdir(candidate):
                return candidate
        return ""

    def _build_env(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory and may not find it via the ambient
        # LD_LIBRARY_PATH; the dependency lib dirs are needed to build against
        # the packaged CMake configs.
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        with self._build_env().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _locate_tool(self, prefix, name):
        candidates = [
            os.path.join(prefix, "bin", name),
            os.path.join(prefix, "lib", "libexec", "kf6", name),
            os.path.join(prefix, "libexec", "kf6", name),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        for root, _dirs, files in os.walk(prefix):
            if name in files:
                return os.path.join(root, name)
        raise ConanException(f"Cannot locate {name} inside {prefix}")

    def _test_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefix = dep.package_folder
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(prefix, "plugins"))
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # shadowing the compatible one; prepend /system/lib64 so the test
            # executables and the packaged tool resolve the compatible libc++
            # first (same fix as the main recipe).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")

        # The OHOS sandbox is not writable for the test user, so isolate
        # HOME/XDG under the build folder; Case B then installs its fixture
        # into $XDG_DATA_HOME/applications and the sycoca cache lands below
        # $XDG_CACHE_HOME.
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(test_home, "runtime")
        for directory in (test_home, xdg_runtime):
            os.makedirs(directory, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, "cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, "config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, "data"))

        # Second discovery root: a fixture staged under XDG_DATA_DIRS so Case B
        # also covers the system data directory scan of the sycoca build.
        system_share = os.path.join(self.build_folder, "test-xdg-share")
        system_apps = os.path.join(system_share, "applications")
        os.makedirs(system_apps, exist_ok=True)
        with open(
            os.path.join(system_apps, "org.kde.ohpc-envdirstest.desktop"), "w"
        ) as handle:
            handle.write(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=OHPC EnvDir Service\n"
                "Exec=ohpc-envdir --run\n"
                "Icon=ohpc-envdir-icon\n"
            )
        env.define("XDG_DATA_DIRS", system_share)
        return env

    def _assert_resolvable_needed(self, path):
        """Consumer-binary tier of the DT_NEEDED hygiene: the test executable
        is linked against the published packages, so it may legitimately
        carry absolute entries inherited from SONAME-less dependencies (musl
        opens those directly; here they point into the local conan cache).
        Require every absolute entry to resolve; relative entries stay fatal
        everywhere because they resolve against the process CWD."""
        fields = _elf_dynamic_fields(path)
        assert fields is not None, f"{path} is not an ELF64 file"
        needed, _soname = fields
        self.output.info(f"{os.path.basename(path)} DT_NEEDED={needed}")
        bad = [
            name
            for name in needed
            if _is_fatal_relative(name)
            or (name.startswith("/") and not os.path.isfile(name))
        ]
        assert not bad, (
            f"{os.path.basename(path)} DT_NEEDED has relative or unresolvable "
            f"entries: {bad}"
        )

    def test(self):
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        assert pkg is not None, "kservice package dependency not resolved"
        prefix = pkg.package_folder

        # ---- package integrity: the core library ----
        core_lib = os.path.join(prefix, "lib", "libKF6Service.so")
        assert os.path.isfile(core_lib), f"missing core library: {core_lib}"
        fields = _elf_dynamic_fields(core_lib)
        assert fields is not None, f"{core_lib} is not an ELF64 file"
        needed, soname = fields
        self.output.info(f"libKF6Service.so DT_SONAME={soname} DT_NEEDED={needed}")
        assert soname == "libKF6Service.so", (
            f"libKF6Service.so carries an unexpected DT_SONAME: {soname!r} "
            "(expected the bare libKF6Service.so)"
        )
        assert not os.path.lexists(core_lib + ".6"), (
            "versioned symlink libKF6Service.so.6 exists; the OHOS user volume "
            "rejects the versioned symlink chain (E330)"
        )
        bad = [n for n in needed if _is_bad_needed(n)]
        assert not bad, f"libKF6Service.so DT_NEEDED contains relative/absolute path(s): {bad}"

        # ---- package integrity: the kbuildsycoca6 tool ----
        tool = self._locate_tool(prefix, "kbuildsycoca6")
        tool_fields = _elf_dynamic_fields(tool)
        assert tool_fields is not None, f"{tool} is not an ELF64 file"
        tool_needed, _tool_soname = tool_fields
        self.output.info(f"kbuildsycoca6 DT_NEEDED={tool_needed}")
        bad = [n for n in tool_needed if _is_bad_needed(n)]
        assert not bad, f"kbuildsycoca6 DT_NEEDED contains relative/absolute path(s): {bad}"

        # ---- consumer test binary: resolved-tier DT_NEEDED hygiene ----
        binary = os.path.join(self.cpp.build.bindirs[0], "test_kservice")
        self._assert_resolvable_needed(binary)

        # ---- run the compiled consumer (R34 case A + end-to-end case B) ----
        with self._test_env().vars(self).apply():
            self.run('"%s"' % binary)
            # The packaged tool must load and run from the install tree.
            self.run('"%s" --version' % tool)
            self.run('"%s" --testmode' % tool)
