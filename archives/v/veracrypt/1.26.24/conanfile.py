#!/usr/bin/env python3
"""Conan recipe for the VeraCrypt 1.26.24 console application."""

import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class VeraCryptConan(ConanFile):
    name = "veracrypt"
    version = "1.26.24"
    description = "Disk encryption utility with a console interface"
    license = "Apache-2.0 AND TrueCrypt-3.0"
    homepage = "https://veracrypt.io/"
    url = "https://github.com/veracrypt/VeraCrypt"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv", "PkgConfigDeps"
    exports_sources = "conandata.yml", "patches/*"

    # Published wxwidgets/3.2.10 links an incomplete base library (no
    # wxThread/wxMutex/wxAppConsole) and its wx-config records another machine's
    # prefix. VeraCrypt builds a console-only base toolkit itself.
    _wx_url = "https://github.com/wxWidgets/wxWidgets/releases/download/v3.2.10/wxWidgets-3.2.10.tar.bz2"
    _wx_sha = "d66e929569947a4a5920699539089a9bda83a93e5f4917fb313a61f0c344b896"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libfuse/2.9.9#bc32f257e37c6598525028a2cc4e6da4")
        self.requires("pcsc-lite/2.4.0")
        self.requires("zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9")
        self.requires("libiconv/1.17#894aeadea9c86949b4b4a32497b9d7d4")
        # ConanCenter is searched first and its expat/2.8.2 recipe does not
        # enable an entropy source, so the OHOS build hits a compile-time
        # #error. The registry revision enables getrandom and already has a binary.
        self.requires("expat/2.8.2#d4cf31cad46d9a206cad68ce0bd8b562")

    def source(self):
        source = dict(self.conan_data["sources"][str(self.version)])
        sha = source["sha256"]
        filename = "VeraCrypt_1.26.24_Source.tar.bz2"
        staged = os.path.expanduser(f"~/work/psj/vc11646/{filename}")
        if os.path.isfile(staged):
            self._extract_verified(staged, sha)
            return
        get(self, source["url"], sha256=sha, strip_root=False, filename=filename)

    def _extract_verified(self, path, sha256):
        import hashlib
        import tarfile
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != sha256:
            raise RuntimeError(f"staged source sha256 mismatch: {path}")
        with tarfile.open(path, "r:bz2") as archive:
            archive.extractall(self.source_folder)

    def _compiler(self, key, fallback):
        mapping = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return mapping.get(key) or fallback

    def _build_wx_base(self):
        cached = os.path.expanduser("~/work/psj/vc11646/wx-prefix")
        if glob.glob(os.path.join(cached, "lib", "libwx_baseu*.a")):
            return cached
        prefix = os.path.join(self.build_folder, "wx-prefix")
        marker = os.path.join(prefix, "lib")
        if glob.glob(os.path.join(marker, "libwx_baseu*.a")):
            return prefix
        filename = "wxWidgets-3.2.10.tar.bz2"
        staged = os.path.expanduser(f"~/work/psj/vc11646/{filename}")
        archive = staged if os.path.isfile(staged) else os.path.join(self.build_folder, filename)
        if not os.path.isfile(archive):
            download(self, self._wx_url, archive, sha256=self._wx_sha)
        else:
            self._check_sha(archive, self._wx_sha)
        src_root = os.path.join(self.build_folder, "wx-src")
        if os.path.isdir(src_root):
            shutil.rmtree(src_root)
        os.makedirs(src_root)
        import tarfile
        with tarfile.open(archive, "r:bz2") as tar:
            tar.extractall(src_root)
        nested = os.path.join(src_root, "wxWidgets-3.2.10")
        src = nested if os.path.isfile(os.path.join(nested, "CMakeLists.txt")) else src_root
        toolkit = os.path.join(src, "build", "cmake", "toolkit.cmake")
        replace_in_file(self, toolkit, "elseif(UNIX)",
                        'elseif(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")', strict=False)
        replace_in_file(self, toolkit, 'message(FATAL_ERROR "Unsupported platform")',
                        "set(wxDEFAULT_TOOLKIT gtk3)", strict=False)
        build = os.path.join(self.build_folder, "wx-build")
        os.makedirs(prefix, exist_ok=True)
        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        zlib = self.dependencies["zlib"].package_folder
        expat = self.dependencies["expat"].package_folder
        cmake = shutil.which("cmake") or "cmake"
        configure = (
            f'"{cmake}" -S "{src}" -B "{build}" -G "Unix Makefiles" '
            f'-DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="{prefix}" '
            f'-DCMAKE_C_COMPILER="{cc}" -DCMAKE_CXX_COMPILER="{cxx}" '
            f'-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_POSITION_INDEPENDENT_CODE=ON '
            f'-DCMAKE_PREFIX_PATH="{zlib};{expat}" '
            f'-DwxBUILD_SHARED=OFF -DwxBUILD_SAMPLES=OFF -DwxBUILD_TESTS=OFF '
            f'-DwxBUILD_DEMOS=OFF -DwxBUILD_PRECOMP=OFF -DwxUSE_GUI=OFF '
            f'-DwxUSE_THREADS=ON -DwxUSE_SOCKETS=OFF -DwxUSE_NET=OFF '
            f'-DwxUSE_PROTOCOL_FTP=OFF -DwxUSE_PROTOCOL_HTTP=OFF -DwxUSE_WEBREQUEST=OFF '
            f'-DwxUSE_EXPAT=sys -DwxUSE_ZLIB=sys -DwxUSE_REGEX=builtin '
            f'-DwxUSE_LIBPNG=OFF -DwxUSE_LIBJPEG=OFF -DwxUSE_LIBTIFF=OFF '
            f'-DwxBUILD_TOOLKIT=gtk3 -DCMAKE_POLICY_VERSION_MINIMUM=3.5'
        )
        self.run(configure, env="conanbuild")
        self.run(f'"{cmake}" --build "{build}" -j 2', env="conanbuild")
        self.run(f'"{cmake}" --install "{build}"', env="conanbuild")
        return prefix

    def _check_sha(self, path, sha256):
        import hashlib
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != sha256:
            raise RuntimeError(f"sha256 mismatch: {path}")

    def _wx_config(self):
        # Build a console base toolkit. The registry binary omits thread and
        # app objects, and its wx-config points at another machine.
        root = self._build_wx_base()
        setup = glob.glob(os.path.join(root, "lib", "wx", "include", "*", "wx", "setup.h"))
        bases = sorted(glob.glob(os.path.join(root, "lib", "libwx_baseu*.a")))
        regexes = sorted(glob.glob(os.path.join(root, "lib", "libwxregexu*.a")))
        def pick_lib(paths):
            for suffix in (".a", ".so", ".dylib"):
                for path in paths:
                    if path.endswith(suffix):
                        return path
            raise RuntimeError(f"no linkable library in {paths}")

        zlibs = glob.glob(os.path.join(
            self.dependencies["zlib"].package_folder, "lib", "libz.*"))
        expats = glob.glob(os.path.join(
            self.dependencies["expat"].package_folder, "lib", "libexpat.*"))
        iconvs = glob.glob(os.path.join(
            self.dependencies["libiconv"].package_folder, "lib", "libiconv.*"))
        if not setup or not bases or not regexes or not zlibs or not expats or not iconvs:
            raise RuntimeError("wxWidgets package is missing headers or static libraries")
        include_setup = os.path.dirname(os.path.dirname(setup[0]))
        include_wx = os.path.join(root, "include", "wx-3.2")
        cxxflags = f'-I"{include_setup}" -I"{include_wx}" -D__WXBASE__ -pthread'
        libs = " ".join(
            f'"{path}"' for path in (
                bases[0], regexes[0], pick_lib(zlibs), pick_lib(expats), pick_lib(iconvs)
            )
        )
        libs += " -lpthread"
        wrapper = os.path.join(self.build_folder, "wx-config-ohos")
        os.makedirs(self.build_folder, exist_ok=True)
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!/bin/sh\n"
                "cxxflags='%s'\n"
                "libs='%s'\n"
                "out=\n"
                "for arg in \"$@\"; do\n"
                "  case \"$arg\" in\n"
                "    --cxxflags|--cflags) out=\"$out $cxxflags\" ;;\n"
                "    --libs) out=\"$out $libs\" ;;\n"
                "  esac\n"
                "done\n"
                "printf '%%s\\n' \"$out\"\n" % (cxxflags, libs)
            )
        os.chmod(wrapper, 0o755)
        return wrapper

    def _tool(self, name, extra_dirs):
        found = shutil.which(name)
        if found:
            return found
        for directory in extra_dirs:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        home = os.path.expanduser("~")
        cellar = os.path.join(home, ".harmonybrew", "Cellar", "ohos-sdk@26.0.0.18")
        if os.path.isdir(cellar):
            for dirpath, _, files in os.walk(cellar):
                if name in files and dirpath.endswith(os.sep + "bin"):
                    return os.path.join(dirpath, name)
        return None

    def _sign_elf(self, path):
        if self.settings.os != "OHOS":
            os.chmod(path, 0o755)
            return
        extra = [
            "/data/service/hnp/bin",
            os.path.expanduser("~/.harmonybrew/bin"),
        ]
        signer = self._tool("binary-sign-tool", extra)
        objcopy = self._tool("llvm-objcopy", extra)
        if not signer or not objcopy:
            raise RuntimeError("HarmonyOS ELF signer or llvm-objcopy is missing")
        self.run(f'"{objcopy}" --remove-section .codesign "{path}" || true')
        signed = path + ".signed"
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{signed}" -selfSign 1')
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def _header_flag(self, package, header):
        root = self.dependencies[package].package_folder
        matches = glob.glob(os.path.join(root, "**", header), recursive=True)
        if not matches:
            raise RuntimeError(f"{header} not found in {package}")
        return "-I" + os.path.dirname(matches[0])

    def build(self):
        apply_conandata_patches(self)
        wx_config = self._wx_config()
        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        src = os.path.join(self.source_folder, "src")
        gen = self.generators_folder
        fuse_pkg = "libfuse" if os.path.exists(os.path.join(gen, "libfuse.pc")) else "fuse"
        extra = " ".join((
            self._header_flag("libfuse", "fuse.h"),
            self._header_flag("pcsc-lite", "pcsclite.h"),
        ))
        # NOTEST: the release link runs the suite before the ELF can be signed.
        # PKG_CONFIG_PATH is not injected by VirtualBuildEnv on this Conan.
        make = (
            f'PKG_CONFIG_PATH="{gen}" '
            f'make -j2 NOGUI=1 NOTEST=1 NOSTRIP=1 CC="{cc}" CXX="{cxx}" '
            f'WX_CONFIG="{wx_config}" WX_CONFIG_ARGS="--unicode --static" '
            f'VC_FUSE_PACKAGE={fuse_pkg} '
            f'TC_EXTRA_CFLAGS="{extra}" TC_EXTRA_CXXFLAGS="{extra}"'
        )
        # musl has no pthread_cancel. wx thread code references it when
        # wxUSE_THREADS is on, which the console headers require.
        stub = os.path.join(self.build_folder, "pthread_cancel_stub.c")
        stub_obj = os.path.join(self.build_folder, "pthread_cancel_stub.o")
        with open(stub, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <pthread.h>\n"
                "int pthread_cancel(pthread_t thread) { (void)thread; return 0; }\n"
                "int pthread_setcancelstate(int state, int *oldstate) {\n"
                "  if (oldstate) *oldstate = 0;\n"
                "  return 0;\n"
                "}\n"
            )
        self.run(f'"{cc}" -c "{stub}" -o "{stub_obj}"', env="conanbuild")
        make += f' TC_EXTRA_LFLAGS="{stub_obj}"'
        self.run(make, cwd=src, env="conanbuild")
        binary = os.path.join(src, "Main", "veracrypt")
        if not os.path.isfile(binary):
            raise RuntimeError(f"VeraCrypt binary was not produced at {binary}")
        self._sign_elf(binary)
        self.run(f'"{binary}" --text --version', cwd=src, env="conanrun")
        self.run(f'"{binary}" --text --test', cwd=src, env="conanrun")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "veracrypt", src=os.path.join(self.source_folder, "src", "Main"), dst=bindir)
        binary = os.path.join(bindir, "veracrypt")
        self._sign_elf(binary)
        copy(self, "License.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
