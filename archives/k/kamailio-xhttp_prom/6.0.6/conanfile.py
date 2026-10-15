#!/usr/bin/env python3
"""Kamailio xhttp_prom 模块（xhttp_prom.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-tls/6.0.6 同族先例）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 xhttp_prom 模块
  - 不依赖 kamailio 本体包：模块 .so 由 kamailio 运行时 loadmodule 加载，
    其引用的 kamailio 核心符号（_pkg_root/parse_params/fixup_* 等）由主程序
    在运行期提供，不在链接期解析

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=xhttp_prom        → 生成 src/config.mak（识别 aarch64-unknown-linux-ohos）
  make modules modules=modules/xhttp_prom    → 产出 src/modules/xhttp_prom/xhttp_prom.so

平台差异（详见同目录 notes.md）：
1) 平台探测宏：Makefile.defs 只处理 linux/solaris/freebsd/darwin 等分支，OS=harmonyos
   不注入任何 HAVE_* 探测宏，而模块含 core 头（sr_module.h → resolve.h/sched_yield.h
   等）会因宏缺失直接 #error。故经 make 命令行 `extra_defs` 注入 linux 分支等价宏集，
   每个宏的符号均已对照 OHOS SDK（musl 语义）sysroot 头文件实证存在。
2) 本模块 0 外部依赖：上游 Makefile 的 LIBS 为空、README 声明无外部依赖，模块自带的
   Prometheus 指标实现（prom.c/prom_metric.c）随模块编译进 .so。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏。
# 每个宏的符号均已对照 OHOS SDK（musl 语义）sysroot 头文件实证存在：
#   gethostbyname2 (netdb.h, _GNU_SOURCE 守卫内)、sched_yield/sched_setscheduler (sched.h)、
#   MSG_NOSIGNAL/msg_control (sys/socket.h)、timegm (time.h)、ip_mreqn (netinet/in.h)、
#   alloca.h。HAVE_UNION_SEMUN 不注入：musl sys/sem.h 不导出 union semun，core lock_ops.h
#   在宏未定义时自带条件定义，注入反而与之冲突。
PLATFORM_DEFS = (
    "-D_GNU_SOURCE",
    "-DHAVE_GETHOSTBYNAME2",
    "-DHAVE_SCHED_YIELD",
    "-DHAVE_MSG_NOSIGNAL",
    "-DHAVE_MSGHDR_MSG_CONTROL",
    "-DHAVE_ALLOCA_H",
    "-DHAVE_TIMEGM",
    "-DHAVE_SCHED_SETSCHEDULER",
    "-DHAVE_IP_MREQN",
)


class KamailioXhttpPromConan(ConanFile):
    name = "kamailio-xhttp_prom"
    version = "6.0.6"
    description = ("Kamailio xhttp_prom module: Prometheus metrics exporter for the "
                   "xhttp (HTTP/WebSocket) server interface")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # 上游模块 0 外部依赖（Makefile 的 LIBS 为空，README 明示无外部依赖）。
        # 刻意不声明 kamailio 本体依赖：模块的目标是作为插件被 kamailio 运行时
        # loadmodule 加载，核心符号在运行期由主程序导出。
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33：编译器取自 Conan 配置，不使用未定义的 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        env = Environment()
        env.define("CC", cc)

        make_vars = f"extra_defs='{' '.join(PLATFORM_DEFS)}'"
        with env.vars(self).apply():
            self.run(f"make cfg include_modules=xhttp_prom {make_vars}",
                     cwd=self.source_folder)
            self.run(f"make modules modules=modules/xhttp_prom -j1 {make_vars}",
                     cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "xhttp_prom")
        dst_dir = os.path.join(self.package_folder, "lib", "kamailio", "modules")
        copy(self, "xhttp_prom.so", src=module_dir, dst=dst_dir)
        # 上游随模块分发的说明文档（内容与源码包内 README 逐字一致，不做改写）
        copy(self, "README", src=module_dir,
             dst=os.path.join(self.package_folder, "share", "doc", "kamailio-xhttp_prom"))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
