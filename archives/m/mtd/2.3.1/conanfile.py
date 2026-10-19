#!/usr/bin/env python3
"""Conan recipe — mtd-utils 2.3.1 (HarmonyOS PC arm64)

mtd-utils: Memory Technology Device (MTD) userspace utilities
(flash_erase/nanddump/mtdinfo/ubiformat/mkfs.ubifs 等命令行工具集)

关键适配点:
- 官方源: sigma-star/mtd-utils GitHub 镜像 codeload tarball (对应上游
  git.infradead.org tag v2.3.1; Savannah 发布目录已失效 404, R39 官方源)
- 手动 bootstrap (autotools 工具链): git 源码无 configure, 且 CI worker 无
  系统 automake/aclocal ("Can't exec aclocal") → build_requirements 声明
  tool_requires autoconf/2.72+automake/1.18+libtool/2.5.4+pkgconf/3.0.5;
  但 conan 的 perl/5.42.2 (autotools 传递依赖) 是 aarch64-ohos 交叉编译版,
  Cwd.so 无法在构建机 dlopen, 故 build() 内强制系统 perl
  (/data/service/hnp/bin/perl) 手动逐步执行 aclocal → autoheader →
  automake → autoconf (每次调用前 PERL5LIB 指向对应工具模块目录;
  与 burp2/2.1.0 同款方案)
- E566 (OHOS config.guess/config.sub): automake 1.18 的 config.guess 不认识
  HarmonyOS (本机 uname -s=HarmonyOS), configure 报 "cannot guess build type"
  → build() 内 _patch_config_guess_sub() 给生成的 config.guess/config.sub 打
  OHOS triplet 识别补丁 (与 burp2/2.1.0 同款方案)
- E011 (HMDFS umask 077): autotools 工具链生成 configure 后, build() 内
  Python 替换 configure 中内嵌的 umask 077→022 (configure 内嵌 umask 077
  创建临时目录, HMDFS 上 UID 映射导致 config.status 报
  "Permission denied (subs1.awk)"; configure 为构建产物, refresh-patch
  无法追踪, 不入 patches/; 与 akku/1.1.0 同方案)
- uuid 头文件布局: 上游 #include <uuid.h>, 标准 libuuid 提供 include/uuid/uuid.h
  → patches/0001-ubifs-utils-mkfs.ubifs-mkfs.ubifs.c.patch
- 依赖: zlib/lzo/zstd/libuuid/openssl 全部由 Conan 制品仓管理 (W0 已验证发布);
  mtd-utils 2.3.1 不依赖 lz4 (configure.ac 无 lz4 检查)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
import os as _os


class MtdConan(ConanFile):
    name = "mtd"
    version = "2.3.1"
    description = "mtd-utils: Memory Technology Device (MTD) userspace utilities"
    license = "GPL-2.0-only"
    homepage = "https://www.linux-mtd.infradead.org/"
    url = "https://git.infradead.org/mtd-utils.git"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # R44 修复(CI 第1轮失败): CI worker 无系统 automake/aclocal,
        # autogen.sh(autoreconf --force --install) 在 aclocal 处失败
        # ("Can't exec aclocal: No such file or directory")。本地 W3 通过
        # 是因为本机有系统 automake 1.16.5; CI 必须由 Conan tool_requires
        # 补齐 bootstrap 工具链 (与 burp2/2.1.0 同款方案, 制品仓均已发布)。
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("pkgconf/3.0.5")

    def requirements(self):
        # R36: 依赖已发布到 ohpcd 制品仓 (W0 preflight 验证)
        self.requires("zlib/1.3.1")
        self.requires("lzo/2.10")
        self.requires("zstd/1.5.6")
        self.requires("libuuid/2.42.2")
        self.requires("openssl/3.0.21")

    def layout(self):
        basic_layout(self)

    def _patch_config_guess_sub(self, aux_dir):
        """Make the generated config.guess/config.sub recognize OHOS/HarmonyOS.

        automake 1.18 (from tool_requires) ships config.guess/config.sub that
        do not know the `aarch64:...:HarmonyOS` triplet (CI/本地 worker 本机即
        HarmonyOS, uname -s=HarmonyOS), so configure's `checking build system
        type` fails with "cannot guess build type". Insert an early OHOS
        identification branch in config.guess and allow the aarch64-ohos OS
        in config.sub. (与 burp2/2.1.0 同款方案)
        """
        import re as _re
        cg = _os.path.join(aux_dir, "config.guess")
        if _os.path.isfile(cg):
            with open(cg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "OHOS-PC adaptation" not in content:
                marker = "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in"
                patch_txt = (
                    "# ---- OHOS-PC adaptation: identify HarmonyOS/OHOS early ----\n"
                    "case \"$UNAME_SYSTEM\" in\n"
                    "  HarmonyOS|OHOS|OpenHarmony)\n"
                    "    case \"$UNAME_MACHINE\" in\n"
                    "      aarch64|arm64) echo \"aarch64-unknown-linux-ohos\"; exit 0 ;;\n"
                    "      armv7*) echo \"arm-unknown-linux-ohos-eabi\"; exit 0 ;;\n"
                    "      *) echo \"$UNAME_MACHINE-unknown-linux-ohos\"; exit 0 ;;\n"
                    "    esac ;;\n"
                    "esac\n"
                    "# ---- end OHOS-PC adaptation ----\n"
                )
                if marker in content:
                    content = content.replace(marker, patch_txt + marker, 1)
                    with open(cg, "w", encoding="utf-8") as f:
                        f.write(content)
        cs = _os.path.join(aux_dir, "config.sub")
        if _os.path.isfile(cs):
            with open(cs, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "-linux-ohos" not in content:
                marker = "\t | -linux* | -uma* | -amigaos* | -amigados* \\"
                if marker in content:
                    content = content.replace(
                        marker, "\t | -linux* | -linux-ohos* | -uma* | -amigaos* | -amigados* \\", 1)
                    with open(cs, "w", encoding="utf-8") as f:
                        f.write(content)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps: configure.ac 用 PKG_CHECK_MODULES(ZLIB/UUID/...) 探测
        # 依赖, 必须把依赖的 .pc 生成并注入 PKG_CONFIG_PATH
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # R49: 依赖注入由 Conan Toolchain 管理(私有 build_folder prefix);
        # --prefix=/ + DESTDIR(Conan Autotools.install) 打包到 package_folder
        tc.configure_args.append("--prefix=/")
        # 可选依赖默认 check: 找不到时自动降级, 不强制
        tc.generate()

    def build(self):
        # R44 修复(CI 第1轮失败, 本地 W3 复验同步暴露):
        # 1) CI worker 无系统 automake/aclocal → build_requirements 补齐工具链;
        # 2) conan 的 perl/5.42.2 (automake/autoconf 传递依赖) 是 aarch64-ohos
        #    交叉编译版, Cwd.so 无法在构建机 dlopen (与 burp2/2.1.0 完全一致),
        #    故不能直接 sh ./autogen.sh (autoreconf 会走 conan perl 必挂):
        #    → 强制系统 perl (/data/service/hnp/bin/perl) + 手动逐步执行
        #      aclocal → autoheader → automake → autoconf, 每次调用前
        #      PERL5LIB 指向对应工具模块目录 (share/automake-1.18 / share/autoconf)。
        src = self.source_folder.replace("\\", "/")
        shell = _os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            f"{shell} -c \"set -e"
            f" && export PERL=/data/service/hnp/bin/perl"
            f" && cd '{src}'"
            f" && unset PERL5LIB"
            f" && ACLOCAL=$(command -v aclocal 2>/dev/null || exit 1)"
            f" && unset PERL5LIB"
            f" && export PERL5LIB=$(dirname $(dirname $ACLOCAL))/share/automake-1.18"
            f" && sh $ACLOCAL -I m4"
            f" && AUTOHEADER=$(command -v autoheader 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOHEADER))/share/autoconf"
            f" && sh $AUTOHEADER"
            f" && AUTOMAKE=$(command -v automake 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOMAKE))/share/automake-1.18"
            f" && sh $AUTOMAKE -a --copy"
            f" && AUTOCONF=$(command -v autoconf 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOCONF))/share/autoconf"
            f" && sh $AUTOCONF\"",
            env="conanbuild",
        )
        # E011 (HMDFS umask 077): autoconf 生成的 configure 内嵌
        #   `(umask 077 && mktemp -d "./confXXXXXX")` 创建 0700 临时目录, HMDFS
        #   上 UID 映射导致 config.status 报 "Permission denied"（无法写 subs1.awk）。
        #   与 akku/1.1.0、guile 的 0001-configure-umask.patch 同方案; 因 configure
        #   是 autoreconf 构建产物（refresh-patch 无法追踪），故在 build() 内
        #   Python 替换（同时覆盖 source/build 两处, 生成的 config.status 继承修复）。
        for _folder in (self.source_folder, self.build_folder):
            _cfg = _os.path.join(_folder, "configure")
            if _os.path.isfile(_cfg):
                with open(_cfg, "r", encoding="utf-8") as _f:
                    _content = _f.read()
                if "umask 077" in _content:
                    with open(_cfg, "w", encoding="utf-8") as _f:
                        _f.write(_content.replace("umask 077", "umask 022"))
                    self.output.info("E011: configure umask 077 -> 022 patched in build()")
        # 源码补丁 (mkfs.ubifs.c uuid 头路径)
        apply_conandata_patches(self)
        # OHOS triplet: automake 1.18 的 config.guess/config.sub 不认识
        # HarmonyOS (本机 uname -s=HarmonyOS), configure 报 "cannot guess
        # build type" → 打 OHOS 识别补丁 (与 burp2/2.1.0 同款方案)
        self._patch_config_guess_sub(src)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 纯命令行工具集, 无库文件; 工具安装到 sbin (R38 commands.json 声明)
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.cpp_info.libdirs = []
