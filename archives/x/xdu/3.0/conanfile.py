#!/usr/bin/env python3
"""Conan recipe — xdu 3.0 (X11 磁盘占用可视化工具)

Build system: Imakefile (X11R6 contrib，无 configure/makefile 常规流程)
License: X Consortium / MIT-style (Phillip C. Dykstra 1991-1994)
Homepage: https://github.com/vlasovskikh/xdu (ftp.arl.mil xdu-3.0.tar.Z 归档镜像)

构建方式: Imakefile 的 XawClientLibs = -lXaw -lXt -lXext -lX11，与 README
手工直编命令一致（`cc -o xdu xdu.c xwin.c -lXaw -lXt -lXext -lX11`）。
OHOS 无 imake/xorg-cf-files（制品仓无此包），采用 README 官方手工直编路径：
在 build() 内用 Conan Toolchain 编译器（R33）直编 2 个 K&R C 源文件。

依赖: X11 库全部来自制品仓 conan 依赖（R36 已发布）：
  libxaw/1.0.14（Athena 控件集：Label/Form/AsciiText/AsciiSrc，xdu 核心依赖）
    → libxt/1.3.1 + libxmu/1.3.1.1 + libxpm/3.5.17 + libxext/6.4.0.1 + libx11/1.8.13
libX11.so.6 运行期 DT_NEEDED 需要 libxcb.so.1/libXau.so.6（libxcb 传递依赖
libXdmcp.so.6），显式声明 run=True（xeyes 同款先例），test_package 的
conanrun 环境注入其 libdir 到 LD_LIBRARY_PATH，并配 LD_PRELOAD 兜底
（HMBS [stale_runtime_library]）。

上游测试: xdu 3.0 无任何自动化测试（Imakefile 无 check 目标、无 tests/
目录、xdu.man 无测试章节）。test_package 以真实执行被测二进制验证：
无 DISPLAY 环境下 xdu -help 走 XtAppInitialize 报 "Can't open display"
干净退出（exit=1），证明 libXaw/libXt/libX11 动态链接链完整可加载
（xeyes 同款策略；缺库时 loader 会报 "Error loading shared library"）。

源码: Debian 官方 pool 的 xdu_3.0.orig.tar.gz（上游原版未打补丁，
R39 权威镜像源），sha256 与下载内容一致。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class XduConan(ConanFile):
    name = "xdu"
    version = "3.0"
    description = "Display the output of du in an X window (graphical disk usage tree)"
    license = "MIT"
    homepage = "https://github.com/vlasovskikh/xdu"
    url = "https://github.com/vlasovskikh/xdu"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS 平台兼容——os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xdu supports Linux/OHOS only (current os: {self.settings.os})"
            )

    def requirements(self):
        # X11 链接库全部来自制品仓 conan 依赖（R36 已发布 OHOS armv8 binary）。
        # libxaw 传递链自动带入 libxt/libxmu/libxpm/libxext/libx11/xorgproto。
        self.requires("libxaw/1.0.14", transitive_headers=True, transitive_libs=True)
        # libX11.so.6 运行期 DT_NEEDED 需要 libxcb.so.1/libXau.so.6（libxcb
        # 传递依赖 libXdmcp.so.6，见 libx11/1.8.13 配方 requirements），
        # 显式声明 run=True 保证 test_package 的 conanrun 环境注入其 libdir
        # （xeyes 第 4 轮真机根因同款：loader 可能忽略 LD_LIBRARY_PATH，
        # test_package 再以 LD_PRELOAD 绝对路径兜底）。
        self.requires("libxcb/1.17.0", run=True)
        self.requires("libxau/1.0.11", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # 收集全部依赖包的 include/lib 路径（不依赖编译环境预编译栈；
        # xclip 同款：从 self.dependencies 的 cpp_info 显式收集）
        dep_incs = " ".join(
            f"-I{os.path.join(dep.package_folder, inc)}"
            for dep in self.dependencies.values()
            for inc in dep.cpp_info.includedirs
        )
        dep_libs = " ".join(
            f"-L{os.path.join(dep.package_folder, libdir)}"
            for dep in self.dependencies.values()
            for libdir in dep.cpp_info.libdirs
        )
        # K&R C (1994) 代码：隐式 int 返回 / 无原型 / 无 return 值等
        # 均为历史风格，clang 报 warning 级，显式禁用避免 -Wreturn-type
        # 在部分工具链配置下被提升为 error（本地实测 xdrawrect 无 return）。
        warnings = (
            "-Wno-return-type -Wno-implicit-int "
            "-Wno-implicit-function-declaration -Wno-deprecated-non-prototype "
            "-Wno-incompatible-library-redeclaration"
        )
        # 手工直编（README 官方命令）：链接 -lXaw7 -lXt -lXext -lX11。
        # 用 -lXaw7 显式指向 Athena 第 7 版库（libxaw 包同时提供
        # libXaw6/libXaw7，未版本化 libXaw.so 是符号链接，HMFS 物化不可靠）。
        # R33: 编译器从 Conan conf 获取（dict 形式，conan 2.29.1 兼容），
        # 禁止裸用 shell 环境变量 $CC（conanbuild 环境实测不导出 CC，
        # 干净 CI worker 上 $CC 为空会导致编译命令失效；abc 同款先例）。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(
            f'cd "{src}" && {cc} {warnings} -o xdu xdu.c xwin.c '
            f"{dep_incs} {dep_libs} -lXaw7 -lXt -lXext -lX11",
            env="conanbuild",
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "xdu"),
            os.path.join(bin_dir, "xdu"),
        )
        # app-defaults 资源文件（XDu.ad）：窗口默认字体/尺寸/排序。
        # 代码内 fallback_resources 已覆盖宽高/排序，缺字体文件也能运行
        # （Xt 退回服务器默认字体），仍随包安装保持上游行为完整。
        share_dir = os.path.join(self.package_folder, "share", "X11", "app-defaults")
        os.makedirs(share_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "XDu.ad"),
            os.path.join(share_dir, "XDu"),
        )
        self._sign_elf(os.path.join(bin_dir, "xdu"))

    def _sign_elf(self, path):
        """ELF 代码签名（OHOS 内核拒绝未签名 ELF，xeyes/clinfo 同款）。"""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # chmod may be unsupported on the device FS (HMBS_CAP_CHMOD=0)

    def package_info(self):
        # 命令行工具：仅提供 bin/（R38）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
