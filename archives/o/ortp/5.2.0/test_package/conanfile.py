#!/usr/bin/env python3
"""Conan test_package for ortp 5.2.0 — 消费者视角验证（L1）。

C 消费者（test_ortp.c，随 exports_sources 交付）真实调用上游公开 API：
  - rtp_session_new(RTP_SESSION_RECVONLY) / rtp_session_destroy
  - rtp_session_set_scheduling_mode / set_blocking_mode
  - rtp_session_set_local_addr（127.0.0.1 本地端点绑定）
原生构建必须编译、链接并运行；原生消费者运行失败即测试失败。
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class OrtpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test_ortp.c"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ortp 的公开头（ortp/logging.h）直接包含 bctoolbox/logging.h，
        # bctoolbox 属于公开链接接口，消费侧显式声明以获取其 includedirs
        self.requires("bctoolbox/5.3.115")

    def generate(self):
        pass

    def build(self):
        inc = []
        libdirs = []
        for _ref, d in self.dependencies.items():
            inc += ["-I" + p for p in d.cpp_info.includedirs]
            libdirs += list(d.cpp_info.libdirs)
            for _cn, comp in d.cpp_info.components.items():
                libdirs += list(comp.libdirs)
        link = (["-lortp", "-lbctoolbox"]
                + ["-L" + p for p in dict.fromkeys(libdirs)])
        cc = os.environ.get("CC", "clang")
        src = os.path.join(self.source_folder, "test_ortp.c")
        self.run(f"{cc} -std=gnu11 {src} -o test_ortp_probe "
                 f"{' '.join(inc)} {' '.join(link)}")

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building/cannot-run: compile+link verified")
            return
        libdirs = []
        for _ref, d in self.dependencies.items():
            if not d.package_folder:
                continue
            for info in [d.cpp_info, *d.cpp_info.components.values()]:
                libdirs.extend(os.path.join(d.package_folder, path)
                               for path in info.libdirs if path)
        ldpath = ":".join(dict.fromkeys(libdirs))
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not bash:
            raise RuntimeError("bash is required to run the oRTP consumer test")
        binary = os.path.join(self.build_folder, "test_ortp_probe")
        script = ("export LD_LIBRARY_PATH=" + shlex.quote(ldpath)
                  + '"${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"; exec ' + shlex.quote(binary))
        self.run(shlex.quote(bash) + " -c " + shlex.quote(script), env="conanrun")
