#!/usr/bin/env python3
"""Conan recipe for synergy-core 1.21.4 on OpenHarmony PC (OHOS armv8).

synergy-core -- Synergy's core keyboard/mouse sharing service. This
adaptation ships the headless core CLI (combined server + client) built
against the conan-provided X11 client libraries, mirroring the in-repo
barrier/2.4.0 precedent (barrier is synergy's direct upstream fork and uses
the same X11 platform layer).
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Git


class SynergyCoreConan(ConanFile):
    name = "synergy-core"
    version = "1.21.4"
    description = "Keyboard and mouse sharing core service (server + client CLI)"
    license = "GPL-2.0-only WITH LicenseRef-OpenSSL-Exception"
    homepage = "https://symless.com/synergy"
    url = "https://github.com/symless/synergy-core"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt: upstream resolves Qt through the version-agnostic
        # find_package(QT NAMES Qt6 Qt5) and ships the Qt5->Qt6 target
        # aliases itself; the registry's qt5-qtbase provides the
        # Core/Gui/Widgets/Network/Xml/DBus/Test modules, the moc/rcc/uic
        # host tools and the minimal platform plugin the Qt Test suites
        # need.
        # glib is deliberately absent: it is only consumed by the libportal
        # sources (not selected in this X11-only delivery) and its .pc
        # drags a musl-specific -l:ld-musl-aarch64.so.1 linker flag that
        # lld cannot resolve on this platform.
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("openssl/3.5.6.1")
        # X11 client libraries (link-time only; no X server is needed to
        # build or to run the headless core CLI). libxrandr is deliberately
        # absent (barrier/2.4.0 precedent): it is the optional
        # display-hotplug extension and every use site is guarded by the
        # HAVE_X11_EXTENSIONS_XRANDR_H probe, which disables that path when
        # the library is not in the graph. Keeping it would pull libxrender,
        # whose published binary was built against the libx11/1.8 graph
        # while this graph pins libx11/6.4 (libxtst/libxi/libxinerama), so
        # CI workers would have to build libxrender from source - which
        # deterministically trips their fork-exhaustion fault during the
        # autotools configure (observed across workers CI-003/006/020/030).
        self.requires("libx11/6.4.0")
        self.requires("libxtst/6.1.0")
        self.requires("libxext/6.4.0")
        self.requires("libxi/6.1.0")
        self.requires("libxinerama/1.1.6")
        self.requires("libxkbfile/1.1.3")
        self.requires("libxkbcommon/1.8.0")
        self.requires("libsm/1.2.6")
        self.requires("libice/1.1.2")

    def build_requirements(self):
        # upstream configure runs pkg_check_modules(xkbcommon)
        self.tool_requires("pkgconf/3.0.6")

    def configure(self):
        # Upstream requires C++20 (CMakeLists.txt sets it and the sources
        # use `using Container::size_type` and `using enum`, both C++20).
        # The CI profile pins cppstd=17 and the OHOS conan toolchain
        # appends -std=c++17 after any CMAKE_CXX_FLAGS injection (the
        # trailing flag wins), so the standard must be raised at the
        # settings level (apache-arrow 25.0.0 precedent).
        self.settings.compiler.cppstd = "20"

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("This recipe targets OpenHarmony PC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # CI #97722 实锤：上游 GitHub symless/synergy-core tag v1.21.4 归档
        # 404（上游删 tag/仓库转私有，codeload/gh-proxy 均死，gitcode
        # mirrors tarball 200 但 sha256 异=重打包）。fallback：gitcode
        # gh_mirrors 同名镜像 Git 协议 clone（v1.21.4 -> commit c8dfecb
        # "Add the 1.21.4 release to the AppStream metainfo (#264)"，git
        # 协议内容即上游树，无重打包问题）。CI Pre-download 会把
        # conandata url 还原官方——get() 404 后走本 fallback，行为幂等。
        # kylin-ai-proto 同款先例（Git 协议+archived commit）。
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            # 浅克隆（--depth 1 --branch v1.21.4）：全量 clone 大仓在 CI
            # 网络下超时（#98736 实锤 97s 失败）；tag 分支 HEAD 即
            # c8dfecb，无需显式 checkout。
            # get() 失败后 source_folder 可能残留下载碎片——git clone
            # 要求空目标目录，先清空再 clone（r5 本机实锤
            # "destination path '.' already exists"）。但 conan 已把
            # export_sources（patches/）预注入 source_folder（r6 本机实锤
            # FileNotFoundError patches/0001-*.patch）——先备份，clone 后恢复。
            patches_dir = os.path.join(self.source_folder, "patches")
            backup_dir = os.path.join(
                os.path.dirname(self.source_folder.rstrip("/")), "_patches_backup"
            )
            if os.path.isdir(patches_dir) and not os.path.isdir(backup_dir):
                shutil.copytree(patches_dir, backup_dir)
            for entry in os.listdir(self.source_folder):
                ep = os.path.join(self.source_folder, entry)
                if os.path.isdir(ep) and not os.path.islink(ep):
                    shutil.rmtree(ep, ignore_errors=True)
                else:
                    try:
                        os.remove(ep)
                    except OSError:
                        pass
            git = Git(self)
            git.clone(url="https://gitcode.com/gh_mirrors/sy/synergy-core.git",
                      target=".",
                      args=["--depth", "1", "--branch", "v1.21.4"])
            shutil.rmtree(os.path.join(self.source_folder, ".git"),
                          ignore_errors=True)
            if os.path.isdir(backup_dir):
                shutil.copytree(backup_dir, patches_dir,
                                dirs_exist_ok=True)

    def generate(self):
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()

        # Keep the default parallelism capped: this is a large CMake project
        # and the CI workers are memory constrained.
        self.conf.define("tools.build:jobs", 2)

        tc = CMakeToolchain(self)
        # barrier P3 precedent: CMake has no HarmonyOS platform module, so
        # CMAKE_SYSTEM_NAME=HarmonyOS leaves UNIX empty and every Linux
        # branch (X11 detection, XWindows platform sources, Unix arch)
        # would be skipped. Force the Linux platform identity.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # Upstream requires C++20 (CMakeLists.txt sets it and the sources
        # use `using Container::size_type` / `using enum`, both C++20).
        # cppstd is raised at the settings level in configure() (the OHOS
        # toolchain appends -std=c++17 after CMAKE_CXX_FLAGS injections);
        # these cache entries keep CMake's own view consistent.
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"

        # Upstream flavor knobs: headless core, deterministic release
        # version, tests built. SYNERGY_CORE_FLAVOR would seed
        # BUILD_TESTS=OFF, so drive the options directly instead.
        tc.variables["BUILD_GUI"] = False
        tc.variables["BUILD_INSTALLER"] = False
        tc.variables["BUILD_TESTS"] = True
        tc.variables["BUILD_X11_SUPPORT"] = True
        tc.variables["SYNERGY_VERSION_RELEASE"] = True
        tc.variables["SYNERGY_ENABLE_ACTIVATION"] = False
        tc.variables["SYNERGY_VERSION_CHECK"] = False
        tc.variables["CMAKE_SKIP_RPATH"] = True
        # No Qt LinguistTools (lrelease/lupdate) exist on this toolchain,
        # so the deskflow_*.qm artifacts I18NTests copies are never
        # produced; exclude that suite rather than failing it.
        tc.variables["SKIP_I18N_TESTS"] = True
        # Upstream VersionOverrides.cmake honors these (el8 CI leg
        # precedent): the registry provides Qt 5.15, not the 6.4 default.
        tc.variables["QT_VERSION_OVERRIDE"] = "5.15"

        # barrier P8 precedent: upstream probes X11 headers and libraries
        # in CMake module mode and links bare library names, so the conan
        # dependency dirs must be visible to the probes and the linker.
        inc = []
        libs = []
        for dep in self.dependencies.host.values():
            if dep.package_folder is None:
                continue
            for inc_dir in dep.cpp_info.includedirs:
                if inc_dir:
                    inc.append(os.path.join(dep.package_folder, inc_dir))
            for lib_dir in dep.cpp_info.libdirs:
                if lib_dir:
                    libs.append(os.path.join(dep.package_folder, lib_dir))
        inc_flags = " ".join(f"-I{p}" for p in inc)
        link_flags = " ".join(f"-L{p}" for p in libs)
        tc.variables["CMAKE_C_FLAGS_INIT"] = inc_flags
        tc.variables["CMAKE_CXX_FLAGS_INIT"] = inc_flags
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = link_flags
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = link_flags
        tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = link_flags
        tc.variables["CMAKE_REQUIRED_INCLUDES"] = ";".join(inc)
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(libs)
        # The toolchain rewrites the *_FLAGS/_INIT blocks from the profile,
        # so the dependency paths also need a channel that survives into
        # target compile and link command lines. The patched
        # cmake/Libraries.cmake reads these cache variables and applies
        # directory-level include_directories()/link_directories() before
        # any target is defined (upstream links bare -lXtst/-lX11 names
        # and includes X11 headers directly).
        tc.variables["SYNERGY_CONAN_INCLUDE_DIRS"] = ";".join(inc)
        tc.variables["SYNERGY_CONAN_LIB_DIRS"] = ";".join(libs)

        # attica5/dewalls precedent: qt5-qtbase ships bin/moc but exports
        # no Qt5::moc executable target, so AUTOMOC needs the tool path.
        qt5 = self.dependencies["qt5-qtbase"]
        for tool, var in (
            ("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
            ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
            ("uic", "CMAKE_AUTOUIC_EXECUTABLE"),
        ):
            path = os.path.join(qt5.package_folder, "bin", tool)
            if os.path.isfile(path):
                tc.variables[var] = path

        tc.generate()

        # AUTOMOC executes the OHOS-ELF moc at build time; it needs to
        # resolve libc++_shared.so and libQt5Core.so from the package.
        self.buildenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(qt5.package_folder, "lib")
        )
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(qt5.package_folder, "bin")
        )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        qt5 = self.dependencies["qt5-qtbase"]
        lib_dirs = []
        for dep in self.dependencies.host.values():
            if dep.package_folder is None:
                continue
            for lib_dir in dep.cpp_info.libdirs:
                if lib_dir:
                    lib_dirs.append(os.path.join(dep.package_folder, lib_dir))

        run_env = os.environ.copy()
        existing = run_env.get("LD_LIBRARY_PATH")
        if existing:
            lib_dirs.append(existing)
        run_env["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs)
        # Qt Test suites that (transitively) link Qt5::Gui instantiate a
        # QGuiApplication; the minimal platform plugin keeps that headless.
        run_env["QT_QPA_PLATFORM"] = "minimal"
        run_env["QT_PLUGIN_PATH"] = os.path.join(qt5.package_folder, "plugins")

        test_dir = os.path.join(self.build_folder, "src", "unittests")

        listed = subprocess.run(
            ["ctest", "--test-dir", test_dir, "-N"],
            cwd=self.build_folder,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if listed.returncode != 0:
            raise ConanInvalidConfiguration(
                "ctest discovery failed:\n{}{}".format(
                    listed.stdout, listed.stderr
                )
            )
        names = re.findall(r"Test\s+#\d+:\s*(\S+)", listed.stdout)
        discovered = len(names)

        # Verbose ctest prints every suite's full Qt Test output, so one
        # pass yields both the suite summary and the function totals.
        ran = subprocess.run(
            ["ctest", "--test-dir", test_dir, "-V"],
            cwd=self.build_folder,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        raw = (ran.stdout or "") + (ran.stderr or "")
        print(raw, end="", flush=True)
        if ran.returncode != 0:
            raise ConanInvalidConfiguration(
                "upstream unittests failed (ctest exit {})".format(ran.returncode)
            )

        m = re.search(
            r"([0-9]+)% tests passed, ([0-9]+) tests failed out of ([0-9]+)", raw
        )
        if not m:
            raise ConanInvalidConfiguration(
                "could not parse the ctest summary from the test output"
            )
        suites_total = int(m.group(3))
        suites_failed = int(m.group(2))

        totals = re.findall(
            r"Totals:\s*([0-9]+) passed,\s*([0-9]+) failed,\s*([0-9]+) skipped", raw
        )
        functions_passed = sum(int(t[0]) for t in totals)
        functions_failed = sum(int(t[1]) for t in totals)
        functions_skipped = sum(int(t[2]) for t in totals)

        marker = {
            "status": "passed",
            "framework": "qtest",
            "command": "ctest --test-dir <build>/src/unittests -V",
            "discovered": discovered,
            "executed": suites_total,
            "passed": suites_total - suites_failed,
            "failed": suites_failed,
            "skipped": 0,
            "functions_passed": functions_passed,
            "functions_failed": functions_failed,
            "functions_skipped": functions_skipped,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # synergy-core is an application; expose the CLI binary.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
