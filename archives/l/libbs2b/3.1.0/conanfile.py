"""Conan 2 recipe for libbs2b 3.1.0 on HarmonyOS PC.

适配要点（详见 notes.md）：
* 源：上游 sourceforge 在沙箱不可达 → 换用 Fedora lookaside 的 pristine 上游 tarball
  （md5 与 Fedora 记录逐字一致），其内含**预生成 configure**，无需 autoreconf；
* 仓内既有 4 段补丁（config.guess / config.sub / configure.ac / src-Makefile.am）实测均可打在换源后的源树上；
* OHOS 分支显式给出 clang/llvm-* 工具与目标三元组（与同批 libcddb/libxxf86dga 一致的做法）；
* 不引入 libsndfile：上游 `PKG_CHECK_EXISTS([sndfile])` 只影响命令行工具（examples），库本体不需要。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libbs2bConan(ConanFile):
    name = "libbs2b"
    version = "3.1.0"
    description = "Bauer stereophonic-to-binaural DSP library"
    license = "MIT"
    homepage = "http://bs2b.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 上游 configure.ac 第 18-19 行是**硬性**要求（不是可选）：
        #   PKG_CHECK_EXISTS([sndfile], [], [AC_MSG_ERROR(Please install libsndfile.)])
        # 初版误判为可选，实测 configure 直接报 "Please install libsndfile."。
        self.requires("libsndfile/1.2.2")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Conan 的 get() 不支持 .tar.lzma（会走 zip 分支报 BadZipFile），故：
        # download() 取包并校验 sha256 → Python 标准库 lzma+tarfile 解包 → 上移一层（等价 strip_root）。
        import io
        import lzma
        import tarfile

        sources = self.conan_data["sources"]
        filename = "libbs2b-3.1.0.tar.lzma"
        download(self, sources["url"], filename, sha256=sources["sha256"])
        archive = os.path.join(self.source_folder, filename)
        with lzma.open(archive) as stream:
            data = stream.read()
        # 注意：export_sources 已把 patches/ 放进 source_folder，因此不能靠“唯一子目录”判断，
        # 先把 tarball 解到独立子目录，再把其唯一条目（libbs2b-3.1.0/）的内容上移一层。
        staging = os.path.join(self.source_folder, "_staging")
        os.makedirs(staging, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(staging)
        os.remove(archive)
        roots = [entry for entry in os.listdir(staging)
                 if os.path.isdir(os.path.join(staging, entry))]
        if len(roots) != 1:
            raise ConanException("unexpected tarball layout: {}".format(sorted(roots)))
        root = os.path.join(staging, roots[0])
        for entry in os.listdir(root):
            shutil.move(os.path.join(root, entry), self.source_folder)
        shutil.rmtree(staging, ignore_errors=True)
        apply_conandata_patches(self)

    def generate(self):
        # 上游用 PKG_CHECK_EXISTS([sndfile]) 探测；Conan 的 conanbuild 环境不会自动把
        # 生成器目录加进 PKG_CONFIG_PATH，故显式注入（与同仓 abiword-plugin-* 的做法一致）。
        from conan.tools.gnu import PkgConfigDeps

        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(self.generators_folder))
        # 上游 configure.ac 只做 `PKG_CHECK_EXISTS([sndfile])`（检查存在性），**不会**导出
        # sndfile 的 CFLAGS/LIBS；而 src/Makefile.am 的 bs2bconvert/bs2bstream 要
        # `#include <sndfile.h>` 并链接 -lsndfile。故显式把依赖头/库路径注入 CPPFLAGS/LDFLAGS
        # （实测：不注入时编译 bs2bconvert.c 报 `'sndfile.h' file not found`）。
        sndfile = self.dependencies["libsndfile"]
        include_flags = ["-I" + os.path.join(sndfile.package_folder, d)
                         for d in sndfile.cpp_info.includedirs
                         if os.path.isdir(os.path.join(sndfile.package_folder, d))]
        lib_flags = ["-L" + os.path.join(sndfile.package_folder, d)
                     for d in sndfile.cpp_info.libdirs
                     if os.path.isdir(os.path.join(sndfile.package_folder, d))]
        if include_flags:
            tc.configure_args.append("CPPFLAGS={}".format(" ".join(include_flags)))
        if lib_flags:
            tc.configure_args.append("LDFLAGS={}".format(" ".join(lib_flags)))
        tc.configure_args.append("--disable-rpath")
        tc.configure_args.append("--enable-shared" if self.options.shared else "--disable-shared")
        tc.configure_args.append("--disable-static" if self.options.shared else "--enable-static")
        env = tc.environment()
        if str(self.settings.os) == "OHOS":
            exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            cc = exes.get("c", "/data/service/hnp/bin/clang")
            cxx = exes.get("cpp", "/data/service/hnp/bin/clang++")
            tool_dir = os.path.dirname(cc)
            env.define("CC", cc)
            env.define("CXX", cxx)
            for variable, command in (("LD", "ld.lld"), ("AR", "llvm-ar"),
                                      ("RANLIB", "llvm-ranlib"), ("NM", "llvm-nm"),
                                      ("STRIP", "llvm-strip"), ("OBJDUMP", "llvm-objdump")):
                found = os.path.join(tool_dir, command)
                if not os.path.isfile(found):
                    found = shutil.which(command)
                if not found:
                    raise ConanException("required OHOS tool not found: " + command)
                env.define(variable, found)
            triplet = self._gnu_triplet()
            tc.update_configure_args({"--build": triplet, "--host": triplet})
        tc.generate(env=env)

    def build(self):
        self._relax_umask()
        autotools = Autotools(self)
        autotools.configure()
        # configure 生成的 config.status **同样**带 `umask 077`，make 期间一旦有规则重跑它
        # 就会再次报 `could not setup config files machinery`（本轮实测：只改 configure 仍失败）。
        self._relax_umask()
        autotools.make()

    def _relax_umask(self):
        """把 configure / config.status 里的 `umask 077` 改成 `umask 022`（HMDFS 必需）。

        实测（本机）：二者都用 `(umask 077 && mktemp -d "./confXXXXXX")` 建 2700 的临时目录；
        hmdfs 经 group 位中介目录访问且 chmod 无效，目录不可遍历 → config.status 报
        `could not setup config files machinery`。022 生成 drwxr-s--x 即可通过。
        源目录与构建目录都扫（configure 在源目录、config.status 由 configure 生成）。
        """
        from pathlib import Path

        patched = []
        for root in {self.source_folder, self.build_folder}:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in ("configure", "config.status"):
                    if name not in filenames:
                        continue
                    path = Path(dirpath, name)
                    content = path.read_text(encoding="utf-8", errors="replace")
                    if "umask 077" in content:
                        path.write_text(content.replace("umask 077", "umask 022"),
                                        encoding="utf-8")
                    patched.append(path)
        # 关键：补丁 0003 改过 configure.ac，比 configure 新 → make 会触发
        # `$(srcdir)/configure: $(am__configure_deps)` / `config.status --recheck` 规则，
        # 重跑 configure 并**重新生成带 umask 077 的 config.status**（本轮实测：仅改文件仍失败）。
        # 处理方式：把 autotools 的**输入**置旧、**生成物**置当前时间（都不能用未来时间戳，
        # 否则 autoconf 的健全性检查报 "newly created file is older than distributed files"）。
        import time

        now = time.time()
        old = now - 600
        for path in patched:
            os.utime(path, (now, now))
        for base in {self.source_folder, self.build_folder}:
            for name in ("Makefile", "config.h"):
                candidate = Path(base, name)
                if candidate.is_file():
                    os.utime(candidate, (now, now))
            for name in ("configure.ac", "configure.in", "aclocal.m4", "Makefile.am",
                         "Makefile.in", "config.h.in", "config.h.in~"):
                candidate = Path(base, name)
                if candidate.is_file():
                    os.utime(candidate, (old, old))
        return [str(p) for p in patched]

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["bs2b"]
        # 上游把公开头安装在 include/bs2b/（bs2b.h / bs2btypes.h / bs2bclass.h / bs2bversion.h），
        # 因此同时导出该子目录，使 `#include <bs2b/bs2b.h>` 与 `#include <bs2b.h>` 两种写法都可用
        # （实测：只导出 include/ 时 test_package 报 `'bs2b.h' file not found`）。
        self.cpp_info.includedirs = ["include", "include/bs2b"]
        self.cpp_info.set_property("pkg_config_name", "libbs2b")

    def _gnu_triplet(self):
        machine = {"armv8": "aarch64", "armv8.3": "aarch64", "x86_64": "x86_64"}.get(
            str(self.settings.arch), str(self.settings.arch))
        return "{}-unknown-linux-ohos".format(machine)
