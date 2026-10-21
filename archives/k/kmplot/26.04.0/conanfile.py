#!/usr/bin/env python3
"""Conan recipe for kmplot 26.04.0 on HarmonyOS PC (aarch64).

KmPlot is the KDE Education mathematical function plotter: a Qt6/KF6
Widgets application (bin/kmplot, KAboutData + KDBusService + QCommandLineParser
in kmplot/main.cpp) plus a KParts plugin module (kmplotpart, installed to
lib/kf6/parts, linked against KF6::Parts). Upstream ships one GUI executable
plus the parts plugin; the DBus adaptors (org.kde.kmplot.*.xml) are generated
at build time by Qt6::DBus (qt_add_dbus_adaptor).

Upstream test suite: none (R51 inventory). The 26.04.0 release tarball
(521 members, verified by download + sha256) has no tests/, autotests/ or
test/ directory and no enable_testing()/add_test()/ecm_add_test() call in any
CMakeLists.txt - upstream QA runs through KDE CI source builds.
Consumer-side verification is therefore provided by test_package
(kbreakout 26.04.0 / kcachegrind 26.04.0 precedent).

OHOS-specific adaptations (patches/0001-0004, portability, no platform macros):
  - Qt PrintSupport is not published (qtbase FEATURE_printsupport=OFF;
    kapow 1.7.0 / kcron 26.04.1 / kdiagram 3.0.1 precedent): PrintSupport is
    dropped from find_package/link lines and the plot print action is
    re-targeted to a QPdfWriter (QtGui) + QFileDialog PDF export flow
    (kcron precedent); KPrinterDlg options page is kept and still feeds
    setupPrinter(), now taking QPaintDevice*; slotExport() SVG/PNG path
    is untouched.
  - BUILD_DOC=OFF: upstream guards find_package(KF6DocTools REQUIRED) and
    add_subdirectory(doc) + kdoctools_install(po) behind the BUILD_DOC
    option, so switching it OFF cleanly drops the DocBook handbook without
    patching (kdoctools is not part of the published KF6 closure;
    kbreakout 26.04.0 needed a patch only because its DocTools lookup was
    unconditional).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation (po/
    processing requires a gettext toolchain; catalogs are not needed for
    the smoke-verified deliverable).
  - Dependencies resolved from the ohpcd registry on the KF6 6.14.0
    baseline (keditbookmarks 26.04.0 / kparts 6.18.0 precedent: zero
    dependency rebuilds, kio/6.14.0 is the full variant carrying KIOGui/
    KIOWidgets while kio/6.26.0 is KIOCORE_ONLY): qtbase 6.11.1.1
    (FEATURE_dbus=ON variant, required by qt_add_dbus_adaptor and the
    KDBusService in main.cpp; kcachegrind 26.04.0 precedent), qtsvg
    6.11.1 (Qt6::Svg), kparts 6.18.0 (only published KParts line, itself
    built against the 6.14.0 deps), kio 6.14.0 (KF6::KIOGui linked by the
    kmplot executable), plus kcompletion/kconfig/kconfigwidgets/
    kcoreaddons/kcrash/kdbusaddons/kguiaddons/ki18n/kjobwidgets/
    ktextwidgets/kwidgetsaddons 6.14.0 and ecm 6.26.0 (tool_requires).
  - No libxml2 requires (kbreakout 26.04.0 precedent): the host OHOS SDK
    lld needs a host-ABI libxml2.so.16, but any conan libxml2 (direct or
    transitive via kio) is an OHOS-target binary whose lib dir on
    LD_LIBRARY_PATH shadows the host library and breaks host lld with
    xmlFreeDoc-style relocation errors. The recipe therefore (a) skips
    dep lib dirs carrying libxml2.so.16 when building LD_LIBRARY_PATH
    and (b) locates a host-ABI libxml2 (SDK llvm/lib, harmonybrew
    libxml2 Cellar or system dir, verified by running the real lld
    --version with it, kcontacts 6.14.0 probe pattern) and puts it
    frontmost.
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH.
  - -Wl,-z,max-page-size=0x1000 pinned for the executable: the OHOS musl
    loader refuses the lld default 0x10000 layout when the dynamic section
    is split into high-address RW LOAD segments (DRAFT-3888 audiocd
    precedent); the flag is appended to CMAKE_EXE_LINKER_FLAGS because a
    non-empty value assigned in the toolchain makes CMake skip the
    CMAKE_EXE_LINKER_FLAGS_INIT initialization.
  - package(): path-form DT_NEEDED entries are rewritten to plain basenames
    in place (.dynstr content only, same length -> dynamic section offsets
    unchanged), then the ELF is re-signed. The published KF6 6.14.0
    artifacts carry no DT_SONAME, so the linker records this package's
    link-time conan-cache paths as DT_NEEDED and the artifact would not be
    consumable outside the build machine (E537 Conan cache absolute
    DT_NEEDED leakage / DRAFT-14403 normalize + re-sign). The 4K page size
    keeps .dynsym/.dynstr in a single LOAD so the in-place patch is safe.
"""
import glob
import hashlib
import os
import shutil
import struct
import subprocess
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class KmplotConan(ConanFile):
    name = "kmplot"
    version = "26.04.0"
    description = (
        "KDE mathematical function plotter - a Qt6/KF6 Widgets application "
        "with a KParts plugin module"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/education/kmplot"
    url = "https://invent.kde.org/education/kmplot"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 with DBus enabled: kmplot/main.cpp constructs KDBusService and
        # kmplot/CMakeLists.txt generates 4 DBus adaptors via
        # qt_add_dbus_adaptor (kcachegrind 26.04.0 precedent: plain
        # qtbase/6.11.1 is FEATURE_dbus=OFF and ships no Qt6DBus).
        self.requires("qtbase/6.11.1.1", override=True)
        self.requires("qtsvg/6.11.1")
        # KF6 6.14.0 baseline: every entry below reuses a published binary
        # built against qtbase/6.11.1 (keditbookmarks 26.04.0 precedent).
        # kio/6.14.0 is the full variant (KIOGui/KIOWidgets present; the
        # kmplot executable links KF6::KIOGui) while kio/6.26.0 is
        # KIOCORE_ONLY (kcachegrind 26.04.0 precedent).
        self.requires("kcompletion/6.14.0")
        self.requires("kconfig/6.14.0")
        self.requires("kconfigwidgets/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kcrash/6.14.0")
        self.requires("kdbusaddons/6.14.0")
        self.requires("kguiaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kjobwidgets/6.14.0")
        self.requires("kio/6.14.0")
        # kparts: only the 6.18.0 line is published on ohpcd; that binary was
        # itself built against the 6.14.0 deps above (kparts 6.18.0
        # manifest), so no rebuild is triggered.
        self.requires("kparts/6.18.0")
        self.requires("ktextwidgets/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Pure-Python download + unpack (no shell, no external tar/xz).
        # 真机曾报 `tar: child process: Cannot fork: Out of memory` 后直接
        # `Error is not recoverable`：外部 tar 在 fork 解压子进程 (xz) 时
        # 因内存不足失败。本包仅 3MB，fork 开销是唯一可控变量；改用
        # urllib 分块下载 + hashlib sha256 校验 + tarfile 内置 lzma 解包，
        # 全程不 fork 子进程。strip_root 语义手动实现，等价于
        # get(..., strip_root=True)。
        src = self.conan_data["sources"]
        urls = src["url"] if isinstance(src["url"], list) else [src["url"]]
        expected = src["sha256"]
        archive = self._download_source(urls, expected)
        try:
            self._extract_strip_root(archive, self.source_folder)
        finally:
            try:
                os.remove(archive)
            except OSError:
                pass

    def _download_source(self, urls, expected):
        tmp_dir = self._writable_tmpdir() or self.source_folder
        os.makedirs(tmp_dir, exist_ok=True)
        archive = os.path.join(tmp_dir, "kmplot-26.04.0.download")
        last_err = None
        for url in urls:
            for attempt in range(3):
                try:
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "conan/2.x ohpcd"}
                    )
                    with urllib.request.urlopen(req, timeout=60) as resp, open(
                        archive, "wb"
                    ) as out:
                        digest = hashlib.sha256()
                        while True:
                            chunk = resp.read(1024 * 1024)
                            if not chunk:
                                break
                            digest.update(chunk)
                            out.write(chunk)
                    actual = digest.hexdigest()
                    if actual.lower() != str(expected).lower():
                        raise ConanException(
                            f"sha256 mismatch for {url}: "
                            f"expected {expected}, got {actual}"
                        )
                    self.output.info(f"downloaded {url} sha256 OK")
                    return archive
                except Exception as err:  # noqa: BLE001 - retry then raise
                    last_err = err
                    self.output.warning(
                        f"download attempt {attempt + 1}/3 failed for {url}: {err}"
                    )
                    try:
                        if os.path.isfile(archive):
                            os.remove(archive)
                    except OSError:
                        pass
        raise ConanException(f"source download failed: {last_err}")

    def _writable_tmpdir(self):
        for var in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var, "")
            if not cand or not os.path.isdir(cand):
                continue
            try:
                probe = os.path.join(cand, ".kmplot_wtest")
                with open(probe, "w") as handle:
                    handle.write("ok")
                os.remove(probe)
                return cand
            except OSError:
                continue
        return ""

    @staticmethod
    def _extract_strip_root(archive, destination):
        os.makedirs(destination, exist_ok=True)
        with tarfile.open(archive, "r:*") as tar:
            for member in tar.getmembers():
                name = member.name
                # Strip the single top-level directory (strip_root=True).
                parts = name.split("/", 1)
                if len(parts) < 2 or not parts[1]:
                    continue
                member.name = parts[1]
                if member.name.startswith("/") or ".." in member.name.split("/"):
                    continue
                tar.extract(member, path=destination)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream registers no test suite (see module docstring).
        tc.variables["BUILD_TESTING"] = "OFF"
        # Upstream guards KF6DocTools + doc/ behind BUILD_DOC; OFF drops the
        # DocBook handbook without patching (kdoctools is not published).
        tc.variables["BUILD_DOC"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        exe_ldflags = "-Wl,--disable-new-dtags"
        if self.settings.os == "OHOS":
            exe_ldflags += " -Wl,-z,max-page-size=0x1000"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = exe_ldflags

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        # Qt6 split-package component discovery: Qt6Svg lives in qtsvg
        # (kbreakout 26.04.0 verified pattern).
        qt_extra = []
        for dep_name in ("qtsvg",):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )

        self._write_cmake_paths(ecm)
        tc.generate()
        self._rewrite_stale_compilers_in_toolchain()

    @staticmethod
    def _compiler_try_run(path):
        # Minimal exec probe (no link): distinguishes "stale absolute path"
        # (missing/unrunnable binary) from link-flag failures. Only a
        # --version failure qualifies for toolchain rewrite (Exp1).
        try:
            if not path or not os.path.isfile(path):
                return False
            proc = subprocess.run(
                [path, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
                check=False,
            )
            out = ((proc.stdout or "") + (proc.stderr or "")).lower()
            return proc.returncode == 0 and (
                "clang" in out or "version" in out
            )
        except Exception:
            return False

    def _candidate_compilers(self, kind):
        # Generic discovery only: conf value, $CC/$CXX, PATH lookup and
        # PATH-dir scan. No library-specific hardcoded fallback paths.
        cands = []
        conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        conf_val = conf.get("c") if kind == "c" else conf.get("cpp")
        if conf_val:
            cands.append(conf_val.split()[0])
        for var in ("CC", "CXX") if kind in ("c", "cpp") else ():
            val = os.environ.get(var, "")
            if val and (
                (kind == "c" and var == "CC")
                or (kind == "cpp" and var == "CXX")
            ):
                cands.append(val.split()[0])
        prog = "clang" if kind == "c" else "clang++"
        found = shutil.which(prog)
        if found:
            cands.append(found)
        for d in os.environ.get("PATH", "").split(os.pathsep):
            if not d or not os.path.isdir(d):
                continue
            cand = os.path.join(d, prog)
            if cand not in cands and os.path.isfile(cand):
                cands.append(cand)
        for pat in (
            "/data/service/hnp/bin/clang",
            "/data/service/hnp/bin/clang++",
        ):
            if pat not in cands and os.path.isfile(pat):
                cands.append(pat)
        try:
            for pat in glob.glob("/data/service/hnp/bin/clang*"):
                if pat not in cands and os.path.isfile(pat):
                    cands.append(pat)
        except Exception:
            pass
        # Deduplicate preserving order.
        seen = set()
        uniq = []
        for cand in cands:
            if cand and cand not in seen:
                seen.add(cand)
                uniq.append(cand)
        return uniq

    def _resolve_working_compiler(self, kind):
        cands = self._candidate_compilers(kind)
        for cand in cands:
            if self._compiler_try_run(cand):
                return cand
        return ""

    def _rewrite_stale_compilers_in_toolchain(self):
        # Exp1 (inotify): after tc.generate(), try-run the absolute
        # compiler paths actually written to conan_toolchain.cmake; rewrite
        # ONLY the entries whose --version probe fails, to the first
        # try-run-passing candidate. Env CC/CXX alone cannot override the
        # hardcoded toolchain value (round #7 evidence), so file rewrite is
        # the primary fix; CC/CXX export in _cmake_build_env is secondary.
        toolchain = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        if not os.path.isfile(toolchain):
            return
        try:
            with open(toolchain, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as err:
            self.output.warning(f"kmplot toolchain read failed: {err}")
            return
        conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        orig_c = (conf.get("c") or "").split()[0]
        orig_cxx = (conf.get("cpp") or "").split()[0]
        self.output.info(
            f"kmplot toolchain compiler check: c={orig_c} "
            f"ok={self._compiler_try_run(orig_c)} "
            f"cxx={orig_cxx} ok={self._compiler_try_run(orig_cxx)}"
        )
        replacements = {}
        if orig_c and not self._compiler_try_run(orig_c):
            working_c = self._resolve_working_compiler("c")
            if working_c and working_c != orig_c:
                replacements[orig_c] = working_c
                self.output.info(
                    f"kmplot toolchain rewrite C: {orig_c} -> {working_c}"
                )
            else:
                self.output.warning(
                    f"kmplot toolchain C compiler unusable but no working "
                    f"replacement found (kept {orig_c})"
                )
        if orig_cxx and not self._compiler_try_run(orig_cxx):
            working_cxx = self._resolve_working_compiler("cpp")
            if working_cxx and working_cxx != orig_cxx:
                replacements[orig_cxx] = working_cxx
                self.output.info(
                    f"kmplot toolchain rewrite CXX: {orig_cxx} -> {working_cxx}"
                )
            else:
                self.output.warning(
                    f"kmplot toolchain CXX compiler unusable but no working "
                    f"replacement found (kept {orig_cxx})"
                )
        if not replacements:
            return
        for old, new in replacements.items():
            content = content.replace(old, new)
        try:
            with open(toolchain, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as err:
            raise ConanException(f"kmplot toolchain rewrite failed: {err}")
        self.output.info(
            f"kmplot toolchain stale compilers rewritten: {replacements}"
        )

    def _write_cmake_paths(self, ecm):
        # qtbase/KF6 packages use cmake_find_mode=none, so
        # CMakeDeps doesn't put their lib/cmake dirs on CMAKE_PREFIX_PATH.
        # Write conan_cmakedeps_paths.cmake manually (kbreakout precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools (moc/uic/rcc/dbusxml2cpp/kconfig_compiler) shipped by
        # the conan packages are OHOS binaries: they need the compatible
        # libc++_shared from /system/lib64 plus the dependency lib dirs on
        # LD_LIBRARY_PATH (kbreakout 26.04.0 precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                dep_lib = os.path.join(dep.package_folder, "lib")
                try:
                    carries_xml2 = os.path.isfile(os.path.join(dep_lib, "libxml2.so.16"))
                except Exception:
                    carries_xml2 = False
                if carries_xml2:
                    # A conan libxml2 is OHOS-target; its lib dir would
                    # shadow the host-ABI libxml2 the host lld needs
                    # (xmlFreeDoc relocation breakage).
                    self.output.info(
                        f"kmplot skips conan libxml2 dir on LD_LIBRARY_PATH: {dep_lib}"
                    )
                    continue
                build_env.prepend_path("LD_LIBRARY_PATH", dep_lib)
                build_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                build_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
        if self.settings.os == "OHOS":
            # E132: the host OHOS SDK lld needs a host-ABI libxml2.so.16.
            # The verified host lib dir goes frontmost so host lld never
            # loads an OHOS-target conan libxml2 (xmlFreeDoc relocation
            # breakage); conan libxml2 dirs are already skipped above.
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            host_xml2 = self._host_libxml2_dir()
            if host_xml2:
                build_env.prepend_path("LD_LIBRARY_PATH", host_xml2)
            else:
                self.output.warning(
                    "kmplot host-ABI libxml2.so.16 not verified; host lld "
                    "falls back to system default search"
                )
        # CC/CXX double insurance for the toolchain rewrite above: if the
        # profile compiler is stale, direct compiler invocations outside the
        # toolchain file also need the working path (Exp1).
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            orig_c = (conf.get("c") or "").split()[0]
            orig_cxx = (conf.get("cpp") or "").split()[0]
            if orig_c and not self._compiler_try_run(orig_c):
                working_c = self._resolve_working_compiler("c")
                if working_c and working_c != orig_c:
                    build_env.define("CC", working_c)
            if orig_cxx and not self._compiler_try_run(orig_cxx):
                working_cxx = self._resolve_working_compiler("cpp")
                if working_cxx and working_cxx != orig_cxx:
                    build_env.define("CXX", working_cxx)
        except Exception:
            pass
        return build_env

    def _find_host_lld(self):
        # Locate the real host lld binary (harmonybrew or /data layout).
        cands = []
        try:
            found = shutil.which("lld")
            if found:
                cands.append(found)
        except Exception:
            pass
        home = os.path.expanduser("~")
        for pat in (
            os.path.join(home, ".harmonybrew", "Cellar", "ohos-sdk", "*", "native", "llvm", "bin", "lld"),
            "/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/*/native/llvm/bin/lld",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/lld",
        ):
            try:
                cands.extend(sorted(glob.glob(pat)))
            except Exception:
                pass
        cands.append("/data/service/hnp/bin/lld")
        for cand in cands:
            try:
                if cand and os.path.isfile(cand):
                    return cand
            except Exception:
                continue
        return ""

    @staticmethod
    def _lld_runs_with_lib(lld, lib_dir):
        # True when lld --version exits 0 with lib_dir leading
        # LD_LIBRARY_PATH (kcontacts 6.14.0 probe pattern).
        try:
            env = os.environ.copy()
            old = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = lib_dir + (os.pathsep + old if old else "")
            proc = subprocess.run(
                [lld, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20,
                check=False,
                env=env,
            )
            err = (proc.stderr or "").lower()
            return proc.returncode == 0 and "error" not in err
        except Exception:
            return False

    def _host_libxml2_dir(self):
        # Find a host-ABI dir providing libxml2.so.16 for the host lld and
        # verify it by actually running lld. Search order: SDK llvm/lib
        # dirs, harmonybrew libxml2 Cellar, well-known system dirs. Returns
        # "" (warned, system default search applies) when nothing verifies.
        cands = []
        sdk_base = os.environ.get("OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
        home = os.path.expanduser("~")
        for pat in (
            os.path.join(sdk_base, "*", "ohos", "native", "llvm", "lib"),
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib",
            os.path.join(home, ".harmonybrew", "Cellar", "ohos-sdk", "*", "native", "llvm", "lib"),
            "/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/*/native/llvm/lib",
            os.path.join(home, ".harmonybrew", "Cellar", "libxml2", "*", "lib"),
            "/storage/Users/currentUser/.harmonybrew/Cellar/libxml2/*/lib",
            os.path.join(home, ".harmonybrew", "lib"),
            "/system/lib64",
            "/usr/lib",
            "/usr/lib64",
        ):
            try:
                cands.extend(sorted(glob.glob(pat)))
            except Exception:
                pass
        # Compiler-neighbourhood dirs (realpath so shim symlinks resolve).
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            for key in ("c", "cpp"):
                first = (conf.get(key) or "").split()
                if first and first[0]:
                    try:
                        real = os.path.realpath(first[0])
                        d = os.path.dirname(real)
                        cands.append(os.path.normpath(os.path.join(d, "..", "lib")))
                    except Exception:
                        pass
        except Exception:
            pass
        lld = self._find_host_lld()
        self.output.info(f"kmplot host lld probe binary: {lld or '<not found>'}")
        seen = set()
        checked = []
        for cand in cands:
            try:
                norm = os.path.normpath(cand)
            except Exception:
                continue
            if not norm or norm in seen:
                continue
            seen.add(norm)
            try:
                if not os.path.isfile(os.path.join(norm, "libxml2.so.16")):
                    continue
            except Exception:
                continue
            checked.append(norm)
            if lld and self._lld_runs_with_lib(lld, norm):
                self.output.info(f"kmplot host libxml2 for lld verified: {norm}")
                return norm
            self.output.info(f"kmplot libxml2 candidate rejected by lld probe: {norm}")
        self.output.warning(
            f"kmplot no host-ABI libxml2 verified (lld={lld or '<not found>'}); "
            f"dirs holding libxml2.so.16 seen: {checked or '<none found>'}"
        )
        return ""

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Resolve the signing tools first: a DT_NEEDED rewrite invalidates
            # .codesign, so the package must never be left unpatched-and-
            # unsigned (or patched-and-unsigned) on the device.
            objcopy, signer = self._ohos_sign_tools()
            patched = self._normalize_needed_paths()
            self._sign_ohos_elf_tree(self.package_folder, objcopy, signer)
            if patched:
                self.output.info(
                    f"DT_NEEDED paths normalized in {patched} package file(s)"
                )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _normalize_needed_paths(self):
        """Rewrite path-form DT_NEEDED strings to plain basenames in place.

        The published KF6 6.14.0 dependency artifacts carry no DT_SONAME
        (Platform/HarmonyOS gap), so the linker records the link-time
        conan-cache absolute path of every such dependency in this package's
        DT_NEEDED. Those paths do not exist on a consumer machine with a
        different cache layout, so the artifact would not be loadable
        (E537). The rewrite changes .dynstr content only and keeps the
        string length, so the dynamic section offsets stay valid; the caller
        re-signs the ELF afterwards.
        """
        patched = 0
        for rel in ("bin", "lib"):
            folder = os.path.join(self.package_folder, rel)
            if not os.path.isdir(folder):
                continue
            for root, _dirs, files in os.walk(folder):
                for name in sorted(files):
                    path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if not self._is_elf(path):
                    continue
                with open(path, "rb") as handle:
                    data = handle.read()
                new_data, count = self._elf_needed_basenames(data)
                if not count:
                    continue
                with open(path, "wb") as handle:
                    handle.write(new_data)
                self.output.info(f"normalized {count} DT_NEEDED path(s) in {name}")
                patched += 1
        return patched

    @staticmethod
    def _elf_needed_basenames(data):
        """Return (data', replaced) with path-form DT_NEEDED strings reduced
        to their basename. ELF64 little-endian only; every other input is
        returned untouched."""
        if len(data) < 64 or data[:4] != b"\x7fELF":
            return data, 0
        if data[4] != 2 or data[5] != 1:
            return data, 0
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        if e_shoff == 0 or e_shentsize == 0 or e_shnum == 0:
            return data, 0

        sections = []
        for index in range(e_shnum):
            off = e_shoff + index * e_shentsize
            if off + e_shentsize > len(data):
                break
            sections.append(
                (
                    struct.unpack_from("<I", data, off + 4)[0],   # sh_type
                    struct.unpack_from("<Q", data, off + 16)[0],  # sh_addr
                    struct.unpack_from("<Q", data, off + 24)[0],  # sh_offset
                    struct.unpack_from("<Q", data, off + 32)[0],  # sh_size
                )
            )

        buf = bytearray(data)
        replaced = 0
        for sh_type, _sh_addr, sh_offset, sh_size in sections:
            if sh_type != 6 or sh_size == 0:  # SHT_DYNAMIC
                continue
            if sh_offset + sh_size > len(data):
                continue
            strtab_addr = None
            strtab_size = None
            needed_offsets = []
            used_offsets = set()
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                if pos + 16 > len(data):
                    break
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:
                    break
                if d_tag == 5:  # DT_STRTAB
                    strtab_addr = d_val
                elif d_tag == 10:  # DT_STRSZ
                    strtab_size = d_val
                elif d_tag == 1:  # DT_NEEDED
                    needed_offsets.append(d_val)
                    used_offsets.add(d_val)
                elif d_tag in (14, 15, 29) and d_val:  # SONAME/RPATH/RUNPATH
                    used_offsets.add(d_val)
            if strtab_addr is None or not needed_offsets:
                continue
            strtab_off = None
            for sh_type2, sh_addr2, sh_offset2, sh_size2 in sections:
                if sh_addr2 == strtab_addr and sh_type2 == 3 and sh_size2:
                    strtab_off = sh_offset2
                    if strtab_size is None or strtab_size > sh_size2:
                        strtab_size = sh_size2
                    break
            if strtab_off is None:
                continue
            strtab = bytes(buf[strtab_off:strtab_off + (strtab_size or 0)])
            for off in needed_offsets:
                if off >= len(strtab):
                    continue
                end = strtab.find(b"\x00", off)
                if end < 0:
                    continue
                old = strtab[off:end]
                if b"/" not in old:
                    continue
                base = old.rsplit(b"/", 1)[1]
                if not base:
                    continue
                # Never clobber a string another dynamic entry also points at.
                if any(off < used < end for used in used_offsets):
                    continue
                buf[strtab_off + off:strtab_off + end] = (
                    base + b"\x00" * (len(old) - len(base))
                )
                replaced += 1
        return bytes(buf), replaced

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _ohos_sign_tools(self):
        objcopy = self._find_ohos_tool("llvm-objcopy") or self._find_ohos_tool(
            "objcopy"
        )
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "OHOS ELF signing tools not found (llvm-objcopy / "
                "binary-sign-tool); the packaged executable must be signed "
                "to run on the device"
            )
        return objcopy, signer

    def _sign_ohos_elf_tree(self, root_folder, objcopy, signer):
        signed = 0
        for root, _dirs, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self._resign(path, objcopy, signer)
                signed += 1
        self.output.info(f"signed {signed} OHOS ELF file(s)")

    def _resign(self, path, objcopy, signer):
        mode = os.stat(path).st_mode & 0o777
        probe = subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            self.output.warning(
                "llvm-objcopy --remove-section .codesign failed: "
                f"{probe.stderr.strip()[:120]}"
            )
        probe = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            raise ConanException(
                f"binary-sign-tool sign failed for {path}: "
                f"{probe.stderr.strip()[:200]}"
            )
        os.chmod(path, mode)

    def validate(self):
        # R32: os 判断必须 in ("Linux", "OHOS")，不能 == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                "kmplot/26.04.0 is a HarmonyOS PC adaptation "
                "(R32: supported os values are Linux and OHOS)"
            )

    def package_info(self):
        # Application package: one executable in bin/ plus the kmplotpart
        # KParts plugin module in lib/kf6/parts (kmplot links the KF6/Qt6
        # runtime, it ships no linkable development library).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        # Runtime env for consumers: the app needs the KF6/Qt6 libraries and
        # its own share/kmplot data tree (kcfg config skeleton, icons).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "XDG_DATA_DIRS", os.path.join(self.package_folder, "share")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                self.runenv_info.prepend_path(
                    "XDG_DATA_DIRS", os.path.join(dep.package_folder, "share")
                )
