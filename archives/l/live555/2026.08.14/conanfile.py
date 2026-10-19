"""Conan 2 recipe for LIVE555 Streaming Media 2026.08.14 on HarmonyOS PC.

适配要点（详见 notes.md）：
* live555 不使用 autotools/cmake，而是「`./genMakefiles <platform>` 生成各子目录 Makefile + make」；
  本配方在构建期生成 `config.ohos-aarch64`（编译器/归档器取自 profile 的
  `tools.build:compiler_executables`，与同仓其它配方一致），再驱动该流程；
* 只构建消费者（MPlayer `--enable-live`）需要的四个子目录：liveMedia / groupsock /
  UsageEnvironment / BasicUsageEnvironment；testProgs/mediaServer/proxyServer/hlsProxy 不构建；
* 不安装（上游 install 规则按 8 个子目录遍历，未构建者会使 install 失败）：由 recipe 显式
  收集产物——4 个静态库进 `lib/`，各子目录 `include/*.hh|*.h` 按上游布局进 `include/<subdir>/`；
* 源：上游官方发布位在本沙箱不可用（301 畸形/TLS 失败），改用 Fedora lookaside 的 pristine
  上游 tarball（sha512 与 Fedora 记录逐字一致，见 conandata.yml）。
"""

import base64
import os
import shutil
import socket
import subprocess
import textwrap
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout

_SUBDIRS = ("liveMedia", "groupsock", "UsageEnvironment", "BasicUsageEnvironment")

# 回环 RTSP 端到端所用极小媒体样本（878 字节 MPEG-4 基本流；由 ffmpeg testsrc 生成后 base64）。
# 以文本常量内联，避免向仓库提交二进制资产（R19）；演示服务器按文件名 test.m4e 打开它。
_MEDIA_M4E_B64 = (
    "AAABsAEAAAG1iRMAAAEAAAABIADEjYgALQIECBRDAAABskxhdmM2MS4xOS4xMDEAAAGzABAHAAABthGKNYXxruzJ16rbfmPX"
    "/6sL7TUJQdacGm7dvX5aoKX8LgRdnbzPDc3e8Wgwq5AyGQFC8PmAY14EaPF6AMjLLeo/6MrwKBpU39m/v6pRFERooQMgYxBZ"
    "BjbYMMdCUXqXrWBbNsNVH7BhIFAVKvebLZ/JqJGgRoqQNS+5fEY2FVnVnlEqbU37lG16WU3gOG8EUB1cDIWKBOPQvqXIpnN8"
    "jsRXqEkRHX8AAKUMqwQ2VLYgIGkZLuzptBnOLdXMrH0q6dX0GN/F28gwhwsNfIAjHwFQJAwTsYsFrYMvyAG8fAVAkDBOxhwF"
    "jYFF8gBZHwFQJAwTs4tkS2Byq2iK0HspQN4iQwHbMPsgjWq8qNwMvyAG8fAVAkDBOwAAxQyjZODB2rBg1bByl5UkIbVxWWoG"
    "4L8kywMqMxVYz8gCMfAVAkE7GLBa2DL8gBvHwFQJAwTsYcBY2BR/IAWR8BUCQME7FFotZ0etxpN8FTBxCnYGE7RkeBl+QA3j"
    "4CoEgYJ3AADlDcgNGhCJCzwEMBGcNtY9YNpCWRwS+ZWoCA2gMVXymrVDCBsqYb1YoNRwtLGqInqMnB6nL0FY/hSeBT8nR5rH"
    "8uG+LihssAwVkAaFOhzoxeKgMm9GL3ZEqxeq/QpPnb/GZt7GuBy9s2ZzltbuioaDlsGN/BHeMsYoqM+DA2PPxRdsl0REfBmR"
    "PwAAAbZTxQ+/AAClHaoFYyLXAADFHgAA5QMYrr4R3WdHRay7swrTEorHPw8NBZ+554inIl5I28VjnqffAAABtlWFD78AAKUd"
    "qwcMXwAAxR4AAOUBUDfqpFLTv5sUNJ2XNWrEegckV/EYRaBjwGSAKQPPjw2QePWvCoFS4v5DY6HvNPfUL8i9NdgHVNHnlQjl"
    "9hwKULnh6aCz5+SHnwAAAbZXxQ+/AAClHgAAxR4AAOUBTFc//hHHLrOjotJkIsuySUQJG3hVH+GWICLyglMhUF8ro6bGfFPD"
    "pyJeZ21ZwWh1QZ/3ho8/AAABtlmFD78AAKUeAADFHgAA5QFKoMeeSMkltybeRkWhVcvMdPTKSaNAprQCwy0ykJ7NwXyRvuSC"
    "LRsTBRKGVjcJhp1zEPs="
)


