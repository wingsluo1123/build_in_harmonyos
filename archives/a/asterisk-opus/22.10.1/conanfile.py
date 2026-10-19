#!/usr/bin/env python3
"""Conan recipe — asterisk-opus 22.10.1 (Asterisk Opus format module).

Asterisk's Opus format-attribute module — res_format_attr_opus.so.
Uses the full Asterisk autotools build (configure + make). The source
tarball is the canonical Asterisk release (GitHub codeload tag, since
downloads.asterisk.org 404s in the OHOS sandbox); this recipe packages only
the Opus format-attribute module.

The module uses only Asterisk's internal format and Opus attribute APIs; the
actual codec implementation is a separate codec_opus module and is not part
of this package.

Asterisk configure also hard-requires libedit (pkg-config probe), libuuid
(e2fsprogs), jansson >= 2.11 and sqlite3; menuselect's own configure
hard-requires libxml2. Those deps are provisioned the same way (from
published ohpcd packages). The packaged deliverable is the Opus format
attribute module.
"""

import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, chdir, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

SYS_PREFIX = os.environ.get("DEFAULT_PREFIX") or os.path.join(os.path.expanduser("~"), "usr", "local")


def _copy_tree(src, dst):
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s):
                _copy_tree(s, d)
            else:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                if not os.path.exists(d):
                    shutil.copy2(s, d)


def _ensure_dep_present(prefix, pkg_dirs, rels):
    """Copy header/lib files from a dependency package folder into the prefix.

    pkg_dirs: list of (pkg_dir, rel_path) pairs; rels: list of rel paths to verify.
    """
    missing = [r for r in rels if not os.path.exists(os.path.join(prefix, r))]
    if not missing:
        return
    for pkg_dir, rel in pkg_dirs:
        src = os.path.join(pkg_dir, rel)
        if os.path.exists(src):
            _copy_tree(src, os.path.join(prefix, rel))
    still = [r for r in rels if not os.path.exists(os.path.join(prefix, r))]
    if still:
        raise ConanInvalidConfiguration(
            "dependency provisioning did not provide: " + ", ".join(still))


def _fix_pc_prefix(pc_path, prefix):
    """Rewrite the .pc `prefix=` line to the private SYS_PREFIX."""
    if not os.path.isfile(pc_path):
        return
    import re as _re
    data = open(pc_path, encoding="utf-8", errors="replace").read()
    data = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
    open(pc_path, "w", encoding="utf-8").write(data)


