#!/usr/bin/env python3
"""Kamailio websocket 模块（websocket.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-tls/6.0.6、kamailio-xml/6.0.6 同族先例）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 websocket 模块
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=websocket        → 生成 src/config.mak（探测 aarch64-unknown-linux-ohos）
  make modules modules=modules/websocket    → 产出 src/modules/websocket/websocket.so

平台差异（详见同目录 notes.md）：
1) 平台探测宏：Makefile.defs 只处理 linux/solaris/freebsd/darwin 等分支，OS=harmonyos
   不注入任何 HAVE_* 探测宏，core 头直接 #error。故经 extra_defs 注入 linux 分支
   等价宏集（宏集与 kamailio-tls/xml 同族先例一致，均对照 OHOS SDK sysroot 实证）。
2) OpenSSL 探测：模块 Makefile 在 CROSS_COMPILE 为空时用构建机 pkg-config 探测
   libssl/libcrypto；显式传 SSL_BUILDER=/CRYPTO_BUILDER=（make 命令行变量优先于
   Makefile 内部赋值）钉死 LOCALBASE 回退分支，LOCALBASE 指向 conan openssl 包目录，
   构建机（含 CI 机器）系统 OpenSSL 无法劫持探测结果。
3) libunistring 探测：EMBEDDED_UTF8_DECODE=0（上游默认）时
   DEFS += -I$(LOCALBASE)/include；LIBS += -L$(LOCALBASE)/lib -lunistring。
   经 CPATH/LIBRARY_PATH 注入 conan libunistring 包目录，构建机系统 libunistring
   不会混入（链接器搜索顺序：-L 显式目录 + LIBRARY_PATH 注入目录优先）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏。
# 与 kamailio-tls/xml 同族先例一致（对照 OHOS SDK musl 语义 sysroot 实证存在）：
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


class KamailioWebsocketConan(ConanFile):
    name = "kamailio-websocket"
    version = "6.0.6"
    description = ("Kamailio websocket module: RFC 6455 WebSocket transport for SIP "
                   "(WS/WSS) including binary frame parsing and TLS handshake")
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
        self.requires("openssl/3.5.7")
        self.requires("libunistring/1.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        openssl = self.dependencies["openssl"].package_folder
        unistr = self.dependencies["libunistring"].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # R33：编译器与头/库搜索路径全部显式注入，不使用未定义的 shell 变量。
        # CPATH 覆盖 openssl 头（include/openssl）与 libunistring 头（include/unistr.h 等）；
        # LIBRARY_PATH 覆盖两个静态库目录；LOCALBASE 指向 openssl 包满足
        # Makefile 的 LOCALBASE 回退分支（-L$(LOCALBASE)/lib -lssl -lcrypto）。
        env = Environment()
        env.define("CC", cc)
        env.define("CPATH", f"{openssl}/include:{unistr}/include")
        env.define("LIBRARY_PATH", f"{openssl}/lib:{unistr}/lib")

        make_vars = (f"LOCALBASE={openssl} SSL_BUILDER= CRYPTO_BUILDER= "
                     f"extra_defs='{' '.join(PLATFORM_DEFS)}'")
        with env.vars(self).apply():
            self.run(f"make cfg include_modules=websocket {make_vars}", cwd=self.source_folder)
            self.run(f"make modules modules=modules/websocket -j1 {make_vars}",
                     cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "websocket")
        dst_dir = os.path.join(self.package_folder, "lib", "kamailio", "modules")
        copy(self, "websocket.so", src=module_dir, dst=dst_dir)

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
