#!/usr/bin/env python3
"""Conan recipe for zeGrapher 3.1.1 — Qt5 math plotter (OHOS aarch64).

zeGrapher is a Qt5 Widgets application (qmake build, upstream ZeGrapher.pro,
QT += widgets printsupport network).  Built natively on aarch64 HarmonyOS PC
against qt5-qtbase/5.15.2.2 (Core/Gui/Widgets/PrintSupport/Network) and
boost/1.90.0.4.1 (headers only: boost/math/binomial + multiprecision).

qmake-driven build (no CMake, so no CMakeDeps): the Qt5 package's own
`bin/qmake` is invoked directly.  qmake resolves Qt libs/headers/includes
through its mkspecs + qt.conf inside the qt5-qtbase package, so no manual
-QT_LIBS/-QT_INCLUDEPATH wiring is needed.  boost headers are injected via
INCLUDEPATH+= and the boost libs are header-only for this consumer.

Upstream test suites: zeGrapher ships no tests/ directory and the .pro
registers no test target (verified against the v3.1.1 tarball — 55 cpp
files, zero test files).  test_package therefore provides the smoke test:
runs the packaged ZeGrapher binary headless (QT_QPA_PLATFORM=offscreen)
and asserts the QApplication boot path reaches the main window loop
without crashing — see test_package/smoke_test.sh.

OHOS adaptations (see notes.md):
  - P1: QMAKE_LFLAGS_RELEASE = -s (strip) is fine, but the upstream .pro
    installs translations/ desktop/ icon files under absolute $${PREFIX}
    paths; we pass INSTALL_ROOT via `make install INSTALL_ROOT=...`
    (qmake standard) which the .pro already honours through its
    target.path/appdata.path etc. entries.
  - P2: updatecheck.cpp phones home to zegrapher.com at startup; kept as
    upstream (pure client-side HTTP, no build impact).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZegrapherConan(ConanFile):
    name = "zegrapher"
    version = "3.1.1"
    description = "zeGrapher — open source 2D math plotter (Qt5)"
    license = "GPL-3.0-or-later"
    homepage = "https://zegrapher.com/"
    url = "https://github.com/AdelKS/ZeGrapher"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
        # boost is header-only for this consumer (math/binomial.hpp +
        # multiprecision/cpp_dec_float.hpp); the shared-library boost build
        # still satisfies the R36 dependency-published gate.
        self.requires("boost/1.90.0.4.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"zegrapher supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _qt5(self):
        return self.dependencies["qt5-qtbase"]

    def _build_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        return env

    def generate(self):
        # qmake reads tool paths from qt.conf inside the Qt package; ensure
        # moc/uic/rcc (which it shells out to) can load their own Qt libs.
        self._build_env().vars(self).save_script("conanbuild_zegrapher")

    def _private_qmake_modules(self, qt5):
        """Use a private, relocatable copy of Qt's qmake metadata.

        The CI Qt package contains absolute paths to its build-worker
        mkspecs/modules-inst files.  qmake then reports installed modules as
        missing.  Rewrite only the private copy; never mutate Conan cache.
        """
        import re
        import shutil

        source_mkspecs = os.path.join(qt5.package_folder, "mkspecs")
        private_mkspecs = os.path.join(self.build_folder, "mkspecs")
        if not os.path.isdir(source_mkspecs):
            raise ConanException("qt5-qtbase package has no mkspecs directory")
        shutil.copytree(source_mkspecs, private_mkspecs, dirs_exist_ok=True)
        module_dir = os.path.join(private_mkspecs, "modules")
        inst_dir = os.path.join(private_mkspecs, "modules-inst")
        if not os.path.isdir(module_dir) or not os.path.isdir(inst_dir):
            raise ConanException("qt5-qtbase package has incomplete qmake module metadata")
        inst_prefix = os.path.join(inst_dir, "")
        for root, _, files in os.walk(private_mkspecs):
            for filename in files:
                if not filename.endswith(".pri"):
                    continue
                path = os.path.join(root, filename)
                with open(path, encoding="utf-8") as stream:
                    content = stream.read()
                # Qt's packaged .pri files may retain either the old
                # modules-inst include path or other absolute build paths
                # (QT_MODULE_*_BASE and QT_TOOL.*.binary).  Rewrite every
                # occurrence in our private copy, leaving the dependency
                # package itself untouched.
                fixed = content.replace(
                    os.path.join(qt5.package_folder, "mkspecs", "modules-inst"),
                    inst_prefix.rstrip(os.sep),
                )
                # The binary package's .pri files can instead contain the
                # build-package prefix directly, e.g.
                # ~/.conan2/p/b/qt5-<id>/b/bin/uic.  Match both .conan2 and
                # .cache/conan2 layouts without depending on the worker home.
                fixed = re.sub(
                    r"/[^\s\"'()]*conan2/p/b/qt5-[^/]+/b",
                    qt5.package_folder,
                    fixed,
                )
                if fixed != content:
                    with open(path, "w", encoding="utf-8") as stream:
                        stream.write(fixed)

        private_bin = os.path.join(self.build_folder, "qt-bin")
        os.makedirs(private_bin, exist_ok=True)
        shutil.copy2(os.path.join(qt5.package_folder, "bin", "qmake"), private_bin)
        with open(os.path.join(private_bin, "qt.conf"), "w", encoding="utf-8") as stream:
            stream.write("[Paths]\nPrefix=%s\n" % self.build_folder)
        return os.path.join(private_bin, "qmake")

    def build(self):
        apply_conandata_patches(self)
        qt5 = self._qt5()
        if not os.path.isfile(os.path.join(qt5.package_folder, "bin", "qmake")):
            raise ConanException(
                "qt5-qtbase/5.15.2.2 does not provide bin/qmake"
            )
        build_dir = os.path.join(self.build_folder, "qbuild")
        src = self.source_folder
        os.makedirs(build_dir, exist_ok=True)
        qmake = self._private_qmake_modules(qt5)

        boost = self.dependencies["boost"]
        boost_inc = os.path.join(boost.package_folder, "include")

        # Equivalent of `qmake ../ZeGrapher.pro && make`.  extra args via
        # QMAKE variables on the command line (CONFIG+=... style).
        # -spec: the packaged qt5-qtbase ships no default QMAKESPEC (qmake
        # -query QMAKESPEC = **Unknown**); the OHOS native toolchain is
        # clang + libc++, matching the shipped linux-clang-libc++ spec.
        # CONFIG+=c++17: upstream .pro pins CONFIG += c++11, but boost 1.90
        # headers (math/tools/type_traits.hpp: std::decay_t/enable_if_t)
        # require C++14+; override to c++17 (matches the OHOS libc++).
        # The module .pri files can also carry stale QT_TOOL paths, so pin
        # every host Qt generator to the packaged executable explicitly.
        qt_bin = os.path.join(qt5.package_folder, "bin")
        tool_overrides = " ".join(
            '"%s=%s"' % (name, os.path.join(qt_bin, tool))
            for name, tool in (
                ("QMAKE_MOC", "moc"),
                ("QMAKE_UIC", "uic"),
                ("QMAKE_RCC", "rcc"),
            )
        )
        self.run(
            '"%s" -spec linux-clang-libc++ "%s" '
            'INCLUDEPATH+="%s" CONFIG+=c++17 %s'
            % (qmake, os.path.join(src, "ZeGrapher.pro"), boost_inc, tool_overrides),
            cwd=build_dir,
        )
        with self._build_env().vars(self).apply():
            # The CI worker filesystem does not permit make's jobserver fifo.
            self.run("make -j1", cwd=build_dir)

    def package(self):
        import shutil
        import subprocess

        build_dir = os.path.join(self.build_folder, "qbuild")
        src = self.source_folder
        # qmake .pro install rules honour INSTALL_ROOT (standard qmake
        # DESTDIR-of-install mechanism).
        self.run(
            'make install INSTALL_ROOT="%s"' % self.package_folder,
            cwd=build_dir,
        )
        # licenses
        from conan.tools.files import copy

        copy(self, "LICENSE", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=src, dst=os.path.join(self.package_folder, "licenses"))

        # OHOS: unsigned ELF executables are not runnable (rc=126
        # "Operation not permitted" — §7 ELF-signing gotcha).  Self-sign
        # every packaged executable.
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
            if not os.path.isfile(signer):
                raise ConanException("binary-sign-tool not found; required to sign OHOS executables")
            objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
            strip_sign = os.path.isfile(objcopy)
            bin_dir = os.path.join(self.package_folder, "bin")
            if os.path.isdir(bin_dir):
                for name in os.listdir(bin_dir):
                    path = os.path.join(bin_dir, name)
                    if not os.path.isfile(path) or os.path.islink(path):
                        continue
                    signed = path + ".signed"
                    # qmake's `strip -s` (QMAKE_LFLAGS_RELEASE=-s / install
                    # step) leaves a stale .codesign section behind; the
                    # signer refuses to overwrite ("sign elf failed").
                    # Remove it first so signing always starts clean.
                    if strip_sign:
                        subprocess.check_call(
                            [objcopy, "--remove-section", ".codesign", path],
                            stderr=subprocess.DEVNULL,
                        )
                    subprocess.check_call([
                        signer, "sign", "-selfSign", "1",
                        "-inFile", path, "-outFile", signed,
                        "-signAlg", "SHA256withECDSA",
                    ])
                    shutil.move(signed, path)
                    os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
