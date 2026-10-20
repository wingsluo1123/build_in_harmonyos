#!/usr/bin/env python3
"""Conan 2 recipe — rarcrack 0.2-20240214-413ea3a (Makefile).

rarcrack 是单文件 C 命令行工具：对遗忘口令的 rar/7z/zip 加密压缩包做
暴力破解（多线程逐个试探口令，调用外部 unrar/7z/unzip 验证）。上游构建
形态为纯 Makefile（`all` 直出单二进制 `rarcrack`，无 configure、无
check/test 目标），构建期唯一三方依赖是 libxml2（状态文件 XML 读写）。

OHOS 适配要点：
- 编译器从 `tools.build:compiler_executables` 取（R33：CI 上 $CC 为空），
  以 make 命令行变量 CC 覆盖上游写死的 `CC=gcc`（补丁同步改为 `CC?=`）。
- 上游 Makefile 用宿主机 `` `xml2-config --libs --cflags` `` 反引号内联
  libxml2 旗标（交叉/原生隔离下会混入宿主路径），补丁改为
  `$(XML2_CFLAGS)` / `$(XML2_LIBS)` 变量，由配方从 Conan 的 libxml2
  依赖包目录显式传值（juise/3.0.0 同型做法）。
- 不调用上游 `install`（其 `install -s` 依赖 strip 且写绝对 PREFIX），
  package() 直接 copy 二进制与文档（regldg/1.0.1 同型处理）。
- 上游无任何自动化测试（Makefile 仅 all/debug/clean/install/uninstall
  目标，见 test_package/MANIFEST.yml 审计），build() 内不做启动式
  smoke（缺 unzip 时真机启动破解会空转）；功能断言全部由
  test_package 承载。
"""

import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class RarcrackConan(ConanFile):
    name = "rarcrack"
    version = "0.2-20240214-413ea3a"
    description = "Brute-force password cracker for RAR, 7Z and ZIP archives"
    license = "GPL-2.0-only"
    homepage = "https://github.com/jaredsburrows/rarcrack"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("security", "password-recovery", "rar", "zip", "7z", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # rarcrack 是单文件 CLI 工具（无库产物），无 shared/static 选项（R26 不适用：
    # 非系统同名库，无 .so 污染风险）。

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 真机预检远端顺序 conancenter 在前：裸 libxml2/2.15.3 双远端共存时
        # 命中 CCI 配方，其 tool_requires("cmake") 拉起 conandata 无 OHOS
        # 条目的 cmake/4.4.x，从源码构建即报 KeyError: 'OHOS'
        #（zurl/1.12.0 notes #26-#27、baka/2.0.4、atracdenc/0.2.3 同型实证）。
        # 2.15.3.1 为本仓 R37 适配后缀版本（同上游 v2.15.3 tarball、同构建
        # 方式、零 tool_requires），仓内独有，强制落 ohpcd 切断该边。
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        buildenv = VirtualBuildEnv(self)
        buildenv.generate()

    def _resolve_cc(self):
        # 真机 clang 已从 /data/service/hnp/bin 迁移到 ~/usr/local/bin，
        # 而共享 profile 仍可能指向旧绝对路径。配置路径存在才用，否则按
        # PATH 与用户目录回退（regldg/1.0.1 已验证模式），避免 make 报
        # "No such file or directory"。
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables",
                default={}, check_type=dict) or {}
        except Exception:
            executables = {}
        configured = executables.get("c")
        if configured and os.path.isfile(configured):
            return configured
        for tool in ("clang", "cc", "gcc"):
            found = shutil.which(tool)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for tool in ("clang", "cc", "gcc"):
            cand = os.path.join(home_bin, tool)
            if os.path.isfile(cand):
                return cand
        return configured or "clang"

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器从 conan conf 取（CI 上 $CC 为空），配置路径失效时
        # 回退到 PATH/~/usr/local/bin 的真实编译器并打印诊断。
        cc = self._resolve_cc()
        self.output.info("HMBS diag resolved cc=%s" % cc)

        # libxml2 旗标显式取自 Conan 依赖包目录，不用宿主机 xml2-config
        #（juise/3.0.0 同型做法；conan 包内 xml2-config 硬编码构建期
        # prefix，直接调用会污染 -I/-L）。
        libxml2 = self.dependencies["libxml2"].package_folder
        xml2_cflags = "-I%s" % os.path.join(libxml2, "include", "libxml2")
        # libxml2/2.15.3.1 默认 shared、无三方 requirements（zlib/lzma 均 OFF，
        # iconv 走 musl 内建），system_libs 仅 m；链接只需 -lxml2 -lm。
        xml2_libs = "-L%s -lxml2 -lm" % os.path.join(libxml2, "lib")

        src = str(self.source_folder)
        # R9: -j1。上游 Makefile 经补丁支持 CC / CFLAGS / XML2_* 变量覆盖
        #（make 命令行变量优先级高于 Makefile 内定义）。
        # CI #95891 差异化处理：该构建在单文件 -j1 编译时报
        # `clang-15: posix_spawn failed: Resource temporarily unavailable`
        #（EAGAIN，Worker 进程资源压力），无任何语法/符号/缺头文件报错。
        # 前三轮零改动等待重试复用同一构建号未产生新流水线，故本轮改用
        # 瞬时派生失败退避重试：仅当本次 make 日志含 posix_spawn /
        # Resource temporarily unavailable 签名时重试（最多 3 次，
        # 30s/60s 退避），真实编译错误直接抛出不重试、不掩盖。
        make_cmd = ('make CC="%s" XML2_CFLAGS="%s" XML2_LIBS="%s" -j1'
                    % (cc, xml2_cflags, xml2_libs))
        for attempt in (1, 2, 3):
            attempt_log = "hmbs_make_attempt_%d.log" % attempt
            attempt_log_abs = os.path.join(src, attempt_log)
            try:
                self.run('sh -c \'%s > "%s" 2>&1; rc=$?; cat "%s"; exit $rc\''
                         % (make_cmd, attempt_log_abs, attempt_log_abs),
                         cwd=src, env="conanbuild")
                break
            except ConanException:
                content = ""
                try:
                    with open(attempt_log_abs, encoding="utf-8",
                              errors="replace") as f:
                        content = f.read()
                except Exception:
                    content = ""
                transient = ("Resource temporarily unavailable" in content
                             or "posix_spawn failed" in content)
                if not transient or attempt >= 3:
                    raise
                self.output.warning(
                    "HMBS transient build-spawn failure "
                    "(attempt %d/3, posix_spawn/EAGAIN), "
                    "backing off before retry" % attempt)
                time.sleep(30 * attempt)
        for stale in ("hmbs_make_attempt_1.log",
                      "hmbs_make_attempt_2.log",
                      "hmbs_make_attempt_3.log"):
            try:
                os.remove(os.path.join(src, stale))
            except OSError:
                pass

    def package(self):
        src = str(self.source_folder)
        pkg = str(self.package_folder)
        copy(self, "rarcrack", src=src, dst=os.path.join(pkg, "bin"))
        copy(self, "LICENSE", src=src, dst=os.path.join(pkg, "licenses"))
        # 上游 install 把文档装到 share/doc/rarcrack，本配方等价处理。
        copy(self, "README.md", src=src,
             dst=os.path.join(pkg, "share", "doc", "rarcrack"))
        copy(self, "CHANGELOG", src=src,
             dst=os.path.join(pkg, "share", "doc", "rarcrack"))

    def package_info(self):
        # 命令行工具：为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
