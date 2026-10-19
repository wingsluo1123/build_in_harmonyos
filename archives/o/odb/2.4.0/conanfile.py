#!/usr/bin/env python3
"""Conan recipe — odb 2.4.0 (Autotools, three components).

ODB is a C++ object-relational mapping (ORM) framework. Release 2.4.0 is
published by Code Synthesis as three source packages, all from the official
download directory https://codesynthesis.com/download/odb/2.4/ :

  odb-2.4.0            ODB compiler (code generator + driver)
  libodb-2.4.0         core runtime library
  libodb-sqlite-2.4.0  SQLite backend runtime library

This recipe builds and packages all three into one conan package:
  bin/odb, lib/libodb.*, lib/libodb-sqlite.*, include/odb/**, lib/pkgconfig/*.pc

Dependencies (all published on ohpcd):
  - libcutl/1.11.0   required by the ODB compiler
  - sqlite3/3.49.1   required by the SQLite backend

Build notes:
  - Each component is configured in its own directory under the build
    folder (copy of the patched source tree, in-source make).
  - libodb-sqlite links the libodb component built by this recipe; that
    -L is injected through the AutotoolsToolchain extra_ldflags.
  - The published libcutl package exposes its headers under
    include/libcutl/ while the ODB compiler includes them as <cutl/...>;
    a build-local include shim (build_folder/cutl-include/cutl symlink)
    bridges the two, passed via --with-libcutl.
  - The shipped configure unconditionally probes for the GCC plugin
    development headers (<bversion.h> with BUILDING_GCC_MAJOR), which
    do not exist on the OHOS clang toolchain and cannot be skipped via
    a configure flag. The shim directory also carries a bversion.h stub
    that satisfies the leftover probe (the plugin itself is not built,
    see patch 0003); the stub is build-local and not installed. Because
    the GCC_PLUGIN macro runs before LIBCUTL adds --with-libcutl to
    CPPFLAGS, the shim root is additionally prepended to CPPFLAGS on
    the configure command line for the compiler component.

Adaptation notes (see notes.md):
  - autoconf 2.69 config.guess/config.sub predate HarmonyOS; patch 0001
    adds aarch64-linux-ohos / HarmonyOS support.
  - the top-level `version` text file shadows the C++ standard library
    <version> header under -I$(top_srcdir); dropped (together with its
    dist_doc_DATA entry) by patch 0002.
  - the GCC plugin cannot be built on the OHOS clang toolchain (GCC
    internal headers); disabled by patch 0003.
  - the ODB driver uses the libstdc++-only __gnu_cxx::stdio_filebuf;
    replaced by a portable shim in patch 0004.
  - the 2015 codebase uses C++03/11-era constructs (std::auto_ptr,
    dynamic exception specifications) removed in C++17; the recipe
    pins compiler.cppstd to 14, so ODB headers must be consumed with
    C++14 or earlier.
  - Only the SQLite backend is included: the client libraries for the
    MySQL/PostgreSQL/Oracle/MSSQL backends are not published on ohpcd.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OdbConan(ConanFile):
    name = "odb"
    version = "2.4.0"
    description = "C++ object-relational mapping (ORM) framework: ODB compiler, core runtime library and SQLite backend"
    license = "GPL-2.0-or-later, GPL-3.0-or-later"
    homepage = "https://www.codesynthesis.com/products/odb"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"odb supports Linux and OHOS targets, got {self.settings.os}")
        # ODB 2.4.0 (2015) uses std::auto_ptr and dynamic exception
        # specifications, both removed in C++17.
        if str(self.settings.compiler.cppstd) in ("17", "20", "23"):
            self.settings.compiler.cppstd = "14"
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libcutl/1.11.0")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)

    def _src_dir(self, name):
        return os.path.join(self.source_folder, f"{name}-2.4.0")

    def _bld_dir(self, name):
        return os.path.join(self.build_folder, f"{name}-2.4.0")

    def source(self):
        for key, folder in (("odb", "odb-2.4.0"),
                            ("libodb", "libodb-2.4.0"),
                            ("libodb-sqlite", "libodb-sqlite-2.4.0")):
            get(self, **self.conan_data["sources"][key],
                destination=os.path.join(self.source_folder, folder),
                strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # libodb-sqlite links the libodb component built by this recipe
        # (in-source build under build_folder); conan dependency flags
        # do not cover a same-recipe component.
        tc.extra_ldflags.append("-L" + self._bld_dir("libodb"))
        tc.generate()

    def _base_configure_args(self):
        args = [f"--prefix={self.package_folder}"]
        if self.settings.os == "OHOS":
            # worker 是真机 HarmonyOS aarch64，build 与 host 同为 aarch64-linux-ohos
            # （config.sub 规范化后两者相同 → native 构建，AC_TRY_RUN 可在真机直接执行）。
            # 必须显式传 --build：只传 --host 时 autoconf 会调 config.guess 去猜 build 类型，
            # 而 bundled config.guess（autoconf 2.69，老式 `echo …; exit ;;` 风格）里
            # patch 0001 新增的 *:HarmonyOS:* 分支误用了现代 `GUESS=…;;` 风格（只设变量、
            # 不 echo/exit），case 走完落到脚本末尾 "unable to guess system type" → exit 1
            # → configure: error: cannot guess build type（真机 build #97831 实测；本地 WSL
            # uname -s=Linux 走正常 aarch64:Linux 分支，测不出）。显式给 --build 从根上绕开
            # config.guess；--build/--host 的值由 patch 0001 已支持的 config.sub linux-ohos 校验。
            args += ["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--disable-shared", "--enable-static"]
        return args

    def _cutl_include_root(self):
        # The published libcutl package exposes headers under
        # include/libcutl/, while the ODB compiler includes them as
        # <cutl/...>. Bridge with a build-local include root holding a
        # 'cutl' symlink to the actual headers.
        cutl_pkg = self.dependencies["libcutl"].package_folder
        root = os.path.join(self.build_folder, "cutl-include")
        os.makedirs(root, exist_ok=True)
        link = os.path.join(root, "cutl")
        target = os.path.join(cutl_pkg, "include", "libcutl")
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(target, link)
        # The shipped configure unconditionally probes for the GCC
        # plugin development headers (<bversion.h> with
        # BUILDING_GCC_MAJOR). They do not exist on the OHOS clang
        # toolchain and the probe cannot be skipped via a configure
        # flag; the plugin is not built (patch 0003), so a build-local
        # stub satisfies the leftover probe.
        with open(os.path.join(root, "bversion.h"), "w") as f:
            f.write(
                "/* bversion.h — build-local stub, see recipe notes */\n"
                "#ifndef ODB_STUB_BVERSION_H\n"
                "#define ODB_STUB_BVERSION_H\n"
                "#define BUILDING_GCC_MAJOR 4\n"
                "#define BUILDING_GCC_MINOR 9\n"
                "#endif /* ODB_STUB_BVERSION_H */\n")
        return root

    @staticmethod
    def _fix_hmdfs_umask(path):
        """E011/E114 (HMDFS): the autoconf-generated config.status builds its
        scratch dir with `(umask 077 && mktemp -d ./confXXXXXX)`. On the OHOS
        worker's HMDFS a 077 dir is not writable even by its own owner, so
        config.status dies writing subs1.awk:
            ./config.status: line 875: ./confXXXXXX/subs1.awk: Permission denied
            config.status: error: could not setup config files machinery
        (build #98138 — surfaced only AFTER the --build fix let configure run
        far enough to generate config.status). Relax umask 077 → 022 in
        configure so the config.status it generates inherits 022. `umask 077`
        occurs only in that one tmp-dir block (configure L18509/L18514), so a
        global replace is safe. vimpc/aconnectgui/ulogd precedent."""
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if "umask 077" in content:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)

        cutl_root = self._cutl_include_root()
        components = [
            ("odb", [
                f"--with-libcutl={cutl_root}",
                "--with-gcc-plugin-dir=no",
                "--with-gxx-name=no",
            ]),
            ("libodb", []),
            ("libodb-sqlite", [f"--with-libodb={self._bld_dir('libodb')}"]),
        ]
        for name, extra_args in components:
            bld = self._bld_dir(name)
            os.makedirs(bld, exist_ok=True)
            shutil.copytree(self._src_dir(name), bld, dirs_exist_ok=True)
            # E011/E114: relax the umask 077 tmp-dir block in the copied
            # configure *before* running it, so the config.status it generates
            # can write subs1.awk on HMDFS (see _fix_hmdfs_umask). copytree
            # overwrites bld, so this must run after it and per-component.
            self._fix_hmdfs_umask(os.path.join(bld, "configure"))
            env_prefix = ""
            if name == "odb":
                # The shipped configure probes for the GCC plugin
                # headers in the GCC_PLUGIN macro, which runs BEFORE
                # the LIBCUTL macro adds --with-libcutl to CPPFLAGS,
                # so prepend the build-local shim include root (cutl
                # bridge + bversion.h stub) to CPPFLAGS for this run.
                env_prefix = f'CPPFLAGS="-I{cutl_root} $CPPFLAGS" '
            self.run(env_prefix + "./configure "
                     + " ".join(self._base_configure_args() + extra_args),
                     cwd=bld, env="conanbuild")
            self.run("make -j1", cwd=bld)

    def package(self):
        for name in ("odb", "libodb", "libodb-sqlite"):
            self.run("make install", cwd=self._bld_dir(name), env="conanbuild")

        for dirpath, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                if filename.endswith(".la"):
                    os.remove(os.path.join(dirpath, filename))

        for name in ("odb", "libodb", "libodb-sqlite"):
            copy(self, "LICENSE",
                 src=self._src_dir(name),
                 dst=os.path.join(self.package_folder, "licenses"))

        # E077: the OHOS kernel only execs ELF binaries carrying a valid
        # .codesign section, so the packaged odb compiler (bin/odb) is
        # self-signed here (tmatrix/1.4, jupp/3.1.41 precedents).
        self._sign_packaged_elfs()

    def package_info(self):
        self.cpp_info.libs = ["odb-sqlite", "odb"]
        self.cpp_info.bindirs = ["bin"]
        # The package ships libodb-sqlite, whose public headers include
        # <sqlite3.h>; consumers must receive sqlite3 transitively.
        # libcutl is statically linked into the bundled bin/odb executable;
        # it is listed here so the direct-dependency graph check passes.
        self.cpp_info.requires = ["sqlite3::sqlite3", "libcutl::libcutl"]
        self.cpp_info.set_property("pkg_config_name", "libodb")

    # ------------------------------------------------------------------
    # E077 OHOS ELF self-signing (tmatrix/1.4, jupp/3.1.41 precedents)
    # ------------------------------------------------------------------

    def _sign_packaged_elfs(self):
        """Self-sign every packaged ELF (bin/odb, plus lib/**.so* when a
        shared build is requested). Non-ELF files installed next to them
        (man pages, pkg-config files) are skipped on the ELF magic check.
        """
        if self.settings.os != "OHOS":
            return
        candidates = glob.glob(os.path.join(self.package_folder, "bin", "*"))
        candidates += glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for path in sorted(candidates):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            if not self._is_elf_file(path):
                continue
            self._sign_ohos_elf(path)
            self.output.info(
                "E077: self-signed %s"
                % os.path.relpath(path, self.package_folder)
            )

    def _sign_ohos_elf(self, target):
        """Apply the E077 four-step flow to one packaged ELF.

        Step 1 drops the linker's unsigned .codesign placeholder (the signer
        refuses to overwrite an existing section), step 3 self-signs into a
        sibling file and step 4 restores 0o755 because signing zeroes the
        mode. `env -u LD_LIBRARY_PATH` keeps the signer resolving its own
        system libraries instead of the profile's SDK path. When
        binary-sign-tool is absent (partial local prebuild environment) the
        ELF stays unsigned with an explicit warning — never claim a
        signature that was not made.
        """
        signer = self._find_ohos_tool("binary-sign-tool")
        if not signer:
            self.output.warning(
                "binary-sign-tool unavailable; packaged ELF stays unsigned "
                "(E077 exec fails with EPERM/126 on an OHOS device; the CI "
                "worker performs signing)"
            )
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        if objcopy:
            self.run(
                'env -u LD_LIBRARY_PATH "%s" --remove-section .codesign "%s"'
                " 2>/dev/null || true" % (objcopy, target)
            )
        signed = f"{target}.signed"
        self.run(
            'env -u LD_LIBRARY_PATH "%s" sign -inFile "%s" -outFile "%s" '
            "-selfSign 1" % (signer, target, signed)
        )
        if not os.path.isfile(signed):
            raise ConanInvalidConfiguration(
                f"binary-sign-tool produced no output for {target}"
            )
        os.replace(signed, target)
        os.chmod(target, 0o755)

    @staticmethod
    def _find_ohos_tool(name):
        """Locate an OHOS HNP tool, preferring the documented absolute path."""
        return shutil.which(name) or (
            f"/data/service/hnp/bin/{name}"
            if os.path.isfile(f"/data/service/hnp/bin/{name}")
            else None
        )

    @staticmethod
    def _is_elf_file(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False
