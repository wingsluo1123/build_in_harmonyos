#!/usr/bin/env python3
"""Conan recipe for libneurosim 1.2.0 — INCF 神经模拟连接生成库（autotools）.

上游 tarball 无预生成 configure，需先跑 autogen.sh 生成。
可选依赖（MPI/Python）默认不启用；自带 libltdl 子目录。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibneurosimConan(ConanFile):
    name = "libneurosim"
    version = "1.2.0"
    description = "INCF libneurosim — neural simulation connection generation library"
    license = "GPL-2.0"
    homepage = "https://github.com/INCF/libneurosim"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # 上游 tarball 无预生成 configure，autogen.sh 需 aclocal/automake/libtool
        # （OHOS 系统缺这些工具）。按 abiword 插件先例以 tool_requires 拉入
        # 制品仓已发布的 automake/1.18 + libtool/2.5.4（按 build profile 解析，
        # conan create 需同时传 -pr:h 与 -pr:b）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess 无法识别 HarmonyOS（UNAME_SYSTEM=HarmonyOS）
        # ——显式指定 build/host triplet（aarch64-unknown-linux-ohos）。
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        # 可选依赖默认不启用（MPI/Python），保持最小依赖链。
        # --disable-maintainer-mode：禁用 autotools 维护者规则，使 make 不会
        # 自动重新运行 aclocal/automake/autoconf 重新生成 configure（libltdl
        # 子目录会因此生成含 umask 077 的 configure 并触发 config.status
        # --recheck → OHOS 沙箱 Permission denied；历次 mtime 方案未根治）。
        tc.configure_args.extend([
            "--without-mpi",
            "--with-python=no",
            "--disable-maintainer-mode",
        ])
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        # OHOS 沙箱默认 umask 077（+SGID）→ 0700 临时目录不可写（librrd 先例）。
        # 在 recipe 进程级统一改 umask 022，使 configure/config.status/make/mktemp
        # 等所有子进程继承 022，从根上避免 config.status 临时目录 Permission denied
        # （下方针对 configure/config.status 文件的 umask 077→022 替换作为双保险）。
        os.umask(0o022)
        # TMPDIR 兜底：config.status 的临时目录改走 $TMPDIR 绝对路径（见
        # _relax_umask，kimwitu 0001 同型方案）——./confXXXXXX 相对路径在
        # OHOS 沙箱 SGID/受限目录创建会 Permission denied（CI #62070 的
        # confgDmlkH/subs1.awk 失败）。TMPDIR 必须指向已存在的可写目录。
        tmpdir = os.environ.get("TMPDIR", "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
        # 上游 tarball 无预生成 configure 且无 libltdl 目录，需先跑 autotools 引导。
        # 不能直接用 ./autogen.sh：其 `libtoolize --ltdl` 会让 libtoolize 从
        # 自身 share/libtool-conan/libltdl 复制源（conan libtool 包该目录只有头文件，
        # 完整源在 share/libtool/）→ 报 lt__alloc.c not found。
        # 手动执行等价步骤：
        #   1) 从 conan libtool 包 share/libtool/ 复制完整 libltdl 源到项目目录
        #   2) aclocal/libtoolize/autoheader/autoconf/automake（libtoolize 不带 --ltdl）
        libtool_pkg = self.dependencies.build["libtool"].package_folder
        ltdl_src = os.path.join(libtool_pkg, "share", "libtool")
        # 同时复制到 source 根与 build 根（Autotools 实际运行 build 根的
        # libltdl/configure，若只复制 source 根，build 根副本仍含 umask 077）
        for base_dir in (self.source_folder, self.build_folder, os.path.dirname(self.build_folder)):
            ltdl_dst = os.path.join(base_dir, "libltdl")
            if os.path.isdir(ltdl_dst):
                continue
            if os.path.isdir(ltdl_src):
                shutil.copytree(ltdl_src, ltdl_dst)
        # 复制 libltdl 后**立即**替换其 configure 的 umask 077→022（config.status
        # 由 configure 生成，configure 022 则生成的 config.status 也为 022）——
        # 覆盖所有副本（source/build 根），避免后续 os.walk 漏掉。
        for base_dir in (self.source_folder, self.build_folder, os.path.dirname(self.build_folder)):
            ltdl_cfg = os.path.join(base_dir, "libltdl", "configure")
            if os.path.isfile(ltdl_cfg):
                with open(ltdl_cfg, encoding="utf-8", errors="surrogateescape") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(ltdl_cfg, "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(content)
        # libltdl 子目录 configure.ac 用 AC_CONFIG_AUX_DIR([../build-aux])，
        # 需在**项目顶层 build-aux/** 放置 auxiliary 文件（compile/config.guess/
        # config.sub/ltmain.sh/missing/install-sh）——从 libtool 包 build-aux 复制。
        aux_src = os.path.join(libtool_pkg, "share", "libtool", "build-aux")
        for base_dir in (self.source_folder, self.build_folder, os.path.dirname(self.build_folder)):
            top_aux = os.path.join(base_dir, "build-aux")
            if os.path.isdir(aux_src):
                os.makedirs(top_aux, exist_ok=True)
                for f in os.listdir(aux_src):
                    shutil.copy(os.path.join(aux_src, f), os.path.join(top_aux, f))
        for cmd in (
            # 直接用 aclocal（tool_requires 已注入 PATH），绕过上游 aclocal.sh：
            # 其 `which`/`dirname` 在 OHOS 沙箱报 Out of memory（CI #50949）
            "aclocal",
            "libtoolize --force --copy --automake",
            "autoheader",
            "autoconf",
            "automake --foreign --copy --add-missing",
        ):
            self.run(cmd, cwd=self.source_folder)
        # configure 由 autoconf/libtoolize 生成（会重新覆盖 libltdl/configure 为
        # umask 077），其 config.status 临时目录用 umask 077（OHOS 沙箱 0700 目录
        # 不可写，librrd 先例）——autogen 后递归替换所有 configure 与 config.status
        # 的 umask 077→022（覆盖 build 根与 build-release 的所有副本）。
        def _relax_umask(path):
            if not os.path.isfile(path):
                return
            with open(path, encoding="utf-8", errors="surrogateescape") as f:
                content = f.read()
            changed = False
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                changed = True
            # config.status 临时目录改走 $TMPDIR 绝对路径（kimwitu 0001 同型方案）：
            # ./confXXXXXX 相对路径在 OHOS 沙箱 SGID/受限目录创建会被拦
            # （CI #62070/#62756: ./confXXXXXX/subs1.awk: Permission denied），
            # 且 mktemp 分支与 ./conf$$-$RANDOM 兜底都要替换。configure 生成
            # config.status 的模板可能带引号也可能不带，故按宽松模式替换
            # ./confXXXXXX → $TMPDIR/confXXXXXX。
            if '"./confXXXXXX"' in content:
                content = content.replace(
                    '"./confXXXXXX"', '"$TMPDIR/confXXXXXX"')
                changed = True
            if "./confXXXXXX" in content:
                content = content.replace(
                    "./confXXXXXX", "$TMPDIR/confXXXXXX")
                changed = True
            if '"./conf$$-$RANDOM"' in content:
                content = content.replace(
                    '"./conf$$-$RANDOM"', '"$TMPDIR/conf$$-$RANDOM"')
                changed = True
            if "tmp=./conf$$-$RANDOM" in content:
                content = content.replace(
                    "tmp=./conf$$-$RANDOM", 'tmp="$TMPDIR/conf$$-$RANDOM"')
                changed = True
            if changed:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(content)

        roots = set()
        for d in (self.build_folder, self.source_folder):
            roots.add(d)
            roots.add(os.path.dirname(d))
        # 显式确保 build 根与 source 根都被遍历（Autotools 实际在 build 根运行
        # configure，其 libltdl/configure 来自 libtool 包副本含 umask 077）
        for root_dir in list(roots):
            for root, _dirs, files in os.walk(root_dir):
                for fn in ("configure", "config.status"):
                    if fn in files:
                        _relax_umask(os.path.join(root, fn))
        # libtoolize/autoconf 在 autogen 时会**重新生成** libltdl/configure 为
        # umask 077（覆盖复制时的替换），而递归 os.walk 可能未命中 build 根
        # libltdl/configure（DBG 实测仍 077=2）。顶层 configure 通过
        # AC_CONFIG_SUBDIRS 递归配置 libltdl 时用该副本生成 config.status（含
        # 077）并立即执行 → OHOS 沙箱 Permission denied。故在 configure() 前
        # **再显式**替换三处 libltdl/configure（source 根 / build 根 / build-release）。
        for _base in (self.source_folder, self.build_folder,
                      os.path.dirname(self.build_folder)):
            _lc = os.path.join(_base, "libltdl", "configure")
            _relax_umask(_lc)
        autotools = Autotools(self)
        autotools.configure()
        # make 阶段 libltdl 触发 config.status --recheck 会重跑 configure 重新
        # 生成 config.status——若 libltdl/configure 副本的模板仍含 umask 077，
        # 重新生成的 config.status 又是 077。故 configure() 后**显式**替换三处
        # libltdl/configure（source 根 / build 根 / build-release）的 umask 077→022，
        # 确保任何 --recheck 重生成的 config.status 均为 022。
        for _base in (self.source_folder, self.build_folder,
                      os.path.dirname(self.build_folder)):
            _lc = os.path.join(_base, "libltdl", "configure")
            _relax_umask(_lc)
            if os.path.isfile(_lc):
                os.utime(_lc, (946684800, 946684800))  # 2000-01-01（旧于 config.status）
        # make 阶段 libltdl 会重跑 config.status（含 umask 077 生成临时目录失败）——
        # configure 运行后全局替换 build/source 树中**所有**含 umask 077 的文件
        # （不限 configure/config.status），并 touch 使 config.status/Makefile 新于
        # configure.ac，避免 make 重新运行 configure 再生成 077。
        for root_dir in roots:
            for root, _dirs, files in os.walk(root_dir):
                for fn in files:
                    fpath = os.path.join(root, fn)
                    if os.path.isfile(fpath):
                        # 阻止 make 阶段重新运行 configure/config.status：三级
                        # 时间戳隔离（autoconf 生成的 automake 规则
                        # `Makefile: Makefile.in config.status` 在任一前置文件
                        # 新于 Makefile 时重跑 ./config.status → OHOS 沙箱
                        # Permission denied）——
                        #   源文件(configure.ac/Makefile.am/aclocal.m4/configure/
                        #     config.h.in) → 2000-01-01
                        #   Makefile.in                    → 2001-01-01
                        #   config.status                  → 2002-01-01
                        #   Makefile                       → 现在（恒最新）
                        # 保证 Makefile 严格新于所有前置，规则永不触发。
                        if fn in ("configure.ac", "Makefile.am", "aclocal.m4",
                                  "configure", "config.h.in"):
                            os.utime(fpath, (946684800, 946684800))  # 2000-01-01
                        elif fn == "Makefile.in":
                            os.utime(fpath, (978307200, 978307200))  # 2001-01-01
                        elif fn == "config.status":
                            os.utime(fpath, (1009843200, 1009843200))  # 2002-01-01
                        elif fn == "Makefile":
                            os.utime(fpath, None)  # 现在
                        try:
                            with open(fpath, encoding="utf-8", errors="surrogateescape") as f:
                                content = f.read()
                        except OSError:
                            continue
                        # 同时替换 umask 077→022 与临时目录相对路径→$TMPDIR 绝对路径
                        # （与 _relax_umask 同口径），确保 make 阶段重跑的
                        # config.status 副本也不会在 OHOS 沙箱受限目录建临时目录。
                        changed = False
                        if "umask 077" in content:
                            content = content.replace("umask 077", "umask 022")
                            changed = True
                        # 与 _relax_umask 同口径的宽松替换：configure 生成
                        # config.status 的 heredoc 模板中路径带转义引号
                        # （\"./confXXXXXX\"），旧模式 'mktemp -d "./confXXXXXX"'
                        # 匹配不到；按 ./confXXXXXX / ./conf$$-$RANDOM 子串替换，
                        # 带引号与否均可命中（CI #62756 根因）。
                        if '"./confXXXXXX"' in content:
                            content = content.replace(
                                '"./confXXXXXX"', '"$TMPDIR/confXXXXXX"')
                            changed = True
                        if "./confXXXXXX" in content:
                            content = content.replace(
                                "./confXXXXXX", "$TMPDIR/confXXXXXX")
                            changed = True
                        if '"./conf$$-$RANDOM"' in content:
                            content = content.replace(
                                '"./conf$$-$RANDOM"', '"$TMPDIR/conf$$-$RANDOM"')
                            changed = True
                        if "tmp=./conf$$-$RANDOM" in content:
                            content = content.replace(
                                "tmp=./conf$$-$RANDOM",
                                'tmp="$TMPDIR/conf$$-$RANDOM"')
                            changed = True
                        if not changed:
                            continue
                        with open(fpath, "w", encoding="utf-8", errors="surrogateescape") as f:
                            f.write(content)
                        # umask 替换会更新 mtime——写回后**按类型重设**时间戳，
                        # 保持三级隔离（末尾不再统一设 now，避免 config.status
                        # 被拉回"现在"产生与 Makefile 的微秒级竞态）。
                        if fn in ("configure.ac", "Makefile.am", "aclocal.m4",
                                  "configure", "config.h.in"):
                            os.utime(fpath, (946684800, 946684800))  # 2000-01-01
                        elif fn == "Makefile.in":
                            os.utime(fpath, (978307200, 978307200))  # 2001-01-01
                        elif fn == "config.status":
                            os.utime(fpath, (1009843200, 1009843200))  # 2002-01-01
                        elif fn == "Makefile":
                            os.utime(fpath, None)  # 现在
        # 阻止 make 重跑 config.status/autogen：命令行 `-o config.status` 只对
        # 顶层 make 生效，不会传递给递归子 make（libltdl 是 AC_CONFIG_SUBDIRS
        # 递归子目录，make[2] 进入 build-release/libltdl 时仍会按
        # `Makefile: Makefile.in config.status` 规则重跑 ./config.status →
        # OHOS 沙箱 Permission denied）。MAKEFLAGS 环境变量经 env="conanbuild"
        # 运行时可能被 conanbuild 环境覆盖丢失（CI #59650 实测仍重跑）。
        # 改用 make **命令行参数** `-o config.status -o Makefile.in`——GNU make
        # 会把 -o 选项经 MAKEFLAGS 自动下传给递归子 make，强制所有层级的
        # make 都不重建 config.status / Makefile.in（即不重跑 autogen 与
        # config.status），直接使用 configure() 已生成的（umask 已替换 022）版本。
        # 但 automake 的 maintainer 规则（Makefile.in/Makefile: configure.ac
        # aclocal.m4 触发 aclocal/automake/autoconf，CI #63653 实测 make[2]
        # 仍重跑 autogen 并重新生成 configure/config.status，覆盖 TMPDIR
        # 替换）不受 -o 约束——把 autotools 工具变量覆盖为 no-op，使这些
        # 规则"成功"但不真正重写文件，保留已替换的 $TMPDIR 版本。
        self.run(
            "make -j1 -o config.status -o Makefile.in "
            "AUTOCONF=true AUTOMAKE=true ACLOCAL=true AUTOHEADER=true "
            "LIBTOOLIZE=true libtoolize=true aclocal-real=true",
            env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        # make install 递归进入 libltdl（AC_CONFIG_SUBDIRS）时同样会按
        # `Makefile: Makefile.in config.status` / maintainer 规则重跑
        # ./config.status → OHOS 沙箱相对路径临时目录 Permission denied
        # （CI #67286：install-recursive 阶段 confbAfDme/subs1.awk）。
        # 与 build() 的 make 一致：`-o` 阻止 config.status/Makefile.in
        # 重建，autotools 工具变量 no-op 阻止 autogen 重写已替换文件；
        # install() 见 args 无 DESTDIR= 时自动插入 DESTDIR=package_folder。
        autotools.install(args=[
            "-j1", "-o", "config.status", "-o", "Makefile.in",
            "AUTOCONF=true", "AUTOMAKE=true", "ACLOCAL=true",
            "AUTOHEADER=true", "LIBTOOLIZE=true", "libtoolize=true",
            "aclocal-real=true",
        ])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["neurosim"]
        self.cpp_info.set_property("pkg_config_name", "libneurosim")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]
