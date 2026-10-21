import os
import shutil
import socket
import tempfile
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

class LibkleoConan(ConanFile):
    name = "libkleo"
    version = "26.04.3"
    exports = "ohos_notmpfile.c"
    description = "KDE PIM OpenPGP and key management library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/pim/libkleo"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("ki18n/6.26.0")
        self.requires("kconfig/6.26.0")
        self.requires("kwidgetsaddons/6.26.0")
        self.requires("kcolorscheme/6.26.0")
        self.requires("kcompletion/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("kcodecs/6.26.0")
        self.requires("kitemmodels/6.26.0")
        # Gpgmepp/QGpgME ship versioned sonames (libgpgmepp.so.6,
        # libqgpgmeqt6.so.15). Propagate those shared libraries to this
        # package and to test_package so the dynamic loader can see them.
        self.requires("gpgme/1.24.2", transitive_libs=True, transitive_headers=True)
        self.requires("libgpg-error/1.55")
        self.requires("boost/1.85.0")
        # Boost's CMake package calls find_dependency(zlib), so expose zlib
        # directly to CMakeDeps instead of relying on its transitive node.
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # Run all upstream tests, including the two fixtures that require
        # gpg/gpgsm/gpgconf. This is a build-only test runner dependency.
        self.tool_requires("gnupg/2.5.22")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualRunEnv(self).generate()
        deps = CMakeDeps(self)
        # BoostConfig.cmake calls find_dependency(zlib) with this exact case.
        deps.set_property("zlib", "cmake_file_name", "zlib")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables.update({
            "BUILD_SHARED_LIBS": "ON",
            "BUILD_TESTING": True,
            "BUILD_QCH": False,
            "KF_IGNORE_PLATFORM_CHECK": True,
            "KF_SKIP_PO_PROCESSING": True,
            "CMAKE_INSTALL_LIBDIR": "lib",
            "CMAKE_CXX_STANDARD": "20",
            "CMAKE_CXX_STANDARD_REQUIRED": True,
            "CMAKE_EXE_LINKER_FLAGS": "-Wl,--disable-new-dtags",
            "CMAKE_FIND_PACKAGE_PREFER_CONFIG": True,
        })
        prefixes = [self.generators_folder]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                prefixes.extend([
                    os.path.join(dep.package_folder, "lib", "cmake"),
                    dep.package_folder,
                ])
        tc.variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
        # Upstream tests dlopen libgpgmepp.so.6 / libqgpgmeqt6.so.15. $ORIGIN
        # alone does not see the dependency package lib directories.
        rpath_dirs = ["$ORIGIN"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                rpath_dirs.append(libdir)
        rpath_dirs.append(os.path.join(self.build_folder, "bin"))
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(rpath_dirs)
        tc.variables["libgpg-error_DIR"] = self.generators_folder
        tc.variables["Boost_DIR"] = self.generators_folder
        # BoostConfig's find_dependency(zlib) needs the CMakeDeps generator dir.
        tc.variables["zlib_DIR"] = self.generators_folder
        tc.variables["Qt6_DIR"] = os.path.join(
            self.dependencies["qtbase"].package_folder, "lib", "cmake", "Qt6"
        )
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(os.path.join(share, x) for x in ("modules", "find-modules", "kde-modules"))
        # Conan's generated toolchain includes generators/conan_cmakedeps_paths.cmake
        # when that file exists. Gpgmepp does not publish cpp_info.builddirs, so the
        # toolchain's own PREFIX_PATH list skips it and find_package(Gpgmepp) fails.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                package = dep.package_folder
                lines += [
                    'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(package),
                    'list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(package),
                    'list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(package),
                    'list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(package),
                ]
        if ecm:
            share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}/cmake")'.format(share))
            for module in ("modules", "find-modules", "kde-modules"):
                lines.append('list(PREPEND CMAKE_MODULE_PATH "{}/{}")'.format(share, module))
        pathfile = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(pathfile, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        tc.generate()

    def _runtime(self):
        env = Environment()
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if not dep or not dep.package_folder: continue
            p=dep.package_folder
            env.prepend_path("LD_LIBRARY_PATH",os.path.join(p,"lib"))
            env.prepend_path("PATH",os.path.join(p,"bin"))
            env.prepend_path("XDG_DATA_DIRS",os.path.join(p,"share"))
            for plugin_dir in (os.path.join(p, "plugins"), os.path.join(p, "lib", "plugins")):
                if os.path.isdir(plugin_dir):
                    env.prepend_path("QT_PLUGIN_PATH", plugin_dir)
        qtbase = self.dependencies["qtbase"].package_folder
        platforms = os.path.join(qtbase, "plugins", "platforms")
        if os.path.isdir(platforms):
            # Qt treats this as the platform-plugin search list. Prepending one
            # empty directory per dependency hid libqoffscreen.so and aborted
            # every QWidget test at startup.
            env.define("QT_QPA_PLATFORM_PLUGIN_PATH", platforms)
        env.prepend_path("LD_LIBRARY_PATH",os.path.join(self.build_folder,"lib"))
        env.prepend_path("LD_LIBRARY_PATH",os.path.join(self.build_folder,"src","lib"))
        env.prepend_path("LD_LIBRARY_PATH",os.path.join(self.build_folder,"bin"))
        env.define("QT_QPA_PLATFORM","offscreen")
        return env

    def _is_ohos(self):
        return str(self.settings.os).upper() == "OHOS"

    def _gnupg_root(self):
        for source in (getattr(self.dependencies, "build", {}), self.dependencies):
            try:
                dep = source["gnupg"]
            except Exception:
                continue
            if dep and dep.package_folder:
                return os.path.realpath(dep.package_folder)
        raise RuntimeError("gnupg tool package is not available")

    def _copy_executables(self, src_dir, dst_dir):
        """Copy real files. GnuPG resolves /proc/self/exe and then reads
        <parent>/bin/gpgconf.ctl, so a symlink would still see the package.
        """
        os.makedirs(dst_dir, exist_ok=True)
        for name in os.listdir(src_dir):
            if name == "gpgconf.ctl":
                continue
            src = os.path.join(src_dir, name)
            dst = os.path.join(dst_dir, name)
            if os.path.isdir(src) and not os.path.islink(src):
                self._copy_executables(src, dst)
                continue
            if not os.path.isfile(src):
                continue
            if not os.path.isfile(dst):
                shutil.copy2(src, dst)
            os.chmod(dst, 0o755)

    def _prepare_gnupg_prefix(self):
        """GnuPG was configured with prefix=/ and then installed into the Conan
        cache, so gpgconf looks for /bin/gpg-agent. Copy bin and libexec into
        this build and write gpgconf.ctl in the private bin. keyboxd and
        scdaemon live in libexec; each component strips one directory from its
        real executable path and reads <root>/bin/gpgconf.ctl. Do not modify
        the gnupg package.
        """
        root = self._gnupg_root()
        priv = os.path.join(self.build_folder, "gnupg-prefix")
        priv_bin = os.path.join(priv, "bin")
        self._copy_executables(os.path.join(root, "bin"), priv_bin)
        libexec = os.path.join(root, "libexec")
        libexec_dst = os.path.join(priv, "libexec")
        if os.path.islink(libexec_dst):
            os.unlink(libexec_dst)
        if os.path.isdir(libexec):
            self._copy_executables(libexec, libexec_dst)
        for name in ("lib", "share"):
            src = os.path.join(root, name)
            dst = os.path.join(priv, name)
            if os.path.isdir(src) and not os.path.lexists(dst):
                os.symlink(src, dst)
        with open(os.path.join(priv_bin, "gpgconf.ctl"), "w", encoding="utf-8") as handle:
            handle.write("rootdir={}\n".format(os.path.realpath(priv)))
        return priv_bin

    def _ohos_socket_tmpdir(self):
        # AF_UNIX bind works under the app-private base and fails on the
        # default QDir::tempPath() (/storage/Users/currentUser). qExtractTestData
        # follows TMPDIR, and the upstream tests use that directory as GNUPGHOME.
        base = "/data/storage/el2/base"
        probe = tempfile.mkdtemp(prefix="lbk14632-sock-", dir=base)
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.bind(os.path.join(probe, "s"))
            finally:
                sock.close()
        finally:
            shutil.rmtree(probe, ignore_errors=True)
        tmp = tempfile.mkdtemp(prefix="lbk14632-tmp-", dir=base)
        os.chmod(tmp, 0o700)
        return tmp

    def _c_compiler(self):
        cache = os.path.join(self.build_folder, "CMakeCache.txt")
        if os.path.isfile(cache):
            with open(cache, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.startswith("CMAKE_C_COMPILER:"):
                        compiler = line.split("=", 1)[1].strip()
                        if compiler:
                            return compiler
        return "clang"

    def _compile_notmp(self):
        source = os.path.join(self.recipe_folder, "ohos_notmpfile.c")
        output = os.path.join(self.build_folder, "ohos_notmpfile.so")
        compiler = self._c_compiler()
        self.run('"{}" -shared -fPIC -O2 "{}" -o "{}" -ldl'.format(compiler, source, output))
        return output

    def _link_soname(self, directory):
        library = os.path.join(directory, "libKPim6Libkleo.so")
        soname = os.path.join(directory, "libKPim6Libkleo.so.6")
        if os.path.isfile(library) and not os.path.lexists(soname):
            os.symlink("libKPim6Libkleo.so", soname)

    def _read_text(self, path):
        if not os.path.isfile(path):
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def _run_bounded(self, executable, cwd, log_path, seconds):
        os.makedirs(cwd, exist_ok=True)
        command = (
            'cd "{cwd}" || exit 1; "{exe}" > "{log}" 2>&1 & p=$!; '
            'i=0; while [ "$i" -lt {seconds} ]; do '
            'kill -0 "$p" 2>/dev/null || break; i=$((i+1)); sleep 1; done; '
            'if kill -0 "$p" 2>/dev/null; then '
            'if grep -q libKPim6Libkleo "/proc/$p/maps" 2>/dev/null; then echo LBK_MAPPED >> "{log}"; fi; '
            'echo LBK_STILL_RUNNING >> "{log}"; '
            'pkill -P "$p" 2>/dev/null || true; kill "$p" 2>/dev/null || true; wait "$p" 2>/dev/null || true; '
            'else wait "$p"; echo LBK_EXIT=$? >> "{log}"; fi'
        ).format(cwd=cwd, exe=executable, log=log_path, seconds=seconds)
        self.run(command, ignore_errors=True)
        return self._read_text(log_path)

    def _runtime_link_farm(self):
        """Resolve path-form DT_NEEDED entries in the published KF6 packages."""
        dependencies = list(self.dependencies.values()) + list(self.dependencies.build.values())
        farm_dirs = [
            os.path.join(self.build_folder, "bin"),
            os.path.normpath(os.path.join(self.build_folder, "..", "bin")),
        ]
        for farm_dir in farm_dirs:
            os.makedirs(farm_dir, exist_ok=True)
        for dep in dependencies:
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if ".so" not in name:
                    continue
                for farm_dir in farm_dirs:
                    link = os.path.join(farm_dir, name)
                    if not os.path.lexists(link):
                        try:
                            os.symlink(os.path.join(libdir, name), link)
                        except OSError as error:
                            self.output.warning("Runtime link farm skipped {}: {}".format(name, error))

    def build(self):
        apply_conandata_patches(self)
        cmake=CMake(self)
        cmake.configure()
        self._runtime_link_farm()
        with self._runtime().vars(self).apply():
            cmake.build(build_tool_args=["-j2"])
        self._link_soname(os.path.join(self.build_folder, "bin"))
        test_env = self._runtime()
        preload = None
        if self._is_ohos():
            tmp = self._ohos_socket_tmpdir()
            self._ohos_test_tmpdir = tmp
            test_env.define("TMPDIR", tmp)
            test_env.define("TEMP", tmp)
            test_env.define("TMP", tmp)
            preload = self._compile_notmp()
            test_env.define("LD_PRELOAD", preload)
        test_error = None
        manual_errors = []
        gnupg_bin = self._prepare_gnupg_prefix()
        # conanbuild.sh prepends the gnupg tool package after this env, so
        # PATH order is not reliable. The library reads this directory first.
        test_env.define("LIBKLEO_GNUPG_BIN", gnupg_bin)
        test_env.prepend_path("PATH", gnupg_bin)
        try:
            with test_env.vars(self).apply():
                try:
                    self.run(
                        'ctest --test-dir "{}" --output-on-failure --timeout 120 --no-tests=error'.format(
                            self.build_folder
                        )
                    )
                except Exception as error:
                    test_error = error
                # These eight programs are built and marked with ecm_mark_as_test
                # but are not CTest entries. DT_NEEDED of each one is
                # ../bin/libKPim6Libkleo.so until the SONAME relink, and the KF6
                # packages use ../../bin/. Both resolve when cwd is build/tests.
                runtime_dir = os.path.join(self.build_folder, "tests")
                for name, seconds in (
                    ("test_cryptoconfig", 60),
                    ("test_keyformailbox", 60),
                    ("test_keyselectiondialog", 20),
                    ("test_keygen", 20),
                    ("test_keylister", 20),
                    ("test_auditlog", 20),
                    ("test_keyselectioncombo", 20),
                    ("test_keyresolver", 25),
                ):
                    executable = os.path.join(self.build_folder, "bin", name)
                    log_path = os.path.join(self.build_folder, "manual-{}.log".format(name))
                    text = self._run_bounded(executable, runtime_dir, log_path, seconds)
                    self.output.info("manual {}:\n{}".format(name, text[-4000:]))
                    if "Error loading shared library" in text or "symbol not found" in text:
                        manual_errors.append("{} failed to load libraries:\n{}".format(name, text[-2000:]))
                    elif "LBK_STILL_RUNNING" in text:
                        # Upstream main() stays in QDialog::exec or QApplication::exec.
                        mapped = "LBK_MAPPED" in text
                        self.output.info(
                            "{} stayed in the upstream event loop; libKPim6Libkleo mapped={}".format(
                                name, mapped
                            )
                        )
                        if not mapped:
                            manual_errors.append(
                                "{} stayed running without mapping libKPim6Libkleo:\n{}".format(
                                    name, text[-2000:]
                                )
                            )
                    elif "LBK_EXIT=0" not in text:
                        manual_errors.append("{} exited nonzero:\n{}".format(name, text[-2000:]))
        finally:
            tmp = getattr(self, "_ohos_test_tmpdir", None)
            if tmp and os.path.isdir(tmp):
                shutil.rmtree(tmp, ignore_errors=True)
        if test_error is not None:
            raise test_error
        if manual_errors:
            raise RuntimeError("\n".join(manual_errors))

    def package(self):
        CMake(self).install()
        self._link_soname(os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode","none")
        self.cpp_info.builddirs=[os.path.join("lib","cmake")]
        self.cpp_info.libs=["KPim6Libkleo"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",os.path.join(self.package_folder,"lib"))
