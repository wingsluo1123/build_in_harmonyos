#!/usr/bin/env python3
"""Conan recipe for kpeople 6.28.0 on HarmonyOS PC.

KPeople is the KDE Frameworks people/contacts aggregation framework. It
provides KF6People (KPeople::PersonsModel / PersonData core API),
KF6PeopleBackend (data source plugin API), KF6PeopleWidgets (dialog/view
facilities) and the org.kde.people QML plugin that person-centric
applications build on.
"""
import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KPeopleConan(ConanFile):
    name = "kpeople"
    version = "6.28.0"
    description = "KDE Frameworks contact/people aggregation framework"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kpeople"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # kpeople's top-level CMakeLists requires Qt6::Sql, which the vanilla
        # qtbase package does not build (FEATURE_sql=OFF). qtbase-sql-dbus is
        # the full qtbase variant that carries Sql/DBus (kdbusaddons/kauth/
        # alkimia precedent). Vanilla qtbase still enters the graph through
        # qtdeclarative and the KF6 dependencies; it is kept off the CMake
        # search path below so it cannot shadow the sql-dbus Qt6Config tree.
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kitemviews/6.18.0")
        self.requires("kcontacts/6.18.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["ENABLE_EXAMPLES"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Conan's HarmonyOS name has no complete CMake platform module. Use
            # CMake's OHOS platform rules so shared C++ targets receive SONAMEs.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            # CMake's OHOS platform module derives from Linux, so UNIX is true
            # and kpeople auto-enables its DBus support. A PC without a D-Bus
            # session bus silently loses the merge/unmerge model updates: that
            # code path sends notifications over D-Bus instead of emitting the
            # in-process Qt signals PersonsModel listens for (the path
            # upstream's own default picks for every non-Linux system). Keep
            # the in-process signal path.
            tc.variables["USE_DBUS"] = "OFF"
            self._configure_ohos_shared_library_rules(tc)

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        qtdeclarative = self.dependencies.get("qtdeclarative")
        if qtdeclarative and qtdeclarative.package_folder:
            # The sql-dbus Qt6Config resolves Qml/Quick configs that live
            # outside the qtbase tree only against
            # QT_ADDITIONAL_PACKAGES_PREFIX_PATH; CMAKE_PREFIX_PATH alone
            # yields "Could NOT find Qt6Qml" (knewstuff precedent).
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = qtdeclarative.package_folder

        self._write_cmake_paths(ecm)
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join(
                (
                    'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                    'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
                )
            )
            + "\n",
        )
        # This recipe configures with an explicit -DCMAKE_TOOLCHAIN_FILE and
        # never passes --preset, so CMakeToolchain.cache_variables (which conan
        # 2.29 writes only into CMakePresets.json cacheVariables) would never
        # reach CMake; plain variables are emitted into conan_toolchain.cmake
        # and do reach this configure path.
        toolchain.variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules
        # The HMDFS user volume rejects symlink() with EPERM, so the versioned
        # lib<name>.so.<major> symlink chain CMake would create after linking
        # fails the build. Emit every shared library under its plain name
        # instead; the explicit -soname flag above still bakes a real
        # DT_SONAME, so consumers keep recording a relocatable NEEDED name
        # (DRAFT-cmake-harmonyos-system-name-soname / kcolorpicker precedent).
        toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                if dep.ref.name == "qtbase":
                    # The vanilla qtbase pulled in transitively by
                    # qtdeclarative/KF6 must not shadow the sql-dbus tree in
                    # find_package(Qt6) (alkimia precedent).
                    continue
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                    ]
                )
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
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            with self._cmake_host_tool_env(include_build=True).vars(self).apply():
                self._run_ohos_cmake_configure()
                self._run_with_ohos_lld_runtime(
                    f"cmake --build {self._quote(self.build_folder)}"
                )
        else:
            with self._library_runtime_env(include_build=True).vars(self).apply():
                cmake.configure()
                cmake.build()
        with self._library_runtime_env(include_build=True).vars(self).apply():
            self._run_upstream_tests()

    def _library_runtime_env(self, include_build=False):
        runtime_env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                runtime_env.prepend_path(
                    "XDG_DATA_DIRS", os.path.join(dep.package_folder, "share")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
        # Keep the runtime Qt module set on the sql-dbus variant: the vanilla
        # qtbase tree also reaches LD_LIBRARY_PATH/QT_PLUGIN_PATH through
        # qtdeclarative/KF6, and libraries or platform plugins must not be
        # mixed across the two trees.
        qtbase = self.dependencies.get("qtbase-sql-dbus")
        if qtbase and qtbase.package_folder:
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib")
            )
            runtime_env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(qtbase.package_folder, "plugins")
            )
            runtime_env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(qtbase.package_folder, "lib", "plugins")
            )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        for rel in ("bin", "plugins", os.path.join("lib", "plugins")):
            runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(self.build_folder, rel))
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        return runtime_env

    def _cmake_host_tool_env(self, include_build=False):
        return self._library_runtime_env(include_build=include_build)

    def _run_ohos_cmake_configure(self):
        os.makedirs(self.build_folder, exist_ok=True)
        cmd = " ".join(
            [
                "cmake",
                '-G "Unix Makefiles"',
                f"-S {self._quote(self.source_folder)}",
                f"-B {self._quote(self.build_folder)}",
                f"-DCMAKE_TOOLCHAIN_FILE={self._quote(os.path.join(self.generators_folder, 'conan_toolchain.cmake'))}",
                f"-DCMAKE_INSTALL_PREFIX={self._quote(self.package_folder)}",
                '-DCMAKE_POLICY_DEFAULT_CMP0091="NEW"',
                f'-DCMAKE_BUILD_TYPE="{self.settings.build_type}"',
            ]
        )
        self._run_with_ohos_lld_runtime(cmd)

    def _run_with_ohos_lld_runtime(self, command):
        sdk_llvm_lib = self._ohos_sdk_llvm_lib()
        prefix = 'LD_LIBRARY_PATH="{}${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}" '.format(
            sdk_llvm_lib
        )
        self.run(prefix + command, env="conanbuild")

    def _configured_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for key in ("c", "cpp"):
            compiler = compilers.get(key)
            if compiler:
                return compiler
        return shutil.which("clang") or shutil.which("cc") or ""

    def _ohos_sdk_llvm_lib(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return ""

        candidates = []
        compiler = self._configured_compiler()
        if compiler:
            compiler_parts = shlex.split(str(compiler))
            compiler_exe = compiler_parts[0] if compiler_parts else ""
            if compiler_exe:
                candidates.append(
                    os.path.normpath(os.path.join(os.path.realpath(os.path.dirname(compiler_exe)), os.pardir, "lib"))
                )
            try:
                result = subprocess.run(
                    compiler_parts + ["-print-resource-dir"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
            except OSError as exc:
                raise ConanException(f"Cannot run configured OHOS compiler {compiler}: {exc}") from exc
            if result.returncode != 0:
                raise ConanException(
                    "Cannot query OHOS compiler resource dir with -print-resource-dir: "
                    + result.stderr.strip()
                )
            resource_dir = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
            if resource_dir:
                candidates.append(os.path.normpath(os.path.join(resource_dir, os.pardir, os.pardir)))

        sdk_base = os.environ.get("OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
        candidates.extend(
            sorted(glob.glob(os.path.join(sdk_base, "*", "ohos", "native", "llvm", "lib")))
        )
        ndk_home = os.environ.get("OHOS_NDK_HOME", "")
        if ndk_home:
            candidates.append(os.path.join(ndk_home, "llvm", "lib"))

        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            llvm_lib = os.path.realpath(os.path.normpath(candidate))
            if llvm_lib in seen:
                continue
            seen.add(llvm_lib)
            if not os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                continue
            self._probe_ohos_lld(llvm_lib)
            self.output.info(f"Using OHOS SDK llvm/lib for lld runtime: {llvm_lib}")
            return llvm_lib

        raise ConanException(
            "Cannot locate OHOS SDK llvm/lib containing libxml2.so.16 for lld runtime"
        )

    def _probe_ohos_lld(self, sdk_llvm_lib):
        lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
        if not os.path.isfile(lld):
            lld = self._find_ohos_tool("lld")
        if not lld:
            raise ConanException("Cannot locate OHOS SDK lld for runtime probe")

        env = os.environ.copy()
        old_ld_path = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = sdk_llvm_lib + (os.pathsep + old_ld_path if old_ld_path else "")
        try:
            result = subprocess.run(
                [lld, "-flavor", "gnu", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False,
            )
        except OSError as exc:
            raise ConanException(f"Cannot run OHOS lld probe {lld}: {exc}") from exc
        if result.returncode != 0:
            raise ConanException(
                "OHOS lld probe failed with SDK llvm/lib runtime: "
                + (result.stderr.strip() or result.stdout.strip())
            )

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env(include_build=True)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        self._prepare_ctest_runtime_links()
        # Bound a wedged test process: on OHOS a crash-reporting loop after a
        # fatal test error can keep the process alive indefinitely, and ctest
        # without a per-test timeout would wait on it forever.
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 300'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bins = [
            os.path.join(self.build_folder, "bin"),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin")),
        ]
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                if dep.ref.name == "qtbase":
                    # Symlink only the sql-dbus Qt tree so the $ORIGIN runtime
                    # contract stays on one Qt variant (alkimia precedent).
                    continue
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            for compatibility_bin in compatibility_bins:
                os.makedirs(compatibility_bin, exist_ok=True)
                dst = os.path.join(compatibility_bin, os.path.basename(src))
                if not os.path.exists(src):
                    continue
                target = os.path.realpath(src)
                if os.path.realpath(dst) == target:
                    continue
                if os.path.lexists(dst):
                    if self._is_same_file_copy(dst, target):
                        continue
                    os.unlink(dst)
                try:
                    os.symlink(target, dst)
                except OSError:
                    # HMDFS rejects symlinks (EPERM) and hard links (EPERM)
                    # on the device; materialize a plain copy so the $ORIGIN
                    # runtime contract still resolves (qzxing precedent).
                    shutil.copy2(target, dst)

    @staticmethod
    def _is_same_file_copy(dst, target):
        """True when dst is already a plain copy of target (copy2 keeps mtime)."""
        if os.path.islink(dst) or not os.path.isfile(dst):
            return False
        try:
            return (
                os.path.getsize(dst) == os.path.getsize(target)
                and int(os.path.getmtime(dst)) == int(os.path.getmtime(target))
            )
        except OSError:
            return False

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

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

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder, label):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        if not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "Cannot locate OHOS llvm-objcopy/binary-sign-tool for ELF signing"
            )

        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                try:
                    os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
                signed += 1
        self.output.info(f"Signed {signed} OHOS {label} ELF file(s)")

    def package(self):
        cmake = CMake(self)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            with self._cmake_host_tool_env(include_build=True).vars(self).apply():
                self._run_with_ohos_lld_runtime(
                    "cmake --install {} --prefix {}".format(
                        self._quote(self.build_folder),
                        self._quote(self.package_folder),
                    )
                )
        else:
            with self._library_runtime_env(include_build=True).vars(self).apply():
                cmake.install()
        self._sign_ohos_elf_tree(self.package_folder, "package")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6People", "KF6PeopleWidgets", "KF6PeopleBackend"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