def _ensure_libedit(prefix, edit_pkg_dir):
    inc = os.path.join(prefix, "include", "histedit.h")
    libs = [os.path.join(prefix, "lib", "libedit.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "libedit.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not edit_pkg_dir or not os.path.isdir(edit_pkg_dir):
        raise ConanInvalidConfiguration(
            "libedit not found in prefix and no libedit dependency package folder available")
    _ensure_dep_present(prefix, [(edit_pkg_dir, "include"), (edit_pkg_dir, "lib")],
                        ["include/histedit.h", "include/editline/readline.h",
                         "lib/libedit.a", "lib/pkgconfig/libedit.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_libxml2(prefix, xml_pkg_dir):
    inc = os.path.join(prefix, "include", "libxml2", "libxml", "parser.h")
    # libxml2 依赖包可能是 shared（libxml2.so）或 static（libxml2.a）——
    # menuselect 子项目 configure 只需 xml2-config + 头文件即可链接（静态可用）。
    so = os.path.join(prefix, "lib", "libxml2.so")
    ar = os.path.join(prefix, "lib", "libxml2.a")
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "libxml-2.0.pc")]
    have_lib = os.path.exists(so) or os.path.exists(ar)
    if os.path.exists(inc) and have_lib and all(os.path.exists(p) for p in pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not xml_pkg_dir or not os.path.isdir(xml_pkg_dir):
        raise ConanInvalidConfiguration(
            "libxml2 not found in prefix and no libxml2 dependency package folder available")
    pc_src = None
    for root, _, files in os.walk(xml_pkg_dir):
        if "libxml-2.0.pc" in files:
            pc_src = os.path.join(root, "libxml-2.0.pc")
            break
    if pc_src:
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        std_pc = os.path.join(pc_dir, "libxml-2.0.pc")
        if not os.path.exists(std_pc):
            shutil.copy2(pc_src, std_pc)
        _fix_pc_prefix(std_pc, prefix)
    _copy_tree(os.path.join(xml_pkg_dir, "include", "libxml2"),
               os.path.join(prefix, "include", "libxml2"))
    # 复制 libxml2 库（.so 与 .a 任一，视依赖包类型）
    _copy_tree(os.path.join(xml_pkg_dir, "lib"),
               os.path.join(prefix, "lib"))
    if not (os.path.exists(so) or os.path.exists(ar)):
        raise ConanInvalidConfiguration(
            "libxml2 provisioning did not provide libxml2.so or libxml2.a")


def _ensure_ncurses(prefix, ncurses_pkg_dir):
    have_w = os.path.exists(os.path.join(prefix, "lib", "libncursesw.a"))
    have_t = os.path.exists(os.path.join(prefix, "lib", "libtinfo.a"))
    if have_w and have_t:
        return
    if not ncurses_pkg_dir or not os.path.isdir(ncurses_pkg_dir):
        raise ConanInvalidConfiguration(
            "ncurses not found in prefix and no ncurses dependency package folder available")
    _copy_tree(os.path.join(ncurses_pkg_dir, "include"),
               os.path.join(prefix, "include"))
    _copy_tree(os.path.join(ncurses_pkg_dir, "lib"),
               os.path.join(prefix, "lib"))
    tinfo = os.path.join(prefix, "lib", "libtinfo.a")
    if not os.path.exists(tinfo) and os.path.exists(os.path.join(prefix, "lib", "libncursesw.a")):
        shutil.copy2(os.path.join(prefix, "lib", "libncursesw.a"), tinfo)


def _ensure_uuid(prefix, uuid_pkg_dir):
    inc = os.path.join(prefix, "include", "uuid", "uuid.h")
    libs = [os.path.join(prefix, "lib", "libuuid.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "uuid.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not uuid_pkg_dir or not os.path.isdir(uuid_pkg_dir):
        raise ConanInvalidConfiguration(
            "uuid not found in prefix and no e2fsprogs dependency package folder available")
    _ensure_dep_present(prefix, [(uuid_pkg_dir, "include"), (uuid_pkg_dir, "lib")],
                        ["include/uuid/uuid.h", "lib/libuuid.a", "lib/pkgconfig/uuid.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_jansson(prefix, jansson_pkg_dir):
    inc = os.path.join(prefix, "include", "jansson.h")
    libs = [os.path.join(prefix, "lib", "libjansson.so")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "jansson.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not jansson_pkg_dir or not os.path.isdir(jansson_pkg_dir):
        raise ConanInvalidConfiguration(
            "jansson not found in prefix and no jansson dependency package folder available")
    _ensure_dep_present(prefix, [(jansson_pkg_dir, "include"), (jansson_pkg_dir, "lib")],
                        ["include/jansson.h", "lib/libjansson.so", "lib/pkgconfig/jansson.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_sqlite3(prefix, sqlite_pkg_dir):
    inc = os.path.join(prefix, "include", "sqlite3.h")
    libs = [os.path.join(prefix, "lib", "libsqlite3.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "sqlite3.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs):
        _ensure_sqlite3_pc(prefix)
        return
    if not sqlite_pkg_dir or not os.path.isdir(sqlite_pkg_dir):
        raise ConanInvalidConfiguration(
            "sqlite3 not found in prefix and no sqlite3 dependency package folder available")
    _ensure_dep_present(prefix, [(sqlite_pkg_dir, "include"), (sqlite_pkg_dir, "lib")],
                        ["include/sqlite3.h", "lib/libsqlite3.a"])
    _ensure_sqlite3_pc(prefix)


def _ensure_sqlite3_pc(prefix):
    pc_dir = os.path.join(prefix, "lib", "pkgconfig")
    os.makedirs(pc_dir, exist_ok=True)
    pc = os.path.join(pc_dir, "sqlite3.pc")
    if not os.path.exists(pc):
        with open(pc, "w", encoding="utf-8") as f:
            f.write("prefix=%s\n" % prefix)
            f.write("exec_prefix=${prefix}\nlibdir=${exec_prefix}/lib\n"
                    "includedir=${prefix}/include\nName: SQLite\n"
                    "Description: SQLite3 shim for Asterisk\n"
                    "Version: 3.49.1\nLibs: -L${libdir} -lsqlite3\n"
                    "Cflags: -I${includedir}\n")


def _drop_umask_077(path):
    try:
        data = open(path, "r", encoding="utf-8", errors="replace").read()
        if "umask 077" in data:
            open(path, "w", encoding="utf-8").write(data.replace("umask 077", "umask 022"))
    except Exception:
        pass


class AsteriskOpusConan(ConanFile):
    name = "asterisk-opus"
    version = "22.10.1"
    description = "Asterisk Opus format attribute module (res_format_attr_opus.so)"
    license = "GPL-2.0-only"
    homepage = "https://www.asterisk.org/"
    url = "https://www.asterisk.org/"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "packaging/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"asterisk-opus does not support os={self.settings.os}")

    def requirements(self):
        # libedit/libuuid/jansson/sqlite3 are hard requirements of the Asterisk
        # main configure;
        # libxml2 is required by the menuselect sub-configure; ncurses provides
        # tinfo symbols referenced by libedit. Remote publication is checked
        # by preflight before the recipe can be built.
        self.requires("libedit/20240808")
        self.requires("libxml2/2.15.3")
        self.requires("ncurses/6.6")
        self.requires("e2fsprogs/1.47.4")
        self.requires("jansson/2.15.1.1")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "menuselect.makedeps", src=os.path.join(self.recipe_folder, "packaging"),
             dst=os.path.join(self.export_sources_folder, "packaging"))

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        for filename in ("menuselect.makedeps", "res_opus_consumer.c"):
            copied = copy(self, filename,
                          src=os.path.join(self.export_sources_folder, "packaging"),
                          dst=os.path.join(self.source_folder, "packaging"))
            if not copied:
                raise FileNotFoundError(f"Exported packaging/{filename} is missing")

    def generate(self):
        edit_pkg = None
        xml_pkg = None
        ncurses_pkg = None
        uuid_pkg = None
        jansson_pkg = None
        sqlite_pkg = None
        try:
            edit_pkg = self.dependencies["libedit"].package_folder
        except Exception:
            pass
        try:
            xml_pkg = self.dependencies["libxml2"].package_folder
        except Exception:
            pass
        try:
            ncurses_pkg = self.dependencies["ncurses"].package_folder
        except Exception:
            pass
        try:
            uuid_pkg = self.dependencies["e2fsprogs"].package_folder
        except Exception:
            pass
        try:
            jansson_pkg = self.dependencies["jansson"].package_folder
        except Exception:
            pass
        try:
            sqlite_pkg = self.dependencies["sqlite3"].package_folder
        except Exception:
            pass
        _ensure_libedit(self._prefix(), edit_pkg)
        _ensure_libxml2(self._prefix(), xml_pkg)
        _ensure_ncurses(self._prefix(), ncurses_pkg)
        _ensure_uuid(self._prefix(), uuid_pkg)
        _ensure_jansson(self._prefix(), jansson_pkg)
        _ensure_sqlite3(self._prefix(), sqlite_pkg)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=x86_64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--without-pjproject",
            "--with-pjproject-bundled=no",
        ])
        inc_dir = os.path.join(self._prefix(), "include")
        lib_dir = os.path.join(self._prefix(), "lib")
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if os.path.isdir(inc_dir):
            tc.configure_args.append(f"CPPFLAGS=-I{inc_dir}")
        if os.path.isdir(lib_dir):
            tc.configure_args.append(f"LDFLAGS=-L{lib_dir} -Wl,-rpath,{lib_dir}")
        tc.configure_args.append(f"PKG_CONFIG_PATH={pc_dir}")
        tc.generate()

    def _prefix(self):
        return os.path.join(self.build_folder, "prefix")

    def _fs_env(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.define("CC", "/data/service/hnp/bin/clang")
        env.define("BUILD_CC", "/data/service/hnp/bin/clang")
        env.define("HOST_CC", "/data/service/hnp/bin/clang")
        # 私有 prefix/bin 放 PATH 最前，确保依赖工具来自当前 Conan 环境。
        bin_dir = os.path.join(self._prefix(), "bin")
        env.prepend_path("PATH", bin_dir)
        return env

    def _configure_args(self) -> list:
        args = [
            "--prefix=/",
            "--build=x86_64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--without-pjproject",
            "--with-pjproject-bundled=no",
        ]
        inc_dir = os.path.join(self._prefix(), "include")
        lib_dir = os.path.join(self._prefix(), "lib")
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if os.path.isdir(inc_dir):
            args.append(f"CPPFLAGS=-I{inc_dir}")
        if os.path.isdir(lib_dir):
            args.append(f"LDFLAGS='-L{lib_dir} -Wl,-rpath,{lib_dir}'")
        args.append(f"PKG_CONFIG_PATH={pc_dir}")
        args.append("ac_cv_prog_cc_works=yes")
        return args

    def build(self):
        apply_conandata_patches(self)
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        _drop_umask_077(os.path.join(self.source_folder, "menuselect", "configure"))
        env = self._fs_env()
        work = os.path.join(self.build_folder, "worktree")
        if os.path.exists(work):
            shutil.rmtree(work)
        os.makedirs(os.path.dirname(work), exist_ok=True)
        shutil.copytree(self.source_folder, work,
                        ignore=shutil.ignore_patterns(".tmp"))
        with env.vars(self, scope="build").apply():
            with chdir(self, work):
                cfg = f"./configure {' '.join(self._configure_args())}"
                makeopts = os.path.join(work, "makeopts")
                for attempt in range(1, 4):
                    try:
                        self.run(cfg, env="conanbuild")
                    except Exception:
                        pass
                    if os.path.isfile(makeopts) and os.path.getsize(makeopts) > 1000:
                        break
                    time.sleep(5)
                    cs = os.path.join(work, "config.status")
                    if os.path.isfile(cs):
                        try:
                            self.run("./config.status", env="conanbuild")
                        except Exception:
                            pass
                    if os.path.isfile(makeopts) and os.path.getsize(makeopts) > 1000:
                        break
                cs = os.path.join(work, "config.status")
                if os.path.isfile(cs):
                    try:
                        self.run("./config.status", env="conanbuild")
                    except Exception:
                        time.sleep(3)
                        self.run("./config.status", env="conanbuild")
                ms_dir = os.path.join(work, "menuselect")
                if os.path.isfile(os.path.join(ms_dir, "configure")):
                    ms_mk = os.path.join(ms_dir, "makeopts")
                    pc_dir = os.path.join(self._prefix(), "lib", "pkgconfig")
                    for _ in range(3):
                        try:
                            self.run(
                                f"cd menuselect && "
                                f"CC=/data/service/hnp/bin/clang "
                                f"PKG_CONFIG_PATH={pc_dir} ./configure "
                                f"--build=x86_64-unknown-linux-gnu "
                                f"--host=aarch64-unknown-linux-ohos "
                                f"ac_cv_prog_cc_works=yes",
                                env="conanbuild",
                            )
                        except Exception:
                            pass
                        if os.path.isfile(ms_mk) and os.path.getsize(ms_mk) > 100:
                            break
                        time.sleep(3)
                        cs = os.path.join(ms_dir, "config.status")
                        if os.path.isfile(cs):
                            try:
                                self.run("cd menuselect && ./config.status",
                                         env="conanbuild")
                            except Exception:
                                pass
                        if os.path.isfile(ms_mk) and os.path.getsize(ms_mk) > 100:
                            break
                # 只注入 menuselect.makedeps（声明目标模块的内部依赖），
                # 不覆盖 configure 生成的 menuselect.makeopts——让 configure
                # 生成的 makeopts 会包含正确的模块自符号（AST_MODULE_SELF_SYM）。
                mdep_src = os.path.join(work, "packaging", "menuselect.makedeps")
                if not os.path.isfile(mdep_src):
                    raise FileNotFoundError("packaging/menuselect.makedeps 缺失")
                mdst = os.path.join(work, "menuselect.makedeps")
                shutil.copy2(mdep_src, mdst)
                os.utime(mdst, (time.time() + 86400 * 365,) * 2)
                self.run("make menuselect.makeopts BUILD_CC=/data/service/hnp/bin/clang "
                         f"PKG_CONFIG_PATH={os.path.join(self._prefix(), 'lib', 'pkgconfig')}",
                         env="conanbuild")
                # autoconfig.h 是 config.header——顶层 config.status 需显式
                # 生成它（缺失会导致所有模块编译失败：asterisk.h include 它）。
                try:
                    self.run(f"cd {work} && ./config.status include/asterisk/autoconfig.h",
                             env="conanbuild")
                except Exception:
                    pass
                hdrs = [
                    "build_tools/make_buildopts_h > include/asterisk/buildopts.h",
                    "build_tools/make_build_h > include/asterisk/build.h",
                    "build_tools/make_defaults_h > defaults.h",
                ]
                for h in hdrs:
                    try:
                        self.run(f"cd {work} && ./{h}", env="conanbuild")
                    except Exception:
                        pass
                pc_dir = os.path.join(self._prefix(), "lib", "pkgconfig")
                mk_vars = (f"BUILD_CC=/data/service/hnp/bin/clang "
                           f"PKG_CONFIG_PATH={pc_dir}")
                consumer_src = os.path.join(work, "packaging", "res_opus_consumer.c")
                shutil.copy2(consumer_src, os.path.join(work, "res", "res_opus_consumer.c"))
                # Build the Opus format-attribute module. It links only against
                # Asterisk's module ABI; libopus belongs to codec_opus.
                for sub, tgt in (("res", "res_format_attr_opus.so"),):
                    try:
                        self.run(f"make -j1 -C {sub} SUBDIR={sub} ASTTOPDIR={work} "
                                 f"ASTCFLAGS=-I{work}/include SOLINK=-shared "
                                 f"{mk_vars} {tgt}", env="conanbuild")
                    except Exception:
                        try:
                            self.run(f"make -j1 -C {sub} SUBDIR={sub} ASTTOPDIR={work} "
                                     f"ASTCFLAGS=-I{work}/include SOLINK=-shared "
                                     f"{mk_vars} all", env="conanbuild")
                        except Exception:
                            pass
                self.run(f"make -j1 -C res SUBDIR=res ASTTOPDIR={work} "
                         f"ASTCFLAGS=-I{work}/include SOLINK=-shared "
                         f"{mk_vars} res_opus_consumer.so", env="conanbuild")
                shutil.copy2(os.path.join(work, "res", "res_opus_consumer.so"),
                             os.path.join(self.build_folder, "res_opus_consumer.so"))
        # Copy the products back to source_folder for package() and debugging
        for sub, tgt in (("res", "res_format_attr_opus.so"),):
            so_src = os.path.join(work, sub, tgt)
            if os.path.isfile(so_src):
                dst_sub = os.path.join(self.source_folder, sub)
                os.makedirs(dst_sub, exist_ok=True)
                shutil.copy2(so_src, os.path.join(dst_sub, tgt))

    def package(self):
        import glob
        mods_dst = os.path.join(self.package_folder, "lib", "asterisk", "modules")
        os.makedirs(mods_dst, exist_ok=True)
        placed = False
        for sub, tgt in (("res", "res_format_attr_opus.so"),):
            candidates = [
                os.path.join(self.build_folder, sub, tgt),
                os.path.join(self.source_folder, sub, tgt),
            ]
            src_so = next((p for p in candidates if os.path.exists(p)), None)
            if src_so and os.path.isfile(src_so):
                shutil.copy2(src_so, os.path.join(mods_dst, tgt))
                placed = True
        if not placed:
            autotools = Autotools(self)
            env = self._fs_env()
            with env.vars(self, scope="build").apply():
                autotools.install(args=["-j1"])
            keep = {os.path.join(mods_dst, "res_format_attr_opus.so")}
            for mod in glob.glob(os.path.join(mods_dst, "*.so")):
                if os.path.abspath(mod) not in keep:
                    try:
                        os.remove(mod)
                    except Exception:
                        pass
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "res_opus_consumer.so", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "asterisk-opus-tests"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/asterisk/modules"]
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
