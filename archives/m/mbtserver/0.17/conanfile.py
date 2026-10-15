#!/usr/bin/env python3
"""Conan recipe -- mbtserver 0.17 (autotools upstream, manual build on OHOS).

MbtServer is the Tilburg Memory-Based Tagger server extension
(LanguageMachines). Upstream builds with GNU Autotools, but the release
tarball ships no pre-generated configure script and OHOS workers provide no
automake/autoreconf, so build() compiles the sources directly with the
Conan toolchain compiler (same approach as the merged sibling recipe
archives/t/timbl/6.1, which shares the LanguageMachines stack).

Dependency vendoring (R36): upstream configure.ac requires
ticcutils >= 0.36, timbl >= 6.4.14 and mbt >= 3.5, but none of those three
is published in the ohpcd remote (preflight: "Package 'ticcutils/0.38'
not resolved"). Following the serf/1.3.10 precedent, this recipe vendors
the three missing sources as private static sub-builds: conandata.yml
keeps their official upstream tarballs + sha256 under `vendored_sources`,
source() unpacks them under _vendored/, build() compiles them to private
static archives with per-lib config.h files, and package() merges the
archives plus all public headers into this package. Remote `requires` keep
only artifacts with publish evidence: icu/76.1, libxml2/2.15.3,
zlib/1.3.2, bzip2/1.0.8.2 (ticcutils XMLtools needs libxml2, Unicode needs
icu, zipper needs zlib/bz2). package_info lists the vendored libs so
consumers link dependents-first without extra references.

Upstream audit (see test_package/MANIFEST.yml): the 0.17 tarball registers
no automated tests (no TESTS/check_PROGRAMS in any Makefile.am, CI runs
build + cppcheck only), so build() does not invoke make check and instead
emits the HMBS_UPSTREAM_TEST_RESULT status=no_tests machine evidence.
"""

import json
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# Vendored LanguageMachines stack, bottom-up (each entry: sources key,
# config package name/string, lib archive base name, include subdir).
_VENDORED = ("ticcutils", "timbl", "mbt")

_TICCUTILS_SOURCES = [
    "LogStream.cxx", "StringOps.cxx", "Configuration.cxx", "Timer.cxx",
    "XMLtools.cxx", "zipper.cxx", "FileUtils.cxx", "CommandLine.cxx",
    "SocketBasics.cxx", "ServerBase.cxx", "FdStream.cxx", "Unicode.cxx",
    "UniHash.cxx",
]
_TIMBL_SOURCES = [
    "Common.cxx", "GetOptClass.cxx", "IBtree.cxx", "IBprocs.cxx",
    "Targets.cxx", "Features.cxx", "Instance.cxx", "MBLClass.cxx",
    "MsgClass.cxx", "StringOps.cxx", "TimblAPI.cxx", "Choppers.cxx",
    "TimblExperiment.cxx", "IGExperiment.cxx", "Metrics.cxx",
    "Testers.cxx", "TRIBLExperiments.cxx", "LOOExperiment.cxx",
    "CVExperiment.cxx", "Types.cxx", "neighborSet.cxx", "Statistics.cxx",
    "BestArray.cxx",
]
_MBT_SOURCES = [
    "MbtAPI.cxx", "Pattern.cxx", "TagLex.cxx", "Sentence.cxx",
    "RunTagger.cxx", "GenerateTagger.cxx", "Tagger.cxx",
]
_MBTSERVER_SOURCES = ["MbtServerBase.cxx", "MbtJSONServerBase.cxx"]

