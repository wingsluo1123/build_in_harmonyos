#!/usr/bin/env python3
"""Conan recipe — uuu 1.5.243 (NXP Universal Update Utility).

uuu is the NXP i.MX chip image deploy tool (mfgtools 3.0), a CMake
command-line application. The top-level build compiles libuuu (static
uuc_s) plus the uuu executable and installs uuu to bin/.

Build system: CMake (top-level adds libuuu + uuu only).
License: BSD-3-Clause.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file


class UuuConan(ConanFile):
    name = "uuu"
    version = "1.5.243"
    description = "NXP Universal Update Utility for i.MX chips (mfgtools)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/nxp-imx/mfgtools"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # No default_options pins: bzip2/openssl keep recipe defaults
    # (static on OHOS), libusb/zstd keep shared defaults to reuse the
    # published ohpcd binaries. tinyxml2 is NOT a Conan dependency:
    # its 10.0.0 recipe dead-ends on this host -- shared=True fails
    # validate() (signing tools absent on preflight, 2026-10-17 graph
    # error) while shared=False has no published static binary for
    # cppstd=17 and its CMakeToolchain source rebuild fails with
    # "System is unknown to cmake, Platform/HarmonyOS" under CMake
    # 4.4.3. Instead the tarball's vendored tinyxml2
    # (9.0.0, upstream pinned) is wired into lib uuc_s in source()
    # with replace_in_file (no patch files, no extra compiler step).

    # R38: this package produces the uuu CLI executable.
    # R26: application package, no system-name library collision risk.

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "uuu is only supported on Linux/OHOS, got %s" % self.settings.os
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Matches the nixpkgs buildInputs for mfgtools 1.5.243 plus the
        # zlib pkg-config module required by uuu/CMakeLists.txt.
        # libzip is NOT required: libuuu/zip.cpp implements zip parsing
        # on top of zlib inflate directly (no libzip include/link).
        # tinyxml2 is NOT a Conan dependency (see _patch_bundled_tinyxml2):
        # the release tarball's vendored tinyxml2 9.0.0 (upstream pinned)
        # is wired into lib uuc_s in source().
        self.requires("bzip2/1.0.8")
        self.requires("libusb/1.0.27")
        self.requires("openssl/1.1.1w")
        self.requires("zstd/1.5.6")
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        # libuuu/CMakeLists.txt and uuu/CMakeLists.txt use
        # find_package(PkgConfig) + pkg_check_modules() against the
        # PkgConfigDeps-generated .pc files, but the preflight worker has
        # no system pkg-config ("Could NOT find PkgConfig (missing:
        # PKG_CONFIG_EXECUTABLE)", 2026-10-17 round). Provide it via the
        # in-repo consensus pin (same failure/fix as xmlsec 1.3.12,
        # ctpl/0.3.5, burp2/2.1.0, fcft/3.3.3).
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_bundled_tinyxml2()
        self._patch_libusb_init_graceful()

    def _patch_bundled_tinyxml2(self):
        # Conan tinyxml2/10.0.0 dead-ends on OHOS preflight (shared
        # validate needs absent signing tools; static has no cppstd=17
        # binary and its recipe rebuild fails on CMake 4.4.3), and the
        # preflight /bin/sh cannot exec the absolute compiler path for
        # a manual pre-build. So wire the release tarball's own vendored
        # tinyxml2 (9.0.0, upstream pinned) directly into the uuu build:
        # its objects join lib uuc_s, the uuu exe links uuc_s. No Conan
        # tinyxml2 package, no tinyxml2.pc, no extra compile step --
        # everything is compiled by uuu's own CMake toolchain (E092).
        # This method also wires the conan bzip2/zlib locations: upstream
        # relies on system include/link paths for them (no BZIP2/zlib
        # include_dirs in libuuu, bare "bz2" at the exe link), which do not
        # exist on the OHOS worker (2026-10-17 round: "fatal error:
        # 'bzlib.h' file not found" in libuuu/buffer.cpp).
        # Anchors are upstream literals; missing anchor fails loudly.
        lib_cmake = os.path.join(self.source_folder, "libuuu", "CMakeLists.txt")
        replace_in_file(
            self, lib_cmake,
            "pkg_check_modules(TINYXML2 REQUIRED tinyxml2)",
            "# OHOS: vendored tinyxml2 9.0.0 compiled in (no Conan dep)\n"
            "pkg_check_modules(LIBZ REQUIRED zlib)  # OHOS: libuuu/zip.cpp "
            "needs zlib.h via zip.h, but upstream only queries zlib in "
            "uuu/ scope",
        )
        replace_in_file(
            self, lib_cmake,
            "include_directories(${LIBUSB_INCLUDE_DIRS} ${LIBZSTD_INCLUDE_DIRS} ${UUUOPENSLL_INCLUDE_DIR} ${TINYXML2_INCLUDE_DIRS} include)",
            "include_directories(${LIBUSB_INCLUDE_DIRS} ${LIBZSTD_INCLUDE_DIRS} ${UUUOPENSLL_INCLUDE_DIR} include ${BZIP2_INCLUDE_DIR} ${LIBZ_INCLUDE_DIRS})\n"
            "include_directories(${CMAKE_SOURCE_DIR}/tinyxml2)",
        )
        replace_in_file(
            self, lib_cmake,
            "\tsparse.cpp\n\tbmap.cpp\n)",
            "\tsparse.cpp\n\tbmap.cpp\n\t${CMAKE_SOURCE_DIR}/tinyxml2/tinyxml2.cpp\n)",
        )
        exe_cmake = os.path.join(self.source_folder, "uuu", "CMakeLists.txt")
        replace_in_file(
            self, exe_cmake,
            "pkg_check_modules(TINYXML2 REQUIRED tinyxml2)",
            "# OHOS: vendored tinyxml2 9.0.0 compiled in (no Conan dep)",
        )
        replace_in_file(
            self, exe_cmake,
            "link_directories(${CMAKE_CURRENT_SOURCE_DIR}/libuuu ${LIBUSB_LIBRARY_DIRS} ${LIBZSTD_LIBRARY_DIRS} ${LIBZ_LIBRARY_DIRS} ${TINYXML2_LIBRARY_DIRS})",
            "link_directories(${CMAKE_CURRENT_SOURCE_DIR}/libuuu ${LIBUSB_LIBRARY_DIRS} ${LIBZSTD_LIBRARY_DIRS} ${LIBZ_LIBRARY_DIRS})",
        )
        replace_in_file(
            self, exe_cmake,
            "target_link_libraries(uuu uuc_s ${OPENSSL_LIBRARIES} ${LIBUSB_LIBRARIES} ${LIBZ_LIBRARIES} ${LIBZSTD_LIBRARIES} ${TINYXML2_LIBRARIES} dl bz2)",
            "# OHOS: bare -lbz2 has no system lib dir on the worker; link "
            "the conan bzip2 by full path (BZIP2_LIBRARIES hinted in "
            "generate())\n"
            "target_link_libraries(uuu uuc_s ${OPENSSL_LIBRARIES} ${LIBUSB_LIBRARIES} ${LIBZ_LIBRARIES} ${LIBZSTD_LIBRARIES} dl ${BZIP2_LIBRARIES})",
        )
        # OHOS (2026-10-17 round): libuuu/http.cpp defines base64_encode()
        # inside `#ifdef UUUSSL` but calls it unconditionally in the
        # non-Windows HttpGetHeader() (Authorization: Basic ...). When
        # FindOpenSSL misses the Conan package, UUUSSL stays undefined and
        # the build dies with `use of undeclared identifier
        # 'base64_encode'`. Basic auth is plain HTTP, not SSL-specific, so
        # hoist the helper out of the SSL guard: close the guard before
        # base64_table and reopen it before class CUUUSSL (single-line
        # anchors, balanced ifdefs).
        http_cpp = os.path.join(self.source_folder, "libuuu", "http.cpp")
        replace_in_file(
            self, http_cpp,
            "static const char* base64_table =",
            "#endif  // OHOS: base64 is plain HTTP, available without UUUSSL\n"
            "static const char* base64_table =",
        )
        replace_in_file(
            self, http_cpp,
            "class CUUUSSL",
            "#ifdef UUUSSL  // OHOS: reopen SSL-only section (see above)\n"
            "class CUUUSSL",
        )

    def _patch_libusb_init_graceful(self):
        # OHOS (2026-10-17 round, test_package rc=134 SIGABRT):
        # `libuuu/usbhotplug.cpp` holds `CAutoDeInit g_autoDeInit`, whose
        # global constructor runs before main() and does
        # `if (libusb_init(nullptr) < 0) throw runtime_error{
        # "Call libusb_init failure" };`. A throw in a global ctor calls
        # terminate -> SIGABRT, so EVERY uuu invocation (no-args/-h/-udev)
        # dies with `libc++abi: terminating ... Call libusb_init failure`
        # and no version banner, even for paths that never touch USB.
        # On the OHOS preflight/HAP sandbox libusb_init unconditionally
        # fails: default init walks sysfs `/sys/bus/usb/devices` + netlink
        # kobject_uevent, both blocked by SELinux neverallow (precedent:
        # knowledge DRAFT-14966 libusb 1.0.29 0/4 FAIL LIBUSB_ERROR_IO;
        # xfel 1.3.5 patched main.c to check libusb_init and exit 255
        # instead of SIGSEGV). Same platform boundary, not a code defect.
        # Fix (same layer as xfel, adapted: uuu throws in a global ctor,
        # xfel ignored the return in main): never throw; record init state,
        # guard libusb_exit, and make the default CAutoList ctor return an
        # error without calling libusb_get_device_list on an uninitialized
        # context (callers already check good() and fail gracefully).
        # Result: version/help/-udev (config-only, no USB) run with rc=0;
        # device paths degrade to proper error strings instead of abort.
        # Whitespace-tolerant regex replaces (tabs differ per checkout);
        # missing anchor fails loudly. No patch files (keeps the
        # replace_in_file-only convention of this recipe).
        import re
        hotplug = os.path.join(self.source_folder, "libuuu", "usbhotplug.cpp")
        with open(hotplug, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        # 1) Ensure <cstdio> for fprintf (global ctor runs before iostream
        #    init, so std::cerr is unsafe here; C stdio is always ready).
        if "#include <cstdio>" not in content:
            anchor_inc = "#include <iostream>"
            if anchor_inc not in content:
                raise Exception("OHOS libusb patch: '#include <iostream>' anchor missing")
            content = content.replace(
                anchor_inc,
                anchor_inc + "\n#include <cstdio>  // OHOS: fprintf in global ctor (iostream unsafe pre-main)",
                1,
            )
        # 2) Declare init flag before the class.
        anchor_cls = "class CAutoDeInit"
        if anchor_cls not in content:
            raise Exception("OHOS libusb patch: 'class CAutoDeInit' anchor missing")
        if "g_libusb_initialized" not in content:
            content = content.replace(
                anchor_cls,
                "// OHOS: sandbox has no USB access (SELinux neverallow on sysfs/netlink);\n"
                "// libusb_init fails there. Never throw from the global ctor (would\n"
                "// terminate before main); remember state for graceful degradation.\n"
                "static bool g_libusb_initialized = false;\n"
                + anchor_cls,
                1,
            )
        # 3) Ctor: warn + remember instead of throw.
        pat_throw = re.compile(
            r"if\s*\(libusb_init\(nullptr\)\s*<\s*0\)\s*\n\s*throw\s+runtime_error\s*\{\s*\"Call libusb_init failure\"\s*\}\s*;"
        )
        if "Call libusb_init failure" not in content:
            raise Exception("OHOS libusb patch: throw anchor missing")
        new_ctor = (
            "if (libusb_init(nullptr) < 0)\n"
            "\t\t{\n"
            "\t\t\tfprintf(stderr, \"Warning: libusb_init failed (no USB access), USB operations unavailable\\n\");\n"
            "\t\t}\n"
            "\t\telse\n"
            "\t\t{\n"
            "\t\t\tg_libusb_initialized = true;\n"
            "\t\t}"
        )
        content, n = pat_throw.subn(lambda _: new_ctor, content, count=1)
        if n != 1:
            raise Exception("OHOS libusb patch: throw regex matched %d times" % n)
        # 4) Dtor: only exit when init succeeded.
        pat_exit = re.compile(r"~\s*CAutoDeInit\s*\(\s*\)\s*\n\s*\{\s*\n\s*libusb_exit\(nullptr\);\s*\n\s*\}")
        new_dtor = (
            "~CAutoDeInit()\n"
            "\t{\n"
            "\t\tif (g_libusb_initialized)\n"
            "\t\t\tlibusb_exit(nullptr);\n"
            "\t}"
        )
        content, n = pat_exit.subn(lambda _: new_dtor, content, count=1)
        if n != 1:
            raise Exception("OHOS libusb patch: dtor regex matched %d times" % n)
        # 5) Default CAutoList ctor: fail gracefully without touching
        #    libusb when uninitialized (else undefined behaviour/crash).
        pat_list = re.compile(
            r"(\bCAutoList\s*\(\s*\)\s*\n\s*\{\s*\n)(\s*m_rc\s*=\s*libusb_get_device_list\(nullptr,\s*&list\);)"
        )
        m = pat_list.search(content)
        if not m:
            raise Exception("OHOS libusb patch: CAutoList() anchor missing")
        guard = (
            m.group(1)
            + "\t\tif (!g_libusb_initialized) {\n"
            "\t\t\tm_rc = -1;\n"
            "\t\t\tset_last_err_string(\"libusb not initialized (no USB access in sandbox)\");\n"
            "\t\t\treturn;\n"
            "\t\t}\n"
            + m.group(2)
        )
        content = pat_list.sub(lambda _: guard, content, count=1)
        with open(hotplug, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092 (toolchain-file route; in-repo precedent: ableton-link 3.1.2,
        # zxc 0.9.1, ayatana-ido 0.10.4-v2): CMake 4.4.3 ships no
        # Platform/HarmonyOS.cmake, so the conan_toolchain default
        # (CMAKE_SYSTEM_NAME=HarmonyOS) fails at project() with
        # "System is unknown to cmake". Alias the target to Linux inside the
        # toolchain file (tc.variables are read before project()).
        # NOTE (2026-10-17 round): the previous cache_variables (-D/presets)
        # form of this alias did NOT save the configure -- it still died in
        # the compiler sanity check at CMakeLists.txt:3 project() with
        # "CMAKE_C/CXX_COMPILER identification is unknown" for the absolute
        # HNP path /data/service/hnp/bin/clang{,++}. That failure is a NEW
        # domain (toolchain/compiler selection): configure dies before any
        # source compiles, so no tinyxml2 dependency wiring can influence
        # it. This round therefore changes layer, not dependency: platform
        # alias moves into the toolchain file and the compiler gets a
        # usability guard (below).
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            # conan arch for OHOS AArch64 is "armv8"; CMake/upstream expect
            # "aarch64" (abcmidi 20260609 precedent).
            arch = str(self.settings.arch)
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if arch == "armv8" else arch
            )
        # Compiler guard (form adapted from ayatana-ido 0.10.4-v2): the
        # profile pins tools.build:compiler_executables to absolute HNP
        # paths, but preflight showed /data/service/hnp/bin/clang++ not
        # directly executable on some workers (self.run absolute path:
        # "/bin/sh: ... inaccessible or not found", Error 127; CMake
        # compiler identification unknown on the same path). Prefer the conf
        # absolute path when it exists as a file; otherwise fall back to the
        # PATH-resolved compiler (worker shims live on PATH) so a dangling
        # absolute path is never baked into the toolchain. os.access(X_OK)
        # is deliberately NOT decisive (HMDFS ignores chmod); isfile plus
        # the PATH fallback keeps both worker flavors working -- on healthy
        # workers which() resolves to the same HNP binary, i.e. the fallback
        # is behavior-preserving. When neither source yields a compiler,
        # nothing is pinned and conan's default applies (status quo).
        try:
            _exes = self.conf.get("tools.build:compiler_executables",
                                   default=None)
        except Exception:
            _exes = None
        _conf_c = _conf_cxx = None
        if isinstance(_exes, dict):
            _conf_c = _exes.get("c")
            _conf_cxx = (_exes.get("cpp") or _exes.get("cxx")
                         or _exes.get("c"))
        for _key, _conf_val, _bare in (
                ("CMAKE_C_COMPILER", _conf_c, "clang"),
                ("CMAKE_CXX_COMPILER", _conf_cxx, "clang++")):
            if _conf_val and (os.path.sep in str(_conf_val)
                              or "/" in str(_conf_val)):
                try:
                    _usable = os.path.isfile(str(_conf_val))
                except Exception:
                    _usable = False
                if not _usable:
                    self.output.warning(
                        "conf compiler '%s' not usable; falling back to PATH"
                        % _conf_val)
                    _which = shutil.which(_bare)
                    if _which:
                        tc.variables[_key] = _which
            elif not _conf_val:
                _which = shutil.which(_bare)
                if _which:
                    tc.variables[_key] = _which
        # Help upstream FindBZip2 locate the Conan bzip2 package.
        # CMakeDeps generates bzip2-config (lowercase); the upstream
        # find_package(BZip2) module needs explicit hints.
        try:
            bz2 = self.dependencies["bzip2"]
            bz2_root = bz2.package_folder
            tc.variables["BZIP2_INCLUDE_DIR"] = os.path.join(bz2_root, "include").replace("\\", "/")
            cand = os.path.join(bz2_root, "lib", "libbz2.a")
            if os.path.isfile(cand):
                tc.variables["BZIP2_LIBRARIES"] = cand.replace("\\", "/")
            else:
                # Shared fallback (bzip2 defaults static on OHOS, but keep
                # the hint valid if the graph resolves shared).
                for alt in ("libbz2.so", "libbz2.dylib"):
                    alt_p = os.path.join(bz2_root, "lib", alt)
                    if os.path.isfile(alt_p):
                        tc.variables["BZIP2_LIBRARIES"] = alt_p.replace("\\", "/")
                        break
        except KeyError:
            pass
        # Help upstream FindOpenSSL locate the Conan openssl package.
        # libuuu/http.cpp defines base64_encode() only under UUUSSL, which
        # is set only when find_package(OpenSSL) succeeds; the module
        # searches system paths by default and misses the Conan package on
        # the OHOS worker (no /usr ssl), leaving UUUSSL undefined and
        # breaking http.cpp with `use of undeclared identifier
        # 'base64_encode'` (2026-10-17 round). Point the module at the
        # Conan package root (plus static-lib preference when the graph
        # resolves openssl shared=False).
        try:
            ossl = self.dependencies["openssl"]
            ossl_root = ossl.package_folder
            tc.variables["OPENSSL_ROOT_DIR"] = ossl_root.replace("\\", "/")
            try:
                ossl_shared = ossl.options.shared
            except Exception:
                ossl_shared = None
            if ossl_shared is False:
                tc.variables["OPENSSL_USE_STATIC_LIBS"] = True
        except KeyError:
            pass
        tc.generate()
        CMakeDeps(self).generate()
        # PkgConfigDeps generates .pc files for libusb-1.0 / libzstd /
        # zlib, consumed by upstream pkg_check_modules(). tinyxml2 is
        # intentionally absent (vendored sources wired in source()).
        from conan.tools.gnu import PkgConfigDeps
        PkgConfigDeps(self).generate()

    def _write_tarball_version(self):
        # libuuu gen_ver.sh prefers ../.tarball-version over git describe
        # (nixpkgs preConfigure precedent). Conan exports a tarball without
        # .git, so stamp the version to keep the --version output stable.
        stamp = os.path.join(self.source_folder, ".tarball-version")
        with open(stamp, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.version + "\n")

    def build(self):
        apply_conandata_patches(self)
        self._write_tarball_version()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # HMBS machine evidence: uuu 1.5.243 ships no test suite for the
        # deliverable (see test_package/MANIFEST.yml upstream_test_audit).
        # Emitted here; re-emitted every round by test_package in case
        # build() is skipped on a package cache hit.
        upstream = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Audited nxp-imx/mfgtools tag uuu_1.5.243 source "
                      "(uuu_source-uuu_1.5.243.tar.gz): top-level CMake "
                      "adds only libuuu + uuu with no enable_testing / "
                      "add_test / BUILD_TESTING; the only CTest hits are "
                      "inside bundled third-party submodules (tinyxml2, "
                      "zlib, zstd) which the top build never adds; "
                      "wrapper/tests are pytest for the python wrapper, "
                      "not built by CMake. Therefore status no_tests.",
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        lic = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(lic):
            copy(self, "LICENSE", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        if str(self.settings.os) != "OHOS":
            return
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            return
        for fname in os.listdir(bindir):
            fpath = os.path.join(bindir, fname)
            if not os.path.isfile(fpath) or os.path.islink(fpath):
                continue
            if not self._is_elf(fpath):
                continue
            subprocess.run([objcopy, "--remove-section", ".codesign", fpath],
                           check=False)
            signed = fpath + ".signed"
            subprocess.run([signer, "sign", "-inFile", fpath,
                            "-outFile", signed, "-selfSign", "1"], check=True)
            os.replace(signed, fpath)
            os.chmod(fpath, 0o755)

    def package_info(self):
        # uuu provides a CLI executable, not libraries.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