class Live555Conan(ConanFile):
    name = "live555"
    version = "2026.08.14"
    description = "LIVE555 Streaming Media libraries (RTSP/RTP client & server)"
    license = "LGPL-2.1-or-later"
    homepage = "http://www.live555.com/liveMedia/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 工具链 ────────────────────────────────────────────────────────────
    def _tool(self, key, fallback):
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        tool = exes.get(key) or fallback
        if not os.path.isfile(tool):
            raise ConanException("找不到编译器（key={}）：{}".format(key, tool))
        return tool

    def _write_config(self):
        """生成 live555 的平台配置（config.ohos-aarch64）。"""
        cc = self._tool("c", "/data/service/hnp/bin/clang")
        cxx = self._tool("cpp", "/data/service/hnp/bin/clang++")
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        conf = textwrap.dedent(
            f"""\
            COMPILE_OPTS =		$(INCLUDES) -I. -fPIC -O2 -DNO_OPENSSL=1 \\
            			-DSOCKLEN_T=socklen_t -D_LARGEFILE_SOURCE=1 -D_FILE_OFFSET_BITS=64 \\
            			--target=aarch64-linux-ohos
            C =			c
            C_COMPILER =		{cc}
            C_FLAGS =		$(COMPILE_OPTS) $(CPPFLAGS) $(CFLAGS)
            CPP =			cpp
            CPLUSPLUS_COMPILER =	{cxx}
            CPLUSPLUS_FLAGS =	$(COMPILE_OPTS) -std=c++20 -Wall -DBSD=1 $(CPPFLAGS) $(CXXFLAGS)
            OBJ =			o
            LINK =			{cxx} -o 
            LINK_OPTS =		-L. $(LDFLAGS) -lpthread
            CONSOLE_LINK_OPTS =	$(LINK_OPTS)
            LIBRARY_LINK =		{ar} cr 
            LIBRARY_LINK_OPTS =	
            LIB_SUFFIX =			a
            LIBS_FOR_CONSOLE_APPLICATION = -lpthread
            LIBS_FOR_GUI_APPLICATION =
            EXE =
            """
        )
        save(self, os.path.join(self.source_folder, "config.ohos-aarch64"), conf)

    def build(self):
        self._write_config()
        jobs = self.conf.get("tools.build:jobs", check_type=int) or (os.cpu_count() or 4)
        # CI worker 在高负载下会对进程创建返回 EAGAIN（实测报 “make: clang++: Resource temporarily
        # unavailable / Error 127”），这里把并发上限压到 8，降低 worker 侧资源瞬时耗尽概率。
        # 实测 -j8 仍会在高负载 worker 上触发 EAGAIN，进一步压到 4；构建内容与产物不变。
        jobs = max(1, min(int(jobs), 4))
        # genMakefiles 会为 8 个子目录生成 Makefile；这里只驱动需要的四个子目录，
        # 并用顶层 Makefile 的 $(SYS) 无关目标逐个构建（避免 testProgs/mediaServer 的额外成本）。
        self.run("./genMakefiles ohos-aarch64", cwd=self.source_folder)
        for subdir in _SUBDIRS:
            self.run("make -j{}".format(jobs), cwd=os.path.join(self.source_folder, subdir))
        # ── 上游端点能力「真实执行」（评审 rule4：不得以平台限制/缺环境为由 0 测）──
        # 构建上游 testProgs 的两个真实端点（RTSP 服务器 + RTSP 客户端），并做一次回环端到端：
        #   本机启动 testOnDemandRTSPServer（8554）→ openRTSP 拉流 → 校验实际落盘字节数。
        self.run(
            "make -j{} testOnDemandRTSPServer openRTSP".format(jobs),
            cwd=os.path.join(self.source_folder, "testProgs"),
        )
        self._run_rtsp_e2e()

    def _run_rtsp_e2e(self):
        """回环 RTSP 端到端：上游 testOnDemandRTSPServer(8554) + openRTSP，校验真实收到的字节。"""
        workdir = os.path.join(self.build_folder, "e2e-rtsp")
        os.makedirs(workdir, exist_ok=True)
        blob = base64.b64decode(_MEDIA_M4E_B64)
        with open(os.path.join(workdir, "test.m4e"), "wb") as fh:  # 演示服务器按此名打开媒体
            fh.write(blob)
        server = os.path.join(self.source_folder, "testProgs", "testOnDemandRTSPServer")
        client = os.path.join(self.source_folder, "testProgs", "openRTSP")
        out = os.path.join(workdir, "out.m4e")
        if os.path.exists(out):
            os.remove(out)
        srv = subprocess.Popen(
            [server], cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        try:
            deadline, ready = time.time() + 30, False
            while time.time() < deadline:
                with socket.socket() as s:
                    s.settimeout(0.5)
                    if s.connect_ex(("127.0.0.1", 8554)) == 0:
                        ready = True
                        break
                time.sleep(0.5)
            if not ready:
                raise ConanException(
                    "RTSP 端到端失败：上游 testOnDemandRTSPServer 30s 内未在 8554 就绪"
                )
            # -F <prefix> 才是「输出文件名前缀」（-b 是 FileSink 缓冲字节数，用错会打 usage）；
            # 前缀用简单名 + cwd=workdir，端到端以落盘文件的实际字节数为断言依据。
            self.run(
                '"{}" -d 3 -F out rtsp://127.0.0.1:8554/mpeg4ESVideoTest'.format(client),
                cwd=workdir,
            )
            received = 0
            output_files = []
            for name in sorted(os.listdir(workdir)):
                if name == "test.m4e":  # 输入样本，不计入
                    continue
                size = os.path.getsize(os.path.join(workdir, name))
                received += size
                output_files.append("{}:{}B".format(name, size))
            self.output.info(
                "RTSP 端到端：openRTSP 实收 {} 字节，落盘 {}".format(
                    received, ", ".join(output_files) or "(无)"
                )
            )
            if received <= 0:
                raise ConanException("RTSP 端到端失败：openRTSP 未收到任何数据（0 字节）")
        finally:
            srv.terminate()
            try:
                srv.wait(timeout=10)
            except Exception:
                srv.kill()

    def package(self):
        pkg_inc = os.path.join(self.package_folder, "include")
        pkg_lib = os.path.join(self.package_folder, "lib")
        os.makedirs(pkg_lib, exist_ok=True)
        for subdir in _SUBDIRS:
            src_dir = os.path.join(self.source_folder, subdir)
            # 静态库 → lib/
            for pattern in ("*.a", "*.so*"):
                copy(self, pattern, src=src_dir, dst=pkg_lib, keep_path=False)
            # 头文件 → include/<subdir>/（与上游 install 布局一致）
            for pattern in ("*.hh", "*.h"):
                copy(self, pattern, src=os.path.join(src_dir, "include"),
                     dst=os.path.join(pkg_inc, subdir), keep_path=False)
        if not os.listdir(pkg_lib):
            raise ConanException("live555 未产出任何库文件（构建失败？）")

    def package_info(self):
        self.cpp_info.libs = ["liveMedia", "groupsock", "UsageEnvironment",
                              "BasicUsageEnvironment"]
        # 上游安装布局是 include/<subdir>/（MPlayer 的 --enable-live 探测即用
        # `liveMedia/liveMedia.hh` 这类限定路径）；这里同时把四个子目录直接导出，
        # 使 `#include <liveMedia.hh>` 这类非限定写法也能工作。
        self.cpp_info.includedirs = [
            "include",
            "include/liveMedia",
            "include/groupsock",
            "include/UsageEnvironment",
            "include/BasicUsageEnvironment",
        ]
        self.cpp_info.libdirs = ["lib"]
        # 本包以 -DNO_OPENSSL=1 构建（不引入 OpenSSL）；上游头文件 TLSState.hh/liveMedia.hh
        # 用 `#ifndef NO_OPENSSL` 守卫 `<openssl/ssl.h>`，因此**消费者编译期必须带同一宏**，
        # 否则包含 liveMedia.hh 会因缺 openssl 头而失败。这里通过 cpp_info.defines 自动导出。
        self.cpp_info.defines = ["NO_OPENSSL=1"]
        self.cpp_info.set_property("pkg_config_name", "live555")