# (config PACKAGE, PACKAGE_NAME, PACKAGE_STRING, VERSION) per vendored lib.
_CONFIG_META = {
    "ticcutils": ("ticcutils", "ticcutils", "ticcutils 0.38", "0.38"),
    "timbl": ("timbl", "timbl", "timbl 7.0", "7.0"),
    "mbt": ("mbt", "mbt", "mbt 3.13", "3.13"),
}
_CONFIG_EXTRA = {
    # OHOS (Linux-like) provides getaddrinfo; daemon() is absent so the
    # fcntl fallback in ServerBase.cxx is used (HAVE_DAEMON undefined).
    # OpenMP is disabled: clang workers report it unsupported and every
    # use site is guarded by #ifdef HAVE_OPENMP (single-thread fallback).
    "ticcutils": "#define HAVE_GETADDRINFO 1\n",
    "timbl": "/* HAVE_OPENMP intentionally undefined: single-threaded */\n",
    "mbt": "#define HAVE_PTHREAD 1\n#define HAVE_LIBPTHREAD 1\n",
}


class MbtserverConan(ConanFile):
    name = "mbtserver"
    version = "0.17"
    description = "Memory-based Tagger and Tagger Generator (server part) - MBT TCP/JSON tagger server"
    license = "GPL-3.0-only"
    homepage = "https://github.com/LanguageMachines/mbtserver"
    url = "https://github.com/LanguageMachines/mbtserver"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Only artifacts with remote publish evidence. ticcutils/timbl/mbt
        # are vendored privately below (serf/1.3.10 precedent).
        self.requires("icu/76.1")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.2")
        self.requires("bzip2/1.0.8.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        vendored = self.conan_data.get("vendored_sources", {})
        for lib in _VENDORED:
            entry = vendored.get(lib)
            if not entry:
                continue
            dest = os.path.join(self.source_folder, "_vendored", lib)
            get(self, url=entry["url"], sha256=entry["sha256"],
                destination=dest, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def _read_build_env(self):
        """Read compiler settings from conanbuild.conf generated by AutotoolsToolchain."""
        env = {}
        conf_path = os.path.join(self.build_folder, "conanbuild.conf")
        if not os.path.exists(conf_path):
            conf_path = os.path.join(self.generators_folder, "conanbuild.conf")
        if os.path.exists(conf_path):
            with open(conf_path) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("["):
                        key, val = line.split("=", 1)
                        env[key.strip()] = val.strip()
        return env

    def _write_config_h(self, path, package, name, string, version, extra=""):
        content = (
            "/* config.h - generated by Conan build (manual, bypassing autotools) */\n"
            "#ifndef %(guard)s\n#define %(guard)s\n\n"
            "/* Package identification */\n"
            "#define PACKAGE \"%(package)s\"\n"
            "#define PACKAGE_NAME \"%(name)s\"\n"
            "#define PACKAGE_VERSION \"%(version)s\"\n"
            "#define VERSION \"%(version)s\"\n"
            "#define PACKAGE_STRING \"%(string)s\"\n"
            "#define PACKAGE_BUGREPORT \"lamasoftware@science.ru.nl\"\n\n"
            "%(extra)s\n#endif /* %(guard)s */\n"
        ) % {
            "guard": package.upper() + "_VENDORED_CONFIG_H",
            "package": package, "name": name, "string": string,
            "version": version, "extra": extra,
        }
        with open(path, "w", newline="\n") as f:
            f.write(content)

    def _dep_flags(self):
        """Aggregate -I/-L/-l flags from Conan dependencies.

        Only remote deps remain (icu/libxml2/zlib/bzip2); the vendored
        LanguageMachines libs come from _vendored_*_flags. Flags come from
        cpp_info (never from shell environment, R33).
        """
        include_dirs = []
        lib_dirs = []
        libs = []
        sys_libs = []
        defines = []
        cxxflags_extra = []
        for dep in self.dependencies.values():
            pf = getattr(dep, "package_folder", None) or ""

            def _abs(paths):
                out = []
                for p in paths:
                    p = str(p)
                    if not os.path.isabs(p) and pf:
                        p = os.path.join(pf, p)
                    out.append(p)
                return out

            include_dirs += _abs(dep.cpp_info.includedirs)
            lib_dirs += _abs(dep.cpp_info.libdirs)
            for lib in dep.cpp_info.libs:
                if lib not in libs:
                    libs.append(str(lib))
            for syslib in dep.cpp_info.system_libs:
                if syslib not in sys_libs:
                    sys_libs.append(str(syslib))
            defines += [str(d) for d in dep.cpp_info.defines]
            cxxflags_extra += [str(f) for f in dep.cpp_info.cxxflags]
        inc_flags = " ".join("-I\"%s\"" % p for p in dict.fromkeys(include_dirs))
        lib_flags = " ".join("-L\"%s\"" % p for p in dict.fromkeys(lib_dirs))
        link_libs = " ".join("-l%s" % lib for lib in libs)
        if sys_libs:
            link_libs += " " + " ".join("-l%s" % lib for lib in sys_libs)
        define_flags = " ".join("-D%s" % d for d in defines)
        return inc_flags, lib_flags, link_libs, define_flags, " ".join(cxxflags_extra)

    def _vendored_includes(self):
        flags = ["-I\"%s\"" % os.path.join(self.source_folder, "include")]
        for lib in ("mbt", "timbl", "ticcutils"):
            flags.append("-I\"%s\"" % os.path.join(
                self.source_folder, "_vendored", lib, "include"))
        return " ".join(flags)

    def _write_icuio_shim(self, shim_root):
        """Provide a header-only unicode/ustream.h.

        icu/76.1 is built with --disable-icuio (see archives/i/icu/76.1/
        conanfile.py configure_args), so its package lacks the icu-io
        header unicode/ustream.h and libicuio. ticcutils 0.38 hard-requires
        icu-uc + icu-io (configure.ac PKG_CHECK_MODULES) and
        include/ticcutils/Unicode.h includes unicode/ustream.h for the
        debug operator<< / operator>> on UnicodeString (used in
        src/Unicode.cxx cerr << line paths and UniFilter streaming).
        The shim implements the two operators inline on top of the public
        icuuc API (toUTF8String/fromUTF8, UTF-8 is the ticcutils file
        encoding), so no extra link library is needed.
        """
        uni_dir = os.path.join(shim_root, "unicode")
        os.makedirs(uni_dir, exist_ok=True)
        path = os.path.join(uni_dir, "ustream.h")
        content = (
            "/* vendored ustream.h shim - fills icu/76.1 --disable-icuio gap */\n"
            "#ifndef MBTSERVER_VENDORED_USTREAM_H\n"
            "#define MBTSERVER_VENDORED_USTREAM_H\n"
            "\n"
            "#include \"unicode/utypes.h\"\n"
            "\n"
            "#if U_SHOW_CPLUSPLUS_API\n"
            "\n"
            "#include \"unicode/unistr.h\"\n"
            "\n"
            "#include <iostream>\n"
            "#include <string>\n"
            "\n"
            "U_NAMESPACE_BEGIN\n"
            "\n"
            "inline std::ostream& operator<<(std::ostream& stream,\n"
            "                                const UnicodeString& s) {\n"
            "    std::string t;\n"
            "    s.toUTF8String(t);\n"
            "    stream << t;\n"
            "    return stream;\n"
            "}\n"
            "\n"
            "inline std::istream& operator>>(std::istream& stream,\n"
            "                                UnicodeString& s) {\n"
            "    std::string t;\n"
            "    stream >> t;\n"
            "    if (stream) {\n"
            "        s = UnicodeString::fromUTF8(t);\n"
            "    }\n"
            "    return stream;\n"
            "}\n"
            "\n"
            "U_NAMESPACE_END\n"
            "\n"
            "#endif /* U_SHOW_CPLUSPLUS_API */\n"
            "\n"
            "#endif /* MBTSERVER_VENDORED_USTREAM_H */\n"
        )
        with open(path, "w", newline="\n") as f:
            f.write(content)
        return shim_root

    def _compile_lib(self, cxx, base_flags, cfg_dir, src_subdir, sources,
                     obj_prefix, lib_name):
        self._write_config_h(
            os.path.join(cfg_dir, "config.h"),
            *(_CONFIG_META[src_subdir] if src_subdir in _CONFIG_META else
              ("mbtserver", "MbtServer", "MbtServer 0.17", "0.17")),
            extra=_CONFIG_EXTRA.get(src_subdir, ""))
        if src_subdir == "mbtserver":
            src_dir = os.path.join(self.source_folder, "src")
            inc_dir = os.path.join(self.source_folder, "include")
        else:
            src_dir = os.path.join(
                self.source_folder, "_vendored", src_subdir, "src")
            inc_dir = os.path.join(
                self.source_folder, "_vendored", src_subdir, "include")
        # Own config.h dir FIRST: build_dir carries mbtserver's config.h
        # (VERSION 0.17) and must not shadow this lib's VERSION macros.
        flags = "-I\"%s\" -I\"%s\" %s" % (cfg_dir, inc_dir, base_flags)
        objs = []
        for s in sources:
            obj = "%s_%s" % (obj_prefix, s.replace(".cxx", ".o"))
            self.run("\"%s\" %s -c \"%s\" -o \"%s\"" % (
                cxx, flags, os.path.join(src_dir, s), obj))
            objs.append("\"%s\"" % obj)
        return objs

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        build_dir = self.build_folder
        cfg_root = os.path.join(build_dir, "_cfg")
        for lib in list(_VENDORED) + ["mbtserver"]:
            os.makedirs(os.path.join(cfg_root, lib), exist_ok=True)

        # mbtserver's own config.h (kept at build root like before so the
        # documented -I<build_dir> keeps working for dependent tooling).
        self._write_config_h(
            os.path.join(build_dir, "config.h"),
            "mbtserver", "MbtServer", "MbtServer 0.17", "0.17")
        self._write_config_h(
            os.path.join(cfg_root, "mbtserver", "config.h"),
            "mbtserver", "MbtServer", "MbtServer 0.17", "0.17")

        # Read compiler settings from conanbuild.conf (R33: never rely on
        # bare shell CC/CXX/LDFLAGS environment variables)
        env = self._read_build_env()
        cxx = env.get("CXX", "")
        if not cxx:
            try:
                comp_execs = self.conf.get("tools.build:compiler_executables", default={}) or {}
                cxx = comp_execs.get("cpp", "clang++")
            except Exception:
                cxx = "clang++"
        cxxflags = env.get("CXXFLAGS", "-fPIC -O2")
        ldflags = env.get("LDFLAGS", "")
        ar = env.get("AR", "llvm-ar")
        inc_flags, lib_flags, link_libs, define_flags, dep_cxxflags = self._dep_flags()
        vend_inc = self._vendored_includes()
        # icu/76.1 lacks unicode/ustream.h (--disable-icuio); the shim dir
        # provides exactly that header (header-only, no extra link lib).
        # It is prepended FIRST so #include "unicode/ustream.h" resolves.
        icuio_shim = self._write_icuio_shim(os.path.join(build_dir, "_icuio_shim"))
        # Upstream src/Makefile.am files build with -std=c++17
        base_flags = "%s -std=c++17 -I\"%s\" -I\"%s\" %s %s %s %s" % (
            cxxflags, icuio_shim, build_dir, vend_inc, inc_flags, define_flags,
            dep_cxxflags)

        # Bottom-up private static sub-builds (dependents-first link order
        # mirrors the upstream configure.ac LIBS accumulation).
        priv_libs = []
        for lib, sources in (("ticcutils", _TICCUTILS_SOURCES),
                             ("timbl", _TIMBL_SOURCES),
                             ("mbt", _MBT_SOURCES)):
            objs = self._compile_lib(
                cxx, base_flags, os.path.join(cfg_root, lib), lib,
                sources, lib, "lib%s.a" % lib)
            self.run("%s rcs lib%s.a %s" % (ar, lib, " ".join(objs)))
            priv_libs.append(lib)

        # mbtserver library (from src/Makefile.am libmbtserver_la_SOURCES)
        srv_objs = self._compile_lib(
            cxx, base_flags, os.path.join(cfg_root, "mbtserver"),
            "mbtserver", _MBTSERVER_SOURCES, "mbtserver", "libmbtserver.a")
        self.run("%s rcs libmbtserver.a %s" % (ar, " ".join(srv_objs)))

        # Server binary (from src/Makefile.am bin_PROGRAMS), linked against
        # the private static stack plus remote deps. pthread mirrors the
        # upstream AX_PTHREAD handling (configure.ac).
        pthread = "-lpthread" if self.settings.os in ("Linux", "OHOS") else ""
        priv_link = "-L. -lmbtserver -lmbt -ltimbl -lticcutils"
        server_src = os.path.join(src, "src", "MbtServer.cxx")
        self.run("\"%s\" %s \"%s\" -o mbtserver %s %s %s %s %s" % (
            cxx, base_flags, server_src, priv_link, lib_flags, link_libs,
            ldflags, pthread))

        # -- Upstream test evidence --
        # Audited mbtserver 0.17: upstream registers no automated tests
        # (no TESTS/check_PROGRAMS in any Makefile.am; CI runs build +
        # cppcheck only). Emit the no_tests machine evidence here; the
        # test_package re-emits it every run so cache-hits stay covered.
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "mbtserver 0.17 上游无自动化测试套件：39 条目源码归档无 tests/test 目录与 *test* 源文件；顶层/src/include/docs/example 的 Makefile.am 均无 TESTS/check_PROGRAMS/check-local 注册；上游 CI (mbtserver.yml) 仅构建 + cppcheck（详见 test_package/MANIFEST.yml 审计）",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))

    def package(self):
        # Private static stack + server library/binary.
        for lib in ("libticcutils.a", "libtimbl.a", "libmbt.a", "libmbtserver.a"):
            copy(self, lib, src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "mbtserver", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Public headers: own tree plus each vendored lib's tree
        # (preserving include/<lib>/ structure; *.hpp covers json.hpp).
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"))
        for lib in _VENDORED:
            copy(self, "*.h", src=os.path.join(self.source_folder, "_vendored", lib, "include"), dst=os.path.join(self.package_folder, "include"))
            copy(self, "*.hpp", src=os.path.join(self.source_folder, "_vendored", lib, "include"), dst=os.path.join(self.package_folder, "include"))
        # Ship the icu-io shim header to consumers: packaged public headers
        # (ticcutils/Unicode.h) include unicode/ustream.h, but icu/76.1 has
        # --disable-icuio and provides no such header. build() already uses
        # this shim; regenerating here keeps package() hermetic (cache-hit
        # safe) and places it at include/unicode/ustream.h so consumer
        # -I<mbtserver>/include resolves it while nested unicode/unistr.h
        # still resolves to the icu package.
        shim_root = self._write_icuio_shim(os.path.join(self.build_folder, "_icuio_shim"))
        copy(self, "ustream.h",
             src=os.path.join(shim_root, "unicode"),
             dst=os.path.join(self.package_folder, "include", "unicode"))

    def package_info(self):
        # Dependents-first so consumers resolve symbols without extra refs.
        self.cpp_info.libs = ["mbtserver", "mbt", "timbl", "ticcutils"]
        self.cpp_info.bindirs = ["bin"]
        # Public headers (timbl/ticcutils vendored trees) include
        # unicode/unistr.h, libxml/parser.h, zlib.h, bzlib.h, so the
        # remote deps must propagate to consumers (link + includes).
        self.cpp_info.requires = [
            "icu::icu",
            "libxml2::libxml2",
            "zlib::zlib",
            "bzip2::bzip2",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
