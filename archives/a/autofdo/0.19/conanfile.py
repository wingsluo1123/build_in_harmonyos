#!/usr/bin/env python3
"""Conan recipe — autofdo 0.19 (AutoFDO profile tools, HarmonyOS PC 适配)。

上游：https://github.com/google/autofdo  tag 0.19 (commit 492384d0)
产物（CLI 工具）：create_gcov / dump_gcov / sample_merger / profile_merger /
profile_diff / profile_update / create_llvm_prof

构建要点（OHOS/aarch64 原生 build=host，非交叉编译）：
- 上游为 autotools，tag tarball **已自带** configure / Makefile.in / aclocal.m4，
  故本配方直接 ./configure && make，**不需要 automake/libtool**（本机
  /data/service/hnp 无 automake，conan 的 automake 依赖 perl 5.42.2 在此设备
  上 XS 模块加载失败）。因此**不修改 Makefile.am**（改 .am 会触发 make 的
  maintainer 规则重新生成 Makefile.in，需要 automake）。
- 子模块缺失：GitHub release tarball 不含 third_party/{protobuf,perf_data_converter}
  （空目录 + .gitmodules，见知识库 E150）。处理：
    · third_party/perf_data_converter @ d9ef70b —— 单独下载源码解压到树内（conandata）。
    · third_party/protobuf —— 用 Conan 制品 protobuf/3.17.3（含 protoc + libprotobuf
      + 头文件），在 build() 用 make 变量覆盖（PROTOC/PROTOBUF_DEP）绕过树内
      bundled protobuf 子构建。
- 依赖（均由 conan 制品提供，经 AutotoolsDeps 注入 CPPFLAGS/LDFLAGS/LIBS）：
    · protobuf/3.17.3 —— protoc（.proto -> .pb.cc）+ libprotobuf；zlib 由其传递。
    · openssl —— third_party/perf_data_converter/src/quipper/binary_data_utils.cc
      用 <openssl/md5.h> 的 MD5()（configure.ac 有 AC_CHECK_LIB([crypto],[MD5])）。
    · libelf/0.8.13.1（OHOS 移植版）—— quipper/dso.cc 用 <libelf.h>/<gelf.h> 的
      elf_* / gelf_* API（elf_version/elf_begin/gelf_getshdr/elf_getdata/
      gelf_getnote/elf_end…），故 Makefile 的 -lelf 必须保留（不再用 make 变量
      覆盖置空）。0.8.13 的头通过 elf_repl.h 自带 Elf32_/Elf64_ 定义，会与
      SDK <elf.h> 冲突（typedef redefinition）；0.8.13.1 改用系统 <elf.h> 并
      补齐 GElf_Nhdr/GElf_Versym/gelf_getnote。
  configure.ac 的 AC_CHECK_LIB([z],[gzopen]) 由 protobuf 传递的 zlib(-lz) 满足。
- LLVM：create_llvm_prof 用 llvm/ProfileData/SampleProf*.h（LLVM 15 头兼容，已实测
  llvm_profile_writer.cc 对 LLVM 15.0.4 -fsyntax-only 通过）；ohpcd 的 llvm/15.0.4
  二进制包服务器端损坏，不能作 requires，改为 configure --with-llvm=<平台 SDK
  llvm-config>（build=host 时即本机原生 LLVM 15.0.4）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps

BINS = [
    "create_gcov",
    "dump_gcov",
    "sample_merger",
    "profile_merger",
    "profile_diff",
    "profile_update",
    "create_llvm_prof",
]


class AutofdoConan(ConanFile):
    name = "autofdo"
    version = "0.19"
    package_type = "application"
    description = ("AutoFDO toolchain — converts perf.data (LBR) profiles into "
                   "AutoFDO profiles for GCC (create_gcov) and LLVM (create_llvm_prof)")
    license = "Apache-2.0"
    url = "https://github.com/google/autofdo"
    homepage = "https://github.com/google/autofdo"
    topics = ("profiling", "autofdo", "perf", "gcc", "llvm")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"autofdo/0.19 仅支持 Linux/OHOS，当前 {self.settings.os}")

    def layout(self):
        # 上游 autotools 为 in-source 构建（Makefile 引用源码相对路径、就地生成
        # config.h / glog/src/glog/logging.h），故 source/build/generators 同目录。
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # protobuf：perf_data.proto -> .pb.cc 需要 protoc；libquipper.a 需要 libprotobuf。
        self.requires("protobuf/3.17.3", transitive_headers=True, transitive_libs=True)
        # openssl：perf_data_converter/src/quipper/binary_data_utils.cc 用
        # <openssl/md5.h> 的 MD5()（本机/SDK 无 openssl 头，须由 conan 制品提供；
        # 亦满足 configure.ac 的 AC_CHECK_LIB([crypto],[MD5])）。
        self.requires("openssl/3.5.6")
        # libelf：quipper/dso.cc 真实调用 libelf API（<libelf.h>/<gelf.h> 的
        # elf_*/gelf_*），Makefile 的 -lelf 保留，libelf 头/库由本制品注入。
        # 必须用 OHOS 移植版 0.8.13.1：它让 sys_elf.h 使用系统 <elf.h>
        # （避免 elf_repl.h 与 SDK <elf.h> 的 Elf32_/Elf64_ typedef 重定义），
        # 并补上 gelf.h 缺失的 GElf_Nhdr/GElf_Versym 与 gelf_getnote。
        self.requires("libelf/0.8.13.1")
        # 注意 llvm：ohpcd 的 llvm/15.0.4 二进制包在服务器端损坏
        # （"doesn't contain a conan_package.t file"，见 notes.md），
        # 无法作为 requires 下载；create_llvm_prof 改用平台 SDK 自带的
        # llvm-config（LLVM 15.0.4，build=host 时即本机原生 LLVM），
        # 见 generate()/_find_llvm_config()。

    def build_requirements(self):
        # 上游 tag tarball **不含**生成的 configure/Makefile.in/aclocal.m4
        # （只有 configure.ac/Makefile.am），必须自举生成；本机
        # /data/service/hnp/bin 无 automake，故用 Conan 制品 automake + autoconf。
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")

    def source(self):
        # 主源码（tag tarball，自带 configure/Makefile.in）。
        # keep_permissions=True：get() 默认会丢弃可执行位，configure 会变成
        # 不可执行（"configure: inaccessible or not found"）。
        get(self, **self.conan_data["sources"]["autofdo"],
            strip_root=True, keep_permissions=True)
        # 子模块 perf_data_converter：只取 src/quipper（跳过 ~100MB testdata），
        # 放到 third_party/perf_data_converter/src/quipper。
        # 注意 pattern 是对**解压前**的成员路径（含顶层目录
        # perf_data_converter-<sha>/）做 fnmatch，故须用 "*/src/quipper/*"。
        get(self, destination=os.path.join("third_party", "perf_data_converter"),
            strip_root=True, pattern="*/src/quipper/*", keep_permissions=True,
            **self.conan_data["sources"]["perf_data_converter"])

    def _find_llvm_config(self):
        llvm_config = shutil.which("llvm-config")
        if llvm_config:
            return llvm_config
        return None

    def generate(self):
        # E114/E011：鸿蒙安全框架会拦截 configure 的 config.status 在**新建**临时
        # 目录里写 subs1.awk（"Permission denied"）。预建一个可写目录并在
        # conanbuild 环境里把 TMPDIR 指向它（须在 VirtualBuildEnv.generate() 之前），
        # 再在 _fix_ac_tmp() 里把 configure 内嵌的 ac_tmp 也指到该目录。
        import tempfile
        self._ac_tmp_dir = os.path.join(tempfile.gettempdir(), "autofdo-ac-tmp")
        os.makedirs(self._ac_tmp_dir, exist_ok=True)
        self.buildenv_info.define("TMPDIR", self._ac_tmp_dir)

        tc = AutotoolsToolchain(self)
        llvm_config = self._find_llvm_config()
        if llvm_config:
            tc.configure_args.append(f"--with-llvm={llvm_config}")
            self.output.info(f"  llvm-config = {llvm_config}")
        else:
            self.output.warning("  未找到 llvm-config —— create_llvm_prof 可能无法配置")
        # 依赖头/库由 AutotoolsDeps 注入 conanautotoolsdeps.sh（CPPFLAGS/LDFLAGS/LIBS），
        # configure 阶段读取后写入 Makefile。
        tc.generate()
        AutotoolsDeps(self).generate()
        # VirtualBuildEnv：把 tool_requires(autoconf/automake) 的 bin 与
        # ACLOCAL/AUTOMAKE/PERL/PERL5LIB/ACLOCAL_PATH 注入 conanbuild 环境，
        # 供 build() 的自举步骤使用。
        VirtualBuildEnv(self).generate()

    # ── 自举：生成 configure / Makefile.in ──
    # 上游 tarball 无生成物。混合 perl 版本会互相打架，故统一来源：
    #  · aclocal/automake 用 Conan 制品（本机无 automake）。它们的 perl 脚本
    #    shebang 指向**系统 perl**（/data/service/hnp/bin/perl 5.42.0），
    #    而 conanbuild 环境把 PERL5LIB 指向 conan perl(5.42.2) 的 XS 模块目录，
    #    系统 perl 加载 conan perl 的 Cwd.so 会失败（Perl_my_cxt_init not found）。
    #    → 运行自举时把 PERL5LIB 收窄为 automake 自身的**纯 perl** 模块目录
    #      （share/automake-1.18），核心模块由系统 perl 自带。
    #  · autoconf/autoheader/autom4te 用**系统**（/data/service/hnp/bin 在 PATH 首）
    #    自洽版本；故 unset conanbuild 里指向 conan autoconf 的 AUTOM4TE/AUTOCONF/
    #    AUTOHEADER 等变量——否则 aclocal 会调 conan autom4te（走 conan perl，
    #    而此时 PERL5LIB 已收窄，conan perl 找不到核心模块 strict.pm）。
    _AUTOGEN_ENV = (
        'export PERL5LIB="$(dirname "$(dirname "$AUTOMAKE")")/share/automake-1.18"; '
        'export ACLOCAL_PATH="$PWD/m4:'
        '$(dirname "$(dirname "$AUTOMAKE")")/share/aclocal:'
        '$(dirname "$(dirname "$AUTOMAKE")")/share/aclocal-1.18:${ACLOCAL_PATH:-}"; '
        'unset AUTOM4TE AUTOCONF AUTOHEADER AUTORECONF AUTOSCAN AUTOUPDATE IFNAMES '
        'autom4te_perllibdir AC_MACRODIR trailer_m4 autom4te_buildauxdir; '
    )

    def _autogen(self):
        src = self.source_folder
        self.output.info("  自举：aclocal -> autoconf -> autoheader -> automake")
        self.run(self._AUTOGEN_ENV + '"$ACLOCAL" --force -I m4',
                 cwd=src, env="conanbuild")
        self.run(self._AUTOGEN_ENV + 'autoconf -o configure configure.ac',
                 cwd=src, env="conanbuild")
        self.run(self._AUTOGEN_ENV + 'autoheader',
                 cwd=src, env="conanbuild")
        # automake --add-missing 会补 install-sh/missing/depcomp/compile/
        # config.guess/config.sub（上游 tarball 未提供）。
        self.run(self._AUTOGEN_ENV + '"$AUTOMAKE" --add-missing --copy --no-force',
                 cwd=src, env="conanbuild")

    def _fix_ac_tmp(self):
        """E114/E011：把生成的 configure 内嵌 config.status 的 ac_tmp 改指到
        预建可写目录，并去掉退出时删除它的 trap（否则下一轮该目录已不存在）。
        现象：`./config.status: line NNN: ./confXXXXXX/subs1.awk: Permission denied`
        → `config.status: error: could not setup config files machinery`。"""
        from conan.tools.files import replace_in_file
        fixed_tmp = getattr(self, "_ac_tmp_dir", None) or os.path.join(
            self.build_folder, "ac-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        cfg = os.path.join(self.build_folder, "configure")
        if not os.path.exists(cfg):
            cfg = os.path.join(self.source_folder, "configure")
        content = open(cfg, "r", encoding="utf-8", errors="ignore").read()
        if "ac_tmp=$tmp" in content:
            replace_in_file(self, cfg, "ac_tmp=$tmp", f"ac_tmp={fixed_tmp}")
            self.output.info(f"  [E114] configure ac_tmp -> {fixed_tmp}")
        else:
            self.output.warning("  [E114] configure 中未找到 ac_tmp=$tmp 模式，跳过")
        old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
        if old_trap in open(cfg, "r", encoding="utf-8", errors="ignore").read():
            replace_in_file(self, cfg, old_trap, 'exit $exit_status')
            self.output.info("  [E114] configure：移除删除 ac_tmp 的 trap")
        os.chmod(cfg, 0o755)

    def build(self):
        pb = self.dependencies["protobuf"]
        protoc = os.path.join(pb.cpp_info.bindirs[0], "protoc")
        self.output.info(f"  protoc = {protoc}")

        apply_conandata_patches(self)
        self._autogen()
        self._fix_ac_tmp()

        autotools = Autotools(self)
        autotools.configure()

        # 保险（与 make -o 双保险）：在空目录 third_party/protobuf 放一个时间戳极旧
        # 的 configure 占位文件，使那两条 bundled-protobuf 规则的目标/前置都"最新"，
        # 彻底避免触发树内 autoreconf。
        pb_stub_dir = os.path.join(self.build_folder, "third_party", "protobuf")
        os.makedirs(pb_stub_dir, exist_ok=True)
        stub = os.path.join(pb_stub_dir, "configure")
        if not os.path.exists(stub):
            with open(stub, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(stub, 0o755)
            os.utime(stub, (0, 0))

        # make 变量覆盖绕过树内 bundled protobuf 子构建（无 automake 无法 autoreconf）：
        #   PROTOC        -> Conan protobuf 的 protoc（真实文件，make 视为已满足前置）
        #   PROTOBUF_DEP  -> 置空（libprotobuf 由 LIBS 提供）
        #   （LIBELF 不再置空：quipper/dso.cc 真实调用 libelf API，需 -lelf，
        #    由 libelf 依赖经 AutotoolsDeps 注入 LIBS 与 LDFLAGS。）
        # -o third_party/protobuf/configure：Makefile 里 PROTOC 同时是
        #   `$(PROTOC) $(PROTOBUF)/src/.libs/libprotobuf.a: $(PROTOBUF)/configure`
        #   这条规则的目标，其前置 $(PROTOBUF)/configure 不存在 → make 会去构建它
        #   （触发树内 protobuf autoreconf）。用 -o 让 make 视该文件为最新、不重建。
        # README 明确要求串行构建（子项目 configure 并行会失败）。
        self.run(
            "make -j1 "
            "-o third_party/protobuf/configure "
            f"PROTOC={protoc} "
            'PROTOBUF_DEP= ',
            env="conanbuild",
        )

    def package(self):
        for b in BINS:
            copy(self, b, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.build_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
